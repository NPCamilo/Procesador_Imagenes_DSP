"""
Análisis espacial 2D y temporal equivalente 1D de la frecuencia de muestreo (Punto 2).

Identifica la tasa de muestreo espacial de la fotografía, calcula el espectro 2D
y 1D (FFT con ventana Hann), estima el ancho de banda efectivo f_max al 99 % de
energía acumulada y evalúa el criterio de Nyquist-Shannon.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

from .contracts import ImageSignal, SamplingReport
from .primitives import compute_spectrum, diagnostico_nyquist, estimate_max_frequency
from .theme import apply_plot_theme, style_axis


def compute_2d_radial_spectrum(
    luminance: np.ndarray, num_bins: int = 128
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calcula la FFT 2D centrada (sin componente DC) y su perfil radial de potencia.

    Devuelve `(fft_mag_db, freq_radial_cycles_per_px, radial_power)`.
    """
    h, w = luminance.shape
    centered = luminance.astype(np.float64) - float(np.mean(luminance))
    win_y = np.hanning(h)[:, np.newaxis]
    win_x = np.hanning(w)[np.newaxis, :]
    windowed = centered * (win_y * win_x)

    fft2 = np.fft.fftshift(np.fft.fft2(windowed))
    mag = np.abs(fft2)
    mag_db = 20.0 * np.log10(np.clip(mag / (float(np.max(mag)) + 1e-12), 1e-5, 1.0))

    fy = np.fft.fftshift(np.fft.fftfreq(h, d=1.0))
    fx = np.fft.fftshift(np.fft.fftfreq(w, d=1.0))
    grid_fx, grid_fy = np.meshgrid(fx, fy)
    radial_freq = np.sqrt(grid_fx**2 + grid_fy**2)

    # Perfil radial hasta el límite de Nyquist espacial (0.5 ciclos/px)
    edges = np.linspace(0.0, 0.5, num_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    power = mag**2
    bin_idx = np.digitize(radial_freq.ravel(), edges) - 1
    radial_power = np.zeros(num_bins, dtype=np.float64)
    flat_power = power.ravel()
    for b in range(num_bins):
        mask = bin_idx == b
        if np.any(mask):
            radial_power[b] = float(np.mean(flat_power[mask]))

    return mag_db, centers, radial_power


def analyze_sampling_frequency(
    image: ImageSignal,
    energy_threshold: float = 0.99,
    scanline_row: Optional[int] = None,
) -> SamplingReport:
    """
    Identifica la frecuencia de muestreo espacial y la equivalente 1D de la imagen.

    Para imágenes digitales:
      - Frecuencia de muestreo espacial normalizada: fs_esp = 1.0 muestra/píxel
        (límite de Nyquist = 0.5 ciclos/píxel).
      - Si existen metadatos físicos DPI, se reportan adicionalmente en el informe.
      - Para el flujo 1D equivalente (barrido por fila central o señal serializada),
        se mide la FFT unilateral y se evalúa el criterio NQS respecto a `sample_rate_1d_hz`.
    """
    luminance = image.to_luminance()
    _, radial_freqs, radial_power = compute_2d_radial_spectrum(luminance)
    fmax_2d = estimate_max_frequency(
        radial_freqs, np.sqrt(radial_power), energy_threshold=energy_threshold
    )

    # Señal 1D representativa: fila central (o indicada) sin componente DC
    row_idx = image.height // 2 if scanline_row is None else int(np.clip(scanline_row, 0, image.height - 1))
    row_signal = luminance[row_idx, :].astype(np.float64) - float(np.mean(luminance[row_idx, :]))

    fs_1d = float(image.sample_rate_1d_hz)
    freqs_1d, mag_1d, _ = compute_spectrum(row_signal, sample_rate=fs_1d, window="hann")
    fmax_1d = estimate_max_frequency(freqs_1d, mag_1d, energy_threshold=energy_threshold)
    diag_1d = diagnostico_nyquist(fmax=fmax_1d, fs=fs_1d)

    spatial_fs = 1.0  # 1 muestra por píxel
    spatial_nyquist = 0.5  # ciclos/píxel
    report = SamplingReport(
        spatial_fs_per_px=spatial_fs,
        nyquist_spatial_cycles_per_px=spatial_nyquist,
        f_max_spatial_cycles_per_px=fmax_2d,
        equivalent_fs_hz=int(fs_1d),
        f_max_1d_hz=fmax_1d,
        nyquist_diagnosis={
            **diag_1d,
            "spatial_nyquist_satisfied": bool(fmax_2d <= spatial_nyquist),
            "scanline_row": row_idx,
        },
        dpi=image.dpi,
    )
    image.metadata["sampling_report"] = {
        "spatial_fs_per_px": report.spatial_fs_per_px,
        "nyquist_spatial_cycles_per_px": report.nyquist_spatial_cycles_per_px,
        "f_max_spatial_cycles_per_px": round(report.f_max_spatial_cycles_per_px, 4),
        "equivalent_fs_hz": report.equivalent_fs_hz,
        "f_max_1d_hz": round(report.f_max_1d_hz, 2),
        "dpi": report.dpi,
    }
    return report


def summarize_sampling_metrics(image: ImageSignal, report: SamplingReport) -> Dict[str, object]:
    """Devuelve un resumen estructurado listo para consola, JSON o vista web."""
    return {
        "width_px": image.width,
        "height_px": image.height,
        "total_pixels": image.num_pixels,
        "channels": image.channels,
        "spatial_sampling_rate_px": report.spatial_fs_per_px,
        "spatial_nyquist_limit_cycles_per_px": report.nyquist_spatial_cycles_per_px,
        "f_max_spatial_cycles_per_px": round(report.f_max_spatial_cycles_per_px, 4),
        "physical_dpi": report.dpi,
        "equivalent_1d_sample_rate_hz": report.equivalent_fs_hz,
        "f_max_1d_hz": round(report.f_max_1d_hz, 2),
        "nyquist_1d_verdict": report.nyquist_diagnosis["veredicto"],
    }


def plot_sampling_frequency_analysis(
    image: ImageSignal,
    report: SamplingReport,
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Genera una figura técnica con:
      1. Espectro 2D logarítmico centrado de la luminancia.
      2. Perfil radial espacial con f_max (99 % energía) y límite de Nyquist (0.5 ciclos/px).
      3. Perfil 1D de la línea de barrido central y su espectro FFT unilateral en Hz.
    """
    palette = apply_plot_theme(theme_mode)
    lum = image.to_luminance()
    mag_db_2d, radial_freqs, radial_power = compute_2d_radial_spectrum(lum)

    row_idx = int(report.nyquist_diagnosis.get("scanline_row", image.height // 2))
    row_vals = lum[row_idx, :]
    row_ac = row_vals.astype(np.float64) - float(np.mean(row_vals))
    freqs_1d, _, mag_db_1d = compute_spectrum(row_ac, sample_rate=report.equivalent_fs_hz)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), constrained_layout=True)

    # Panel 1: FFT 2D
    ax_fft2 = axes[0, 0]
    ax_fft2.imshow(
        mag_db_2d,
        extent=[-0.5, 0.5, -0.5, 0.5],
        cmap="viridis",
        aspect="auto",
        vmin=-80,
        vmax=0,
    )
    ax_fft2.set_title("1. Espectro Espacial 2D |F{I(x,y)}| [dB]", color=palette["ink"])
    ax_fft2.set_xlabel("Frecuencia horizontal fx [ciclos/px]")
    ax_fft2.set_ylabel("Frecuencia vertical fy [ciclos/px]")
    ax_fft2.grid(False)

    # Panel 2: Energía radial 2D y límite de Nyquist espacial
    ax_rad = axes[0, 1]
    style_axis(ax_rad, palette)
    radial_norm = radial_power / (float(np.max(radial_power)) + 1e-12)
    radial_db = 10.0 * np.log10(np.clip(radial_norm, 1e-6, 1.0))
    ax_rad.plot(radial_freqs, radial_db, color=palette["primary"], linewidth=1.6, label="Densidad radial")
    ax_rad.axvline(
        report.f_max_spatial_cycles_per_px,
        color=palette["accent"],
        linestyle="--",
        linewidth=1.5,
        label=f"f_max 99% = {report.f_max_spatial_cycles_per_px:.3f} ciclos/px",
    )
    ax_rad.axvline(
        report.nyquist_spatial_cycles_per_px,
        color=palette["ok"],
        linestyle="-.",
        linewidth=1.5,
        label=f"Límite Nyquist = {report.nyquist_spatial_cycles_per_px:.2f} ciclos/px",
    )
    ax_rad.set_title("2. Ancho de Banda Espacial vs Nyquist (fs = 1.0 px⁻¹)", color=palette["ink"])
    ax_rad.set_xlabel("Frecuencia radial [ciclos/px]")
    ax_rad.set_ylabel("Potencia relativa [dB]")
    ax_rad.set_xlim(0.0, 0.52)
    ax_rad.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 3: Señal 1D de fila de barrido
    ax_row = axes[1, 0]
    style_axis(ax_row, palette)
    t_row_ms = (np.arange(len(row_vals)) / report.equivalent_fs_hz) * 1000.0
    ax_row.plot(t_row_ms, row_vals, color=palette["secondary"], linewidth=1.1, label=f"Fila y={row_idx}")
    ax_row.set_title(
        f"3. Señal Discreta 1D (Fila y={row_idx}, fs_eq = {report.equivalent_fs_hz:,} Hz)",
        color=palette["ink"],
    )
    ax_row.set_xlabel("Tiempo equivalente [ms]")
    ax_row.set_ylabel("Luminancia normalizada [0, 1]")
    ax_row.set_ylim(-0.05, 1.05)
    ax_row.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 4: Espectro 1D equivalente
    ax_f1d = axes[1, 1]
    style_axis(ax_f1d, palette)
    ax_f1d.plot(freqs_1d, mag_db_1d, color=palette["primary"], linewidth=1.1, label="|X(f)|")
    ax_f1d.axvline(
        report.f_max_1d_hz,
        color=palette["error"],
        linestyle="--",
        linewidth=1.5,
        label=f"f_max 1D = {report.f_max_1d_hz:,.1f} Hz",
    )
    ax_f1d.axvline(
        min(2.0 * report.f_max_1d_hz, report.equivalent_fs_hz / 2.0),
        color=palette["ok"],
        linestyle="-.",
        linewidth=1.5,
        label=f"2·f_max = {2.0 * report.f_max_1d_hz:,.1f} Hz",
    )
    ax_f1d.set_title(
        f"4. Espectro Equivalente 1D ({report.nyquist_diagnosis['veredicto']})",
        color=palette["ink"],
    )
    ax_f1d.set_xlabel("Frecuencia [Hz]")
    ax_f1d.set_ylabel("Magnitud [dBFS]")
    ax_f1d.set_xlim(0.0, report.equivalent_fs_hz / 2.0)
    ax_f1d.set_ylim(-65.0, 5.0)
    ax_f1d.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
