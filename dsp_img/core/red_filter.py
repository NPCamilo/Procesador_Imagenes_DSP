"""
Filtro selectivo de color rojo dominante (Color Splash por componente conexa).

Implementa el requisito del Punto 2:
"Aplique un filtro que deje sólo el color rojo que abarque más espacio y los
demás los deje en grises."
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import rgb_to_hsv
from scipy import ndimage

from .contracts import ImageSignal, RedSplashResult
from .theme import apply_plot_theme


def detect_red_mask(
    rgb_float: np.ndarray,
    hue_low_max: float = 0.045,
    hue_high_min: float = 0.935,
    min_saturation: float = 0.38,
    min_value: float = 0.18,
    min_red_excess: float = 0.10,
) -> np.ndarray:
    """
    Construye una máscara booleana de píxeles rojos combinando HSV y exceso espectral R.

    El término `(R - max(G, B)) >= min_red_excess` evita falsos positivos en tonos
    de piel, madera cálida o sombras oscuras donde el matiz se acerca al rojo.
    """
    hsv = rgb_to_hsv(np.clip(rgb_float, 0.0, 1.0))
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    r = rgb_float[:, :, 0]
    g = rgb_float[:, :, 1]
    b = rgb_float[:, :, 2]
    red_excess = r - np.maximum(g, b)

    is_red_hue = (hue <= hue_low_max) | (hue >= hue_high_min)
    return is_red_hue & (sat >= min_saturation) & (val >= min_value) & (red_excess >= min_red_excess)


def _clean_binary_mask(mask: np.ndarray, min_kernel_size: int = 3) -> np.ndarray:
    """Suaviza bordes, elimina ruido puntual y rellena huecos internos (pliegues/logos)."""
    struct = np.ones((min_kernel_size, min_kernel_size), dtype=bool)
    opened = ndimage.binary_opening(mask, structure=struct, iterations=1)
    closed = ndimage.binary_closing(opened, structure=struct, iterations=2)
    return ndimage.binary_fill_holes(closed)


def isolate_largest_red_region(
    image: ImageSignal,
    hue_low_max: float = 0.045,
    hue_high_min: float = 0.935,
    min_saturation: float = 0.38,
    min_value: float = 0.18,
    min_red_excess: float = 0.10,
    min_component_px: int = 16,
) -> RedSplashResult:
    """
    Conserva en color únicamente la región roja conexa de mayor área y pasa el resto a gris.
    """
    if image.channels != 3:
        raise ValueError("El filtro de color rojo requiere una imagen RGB de 3 canales.")

    rgb = image.pixels
    raw_red_mask = detect_red_mask(
        rgb,
        hue_low_max=hue_low_max,
        hue_high_min=hue_high_min,
        min_saturation=min_saturation,
        min_value=min_value,
        min_red_excess=min_red_excess,
    )
    clean_red_mask = _clean_binary_mask(raw_red_mask)

    # Conectividad 8 para agrupar pliegues contiguos de la camiseta en una sola componente
    labeled, num_features = ndimage.label(clean_red_mask, structure=np.ones((3, 3), dtype=int))

    component_areas: List[int] = []
    largest_mask = np.zeros(clean_red_mask.shape, dtype=bool)
    largest_area = 0

    if num_features > 0:
        counts = np.bincount(labeled.ravel())[1:]  # ignorar fondo (etiqueta 0)
        valid_pairs: List[Tuple[int, int]] = [
            (label_idx, int(area))
            for label_idx, area in enumerate(counts, start=1)
            if int(area) >= min_component_px
        ]
        valid_pairs.sort(key=lambda pair: pair[1], reverse=True)
        component_areas = [area for _, area in valid_pairs]

        if valid_pairs:
            winner_label, largest_area = valid_pairs[0]
            largest_mask = labeled == winner_label

    # Composición: RGB en la región roja ganadora, luminancia en grises en todo lo demás
    luminance = image.to_luminance()
    gray_rgb = np.repeat(luminance[:, :, np.newaxis], 3, axis=2)
    filtered_pixels = np.where(largest_mask[:, :, np.newaxis], rgb, gray_rgb).astype(np.float32)

    filtered_image = ImageSignal(
        pixels=filtered_pixels,
        sample_rate_1d_hz=image.sample_rate_1d_hz,
        dpi=image.dpi,
        filename=image.filename,
        metadata={
            **image.metadata,
            "filter": "largest_red_splash",
            "num_red_components": len(component_areas),
            "largest_red_area_px": largest_area,
        },
    )

    area_ratio = float(largest_area / image.num_pixels) if image.num_pixels > 0 else 0.0
    return RedSplashResult(
        original=image,
        filtered=filtered_image,
        largest_mask=largest_mask,
        all_red_mask=clean_red_mask,
        num_red_components=len(component_areas),
        largest_area_px=largest_area,
        largest_area_ratio=area_ratio,
        component_areas_px=component_areas,
    )


def plot_red_splash_comparison(
    result: RedSplashResult,
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Visualiza en 3 paneles: imagen original, todas las regiones rojas detectadas
    y el resultado final conservando solo la región roja de mayor área.
    """
    palette = apply_plot_theme(theme_mode)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), constrained_layout=True)

    axes[0].imshow(result.original.to_uint8())
    axes[0].set_title("1. Imagen Original RGB", color=palette["ink"])
    axes[0].set_xlabel("X [px]")
    axes[0].set_ylabel("Y [px]")
    axes[0].grid(False)

    # Mapa diagnóstico: azul cielo = regiones rojas descartadas, naranja/rojo = ganadora
    diag_map = np.zeros((*result.largest_mask.shape, 3), dtype=np.float32)
    discarded = result.all_red_mask & (~result.largest_mask)
    diag_map[discarded] = np.array([0.34, 0.71, 0.91], dtype=np.float32)  # Okabe-Ito sky
    diag_map[result.largest_mask] = np.array([0.84, 0.37, 0.00], dtype=np.float32)  # Okabe-Ito vermillion

    axes[1].imshow(diag_map)
    axes[1].set_title(
        f"2. Regiones Rojas ({result.num_red_components} detectadas)\nNaranja: Mayor área | Azul: Descartadas",
        color=palette["ink"],
        fontsize=10,
    )
    axes[1].set_xlabel("X [px]")
    axes[1].set_ylabel("Y [px]")
    axes[1].grid(False)

    axes[2].imshow(result.filtered.to_uint8())
    pct = result.largest_area_ratio * 100.0
    axes[2].set_title(
        f"3. Filtro Aplicado (Solo Mayor Área)\n{result.largest_area_px:,} px ({pct:.1f}% de la imagen)",
        color=palette["ink"],
        fontsize=10,
    )
    axes[2].set_xlabel("X [px]")
    axes[2].set_ylabel("Y [px]")
    axes[2].grid(False)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
