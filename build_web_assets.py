"""
build_web_assets.py — precalcula los artefactos de demostración para Vercel en `public/demo/`.

Genera en una sola pasada consistente todas las figuras científicas, imágenes PNG/SVG,
audios WAV modulados/demodulados/reconstruidos, paquete de envío `.zip` y el archivo
`public/demo/datos_demo.json` para que la app web responda en milisegundos.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil

import numpy as np

from dsp_img.core.analyzer import (
    analyze_sampling_frequency,
    plot_sampling_frequency_analysis,
    summarize_sampling_metrics,
)
from dsp_img.core.audio_wav import save_wav, wav_bytes_to_samples
from dsp_img.core.codec import (
    METHOD_LOSSLESS,
    METHOD_LOSSY_DCT,
    ImageCompressor,
    plot_compression_comparison,
)
from dsp_img.core.contracts import ModulatedWaveform
from dsp_img.core.image_io import load_image, plot_original_reproduction, save_image_png
from dsp_img.core.primitives import psnr_db, unpack_bits
from dsp_img.core.quantization import (
    format_digital_preview,
    plot_quantization_resolution_study,
    quantize_image,
)
from dsp_img.core.red_filter import isolate_largest_red_region, plot_red_splash_comparison
from dsp_img.core.sampling_nqs import plot_nqs_sampling_study
from dsp_img.demodulation import (
    AMDemodulator,
    DigitalPassbandDemodulator,
    FMDemodulator,
    export_demodulated_audio,
    plot_demodulated_recovery,
)
from dsp_img.exchange import package_for_peer_files, receive_from_peer_file
from dsp_img.modulation import (
    AMModulator,
    DigitalPassbandModulator,
    FMModulator,
    export_modulated_audio,
    plot_modulated_signal,
)
from dsp_img.reconstruction import (
    SignalReconstructor,
    evaluate_audio_fidelity,
    plot_full_reconstruction_comparison,
)


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent
    image_path = root / "data" / "input" / "selfie_dsp.jpeg"
    out_dir = root / "public" / "demo"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== build_web_assets.py: generando activos estáticos en public/demo/ ===")

    # 1. Fase 1: Imagen completa + filtro rojo mayor área + análisis de muestreo
    full_img = load_image(str(image_path))
    splash_full = isolate_largest_red_region(full_img)
    sampling = analyze_sampling_frequency(full_img)
    sampling_summary = summarize_sampling_metrics(full_img, sampling)

    save_image_png(full_img, str(out_dir / "selfie_original.png"))
    save_image_png(splash_full.filtered, str(out_dir / "selfie_solo_rojo.png"))
    plot_original_reproduction(full_img, save_path=str(out_dir / "01_original_y_canales.png"))
    plot_red_splash_comparison(splash_full, save_path=str(out_dir / "02_filtro_rojo_mayor_area.png"))
    plot_sampling_frequency_analysis(
        full_img, sampling, save_path=str(out_dir / "03_analisis_frecuencia_muestreo.png")
    )

    # 2. Fase 2: NQS, cuantización Byte/Bit y compresión
    plot_nqs_sampling_study(splash_full.filtered, save_path=str(out_dir / "04_estudio_muestreo_nqs.png"))
    work_256 = isolate_largest_red_region(load_image(str(image_path), max_dim=256)).filtered
    plot_quantization_resolution_study(
        work_256, save_path=str(out_dir / "05_resolucion_byte_bit_sqnr.png")
    )
    _, stream_4b = quantize_image(work_256, bits_per_sample=4)
    _, stream_8b = quantize_image(work_256, bits_per_sample=8)

    comp_ll = ImageCompressor(method=METHOD_LOSSLESS)
    pkt_ll = comp_ll.compress(work_256, bits_per_sample=4)
    rec_ll = comp_ll.decompress(pkt_ll.wire_bytes)

    comp_dct = ImageCompressor(method=METHOD_LOSSY_DCT, quality=82)
    pkt_dct = comp_dct.compress(work_256, quality=82)
    rec_dct = comp_dct.decompress(pkt_dct.wire_bytes)
    plot_compression_comparison(
        work_256,
        pkt_ll,
        rec_ll,
        pkt_dct,
        rec_dct,
        save_path=str(out_dir / "06_compresion_dpcm_vs_dct.png"),
    )

    # 3. Fases 3, 4 y 5: Transmisión acústica completa (72x96 para ~14s de audio rápido en navegador)
    tx_bundle = package_for_peer_files(
        image_path=str(image_path),
        output_dir=str(out_dir),
        scheme="BFSK",
        compression_method=METHOD_LOSSY_DCT,
        quality=82,
        max_dim=96,
        apply_red_filter=True,
    )
    src_tx = tx_bundle["source_image"]
    pkt_tx = tx_bundle["packet"]
    tx_wave = tx_bundle["waveform"]
    tx_bits = unpack_bits(pkt_tx.wire_bytes)

    plot_modulated_signal(
        tx_wave,
        source_bits=tx_bits,
        zoom_ms=15.0,
        save_path=str(out_dir / "07_modulacion_bfsk.png"),
    )

    # Preview 16-QAM para constelación de referencia
    mod_qam = DigitalPassbandModulator(scheme="16-QAM", sampling_rate_hz=48000, samples_per_symbol=32)
    wave_qam = mod_qam.modulate(pkt_tx)
    demod_qam = DigitalPassbandDemodulator(scheme="16-QAM", sampling_rate_hz=48000, samples_per_symbol=32)
    rx_qam = demod_qam.demodulate(wave_qam, reference_bits=tx_bits, has_framing=True, auto_sync=True)
    plot_demodulated_recovery(
        wave_qam,
        rx_qam,
        reference_bits=tx_bits,
        save_path=str(out_dir / "08_demodulacion_16qam.png"),
    )

    # Demodulación ciega desde el WAV generado
    rx_bundle = receive_from_peer_file(
        input_path=tx_bundle["paths"]["wav"],
        output_dir=str(out_dir),
        scheme="BFSK",
    )
    demod_bfsk = rx_bundle["demodulated_result"]
    export_demodulated_audio(demod_bfsk, str(out_dir / "demodulada_bfsk.wav"))
    plot_demodulated_recovery(
        tx_wave,
        demod_bfsk,
        reference_bits=tx_bits,
        save_path=str(out_dir / "09_demodulacion_bfsk.png"),
    )

    # Reconstrucción de audio original vs reconstruido y comparativa final
    reconstructor = SignalReconstructor(dac_method="sinc")
    rec_img = rx_bundle["reconstructed_image"]
    orig_audio = reconstructor.image_to_audible_scanline(src_tx, sample_rate_hz=16000, duration_s=2.5)
    rec_audio = rx_bundle["reconstructed_audio"]
    save_wav(str(out_dir / "audio_original.wav"), orig_audio, 16000)

    img_metrics = reconstructor.evaluate(src_tx, rec_img, compression_ratio=pkt_tx.compression_ratio)
    audio_metrics = evaluate_audio_fidelity(orig_audio, rec_audio)
    plot_full_reconstruction_comparison(
        src_tx,
        rec_img,
        orig_audio,
        rec_audio,
        16000,
        img_metrics,
        audio_metrics,
        save_path=str(out_dir / "10_comparativa_original_vs_reconstruida.png"),
    )

    # Comparativa analógica AM/FM
    am_wave = AMModulator(carrier_freq_hz=4000.0, mod_index=0.8).modulate(src_tx)
    am_rx = AMDemodulator(method="coherent", cutoff_freq_hz=3500.0).demodulate(am_wave)
    fm_wave = FMModulator(carrier_freq_hz=4000.0, freq_dev_hz=1200.0).modulate(src_tx)
    fm_rx = FMDemodulator(cutoff_freq_hz=3500.0).demodulate(fm_wave)
    export_modulated_audio(am_wave, str(out_dir / "modulada_am.wav"))
    export_modulated_audio(fm_wave, str(out_dir / "modulada_fm.wav"))

    datos = {
        "project": {
            "title": "Procesador, Compresor y Transceptor DSP de Imágenes",
            "course": "Comunicaciones I — UTP",
            "source_image": "selfie_dsp.jpeg",
        },
        "fase1": {
            "sampling": sampling_summary,
            "red_filter": {
                "num_components": splash_full.num_red_components,
                "largest_area_px": splash_full.largest_area_px,
                "largest_area_percent": round(splash_full.largest_area_ratio * 100.0, 2),
                "top_5_areas": splash_full.component_areas_px[:5],
            },
        },
        "fase2": {
            "working_resolution": f"{work_256.width}x{work_256.height}",
            "stream_4bits": format_digital_preview(stream_4b),
            "stream_8bits": format_digital_preview(stream_8b),
            "compression_lossless": {
                "compressed_bytes": pkt_ll.compressed_bytes_count,
                "raw_bytes": pkt_ll.raw_bytes_count,
                "ratio": round(pkt_ll.compression_ratio, 3),
                "savings_percent": round(pkt_ll.savings_percent, 2),
                "psnr_db": round(psnr_db(work_256.pixels, rec_ll.pixels), 2),
            },
            "compression_dct": {
                "compressed_bytes": pkt_dct.compressed_bytes_count,
                "raw_bytes": pkt_dct.raw_bytes_count,
                "ratio": round(pkt_dct.compression_ratio, 3),
                "savings_percent": round(pkt_dct.savings_percent, 2),
                "psnr_db": round(psnr_db(work_256.pixels, rec_dct.pixels), 2),
            },
        },
        "fase3_4_5": {
            "tx_manifest": tx_bundle["manifest"],
            "sync_offset_samples": demod_bfsk.sync_offset_samples,
            "ber_bfsk": float(np.mean(tx_bits != demod_bfsk.detected_bits)),
            "crc_valid": rx_bundle["summary"]["crc_valid"],
            "qam_ber": rx_qam.bit_error_rate,
            "image_metrics": {
                "psnr_db": round(img_metrics.psnr_db, 2),
                "ssim": round(img_metrics.ssim, 4),
                "pearson_corr": round(img_metrics.pearson_corr, 4),
                "mse": round(img_metrics.mse, 6),
                "compression_ratio": round(img_metrics.compression_ratio, 3),
            },
            "audio_metrics": {k: round(v, 4) for k, v in audio_metrics.items()},
        },
        "assets": {
            "original_png": "/demo/selfie_original.png",
            "red_splash_png": "/demo/selfie_solo_rojo.png",
            "reconstructed_png": "/demo/imagen_recibida.png",
            "reconstructed_svg": "/demo/imagen_recibida.svg",
            "fig_original": "/demo/01_original_y_canales.png",
            "fig_red_filter": "/demo/02_filtro_rojo_mayor_area.png",
            "fig_sampling": "/demo/03_analisis_frecuencia_muestreo.png",
            "fig_nqs": "/demo/04_estudio_muestreo_nqs.png",
            "fig_quantization": "/demo/05_resolucion_byte_bit_sqnr.png",
            "fig_compression": "/demo/06_compresion_dpcm_vs_dct.png",
            "fig_mod_bfsk": "/demo/07_modulacion_bfsk.png",
            "fig_demod_qam": "/demo/08_demodulacion_16qam.png",
            "fig_demod_bfsk": "/demo/09_demodulacion_bfsk.png",
            "fig_comparison": "/demo/10_comparativa_original_vs_reconstruida.png",
            "wav_modulated_bfsk": "/demo/senal_modulada_para_companero.wav",
            "wav_demodulated_bfsk": "/demo/demodulada_bfsk.wav",
            "wav_audio_original": "/demo/audio_original.wav",
            "wav_audio_reconstructed": "/demo/audio_recibido_reconstruido.wav",
            "wav_modulated_am": "/demo/modulada_am.wav",
            "wav_modulated_fm": "/demo/modulada_fm.wav",
            "packet_dspimg": "/demo/paquete_comprimido.dspimg",
            "peer_zip": "/demo/paquete_envio_companero.zip",
        },
    }

    with open(out_dir / "datos_demo.json", "w", encoding="utf-8") as handle:
        json.dump(datos, handle, indent=2, ensure_ascii=False)
    # Copia ligera dentro del paquete para que /api/demo también funcione en Vercel Serverless
    with open(root / "dsp_img" / "datos_demo.json", "w", encoding="utf-8") as handle:
        json.dump(datos, handle, indent=2, ensure_ascii=False)

    print(f"Listo: activos generados en {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
