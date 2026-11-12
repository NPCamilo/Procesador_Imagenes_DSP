"""
Muestreo discreto espacial 2D / 1D y demostración del Teorema de Nyquist-Shannon (Punto 3).
"""

from __future__ import annotations

import os
from typing import Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage

from .analyzer import analyze_sampling_frequency
from .contracts import ImageSignal
from .primitives import compute_spectrum
from .theme import apply_plot_theme, style_axis


def sample_image_nqs(
    image: ImageSignal,
    spatial_factor: int = 1,
    apply_antialias: bool = True,
) -> ImageSignal:
    """
    Aplica muestreo espacial por diezmado `M = spatial_factor` sobre la imagen.

    Con `apply_antialias=True`, aplica un prefiltro pasa-bajo gaussiano (σ ≈ 0.5·M)
    antes de submuestrear; con `False`, permite observar el aliasing espacial directo.
    """
    if spatial_factor < 1:
        raise ValueError(f"El factor espacial debe ser >= 1; se recibió {spatial_factor}.")

    arr = image.pixels.copy()
    if spatial_factor == 1:
        return ImageSignal(
            pixels=arr,
            sample_rate_1d_hz=image.sample_rate_1d_hz,
            dpi=image.dpi,
            filename=image.filename,
            metadata={**image.metadata, "spatial_factor": 1, "antialias": apply_antialias},
        )

    if apply_antialias:
        sigma = 0.45 * spatial_factor
        for ch in range(arr.shape[2]):
            arr[:, :, ch] = ndimage.gaussian_filter(arr[:, :, ch], sigma=sigma, mode="nearest")

    sampled = arr[::spatial_factor, ::spatial_factor, :]
    return ImageSignal(
        pixels=sampled,
        sample_rate_1d_hz=max(1, image.sample_rate_1d_hz // spatial_factor),
        dpi=image.dpi,
        filename=image.filename,
        metadata={
            **image.metadata,
            "spatial_factor": spatial_factor,
            "antialias": apply_antialias,
        },
    )


def simulate_1d_nqs_sampling(
    signal_1d: np.ndarray, fs_hz: int, downsample_factor: int = 1
) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Muestrea una señal 1D discreta por diezmado directo para estudiar NQS.

    Devuelve `(t_discrete_s, x_discrete, fs_effective_hz)`.
    """
    factor = max(1, int(downsample_factor))
    x = np.asarray(signal_1d, dtype=np.float32).ravel()
    indices = np.arange(0, len(x), factor)
    t_discrete = indices.astype(np.float64) / float(fs_hz)
    fs_eff = max(1, int(round(fs_hz / factor)))
    return t_discrete, x[indices], fs_eff


def plot_nqs_sampling_study(
    image: ImageSignal,
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Genera la gráfica comparativa del Teorema de Nyquist-Shannon (NQS) en 2D y 1D:
      - Fila superior: Muestreo espacial original, crítico con antialiasing y submuestreo con aliasing.
      - Fila inferior: Señal 1D de fila de barrido en sobremuestreo, rango Nyquist y aliasing.
    """
    palette = apply_plot_theme(theme_mode)
    report = analyze_sampling_frequency(image)
    fs_orig = report.equivalent_fs_hz
    f_max = max(50.0, report.f_max_1d_hz)

    # Regímenes espaciales 2D con el mismo encuadre completo para comparar nitidez vs aliasing
    h, w = image.height, image.width
    img_nyq = sample_image_nqs(image, spatial_factor=4, apply_antialias=True)
    img_alias = sample_image_nqs(image, spatial_factor=16, apply_antialias=False)

    # Regímenes 1D sobre la fila central de luminancia
    lum = image.to_luminance()
    row_idx = int(report.nyquist_diagnosis.get("scanline_row", h // 2))
    row_1d = lum[row_idx, :].astype(np.float32)
    t_orig = np.arange(len(row_1d), dtype=np.float64) / float(fs_orig)

    factor_nyq = max(2, int(round(fs_orig / (2.2 * f_max))))
    factor_alias = max(factor_nyq * 3, 8)
    t_nyq, x_nyq, fs_nyq = simulate_1d_nqs_sampling(row_1d, fs_orig, downsample_factor=factor_nyq)
    t_al, x_al, fs_al = simulate_1d_nqs_sampling(row_1d, fs_orig, downsample_factor=factor_alias)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5), constrained_layout=True)

    # Fila 1: Muestreo espacial 2D (mismo encuadre para comparación directa)
    axes[0, 0].imshow(image.to_uint8())
    axes[0, 0].set_title(
        f"1A. Muestreo Nativo 2D (1×)\nfs_esp = 1.0 px⁻¹ | {w}×{h} px",
        color=palette["ink"],
        fontsize=10,
    )

    axes[0, 1].imshow(img_nyq.to_uint8(), interpolation="bilinear")
    axes[0, 1].set_title(
        f"1B. Submuestreo 4× CON Antialiasing\nPrefiltro pasa-bajo ({img_nyq.width}×{img_nyq.height} px)",
        color=palette["ink"],
        fontsize=10,
    )

    axes[0, 2].imshow(img_alias.to_uint8(), interpolation="nearest")
    axes[0, 2].set_title(
        f"1C. Submuestreo 16× SIN Antialiasing\nAliasing espacial ({img_alias.width}×{img_alias.height} px)",
        color=palette["ink"],
        fontsize=10,
    )
    for col in range(3):
        axes[0, col].set_xlabel("X [px]")
        axes[0, col].set_ylabel("Y [px]")
        axes[0, col].grid(False)

    # Fila 2: Muestreo discreto 1D con stem plot
    zoom_ms = min(25.0, float(t_orig[-1] * 1000.0)) if len(t_orig) else 25.0
    zoom_s = zoom_ms / 1000.0
    m_orig = t_orig <= zoom_s
    m_nyq = t_nyq <= zoom_s
    m_al = t_al <= zoom_s

    row_configs = [
        (
            axes[1, 0],
            t_orig[m_orig],
            row_1d[m_orig],
            palette["primary"],
            f"2A. Sobremuestreo 1D (fs = {fs_orig:,} Hz > 2·f_max)",
            False,
        ),
        (
            axes[1, 1],
            t_nyq[m_nyq],
            x_nyq[m_nyq],
            palette["accent"],
            f"2B. Muestreo Cerca a Nyquist (fs' = {fs_nyq:,} Hz)",
            True,
        ),
        (
            axes[1, 2],
            t_al[m_al],
            x_al[m_al],
            palette["error"],
            f"2C. Violación NQS -> Aliasing (fs'' = {fs_al:,} Hz << 2·f_max)",
            True,
        ),
    ]

    for ax, t_pts, x_pts, color, title, use_stem in row_configs:
        style_axis(ax, palette)
        ax.plot(
            t_orig[m_orig] * 1000.0,
            row_1d[m_orig],
            color=palette["muted"],
            linewidth=0.8,
            alpha=0.45,
            label="x(t) Referencia",
        )
        if not use_stem:
            ax.plot(t_pts * 1000.0, x_pts, color=color, linewidth=1.3, label="Muestras x[n]")
        else:
            markerline, stemlines, baseline = ax.stem(
                t_pts * 1000.0, x_pts, linefmt="-", markerfmt="o", basefmt="-"
            )
            plt.setp(stemlines, color=color, linewidth=1.1)
            plt.setp(markerline, color=color, markersize=4.5)
            plt.setp(baseline, color=palette["spine"], linewidth=0.8)
            ax.plot(t_pts * 1000.0, x_pts, color=color, linestyle=":", alpha=0.85, label="Envolvente")

        ax.set_title(title, color=palette["ink"], fontsize=9.8)
        ax.set_xlabel("Tiempo equivalente [ms]")
        ax.set_ylabel("Luminancia [0, 1]")
        ax.set_xlim(0.0, zoom_ms)
        ax.set_ylim(-0.05, 1.05)
        ax.legend(
            facecolor=palette["legend_bg"],
            edgecolor=palette["spine"],
            labelcolor=palette["ink"],
            fontsize=7.5,
            loc="upper right",
        )

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
