"""
Vectorizador SVG genuino mediante cuantización cromática y fusión horizontal RLE.

Genera archivos `.svg` escalables basados en primitivas `<rect>` fusionadas
por corrida horizontal (sin incrustar imágenes PNG en base64).
"""

from __future__ import annotations

import os
from collections import Counter
from typing import List
import numpy as np

from ..core.contracts import ImageSignal


def image_to_svg_string(
    image: ImageSignal,
    color_levels: int = 16,
    pixel_scale: int = 4,
) -> str:
    """
    Convierte un `ImageSignal` en un documento SVG vectorial con fusión RLE por fila.

    Args:
        image: Imagen reconstruida a vectorizar.
        color_levels: Niveles de cuantización por canal para fusionar áreas uniformes.
        pixel_scale: Factor de escala lógico en unidades SVG (`viewBox`).
    """
    if color_levels < 2 or color_levels > 256:
        raise ValueError("`color_levels` debe estar entre 2 y 256.")

    u8 = image.to_uint8()
    if u8.ndim == 2:
        u8 = np.repeat(u8[:, :, np.newaxis], 3, axis=2)

    h, w, _ = u8.shape
    step = 255.0 / float(color_levels - 1)
    quant_u8 = np.clip(np.rint(np.rint(u8.astype(np.float64) / step) * step), 0, 255).astype(np.uint8)

    # Color de fondo dominante para omitir sus corridas y reducir tamaño del SVG
    flat_tuples = [tuple(int(v) for v in px) for px in quant_u8.reshape(-1, 3)]
    bg_rgb = Counter(flat_tuples).most_common(1)[0][0]
    bg_hex = f"#{bg_rgb[0]:02x}{bg_rgb[1]:02x}{bg_rgb[2]:02x}"

    svg_w = w * pixel_scale
    svg_h = h * pixel_scale
    lines: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}" shape-rendering="crispEdges">',
        f'  <title>Imagen DSP Reconstruida ({w}x{h})</title>',
        f'  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="{bg_hex}"/>',
    ]

    for y in range(h):
        row = quant_u8[y]
        x = 0
        y_pos = y * pixel_scale
        while x < w:
            r, g, b = int(row[x, 0]), int(row[x, 1]), int(row[x, 2])
            run_end = x + 1
            while (
                run_end < w
                and int(row[run_end, 0]) == r
                and int(row[run_end, 1]) == g
                and int(row[run_end, 2]) == b
            ):
                run_end += 1

            if (r, g, b) != bg_rgb:
                fill_hex = f"#{r:02x}{g:02x}{b:02x}"
                x_pos = x * pixel_scale
                run_w = (run_end - x) * pixel_scale
                lines.append(
                    f'  <rect x="{x_pos}" y="{y_pos}" width="{run_w}" height="{pixel_scale}" fill="{fill_hex}"/>'
                )
            x = run_end

    lines.append("</svg>")
    return "\n".join(lines)


def save_image_svg(
    image: ImageSignal,
    filepath: str,
    color_levels: int = 16,
    pixel_scale: int = 4,
) -> str:
    """Guarda la imagen reconstruida como archivo SVG vectorial en disco."""
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    svg_content = image_to_svg_string(image, color_levels=color_levels, pixel_scale=pixel_scale)
    with open(abs_path, "w", encoding="utf-8") as handle:
        handle.write(svg_content)
    return abs_path
