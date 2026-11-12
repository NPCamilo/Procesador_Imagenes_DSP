"""
Comparativa visual y auditiva/espectral entre la señal original y la reconstruida (Punto 6).
"""

from __future__ import annotations

import os
from typing import Dict, Optional
import matplotlib.pyplot as plt
import numpy as np

from ..core.contracts import ImageSignal, ReconstructionMetrics
from ..core.primitives import compute_spectrum
from ..core.theme import apply_plot_theme, style_axis


def plot_full_reconstruction_comparison(
    original: ImageSignal,
    reconstructed: ImageSignal,
    orig_audio: np.ndarray,
    rec_audio: np.ndarray,
    audio_fs_hz: int,
    img_metrics: ReconstructionMetrics,
    audio_metrics: Dict[str, float],
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Genera el tablero comparativo integral (6 paneles) del Punto 6:
      - Fila superior: Original vs Reconstruida vs Mapa de Error |I_orig - I_rec| × 5.
      - Fila inferior: Señal de audio 1D Original vs Reconstruida, Espectros FFT y Ficha de Métricas.
    """
    palette = apply_plot_theme(theme_mode)

    fig, axes = plt.subplots(2, 3, figsize=(15.5, 9), constrained_layout=True)

    # Panel 1: Imagen original de referencia
    axes[0, 0].imshow(original.to_uint8())
    axes[0, 0].set_title(
        f"1. Señal Original ({original.width}×{original.height} px)",
        color=palette["ink"],
        fontsize=10,
    )

    # Panel 2: Imagen reconstruida tras compresión + modulación + demodulación
    axes[0, 1].imshow(reconstructed.to_uint8())
    axes[0, 1].set_title(
        f"2. Imagen Reconstruida\nPSNR = {img_metrics.psnr_db:.2f} dB | SSIM = {img_metrics.ssim:.4f}",
        color=palette["ink"],
        fontsize=10,
    )

    # Panel 3: Mapa de error absoluto amplificado ×5
    err_map = np.abs(original.pixels.astype(np.float64) - reconstructed.pixels.astype(np.float64))
    err_lum = np.mean(err_map, axis=2) if err_map.ndim == 3 else err_map
    axes[0, 2].imshow(np.clip(err_lum * 5.0, 0.0, 1.0), cmap="inferno")
    axes[0, 2].set_title(
        f"3. Mapa de Error |I - Î| (×5)\nMSE = {img_metrics.mse:.5f} | Pearson r = {img_metrics.pearson_corr:.4f}",
        color=palette["ink"],
        fontsize=10,
    )

    for col in range(3):
        axes[0, col].set_xlabel("X [px]")
        axes[0, 2 if col == 2 else col].set_ylabel("Y [px]")
        axes[0, col].grid(False)

    # Panel 4: Comparación temporal de audio reconstruido
    ax_time = axes[1, 0]
    style_axis(ax_time, palette)
    n_zoom = min(len(orig_audio), len(rec_audio), int(0.030 * audio_fs_hz))
    t_ms = np.arange(n_zoom) / float(audio_fs_hz) * 1000.0
    ax_time.plot(t_ms, orig_audio[:n_zoom], color=palette["primary"], linewidth=1.3, label="Audio Original")
    ax_time.plot(
        t_ms,
        rec_audio[:n_zoom],
        color=palette["ok"],
        linestyle="--",
        linewidth=1.2,
        label="Audio Reconstruido",
    )
    ax_time.set_title(
        f"4. Comparativa Temporal de Audio (Zoom 30 ms | r = {audio_metrics['pearson_corr']:.4f})",
        color=palette["ink"],
        fontsize=9.8,
    )
    ax_time.set_xlabel("Tiempo [ms]")
    ax_time.set_ylabel("Amplitud normalizada")
    ax_time.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 5: Comparación espectral de audio
    ax_spec = axes[1, 1]
    style_axis(ax_spec, palette)
    freqs_o, _, db_o = compute_spectrum(orig_audio, sample_rate=audio_fs_hz)
    freqs_r, _, db_r = compute_spectrum(rec_audio, sample_rate=audio_fs_hz)
    ax_spec.plot(freqs_o, db_o, color=palette["primary"], linewidth=1.2, label="|X_orig(f)|")
    ax_spec.plot(freqs_r, db_r, color=palette["accent"], linestyle="--", linewidth=1.1, label="|X_rec(f)|")
    ax_spec.set_title(
        f"5. Espectro Auditivo (SNR Audio = {audio_metrics['snr_db']:.2f} dB)",
        color=palette["ink"],
        fontsize=9.8,
    )
    ax_spec.set_xlabel("Frecuencia [Hz]")
    ax_spec.set_ylabel("Magnitud [dBFS]")
    ax_spec.set_xlim(0.0, audio_fs_hz / 2.0)
    ax_spec.set_ylim(-65.0, 5.0)
    ax_spec.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 6: Resumen cuantitativo de desempeño
    ax_card = axes[1, 2]
    ax_card.set_facecolor(palette["panel"])
    ax_card.axis("off")
    summary_lines = [
        "RESUMEN DE FIDELIDAD Y COMPRESIÓN",
        "─────────────────────────────────────",
        f"Resolución        : {original.width} × {original.height} px",
        f"Compresión Ratio  : {img_metrics.compression_ratio:.2f}×",
        f"Imagen PSNR       : {img_metrics.psnr_db:.2f} dB",
        f"Imagen SSIM       : {img_metrics.ssim:.4f}",
        f"Imagen Pearson r  : {img_metrics.pearson_corr:.4f}",
        f"Imagen RMSE       : {img_metrics.rmse:.5f}",
        f"Audio SNR         : {audio_metrics['snr_db']:.2f} dB",
        f"Audio Pearson r   : {audio_metrics['pearson_corr']:.4f}",
    ]
    ax_card.text(
        0.06,
        0.92,
        "\n".join(summary_lines),
        transform=ax_card.transAxes,
        va="top",
        ha="left",
        family="monospace",
        fontsize=9.5,
        color=palette["ink"],
        bbox=dict(boxstyle="round,pad=0.6", facecolor=palette["legend_bg"], edgecolor=palette["spine"]),
    )

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
