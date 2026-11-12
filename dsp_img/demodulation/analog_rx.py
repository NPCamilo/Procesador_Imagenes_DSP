"""
Demoduladores analógicos (AM envolvente/coherente y FM discriminador de fase).
"""

from __future__ import annotations

from typing import Optional
import numpy as np
from scipy import signal as sp_signal

from ..core.contracts import BaseDemodulator, DemodulatedResult, ModulatedWaveform


def _butter_lowpass(sig: np.ndarray, cutoff_hz: float, fs_hz: int, order: int = 5) -> np.ndarray:
    """Aplica filtro paso bajo Butterworth de fase cero."""
    nyq = 0.5 * float(fs_hz)
    wn = float(np.clip(cutoff_hz / nyq, 0.01, 0.95))
    b, a = sp_signal.butter(order, wn, btype="low", analog=False)
    return sp_signal.filtfilt(b, a, sig)


class AMDemodulator(BaseDemodulator):
    """Demodulador AM DSB-FC por detección de envolvente (Hilbert) o mezcla coherente."""

    def __init__(self, method: str = "coherent", cutoff_freq_hz: float = 4000.0) -> None:
        if method not in ("coherent", "envelope"):
            raise ValueError("El método AM debe ser 'coherent' o 'envelope'.")
        self.method = method
        self.cutoff_freq_hz = float(cutoff_freq_hz)

    def demodulate(
        self,
        waveform: ModulatedWaveform,
        cutoff_freq_hz: Optional[float] = None,
    ) -> DemodulatedResult:
        fs = int(waveform.sampling_rate_hz)
        fc = float(waveform.carrier_freq_hz)
        cutoff = float(cutoff_freq_hz) if cutoff_freq_hz is not None else self.cutoff_freq_hz
        s = np.asarray(waveform.samples, dtype=np.float64)
        t = np.arange(len(s), dtype=np.float64) / float(fs)

        if self.method == "envelope":
            env = np.abs(sp_signal.hilbert(s))
            filtered = _butter_lowpass(env - float(np.mean(env)), cutoff, fs)
        else:
            mixed = s * np.cos(2.0 * np.pi * fc * t) * 2.0
            filtered = _butter_lowpass(mixed, cutoff, fs)
            filtered = filtered - float(np.mean(filtered))

        peak = float(np.max(np.abs(filtered))) or 1.0
        recovered = (filtered / peak * 0.92).astype(np.float32)

        return DemodulatedResult(
            recovered_signal_1d=recovered,
            sampling_rate_hz=fs,
            demodulation_type=f"AM-{self.method.capitalize()}",
            metadata={"carrier_freq_hz": fc, "cutoff_freq_hz": cutoff},
        )


class FMDemodulator(BaseDemodulator):
    """Demodulador FM por derivación de fase instantánea analítica + filtro pasabajo."""

    def __init__(self, cutoff_freq_hz: float = 4000.0) -> None:
        self.cutoff_freq_hz = float(cutoff_freq_hz)

    def demodulate(
        self,
        waveform: ModulatedWaveform,
        cutoff_freq_hz: Optional[float] = None,
    ) -> DemodulatedResult:
        fs = int(waveform.sampling_rate_hz)
        fc = float(waveform.carrier_freq_hz)
        cutoff = float(cutoff_freq_hz) if cutoff_freq_hz is not None else self.cutoff_freq_hz
        s = np.asarray(waveform.samples, dtype=np.float64)

        analytic = sp_signal.hilbert(s)
        inst_phase = np.unwrap(np.angle(analytic))
        inst_freq = np.diff(inst_phase, prepend=inst_phase[0]) * float(fs) / (2.0 * np.pi)
        freq_deviation = inst_freq - fc
        # Eliminar transitorios en extremos de la transformada de Hilbert
        if len(freq_deviation) > 16:
            freq_deviation[:4] = freq_deviation[4]
            freq_deviation[-4:] = freq_deviation[-5]

        filtered = _butter_lowpass(freq_deviation, cutoff, fs)
        filtered = filtered - float(np.mean(filtered))
        peak = float(np.max(np.abs(filtered))) or 1.0
        recovered = (filtered / peak * 0.92).astype(np.float32)

        return DemodulatedResult(
            recovered_signal_1d=recovered,
            sampling_rate_hz=fs,
            demodulation_type="FM-PhaseDiscrim",
            metadata={"carrier_freq_hz": fc, "cutoff_freq_hz": cutoff},
        )
