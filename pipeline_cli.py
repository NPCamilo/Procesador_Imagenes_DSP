"""
Orquestador CLI maestro del Procesador, Compresor y Transceptor DSP de Imágenes.

Comandos disponibles:
  - `full`:    Ejecuta de extremo a extremo Puntos 1 al 6 sobre la fotografía.
  - `send`:    Comprime y modula una foto generando el paquete `.zip`/`.wav`/`.dspimg` para un compañero.
  - `receive`: Demodula, descomprime y reconstruye (PNG, SVG, WAV) el archivo de un compañero.
"""

from __future__ import annotations

import argparse
import json
import os

from dsp_img.core.audio_wav import play_wav_or_samples, save_wav
from dsp_img.core.codec import METHOD_LOSSY_DCT, ImageCompressor
from dsp_img.core.image_io import load_image, save_image_png
from dsp_img.core.primitives import unpack_bits
from dsp_img.core.red_filter import isolate_largest_red_region
from dsp_img.demodulation import DigitalPassbandDemodulator
from dsp_img.exchange import package_for_peer_files, receive_from_peer_file
from dsp_img.modulation import DigitalPassbandModulator
from dsp_img.reconstruction import (
    SignalReconstructor,
    evaluate_audio_fidelity,
    plot_full_reconstruction_comparison,
)


def run_full_pipeline(
    image_path: str = "data/input/selfie_dsp.jpeg",
    output_dir: str = "data/output/pipeline_full",
    scheme: str = "BFSK",
    max_dim: int = 96,
    quality: int = 82,
    play: bool = False,
) -> dict:
    """Ejecuta toda la cadena TX -> Canal -> RX -> Reconstrucción -> Empaquetado."""
    os.makedirs(output_dir, exist_ok=True)
    reconstructor = SignalReconstructor(dac_method="sinc")

    # TX y paquete para compañero
    tx_bundle = package_for_peer_files(
        image_path=image_path,
        output_dir=os.path.join(output_dir, "envio_companero"),
        scheme=scheme,
        compression_method=METHOD_LOSSY_DCT,
        quality=quality,
        max_dim=max_dim,
    )
    src_img = tx_bundle["source_image"]
    pkt = tx_bundle["packet"]
    tx_wave = tx_bundle["waveform"]

    # RX desde el WAV generado (simulando al compañero recibiendo el audio)
    rx_bundle = receive_from_peer_file(
        input_path=tx_bundle["paths"]["wav"],
        output_dir=os.path.join(output_dir, "reconstruido"),
        scheme=scheme,
    )
    rec_img = rx_bundle["reconstructed_image"]

    # Audio de referencia original vs audio reconstruido
    orig_audio = reconstructor.image_to_audible_scanline(src_img, sample_rate_hz=16000, duration_s=2.5)
    rec_audio = rx_bundle["reconstructed_audio"]
    orig_wav = save_wav(os.path.join(output_dir, "reconstruido", "audio_original.wav"), orig_audio, 16000)

    img_metrics = reconstructor.evaluate(src_img, rec_img, compression_ratio=pkt.compression_ratio)
    audio_metrics = evaluate_audio_fidelity(orig_audio, rec_audio)

    fig_cmp = os.path.join(output_dir, "comparativa_original_vs_reconstruida.png")
    plot_full_reconstruction_comparison(
        original=src_img,
        reconstructed=rec_img,
        orig_audio=orig_audio,
        rec_audio=rec_audio,
        audio_fs_hz=16000,
        img_metrics=img_metrics,
        audio_metrics=audio_metrics,
        save_path=fig_cmp,
    )

    report = {
        "scheme": tx_bundle["manifest"]["scheme"],
        "compression_ratio": round(pkt.compression_ratio, 3),
        "compressed_bytes": pkt.compressed_bytes_count,
        "crc_valid": rx_bundle["summary"]["crc_valid"],
        "image_metrics": {
            "psnr_db": round(img_metrics.psnr_db, 2),
            "ssim": round(img_metrics.ssim, 4),
            "pearson_r": round(img_metrics.pearson_corr, 4),
            "mse": round(img_metrics.mse, 6),
        },
        "audio_metrics": {k: round(v, 4) for k, v in audio_metrics.items()},
        "tx_files": tx_bundle["paths"],
        "rx_files": {**rx_bundle["paths"], "orig_wav": orig_wav, "comparison_fig": fig_cmp},
    }

    report_path = os.path.join(output_dir, "pipeline_reporte.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print("=== PIPELINE COMPLETO END-TO-END (PUNTOS 1 AL 6) ===")
    print(f"Esquema / Ratio         : {report['scheme']} | CR = {report['compression_ratio']}x ({pkt.compressed_bytes_count} B)")
    print(f"Fidelidad Imagen        : PSNR = {report['image_metrics']['psnr_db']} dB | SSIM = {report['image_metrics']['ssim']}")
    print(
        f"Fidelidad Audio 1D      : SNR = {report['audio_metrics']['snr_db']} dB | "
        f"r = {report['audio_metrics']['pearson_corr']}"
    )
    print(f"PNG / SVG / ZIP listos  : {rx_bundle['paths']['png']} | {rx_bundle['paths']['svg']}")
    print(f"Paquete para compañero  : {tx_bundle['paths']['zip']}")

    if play:
        print("Reproduciendo audio original vs reconstruido...")
        play_wav_or_samples((orig_audio, 16000), async_play=False)
        play_wav_or_samples((rec_audio, 16000), async_play=False)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI Maestro - Procesador DSP de Imágenes")
    sub = parser.add_subparsers(dest="command", required=True)

    p_full = sub.add_parser("full", help="Ejecutar pipeline completo (Puntos 1 al 6)")
    p_full.add_argument("--image", default="data/input/selfie_dsp.jpeg")
    p_full.add_argument("--out", default="data/output/pipeline_full")
    p_full.add_argument("--scheme", default="BFSK")
    p_full.add_argument("--max-dim", type=int, default=96)
    p_full.add_argument("--quality", type=int, default=82)
    p_full.add_argument("--play", action="store_true")

    p_send = sub.add_parser("send", help="Comprimir, modular y empaquetar para un compañero")
    p_send.add_argument("--image", default="data/input/selfie_dsp.jpeg")
    p_send.add_argument("--out", default="data/output/envio_companero")
    p_send.add_argument("--scheme", default="BFSK")
    p_send.add_argument("--max-dim", type=int, default=96)
    p_send.add_argument("--quality", type=int, default=82)

    p_rx = sub.add_parser("receive", help="Demodular y reconstruir (PNG, SVG, WAV) desde compañero")
    p_rx.add_argument("--input", required=True, help="Ruta a .zip, .wav o .dspimg recibido")
    p_rx.add_argument("--out", default="data/output/recibido_companero")
    p_rx.add_argument("--scheme", default="BFSK")

    args = parser.parse_args()
    if args.command == "full":
        run_full_pipeline(
            image_path=args.image,
            output_dir=args.out,
            scheme=args.scheme,
            max_dim=args.max_dim,
            quality=args.quality,
            play=args.play,
        )
    elif args.command == "send":
        res = package_for_peer_files(
            image_path=args.image,
            output_dir=args.out,
            scheme=args.scheme,
            quality=args.quality,
            max_dim=args.max_dim,
        )
        print("Paquete generado para enviar al compañero:", res["paths"]["zip"])
    elif args.command == "receive":
        res = receive_from_peer_file(
            input_path=args.input, output_dir=args.out, scheme=args.scheme
        )
        print("Reconstrucción completada:", res["paths"])


if __name__ == "__main__":
    main()
