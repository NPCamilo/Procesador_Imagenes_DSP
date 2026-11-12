"""Módulo de sincronización y demodulación digital/analógica (Fase 4)."""

from .analog_rx import AMDemodulator, FMDemodulator
from .digital_rx import DigitalPassbandDemodulator
from .sync import extract_framed_payload, find_frame_start_by_preamble
from .visualize import export_demodulated_audio, plot_demodulated_recovery

__all__ = [
    "AMDemodulator",
    "DigitalPassbandDemodulator",
    "FMDemodulator",
    "export_demodulated_audio",
    "extract_framed_payload",
    "find_frame_start_by_preamble",
    "plot_demodulated_recovery",
]
