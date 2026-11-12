"""
api/index.py — Backend FastAPI Serverless para Vercel.

Expone el motor completo de procesamiento DSP de imágenes (Fases 1 a 5) en memoria,
sin escribir en disco del servidor y respetando los límites de tiempo/tamaño de Vercel.
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import tempfile
from typing import Any, Dict, List, Optional

# Evitar errores de escritura de caché de Matplotlib en entorno serverless read-only
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

import matplotlib
matplotlib.use("Agg")

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dsp_img.core.analyzer import analyze_sampling_frequency, summarize_sampling_metrics
from dsp_img.core.audio_wav import samples_to_wav_bytes
from dsp_img.core.codec import METHOD_LOSSLESS, METHOD_LOSSY_DCT, ImageCompressor
from dsp_img.core.contracts import ModulatedWaveform
from dsp_img.core.image_io import image_to_png_bytes, load_image
from dsp_img.core.primitives import compute_spectrum, unpack_bits
from dsp_img.core.quantization import format_digital_preview, quantize_image
from dsp_img.core.red_filter import isolate_largest_red_region
from dsp_img.core.sampling_nqs import sample_image_nqs
from dsp_img.demodulation import DigitalPassbandDemodulator
from dsp_img.exchange import package_for_peer_bytes, receive_from_peer_bytes
from dsp_img.modulation import SUPPORTED_DIGITAL_SCHEMES
from dsp_img.reconstruction import SignalReconstructor, evaluate_audio_fidelity

app = FastAPI(
    title="Procesador DSP de Imágenes API",
    version="1.0.0",
    description="API Serverless para análisis, compresión, modulación audible, demodulación y reconstrucción PNG/SVG.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _b64_data_url(raw: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _downsample_series(arr: np.ndarray, max_points: int = 240) -> List[float]:
    """Reduce un arreglo 1D a `max_points` valores redondeados para gráficas web ágiles."""
    flat = np.asarray(arr, dtype=np.float64).ravel()
    if len(flat) == 0:
        return []
    if len(flat) <= max_points:
        return [round(float(v), 4) for v in flat]
    idx = np.linspace(0, len(flat) - 1, max_points, dtype=int)
    return [round(float(flat[i]), 4) for i in idx]


def _default_selfie_bytes() -> bytes:
    path = ROOT / "data" / "input" / "selfie_dsp.jpeg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No se encontró la fotografía base selfie_dsp.jpeg.")
    return path.read_bytes()


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": "1.0.0",
        "supported_schemes": list(SUPPORTED_DIGITAL_SCHEMES),
        "compression_methods": [METHOD_LOSSY_DCT, METHOD_LOSSLESS],
    }


@app.get("/api/demo")
def get_precomputed_demo() -> Dict[str, Any]:
    demo_json = ROOT / "public" / "demo" / "datos_demo.json"
    if not demo_json.exists():
        raise HTTPException(
            status_code=404,
            detail="datos_demo.json no encontrado. Ejecute `python build_web_assets.py`.",
        )
    return json.loads(demo_json.read_text(encoding="utf-8"))


@app.post("/api/tx/pipeline")
async def run_tx_pipeline(
    file: Optional[UploadFile] = File(default=None),
    scheme: str = Form(default="BFSK"),
    compression_method: str = Form(default=METHOD_LOSSY_DCT),
    bits_per_sample: int = Form(default=4),
    quality: int = Form(default=82),
    tx_max_dim: int = Form(default=72),
    apply_red_filter: bool = Form(default=True),
    nqs_factor: int = Form(default=8),
    snr_db: Optional[float] = Form(default=None),
) -> Dict[str, Any]:
    """
    Ejecuta en vivo las Fases 1 -> 5 sobre una foto subida o la selfie oficial:
    Filtro Rojo Mayor Área, Muestreo NQS, Digitalización, Compresión, Modulación WAV y Loopback RX.
    """
    try:
        raw_bytes = await file.read() if file is not None else _default_selfie_bytes()
        if not raw_bytes:
            raw_bytes = _default_selfie_bytes()

        tx_dim = int(np.clip(tx_max_dim, 32, 96))
        bits = int(np.clip(bits_per_sample, 1, 8))
        qual = int(np.clip(quality, 15, 98))
        nqs_m = int(np.clip(nqs_factor, 2, 16))

        # Nivel 1: Análisis visual ágil (hasta 480 px) para Fase 1 + NQS
        preview_img = load_image(raw_bytes, max_dim=480)
        splash_res = isolate_largest_red_region(preview_img)
        sampling_report = analyze_sampling_frequency(preview_img)
        sampling_summary = summarize_sampling_metrics(preview_img, sampling_report)

        nqs_img = sample_image_nqs(splash_res.filtered, spatial_factor=nqs_m, apply_antialias=False)
        q_img, q_stream = quantize_image(
            load_image(raw_bytes, max_dim=160), bits_per_sample=bits
        )
        digital_preview = format_digital_preview(q_stream, num_bytes=16)

        # Nivel 2: Paquete comprimido + Modulación audible acotada para Vercel (<4.5 MB respuesta)
        tx_bundle = package_for_peer_bytes(
            raw_bytes,
            scheme=scheme,
            compression_method=compression_method,
            quality=qual,
            bits_per_sample=bits,
            max_dim=tx_dim,
            apply_red_filter=apply_red_filter,
        )
        src_tx = tx_bundle["source_image"]
        pkt = tx_bundle["packet"]
        wave = tx_bundle["waveform"]
        tx_bits = unpack_bits(pkt.wire_bytes)

        # Simular ruido AWGN opcional antes de demodulación
        rx_samples = wave.samples.copy()
        if snr_db is not None and np.isfinite(snr_db):
            rng = np.random.default_rng(42)
            p_sig = float(np.mean(rx_samples.astype(np.float64) ** 2))
            p_noise = p_sig / (10.0 ** (float(snr_db) / 10.0))
            rx_samples = (rx_samples + rng.normal(0.0, np.sqrt(p_noise), len(rx_samples))).astype(
                np.float32
            )

        rx_wave = ModulatedWaveform(
            samples=rx_samples,
            sampling_rate_hz=wave.sampling_rate_hz,
            carrier_freq_hz=wave.carrier_freq_hz,
            modulation_type=wave.modulation_type,
            is_digital=True,
            metadata=wave.metadata,
        )
        demod = DigitalPassbandDemodulator(
            scheme=wave.modulation_type,
            sampling_rate_hz=wave.sampling_rate_hz,
            samples_per_symbol=int(wave.metadata.get("samples_per_symbol", 32)),
            carrier_freq_hz=wave.carrier_freq_hz,
            fsk_freqs_hz=tuple(wave.metadata["fsk_freqs_hz"])
            if "fsk_freqs_hz" in wave.metadata
            else None,
        )
        demod_res = demod.demodulate(rx_wave, reference_bits=tx_bits, has_framing=True, auto_sync=True)

        reconstructor = SignalReconstructor(dac_method="sinc")
        orig_audio = reconstructor.image_to_audible_scanline(src_tx, sample_rate_hz=16000, duration_s=1.8)

        if demod_res.crc_valid:
            rec_img = reconstructor.reconstruct_from_demodulated(demod_res, compressor=ImageCompressor())
            rec_audio = reconstructor.image_to_audible_scanline(rec_img, sample_rate_hz=16000, duration_s=1.8)
            img_metrics = reconstructor.evaluate(
                src_tx, rec_img, compression_ratio=pkt.compression_ratio
            )
            audio_metrics = evaluate_audio_fidelity(orig_audio, rec_audio)
            rec_png_url = _b64_data_url(image_to_png_bytes(rec_img), "image/png")
            from dsp_img.reconstruction.svg_vectorizer import image_to_svg_string

            rec_svg_text = image_to_svg_string(rec_img, color_levels=16)
            rec_wav_url = _b64_data_url(samples_to_wav_bytes(rec_audio, 16000), "audio/wav")
            metrics_out = {
                "psnr_db": round(img_metrics.psnr_db, 2) if np.isfinite(img_metrics.psnr_db) else 99.9,
                "ssim": round(img_metrics.ssim, 4),
                "pearson_corr": round(img_metrics.pearson_corr, 4),
                "mse": round(img_metrics.mse, 6),
                "audio_snr_db": round(audio_metrics["snr_db"], 2),
                "audio_pearson_corr": round(audio_metrics["pearson_corr"], 4),
            }
        else:
            rec_png_url = None
            rec_svg_text = None
            rec_wav_url = None
            metrics_out = None

        # Series cortas para gráficas interactivas en el navegador
        lead = int(wave.metadata.get("lead_silence_samples", 0))
        mod_zoom = wave.samples[lead : lead + min(720, len(wave.samples) - lead)]
        freqs, _, mag_db = compute_spectrum(
            wave.samples[lead : min(len(wave.samples), lead + 16384)],
            sample_rate=wave.sampling_rate_hz,
        )
        spec_step = max(1, len(freqs) // 180)
        max_f_mask = freqs <= 6000.0

        # Reducir frecuencia de vista previa auditiva demodulada a 16 kHz para mantener payload < 4.5 MB
        demod_preview_audio = demod_res.recovered_signal_1d[::3]
        demod_preview_fs = max(8000, demod_res.sampling_rate_hz // 3)

        return {
            "fase1": {
                "sampling": sampling_summary,
                "red_filter": {
                    "num_components": splash_res.num_red_components,
                    "largest_area_px": splash_res.largest_area_px,
                    "largest_area_percent": round(splash_res.largest_area_ratio * 100.0, 2),
                },
                "original_png": _b64_data_url(image_to_png_bytes(preview_img), "image/png"),
                "red_splash_png": _b64_data_url(image_to_png_bytes(splash_res.filtered), "image/png"),
            },
            "fase2": {
                "nqs_aliased_png": _b64_data_url(image_to_png_bytes(nqs_img), "image/png"),
                "quantized_png": _b64_data_url(image_to_png_bytes(q_img), "image/png"),
                "digital_stream": digital_preview,
                "compression": {
                    "method": pkt.method,
                    "raw_bytes": pkt.raw_bytes_count,
                    "compressed_bytes": pkt.compressed_bytes_count,
                    "compression_ratio": round(pkt.compression_ratio, 3),
                    "savings_percent": round(pkt.savings_percent, 2),
                    "crc32_hex": f"0x{pkt.crc32:08X}",
                },
            },
            "fase3_4": {
                "manifest": tx_bundle["manifest"],
                "ber": demod_res.bit_error_rate,
                "crc_valid": demod_res.crc_valid,
                "sync_offset_samples": demod_res.sync_offset_samples,
                "first_bits": [int(b) for b in tx_bits[:48]],
                "rx_bits": [int(b) for b in demod_res.detected_bits[:48]]
                if demod_res.detected_bits is not None
                else [],
                "modulated_zoom": _downsample_series(mod_zoom, 200),
                "spectrum_freqs": [round(float(f), 1) for f in freqs[max_f_mask][::spec_step]],
                "spectrum_db": [round(float(m), 2) for m in mag_db[max_f_mask][::spec_step]],
                "constellation_iq": demod_res.metadata.get("rx_constellation_iq", [])[:128],
                "modulated_wav_url": _b64_data_url(tx_bundle["wav_bytes"], "audio/wav"),
                "demodulated_wav_url": _b64_data_url(
                    samples_to_wav_bytes(demod_preview_audio, demod_preview_fs),
                    "audio/wav",
                ),
            },
            "fase5": {
                "source_tx_png": _b64_data_url(image_to_png_bytes(src_tx), "image/png"),
                "reconstructed_png": rec_png_url,
                "reconstructed_svg": rec_svg_text,
                "orig_audio_wav_url": _b64_data_url(samples_to_wav_bytes(orig_audio, 16000), "audio/wav"),
                "reconstructed_audio_wav_url": rec_wav_url,
                "metrics": metrics_out,
                "dspimg_b64": base64.b64encode(pkt.wire_bytes).decode("ascii"),
                "peer_zip_b64": base64.b64encode(tx_bundle["zip_bytes"]).decode("ascii"),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error procesando la señal: {exc}") from exc


@app.post("/api/rx/demodulate")
async def demodulate_peer_upload(
    file: UploadFile = File(...),
    scheme: str = Form(default="BFSK"),
) -> Dict[str, Any]:
    """
    Modo Receptor (Compañero): recibe un archivo `.wav`, `.dspimg` o `.zip`,
    lo demodula, verifica CRC32, descomprime y devuelve PNG, SVG vectorial y audio DAC.
    """
    try:
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="El archivo recibido está vacío.")

        res = receive_from_peer_bytes(
            raw, filename=file.filename or "recibido.wav", scheme=scheme
        )
        demod_res = res["demodulated_result"]

        return {
            "summary": res["summary"],
            "reconstructed_png": _b64_data_url(res["png_bytes"], "image/png"),
            "reconstructed_svg": res["svg_text"],
            "reconstructed_audio_wav_url": _b64_data_url(res["wav_audio_bytes"], "audio/wav"),
            "constellation_iq": demod_res.metadata.get("rx_constellation_iq", [])[:128]
            if demod_res is not None
            else [],
            "demodulated_zoom": _downsample_series(demod_res.recovered_signal_1d[:1200], 200)
            if demod_res is not None
            else [],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error al demodular/descomprimir: {exc}") from exc
