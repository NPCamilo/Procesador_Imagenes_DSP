"""
Script demostrativo de Fase 2 (Punto 3 + Compresor/Descompresor .dspimg):
  - Obtención de valores discretos y gráfica de muestreo aplicando NQS
  - Cuantización y empaquetado digital con técnica de resolución [Byte / Bit]
  - Compresión/Descompresión DPCM+Zlib sin pérdida y DCT 8×8+Zlib con pérdida
"""

from __future__ import annotations

import argparse
import json
import os

from dsp_img.core.codec import (
    METHOD_LOSSLESS,
    METHOD_LOSSY_DCT,
    ImageCompressor,
    plot_compression_comparison,
    save_compressed_packet,
)
from dsp_img.core.image_io import load_image
from dsp_img.core.primitives import psnr_db
from dsp_img.core.quantization import (
    format_digital_preview,
    plot_quantization_resolution_study,
    quantize_image,
    save_digital_stream,
)
from dsp_img.core.red_filter import isolate_largest_red_region
from dsp_img.core.sampling_nqs import plot_nqs_sampling_study


def run_fase2(
    image_path: str = "data/input/selfie_dsp.jpeg",
    output_dir: str = "data/output/fase2",
    bits: int = 4,
    dct_quality: int = 70,
    working_max_dim: int = 256,
    show: bool = False,
) -> dict:
    """Ejecuta el pipeline completo de Fase 2 y guarda figuras, tramas .bin y paquetes .dspimg."""
    os.makedirs(output_dir, exist_ok=True)

    full_img = load_image(image_path)
    splash_full = isolate_largest_red_region(full_img)

    # Estudio NQS sobre imagen original / filtrada
    fig_nqs = os.path.join(output_dir, "01_estudio_muestreo_nqs.png")
    plot_nqs_sampling_study(splash_full.filtered, save_path=fig_nqs, show=show)

    # Imagen de trabajo escalada para digitalización y compresión rápida
    work_img = load_image(image_path, max_dim=working_max_dim)
    work_splash = isolate_largest_red_region(work_img).filtered

    fig_quant = os.path.join(output_dir, "02_resolucion_byte_bit_sqnr.png")
    plot_quantization_resolution_study(work_splash, save_path=fig_quant, show=show)

    _, stream = quantize_image(work_splash, bits_per_sample=bits)
    bin_path, meta_path = save_digital_stream(
        stream, os.path.join(output_dir, f"trama_digital_{bits}bits")
    )

    comp_ll = ImageCompressor(method=METHOD_LOSSLESS)
    pkt_ll = comp_ll.compress(work_splash, bits_per_sample=bits)
    rec_ll = comp_ll.decompress(pkt_ll.wire_bytes)
    ll_path = save_compressed_packet(pkt_ll, os.path.join(output_dir, "paquete_lossless.dspimg"))

    comp_dct = ImageCompressor(method=METHOD_LOSSY_DCT, quality=dct_quality)
    pkt_dct = comp_dct.compress(work_splash, bits_per_sample=8, quality=dct_quality)
    rec_dct = comp_dct.decompress(pkt_dct.wire_bytes)
    dct_path = save_compressed_packet(pkt_dct, os.path.join(output_dir, "paquete_dct.dspimg"))

    fig_comp = os.path.join(output_dir, "03_compresion_dpcm_vs_dct.png")
    plot_compression_comparison(
        work_splash, pkt_ll, rec_ll, pkt_dct, rec_dct, save_path=fig_comp, show=show
    )

    report = {
        "working_resolution": f"{work_splash.width}x{work_splash.height}",
        "digital_stream": format_digital_preview(stream),
        "compression_lossless_dpcm": {
            "raw_bytes": pkt_ll.raw_bytes_count,
            "compressed_bytes": pkt_ll.compressed_bytes_count,
            "compression_ratio": round(pkt_ll.compression_ratio, 3),
            "savings_percent": round(pkt_ll.savings_percent, 2),
            "psnr_vs_source_db": round(psnr_db(work_splash.pixels, rec_ll.pixels), 2),
            "crc32_hex": f"0x{pkt_ll.crc32:08X}",
            "file": ll_path,
        },
        "compression_lossy_dct": {
            "quality": dct_quality,
            "raw_bytes": pkt_dct.raw_bytes_count,
            "compressed_bytes": pkt_dct.compressed_bytes_count,
            "compression_ratio": round(pkt_dct.compression_ratio, 3),
            "savings_percent": round(pkt_dct.savings_percent, 2),
            "psnr_vs_source_db": round(psnr_db(work_splash.pixels, rec_dct.pixels), 2),
            "crc32_hex": f"0x{pkt_dct.crc32:08X}",
            "file": dct_path,
        },
        "artifacts": {
            "bin": bin_path,
            "metadata": meta_path,
            "fig_nqs": fig_nqs,
            "fig_quantization": fig_quant,
            "fig_compression": fig_comp,
        },
    }

    report_path = os.path.join(output_dir, "fase2_reporte.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print("=== FASE 2: MUESTREO NQS, RESOLUCION [BYTE/BIT] Y COMPRESION ===")
    print(f"Resolución de trabajo   : {work_splash.width}x{work_splash.height} px")
    print(
        f"Trama digital ({bits} bits)  : {stream.total_bytes:,} Bytes "
        f"| SQNR = {stream.sqnr_empirical_db:.2f} dB (Teór: {stream.sqnr_theoretical_db:.2f} dB)"
    )
    print(f"Primeros bytes (HEX)    : {report['digital_stream']['first_bytes_hex'][:48]}...")
    print(
        f"Compresión DPCM+Zlib    : {pkt_ll.compressed_bytes_count:,} B "
        f"(Ratio {pkt_ll.compression_ratio:.2f}x | Ahorro {pkt_ll.savings_percent:.1f}%)"
    )
    print(
        f"Compresión DCT 8x8+Zlib : {pkt_dct.compressed_bytes_count:,} B "
        f"(Ratio {pkt_dct.compression_ratio:.2f}x | Ahorro {pkt_dct.savings_percent:.1f}% | "
        f"PSNR={report['compression_lossy_dct']['psnr_vs_source_db']} dB)"
    )
    print(f"Reporte guardado en     : {os.path.abspath(report_path)}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Fase 2: NQS, Cuantización y Compresión")
    parser.add_argument("--image", default="data/input/selfie_dsp.jpeg", help="Ruta a JPG/JPEG")
    parser.add_argument("--out", default="data/output/fase2", help="Directorio de salida")
    parser.add_argument("--bits", type=int, default=4, help="Resolución en bits por canal (1..8)")
    parser.add_argument("--quality", type=int, default=70, help="Calidad DCT 8x8 (1..100)")
    parser.add_argument("--max-dim", type=int, default=256, help="Dimensión máxima de trabajo")
    parser.add_argument("--show", action="store_true", help="Mostrar gráficas en pantalla")
    args = parser.parse_args()
    run_fase2(
        image_path=args.image,
        output_dir=args.out,
        bits=args.bits,
        dct_quality=args.quality,
        working_max_dim=args.max_dim,
        show=args.show,
    )


if __name__ == "__main__":
    main()
