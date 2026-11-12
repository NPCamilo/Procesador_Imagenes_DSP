"""
Visualización diagnóstica y exportación audible de señales demoduladas (Punto 5).
"""

from __future__ import annotations

import os
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np

from ..core.audio_wav import save_wav
from ..core.contracts import DemodulatedResult, ModulatedWaveform
from ..core.primitives import compute_spectrum, pearson_correlation
from ..core.theme import apply_plot_theme, style_axis


def export_demodulated_audio(
    demodulated: DemodulatedResult, filepath: str, bit_depth: int = 16
) -> str:
    """Exporta la señal banda base demodulada a un archivo WAV PCM audible."""
    return save_wav(
        filepath,
        demodulated.recovered_signal_1d,
        demodulated.sampling_rate_hz,
        bit_depth=bit_depth,
    )


def plot_demodulated_recovery(
    modulated: ModulatedWaveform,
    demodulated: DemodulatedResult,
    reference_bits: Optional[np.ndarray] = None,
    reference_analog: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Muestra gráficamente la recuperación de información tras la demodulación:
      1. Comparación directa (bits TX vs RX o señal analógica original vs demodulada).
      2. Forma de onda banda base recuperada (zoom temporal).
      3. Espectro de la señal demodulada recuperada.
      4. Constelación I/Q recibida (si aplica) o correlación/diagnóstico BER + CRC32.
    """
    palette = apply_plot_theme(theme_mode)
    fs = demodulated.sampling_rate_hz
    rec = demodulated.recovered_signal_1d

    fig, axes = plt.subplots(2, 2, figsize=(14, 8.5), constrained_layout=True)

    # Panel 1: Comparativa directa de información recuperada
    ax_cmp = axes[0, 0]
    style_axis(ax_cmp, palette)
    if modulated.is_digital and demodulated.detected_bits is not None:
        rx_bits = demodulated.detected_bits
        n_show = min(48, len(rx_bits))
        if reference_bits is not None and len(reference_bits) >= n_show:
            ax_cmp.step(
                np.arange(n_show),
                reference_bits[:n_show],
                where="post",
                color=palette["primary"],
                linewidth=1.8,
                alpha=0.75,
                label="Bits TX originales",
            )
        ax_cmp.step(
            np.arange(n_show),
            rx_bits[:n_show],
            where="post",
            color=palette["ok"],
            linestyle="--",
            linewidth=1.5,
            label="Bits RX demodulados",
        )
        ber_txt = f"BER = {demodulated.bit_error_rate:.2e}" if demodulated.bit_error_rate is not None else "RX ciego"
        crc_txt = "CRC32 OK" if demodulated.crc_valid else ("CRC ERROR" if demodulated.crc_valid is False else "Sin CRC")
        ax_cmp.set_title(
            f"1. Bits Recuperados ({demodulated.demodulation_type}) | {ber_txt} | {crc_txt}",
            color=palette["ink"],
            fontsize=9.8,
        )
        ax_cmp.set_xlabel("Índice de bit k")
        ax_cmp.set_ylabel("Nivel lógico [0 / 1]")
        ax_cmp.set_ylim(-0.15, 1.28)
        ax_cmp.set_yticks([0, 1])
    else:
        n_cmp = min(len(rec), len(reference_analog) if reference_analog is not None else len(rec), int(0.025 * fs))
        t_ms = np.arange(n_cmp) / float(fs) * 1000.0
        if reference_analog is not None:
            ref_slice = reference_analog[:n_cmp] / (float(np.max(np.abs(reference_analog[:n_cmp]))) or 1.0) * 0.92
            r_corr = pearson_correlation(ref_slice, rec[:n_cmp])
            ax_cmp.plot(t_ms, ref_slice, color=palette["primary"], linewidth=1.4, alpha=0.7, label="Mensaje original m(t)")
            title_txt = f"1. Recuperación Analógica {demodulated.demodulation_type} (r = {r_corr:.4f})"
        else:
            title_txt = f"1. Señal Demodulada {demodulated.demodulation_type}"
        ax_cmp.plot(t_ms, rec[:n_cmp], color=palette["ok"], linestyle="--", linewidth=1.3, label="Demodulada m̂(t)")
        ax_cmp.set_title(title_txt, color=palette["ink"], fontsize=9.8)
        ax_cmp.set_xlabel("Tiempo [ms]")
        ax_cmp.set_ylabel("Amplitud normalizada")
    ax_cmp.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 2: Señal banda base demodulada (zoom)
    ax_bb = axes[0, 1]
    style_axis(ax_bb, palette)
    n_zoom = min(len(rec), max(128, int(0.025 * fs)))
    t_bb = np.arange(n_zoom) / float(fs) * 1000.0
    ax_bb.plot(t_bb, rec[:n_zoom], color=palette["accent"], linewidth=1.2, label="Banda base recuperada")
    ax_bb.set_title(
        f"2. Señal Demodulada Banda Base (Sync offset = {demodulated.sync_offset_samples} muestras)",
        color=palette["ink"],
        fontsize=9.8,
    )
    ax_bb.set_xlabel("Tiempo [ms]")
    ax_bb.set_ylabel("Amplitud normalizada")
    ax_bb.set_ylim(-1.08, 1.08)
    ax_bb.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 3: Espectro de la señal demodulada
    ax_sp = axes[1, 0]
    style_axis(ax_sp, palette)
    spec_slice = rec[: min(len(rec), fs * 2)]
    freqs, _, mag_db = compute_spectrum(spec_slice, sample_rate=fs)
    ax_sp.plot(freqs, mag_db, color=palette["secondary"], linewidth=1.1, label="|M̂(f)| Demodulada")
    ax_sp.set_title("3. Espectro de la Señal Demodulada", color=palette["ink"], fontsize=9.8)
    ax_sp.set_xlabel("Frecuencia [Hz]")
    ax_sp.set_ylabel("Magnitud [dBFS]")
    ax_sp.set_xlim(0.0, min(fs / 2.0, 6000.0))
    ax_sp.set_ylim(-65.0, 5.0)
    ax_sp.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 4: Constelación RX o distribución de decisión
    ax_rx = axes[1, 1]
    style_axis(ax_rx, palette)
    rx_iq = demodulated.metadata.get("rx_constellation_iq")
    if rx_iq:
        pts = np.asarray(rx_iq, dtype=np.float64)
        ax_rx.scatter(pts[:, 0], pts[:, 1], s=28, alpha=0.85, color=palette["ok"], edgecolors=palette["ink"], linewidths=0.4)
        ax_rx.axhline(0.0, color=palette["spine"], linewidth=0.9)
        ax_rx.axvline(0.0, color=palette["spine"], linewidth=0.9)
        ax_rx.set_title(f"4. Constelación Recibida ({demodulated.demodulation_type})", color=palette["ink"], fontsize=9.8)
        ax_rx.set_xlabel("I recibido")
        ax_rx.set_ylabel("Q recibido")
        ax_rx.set_aspect("equal", adjustable="datalim")
    else:
        ax_rx.hist(rec, bins=40, density=True, color=palette["primary"], alpha=0.8, edgecolor=palette["bg"])
        ax_rx.set_title("4. Distribución de Amplitudes Demoduladas", color=palette["ink"], fontsize=9.8)
        ax_rx.set_xlabel("Amplitud de decisión")
        ax_rx.set_ylabel("Densidad")

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
