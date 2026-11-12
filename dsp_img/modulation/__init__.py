"""Módulo de modulación pasabanda analógica y digital con síntesis audible (Fase 3)."""

from .analog import AMModulator, FMModulator
from .digital import SUPPORTED_DIGITAL_SCHEMES, DigitalPassbandModulator
from .framing import FULL_PREAMBLE_BITS, SYNC_WORD, build_framed_bitstream, extract_payload_bytes_and_bits
from .visualize import export_modulated_audio, plot_modulated_signal

__all__ = [
    "FULL_PREAMBLE_BITS",
    "SUPPORTED_DIGITAL_SCHEMES",
    "SYNC_WORD",
    "AMModulator",
    "DigitalPassbandModulator",
    "FMModulator",
    "build_framed_bitstream",
    "export_modulated_audio",
    "extract_payload_bytes_and_bits",
    "plot_modulated_signal",
]
