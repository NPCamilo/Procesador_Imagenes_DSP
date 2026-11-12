"""
Visualización temporal, espectral y de constelación para señales moduladas (Punto 4).
"""

from __future__ import annotations

import os
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np

from ..core.audio_wav import save_wav
from ..core.contracts import ModulatedWaveform
from ..core.primitives import compute_spectrum
from ..core.theme import apply_plot_theme, style_axis


def export_modulated_audio(modulated: ModulatedWaveform, filepath: str, bit_depth: int = 16) -> str:
    """Exporta la señal modulada pasabanda a un archivo WAV PCM audible."""
    return save_wav(filepath, modulated.samples, modulated.sampling_rate_hz, bit_depth=bit_depth)


def plot_modulated_signal(
    modulated: ModulatedWaveform,
    source_bits: Optional[np.ndarray] = None,
    zoom_ms: float = 15.0,
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Genera una figura diagnóstica de modulación:
      1. Banda base de entrada (primeros bits NRZ o envolvente de mensaje).
      2. Zoom temporal de la señal modulada pasabanda s(t).
      3. Espectro unilateral FFT |S(f)| con portadora(s) señalada(s).
      4. Constelación I/Q (cuando aplica BPSK / 16-QAM) o distribución espectral/envolvente.
    """
    palette = apply_plot_theme(theme_mode)
    fs = modulated.sampling_rate_hz
    samples = modulated.samples
    lead = int(modulated.metadata.get("lead_silence_samples", 0))
    active_samples = samples[lead:] if lead < len(samples) else samples

    fig, axes = plt.subplots(2, 2, figsize=(14, 8.5), constrained_layout=True)

    # Panel 1: Tren de bits de entrada o señal mensaje analógica
    ax_in = axes[0, 0]
    style_axis(ax_in, palette)
    if modulated.is_digital and source_bits is not None and len(source_bits) > 0:
        n_bits_show = min(48, len(source_bits))
        bit_slice = np.asarray(source_bits[:n_bits_show], dtype=int)
        ax_in.step(
            np.arange(n_bits_show),
            bit_slice,
            where="post",
            color=palette["accent"],
            linewidth=1.6,
            label="Bits comprimidos",
        )
        ax_in.set_title(
            f"1. Flujo Binario de Entrada (primeros {n_bits_show} de {len(source_bits):,} bits)",
            color=palette["ink"],
            fontsize=10,
        )
        ax_in.set_xlabel("Índice de bit k")
        ax_in.set_ylabel("Nivel lógico [0 / 1]")
        ax_in.set_ylim(-0.15, 1.25)
        ax_in.set_yticks([0, 1])
    else:
        msg = modulated.metadata.get("message_samples", active_samples[:1000])
        n_msg = min(len(msg), int(zoom_ms * 1e-3 * fs))
        t_msg = np.arange(n_msg) / float(fs) * 1000.0
        ax_in.plot(t_msg, msg[:n_msg], color=palette["accent"], linewidth=1.3, label="Mensaje m(t)")
        ax_in.set_title("1. Señal Moduladora Banda Base m(t)", color=palette["ink"], fontsize=10)
        ax_in.set_xlabel("Tiempo [ms]")
        ax_in.set_ylabel("Amplitud")
    ax_in.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 2: Zoom temporal de la portadora modulada
    ax_wave = axes[0, 1]
    style_axis(ax_wave, palette)
    n_zoom = min(len(active_samples), max(64, int(zoom_ms * 1e-3 * fs)))
    t_ms = np.arange(n_zoom) / float(fs) * 1000.0
    ax_wave.plot(t_ms, active_samples[:n_zoom], color=palette["primary"], linewidth=1.1, label="s(t) Modulada")
    ax_wave.set_title(
        f"2. Señal Modulada {modulated.modulation_type} — Zoom ({zoom_ms:.1f} ms | Duración total {modulated.duration_s:.2f} s)",
        color=palette["ink"],
        fontsize=10,
    )
    ax_wave.set_xlabel("Tiempo [ms]")
    ax_wave.set_ylabel("Amplitud normalizada")
    ax_wave.set_ylim(-1.05, 1.05)
    ax_wave.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel 3: Espectro FFT de s(t)
    ax_spec = axes[1, 0]
    style_axis(ax_spec, palette)
    spec_slice = active_samples[: min(len(active_samples), fs * 2)]
    freqs, _, mag_db = compute_spectrum(spec_slice, sample_rate=fs, window="hann")
    ax_spec.plot(freqs, mag_db, color=palette["secondary"], linewidth=1.1, label="|S(f)|")
    fsk_tones = modulated.metadata.get("fsk_freqs_hz")
    if fsk_tones:
        tone_colors = [palette["ok"], palette["accent"], palette["primary"], palette["error"]]
        for idx, tone in enumerate(fsk_tones):
            ax_spec.axvline(
                tone,
                color=tone_colors[idx % len(tone_colors)],
                linestyle="--",
                linewidth=1.2,
                label=f"f{idx}={tone:.0f} Hz",
            )
        max_f_plot = max(fsk_tones) * 1.6
    else:
        ax_spec.axvline(
            modulated.carrier_freq_hz,
            color=palette["error"],
            linestyle="--",
            linewidth=1.3,
            label=f"Portadora fc={modulated.carrier_freq_hz:.0f} Hz",
        )
        max_f_plot = min(fs / 2.0, modulated.carrier_freq_hz * 2.5)
    ax_spec.set_title(f"3. Espectro Pasabanda ({modulated.modulation_type})", color=palette["ink"], fontsize=10)
    ax_spec.set_xlabel("Frecuencia [Hz]")
    ax_spec.set_ylabel("Magnitud [dBFS]")
    ax_spec.set_xlim(0.0, max_f_plot)
    ax_spec.set_ylim(-65.0, 5.0)
    ax_spec.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=7.5)

    # Panel 4: Constelación I/Q o Envolvente / Frecuencia instantánea
    ax_extra = axes[1, 1]
    style_axis(ax_extra, palette)
    constellation = modulated.metadata.get("constellation_iq")
    if constellation:
        pts = np.asarray(constellation, dtype=np.float64)
        ax_extra.scatter(pts[:, 0], pts[:, 1], s=70, color=palette["ok"], edgecolors=palette["ink"], zorder=3)
        ax_extra.axhline(0.0, color=palette["spine"], linewidth=0.9)
        ax_extra.axvline(0.0, color=palette["spine"], linewidth=0.9)
        ax_extra.set_title(f"4. Diagrama de Constelación I/Q ({modulated.modulation_type})", color=palette["ink"], fontsize=10)
        ax_extra.set_xlabel("Componente en Fase I")
        ax_extra.set_ylabel("Componente en Cuadratura Q")
        ax_extra.set_aspect("equal", adjustable="datalim")
    else:
        n_env = min(len(active_samples), max(64, int(zoom_ms * 1e-3 * fs)))
        t_env = np.arange(n_env) / float(fs) * 1000.0
        power_inst = active_samples[:n_env] ** 2
        ax_extra.plot(t_env, power_inst, color=palette["ok"], linewidth=1.1, label="Potencia instantánea s²(t)")
        ax_extra.set_title(
            f"4. Tasa de Transmisión: {modulated.metadata.get('bit_rate_bps', 0):.0f} bps ({modulated.baud_rate:.0f} Bd)"
            if modulated.is_digital
            else "4. Potencia Instantánea de Portadora s²(t)",
            color=palette["ink"],
            fontsize=10,
        )
        ax_extra.set_xlabel("Tiempo [ms]")
        ax_extra.set_ylabel("Potencia normalizada")
        ax_extra.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
