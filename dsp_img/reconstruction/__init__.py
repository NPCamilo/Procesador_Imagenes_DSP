"""Módulo de reconstrucción DAC, exportación PNG/SVG vectorial y métricas (Fase 5)."""

from .metrics import compute_ssim, evaluate_audio_fidelity, evaluate_image_fidelity
from .reconstructor import SignalReconstructor
from .svg_vectorizer import image_to_svg_string, save_image_svg
from .visualize import plot_full_reconstruction_comparison

__all__ = [
    "SignalReconstructor",
    "compute_ssim",
    "evaluate_audio_fidelity",
    "evaluate_image_fidelity",
    "image_to_svg_string",
    "plot_full_reconstruction_comparison",
    "save_image_svg",
]
