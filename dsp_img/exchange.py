"""
Flujo de intercambio entre compañeros (TX / RX) para comprimir, modular, enviar
y demodular/reconstruir señales de imagen a partir de `.wav`, `.dspimg` o `.zip`.

Diseñado en memoria y disco para ser reutilizado directamente tanto por la CLI
local como por los endpoints serverless de la aplicación web en Vercel (Fase 6).
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from typing import Any, Dict, Optional, Tuple
import numpy as np

from .core.audio_wav import samples_to_wav_bytes, save_wav, wav_bytes_to_samples
from .core.codec import METHOD_LOSSLESS, METHOD_LOSSY_DCT, ImageCompressor
from .core.contracts import DemodulatedResult, ImageSignal, ModulatedWaveform
from .core.image_io import image_to_png_bytes, load_image, save_image_png
from .core.red_filter import isolate_largest_red_region
from .demodulation import DigitalPassbandDemodulator
from .modulation import DigitalPassbandModulator
from .reconstruction.reconstructor import SignalReconstructor
from .reconstruction.svg_vectorizer import image_to_svg_string, save_image_svg


def package_for_peer_bytes(
    image_bytes: bytes,
    scheme: str = "BFSK",
    compression_method: str = METHOD_LOSSY_DCT,
    quality: int = 82,
    bits_per_sample: int = 8,
    max_dim: int = 96,
    apply_red_filter: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta TX completo en memoria: carga imagen -> filtro rojo -> compresión ->
    modulación audible -> paquete `.zip` listo para enviar a un compañero.
    """
    work_img = load_image(image_bytes, max_dim=max_dim)
    tx_source = isolate_largest_red_region(work_img).filtered if apply_red_filter else work_img

    compressor = ImageCompressor(method=compression_method, quality=quality)
    packet = compressor.compress(
        tx_source, bits_per_sample=bits_per_sample, method=compression_method, quality=quality
    )

    sps = 48 if scheme.upper() in ("MFSK", "4-FSK", "4FSK") else 32
    mod = DigitalPassbandModulator(scheme=scheme, sampling_rate_hz=48000, samples_per_symbol=sps)
    waveform = mod.modulate(packet)
    wav_bytes = samples_to_wav_bytes(waveform.samples, waveform.sampling_rate_hz, bit_depth=16)

    manifest = {
        "scheme": mod.scheme,
        "sampling_rate_hz": waveform.sampling_rate_hz,
        "samples_per_symbol": sps,
        "fsk_freqs_hz": list(mod.fsk_freqs_hz),
        "carrier_freq_hz": mod.carrier_freq_hz,
        "compression_method": packet.method,
        "compression_ratio": round(packet.compression_ratio, 3),
        "savings_percent": round(packet.savings_percent, 2),
        "compressed_bytes": packet.compressed_bytes_count,
        "raw_bytes": packet.raw_bytes_count,
        "crc32_hex": f"0x{packet.crc32:08X}",
        "audio_duration_s": round(waveform.duration_s, 3),
        "resolution": [tx_source.width, tx_source.height],
    }

    instructions = (
        "PAQUETE DE COMUNICACIONES I - INSTRUCCIONES PARA EL COMPANERO\n"
        "=============================================================\n"
        f"Esquema de modulacion : {mod.scheme}\n"
        f"Frecuencia muestreo   : {waveform.sampling_rate_hz} Hz\n"
        f"Muestras por simbolo  : {sps}\n"
        f"CRC32 esperado        : 0x{packet.crc32:08X}\n\n"
        "Para demodular y reconstruir en Python:\n"
        f"  python pipeline_cli.py receive --input paquete_envio_companero.zip --out recibido\n"
        "O bien cargando directamente `senal_modulada.wav` en la app web (Modo Receptor).\n"
    )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("senal_modulada.wav", wav_bytes)
        zf.writestr("paquete_comprimido.dspimg", packet.wire_bytes)
        zf.writestr("manifiesto_tx.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        zf.writestr("INSTRUCCIONES_DEMODULAR.txt", instructions)

    return {
        "source_image": tx_source,
        "packet": packet,
        "waveform": waveform,
        "wav_bytes": wav_bytes,
        "zip_bytes": zip_buf.getvalue(),
        "manifest": manifest,
    }


def package_for_peer_files(
    image_path: str,
    output_dir: str,
    scheme: str = "BFSK",
    compression_method: str = METHOD_LOSSY_DCT,
    quality: int = 82,
    bits_per_sample: int = 8,
    max_dim: int = 96,
    apply_red_filter: bool = True,
) -> Dict[str, Any]:
    """Genera los archivos físicos para enviar a un compañero (`.zip`, `.wav`, `.dspimg`)."""
    with open(image_path, "rb") as handle:
        raw_img = handle.read()
    bundle = package_for_peer_bytes(
        raw_img,
        scheme=scheme,
        compression_method=compression_method,
        quality=quality,
        bits_per_sample=bits_per_sample,
        max_dim=max_dim,
        apply_red_filter=apply_red_filter,
    )

    os.makedirs(output_dir, exist_ok=True)
    wav_path = save_wav(
        os.path.join(output_dir, "senal_modulada_para_companero.wav"),
        bundle["waveform"].samples,
        bundle["waveform"].sampling_rate_hz,
    )
    pkt_path = os.path.abspath(os.path.join(output_dir, "paquete_comprimido.dspimg"))
    with open(pkt_path, "wb") as f_pkt:
        f_pkt.write(bundle["packet"].wire_bytes)

    zip_path = os.path.abspath(os.path.join(output_dir, "paquete_envio_companero.zip"))
    with open(zip_path, "wb") as f_zip:
        f_zip.write(bundle["zip_bytes"])

    manifest_path = os.path.abspath(os.path.join(output_dir, "manifiesto_tx.json"))
    with open(manifest_path, "w", encoding="utf-8") as f_man:
        json.dump(bundle["manifest"], f_man, indent=2, ensure_ascii=False)

    return {
        **bundle,
        "paths": {
            "zip": zip_path,
            "wav": wav_path,
            "dspimg": pkt_path,
            "manifest": manifest_path,
        },
    }


def receive_from_peer_bytes(
    input_bytes: bytes,
    filename: str = "senal_modulada.wav",
    scheme: str = "BFSK",
    samples_per_symbol: Optional[int] = None,
    carrier_freq_hz: float = 3000.0,
    svg_color_levels: int = 16,
) -> Dict[str, Any]:
    """
    Recibe el archivo enviado por un compañero (`.zip`, `.wav` o `.dspimg`),
    demodula si corresponde, descomprime, verifica CRC32 y reconstruye PNG + SVG + WAV.
    """
    ext = os.path.splitext(filename.lower())[1]
    manifest: Dict[str, Any] = {}
    demod_result: Optional[DemodulatedResult] = None
    compressor = ImageCompressor()

    if ext == ".zip" or input_bytes[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(input_bytes), "r") as zf:
            names = zf.namelist()
            if "manifiesto_tx.json" in names:
                manifest = json.loads(zf.read("manifiesto_tx.json").decode("utf-8"))
                scheme = manifest.get("scheme", scheme)
                samples_per_symbol = manifest.get("samples_per_symbol", samples_per_symbol)
                carrier_freq_hz = float(manifest.get("carrier_freq_hz", carrier_freq_hz))
            if "senal_modulada.wav" in names:
                wav_raw = zf.read("senal_modulada.wav")
                input_bytes = wav_raw
                ext = ".wav"
            elif "paquete_comprimido.dspimg" in names:
                input_bytes = zf.read("paquete_comprimido.dspimg")
                ext = ".dspimg"
            else:
                raise ValueError("El archivo .zip no contiene `senal_modulada.wav` ni `paquete_comprimido.dspimg`.")

    reconstructor = SignalReconstructor(dac_method="sinc")

    if ext == ".dspimg" or input_bytes[:6] == b"IMDSP1":
        reconstructed_img = compressor.decompress(input_bytes)
        crc_valid = True
        sync_offset = 0
        demod_mode = "direct_dspimg"
    else:
        rx_samples, rx_fs, _ = wav_bytes_to_samples(input_bytes)
        sps = int(samples_per_symbol or (48 if scheme.upper() in ("MFSK", "4-FSK", "4FSK") else 32))
        fsk_freqs = tuple(manifest["fsk_freqs_hz"]) if "fsk_freqs_hz" in manifest else None
        blind_wave = ModulatedWaveform(
            samples=rx_samples,
            sampling_rate_hz=rx_fs,
            carrier_freq_hz=carrier_freq_hz,
            modulation_type=scheme,
            is_digital=True,
            metadata={
                "samples_per_symbol": sps,
                **({"fsk_freqs_hz": list(fsk_freqs)} if fsk_freqs else {}),
            },
        )
        demod = DigitalPassbandDemodulator(
            scheme=scheme,
            sampling_rate_hz=rx_fs,
            samples_per_symbol=sps,
            carrier_freq_hz=carrier_freq_hz,
            fsk_freqs_hz=fsk_freqs,
        )
        demod_result = demod.demodulate(blind_wave, has_framing=True, auto_sync=True)
        reconstructed_img = reconstructor.reconstruct_from_demodulated(demod_result, compressor=compressor)
        crc_valid = bool(demod_result.crc_valid)
        sync_offset = demod_result.sync_offset_samples
        demod_mode = demod_result.demodulation_type

    rec_audio = reconstructor.image_to_audible_scanline(reconstructed_img, sample_rate_hz=16000, duration_s=2.5)
    png_bytes = image_to_png_bytes(reconstructed_img)
    svg_text = image_to_svg_string(reconstructed_img, color_levels=svg_color_levels)
    wav_audio_bytes = samples_to_wav_bytes(rec_audio, sample_rate_hz=16000, bit_depth=16)

    return {
        "reconstructed_image": reconstructed_img,
        "reconstructed_audio": rec_audio,
        "audio_sample_rate_hz": 16000,
        "png_bytes": png_bytes,
        "svg_text": svg_text,
        "wav_audio_bytes": wav_audio_bytes,
        "demodulated_result": demod_result,
        "summary": {
            "mode": demod_mode,
            "scheme": scheme,
            "crc_valid": crc_valid,
            "sync_offset_samples": sync_offset,
            "reconstructed_resolution": [reconstructed_img.width, reconstructed_img.height],
            "compression_meta": reconstructed_img.metadata,
            "manifest": manifest,
        },
    }


def receive_from_peer_file(
    input_path: str,
    output_dir: str,
    scheme: str = "BFSK",
    svg_color_levels: int = 16,
) -> Dict[str, Any]:
    """Lee un archivo enviado por un compañero y guarda PNG, SVG y WAV reconstruidos."""
    with open(input_path, "rb") as handle:
        raw = handle.read()
    res = receive_from_peer_bytes(
        raw, filename=os.path.basename(input_path), scheme=scheme, svg_color_levels=svg_color_levels
    )
    os.makedirs(output_dir, exist_ok=True)
    png_path = save_image_png(
        res["reconstructed_image"], os.path.join(output_dir, "imagen_recibida.png")
    )
    svg_path = save_image_svg(
        res["reconstructed_image"],
        os.path.join(output_dir, "imagen_recibida.svg"),
        color_levels=svg_color_levels,
    )
    wav_path = save_wav(
        os.path.join(output_dir, "audio_recibido_reconstruido.wav"),
        res["reconstructed_audio"],
        res["audio_sample_rate_hz"],
    )
    return {**res, "paths": {"png": png_path, "svg": svg_path, "wav": wav_path}}
