"""
Sistema visual accesible (paleta Okabe-Ito) para todas las figuras del proyecto.

Adaptado de `Laboratorio_ADC_DAC/tema.py` con soporte unificado para modo
oscuro (consola técnica / web) y modo claro (informe impreso).
"""

from __future__ import annotations

from typing import Dict
import matplotlib
import matplotlib.pyplot as plt

OKABE_ITO: Dict[str, str] = {
    "blue": "#0072B2",
    "sky": "#56B4E9",
    "orange": "#E69F00",
    "vermillion": "#D55E00",
    "green": "#009E73",
    "purple": "#CC79A7",
    "yellow": "#F0E442",
}

THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "bg": "#0D1117",
        "panel": "#161B22",
        "ink": "#F0F6FC",
        "muted": "#9BA3B0",
        "grid": "#2A313C",
        "spine": "#30363D",
        "legend_bg": "#1C2128",
        "primary": "#56B4E9",
        "accent": "#E69F00",
        "ok": "#009E73",
        "error": "#D55E00",
        "secondary": "#CC79A7",
    },
    "light": {
        "bg": "#FBFAF7",
        "panel": "#FBFAF7",
        "ink": "#1A1A1A",
        "muted": "#6B6862",
        "grid": "#E8E5DF",
        "spine": "#D8D4CC",
        "legend_bg": "#FFFFFF",
        "primary": "#0072B2",
        "accent": "#E69F00",
        "ok": "#009E73",
        "error": "#D55E00",
        "secondary": "#CC79A7",
    },
}


def apply_plot_theme(mode: str = "dark") -> Dict[str, str]:
    """Configura `matplotlib` en modo headless seguro y devuelve la paleta activa."""
    matplotlib.use("Agg", force=False)
    palette = THEMES.get(mode, THEMES["dark"])
    plt.rcParams.update(
        {
            "figure.facecolor": palette["bg"],
            "savefig.facecolor": palette["bg"],
            "savefig.dpi": 300,
            "axes.facecolor": palette["panel"],
            "axes.edgecolor": palette["spine"],
            "axes.labelcolor": palette["muted"],
            "axes.titlesize": 11.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.5,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": palette["grid"],
            "grid.linewidth": 0.7,
            "text.color": palette["ink"],
            "xtick.color": palette["muted"],
            "ytick.color": palette["muted"],
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "font.sans-serif": ["DejaVu Sans", "Segoe UI", "Arial"],
            "axes.unicode_minus": False,
        }
    )
    return palette


def style_axis(ax: plt.Axes, palette: Dict[str, str]) -> None:
    """Aplica estilo consistente a un eje individual."""
    ax.set_facecolor(palette["panel"])
    ax.tick_params(colors=palette["muted"])
    ax.grid(True, axis="y", color=palette["grid"], linestyle="--", linewidth=0.7)
    for spine_name in ("bottom", "left"):
        ax.spines[spine_name].set_color(palette["spine"])
