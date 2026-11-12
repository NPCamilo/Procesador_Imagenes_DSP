"""
Módulo de carga, metadatos EXIF/JFIF y reproducción visual de imágenes JPG/JPEG/PNG.

Cubre el Punto 1 (ingesta de fotografía móvil) y la primera parte del Punto 2
(cargar archivo en Python y reproducir la imagen original en colores).
"""

from __future__ import annotations

import io
import os
from typing import Any, Dict, Optional, Tuple, Union
import matplotlib.pyplot as plt
import numpy as np
from PIL import ExifTags, Image, ImageOps

from .contracts import ImageSignal
from .theme import OKABE_ITO, apply_plot_theme, style_axis


def _extract_physical_dpi(img: Image.Image) -> Optional[Tuple[float, float]]:
    """Extrae densidad física real en DPI solo si existe unidad física válida."""
    dpi = img.info.get("dpi")
    if dpi and len(dpi) == 2 and img.info.get("jfif_unit", 1) in (1, 2):
        x_dpi, y_dpi = float(dpi[0]), float(dpi[1])
        if x_dpi > 1.0 and y_dpi > 1.0:
            return (x_dpi, y_dpi)

    exif = img.getexif()
    if exif:
        x_res = exif.get(282)  # XResolution
        y_res = exif.get(283)  # YResolution
        unit = exif.get(296, 2)  # 2 = inches, 3 = cm
        if x_res and y_res:
            scale = 2.54 if unit == 3 else 1.0
            x_val, y_val = float(x_res) * scale, float(y_res) * scale
            if x_val > 1.0 and y_val > 1.0:
                return (x_val, y_val)
    return None


def _extract_exif_summary(img: Image.Image) -> Dict[str, Any]:
    """Extrae un resumen serializable de metadatos JPEG/EXIF relevantes."""
    summary: Dict[str, Any] = {
        "format": img.format or "UNKNOWN",
        "original_mode": img.mode,
        "jfif_unit": img.info.get("jfif_unit"),
        "jfif_density": tuple(img.info["jfif_density"]) if "jfif_density" in img.info else None,
        "progressive": bool(img.info.get("progressive", False)),
    }
    exif = img.getexif()
    if exif:
        wanted = {"Make", "Model", "DateTime", "Orientation", "Software"}
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if tag_name in wanted:
                summary[f"exif_{tag_name.lower()}"] = str(value)
    return summary


def load_image(
    source: Union[str, os.PathLike[str], bytes],
    sample_rate_1d_hz: int = 16000,
    max_dim: Optional[int] = None,
) -> ImageSignal:
    """
    Carga una imagen JPG/JPEG/PNG desde ruta o bytes respetando orientación EXIF.

    Args:
        source: Ruta al archivo o bytes crudos (ideal para cargas en memoria/Vercel).
        sample_rate_1d_hz: Frecuencia de muestreo equivalente 1D para transmisión DSP.
        max_dim: Si se indica, reduce proporcionalmente conservando relación de aspecto.
    """
    if isinstance(source, (bytes, bytearray)):
        stream = io.BytesIO(source)
        filename = None
        opened = Image.open(stream)
    else:
        path_str = os.fspath(source)
        if not os.path.exists(path_str):
            raise FileNotFoundError(f"No se encontró la imagen: {path_str}")
        filename = os.path.abspath(path_str)
        opened = Image.open(path_str)

    with opened as img:
        metadata = _extract_exif_summary(img)
        dpi = _extract_physical_dpi(img)
        oriented = ImageOps.exif_transpose(img)
        if oriented.mode != "RGB":
            oriented = oriented.convert("RGB")
        if max_dim is not None and max(oriented.size) > max_dim:
            oriented.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            metadata["resized_to"] = oriented.size
        pixels = np.asarray(oriented, dtype=np.uint8)

    metadata["dpi_detected"] = dpi is not None
    return ImageSignal(
        pixels=pixels,
        sample_rate_1d_hz=sample_rate_1d_hz,
        dpi=dpi,
        filename=filename,
        metadata=metadata,
    )


def image_to_png_bytes(image: ImageSignal) -> bytes:
    """Serializa un `ImageSignal` a bytes PNG sin pérdidas en memoria."""
    arr = image.to_uint8()
    mode = "L" if image.channels == 1 else "RGB"
    pil_img = Image.fromarray(arr, mode=mode)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def save_image_png(image: ImageSignal, filepath: str) -> str:
    """Guarda un `ImageSignal` como PNG en disco y devuelve la ruta absoluta."""
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as handle:
        handle.write(image_to_png_bytes(image))
    return abs_path


def plot_original_reproduction(
    image: ImageSignal,
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Reproduce la imagen original en colores junto con sus planos R, G, B e histograma.
    """
    palette = apply_plot_theme(theme_mode)
    rgb = image.to_uint8()

    fig = plt.figure(figsize=(13, 8), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, height_ratios=[1.35, 1.0])

    ax_main = fig.add_subplot(grid[0, :2])
    ax_hist = fig.add_subplot(grid[0, 2])
    ax_channels = [fig.add_subplot(grid[1, idx]) for idx in range(3)]

    ax_main.imshow(rgb)
    ax_main.set_title(
        f"Señal Original RGB ({image.width}×{image.height} px | {image.num_pixels:,} muestras espaciales)",
        color=palette["ink"],
    )
    ax_main.set_xlabel("Coordenada espacial X [px]")
    ax_main.set_ylabel("Coordenada espacial Y [px]")
    ax_main.grid(False)

    # Histograma por canal
    style_axis(ax_hist, palette)
    channel_specs = [
        ("Canal R (Rojo)", OKABE_ITO["vermillion"], 0),
        ("Canal G (Verde)", OKABE_ITO["green"], 1),
        ("Canal B (Azul)", OKABE_ITO["sky"], 2),
    ]
    bins = np.arange(257)
    for label, color, ch_idx in channel_specs:
        counts, _ = np.histogram(rgb[:, :, ch_idx].ravel(), bins=bins, density=True)
        ax_hist.plot(np.arange(256), counts, color=color, linewidth=1.4, label=label)
    ax_hist.set_title("Distribución de Intensidades RGB", color=palette["ink"])
    ax_hist.set_xlabel("Nivel digital [0–255]")
    ax_hist.set_ylabel("Densidad normalizada")
    ax_hist.set_xlim(0, 255)
    ax_hist.legend(
        facecolor=palette["legend_bg"],
        edgecolor=palette["spine"],
        labelcolor=palette["ink"],
        fontsize=8,
    )

    # Planos individuales R, G, B (negro = 0, color puro = 255)
    titles = ["Componente R(x, y)", "Componente G(x, y)", "Componente B(x, y)"]
    for idx, (ax_ch, title) in enumerate(zip(ax_channels, titles)):
        plane_rgb = np.zeros_like(rgb)
        plane_rgb[:, :, idx] = rgb[:, :, idx]
        ax_ch.imshow(plane_rgb)
        ax_ch.set_title(title, color=palette["ink"], fontsize=10)
        ax_ch.set_xlabel("X [px]")
        ax_ch.set_ylabel("Y [px]")
        ax_ch.grid(False)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
