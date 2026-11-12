"""
Script demostrativo de Fase 1 (Puntos 1 y 2 del proyecto):
  - Carga de la fotografía móvil JPG/JPEG con corrección EXIF
  - Reproducción de la señal original en color
  - Filtro selectivo: solo la región roja de mayor área en color, resto en grises
  - Identificación de frecuencia de muestreo (espacial 2D y equivalente 1D)
"""

from __future__ import annotations

import argparse
import json
import os
from dsp_img.core.analyzer import (
    analyze_sampling_frequency,
    plot_sampling_frequency_analysis,
    summarize_sampling_metrics,
)
from dsp_img.core.image_io import (
    load_image,
    plot_original_reproduction,
    save_image_png,
)
from dsp_img.core.red_filter import (
    isolate_largest_red_region,
    plot_red_splash_comparison,
)


def run_fase1(
    image_path: str = "data/input/selfie_dsp.jpeg",
    output_dir: str = "data/output/fase1",
    sample_rate_1d_hz: int = 16000,
    show: bool = False,
) -> dict:
    """Ejecuta la Fase 1 completa y guarda figuras y reporte JSON."""
    os.makedirs(output_dir, exist_ok=True)

    image = load_image(image_path, sample_rate_1d_hz=sample_rate_1d_hz)
    splash = isolate_largest_red_region(image)
    sampling = analyze_sampling_frequency(image)
    summary = summarize_sampling_metrics(image, sampling)

    summary["red_filter"] = {
        "num_red_components_detected": splash.num_red_components,
        "largest_area_px": splash.largest_area_px,
        "largest_area_percent": round(splash.largest_area_ratio * 100.0, 2),
        "top_5_component_areas_px": splash.component_areas_px[:5],
    }

    paths = {
        "original_png": save_image_png(image, os.path.join(output_dir, "selfie_original.png")),
        "red_splash_png": save_image_png(
            splash.filtered, os.path.join(output_dir, "selfie_solo_rojo.png")
        ),
        "fig_original": os.path.join(output_dir, "01_original_y_canales.png"),
        "fig_red_filter": os.path.join(output_dir, "02_filtro_rojo_mayor_area.png"),
        "fig_sampling": os.path.join(output_dir, "03_analisis_frecuencia_muestreo.png"),
    }

    plot_original_reproduction(image, save_path=paths["fig_original"], show=show)
    plot_red_splash_comparison(splash, save_path=paths["fig_red_filter"], show=show)
    plot_sampling_frequency_analysis(image, sampling, save_path=paths["fig_sampling"], show=show)

    report_path = os.path.join(output_dir, "fase1_reporte.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    print("=== FASE 1: INGESTA, FILTRO ROJO DOMINANTE Y FRECUENCIA DE MUESTREO ===")
    print(f"Imagen cargada          : {image.filename} ({image.width}x{image.height} px)")
    print(f"Componentes rojas       : {splash.num_red_components} detectadas")
    print(
        f"Región roja ganadora    : {splash.largest_area_px:,} px "
        f"({splash.largest_area_ratio * 100:.2f}% de la imagen)"
    )
    print(
        f"Muestreo espacial 2D    : fs = {sampling.spatial_fs_per_px} px^-1 "
        f"(Nyquist = {sampling.nyquist_spatial_cycles_per_px} ciclos/px, "
        f"f_max = {sampling.f_max_spatial_cycles_per_px:.4f} ciclos/px)"
    )
    print(
        f"Muestreo equivalente 1D : fs = {sampling.equivalent_fs_hz:,} Hz, "
        f"f_max = {sampling.f_max_1d_hz:.1f} Hz -> {sampling.nyquist_diagnosis['veredicto']}"
    )
    print(f"Reporte guardado en     : {os.path.abspath(report_path)}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Fase 1: Puntos 1 y 2 de Imagen DSP")
    parser.add_argument("--image", default="data/input/selfie_dsp.jpeg", help="Ruta a imagen JPG/JPEG")
    parser.add_argument("--out", default="data/output/fase1", help="Directorio de salida")
    parser.add_argument("--fs1d", type=int, default=16000, help="Frecuencia de muestreo 1D equivalente (Hz)")
    parser.add_argument("--show", action="store_true", help="Mostrar figuras en pantalla")
    args = parser.parse_args()
    run_fase1(image_path=args.image, output_dir=args.out, sample_rate_1d_hz=args.fs1d, show=args.show)


if __name__ == "__main__":
    main()
