"""
Moduladores analógicos pasabanda (AM DSB-FC y FM) sobre señales 1D de imagen.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple
import numpy as np
from scipy import signal as sp_signal

from ..core.contracts import BaseModulator, ImageSignal, ModulatedWaveform


def _extract_1d_message(source: Any, default_fs_hz: int = 16000) -> Tuple[np.ndarray, int]:
    """Extrae una señal banda base normalizada [-1, 1] y su tasa de muestreo."""
    if isinstance(source, ImageSignal):
        # Usamos una ventana representativa (por defecto 12 filas alrededor del centro)
        lum = source.to_luminance()
        mid = source.height // 2
        half = min(6, source.height // 4)
        strip = lum[max(0, mid - half) : min(source.height, mid + half + 1), :].reshape(-1)
        ac = strip - float(np.mean(strip))
        peak = float(np.max(np.abs(ac))) or 1.0
        return (ac / peak).astype(np.float64), source.sample_rate_1d_hz

    arr = np.asarray(source, dtype=np.float64).ravel()
    arr = arr - float(np.mean(arr))
    peak = float(np.max(np.abs(arr))) or 1.0
    return (arr / peak).astype(np.float64), default_fs_hz


def _ensure_carrier_sampling(
    message: np.ndarray, fs_in: int, carrier_freq_hz: float, target_fs_hz: int
) -> Tuple[np.ndarray, int]:
    """Remuestrea la señal banda base si `fs_in` no cumple fs >= 6*fc."""
    min_fs = max(int(target_fs_hz), int(np.ceil(8.0 * carrier_freq_hz)))
    if fs_in >= min_fs:
        return message, fs_in
    ratio = int(np.ceil(min_fs / float(fs_in)))
    upsampled = sp_signal.resample_poly(message, ratio, 1)
    peak = float(np.max(np.abs(upsampled))) or 1.0
    return np.clip(upsampled / peak, -1.0, 1.0), fs_in * ratio


class AMModulator(BaseModulator):
    """Modulador de Amplitud Convencional (AM DSB-FC): s(t) = [Ac + m(t)] cos(2π fc t)."""

    def __init__(
        self,
        carrier_freq_hz: float = 4000.0,
        mod_index: float = 0.80,
        target_fs_hz: int = 48000,
    ) -> None:
        if not (0.05 <= mod_index <= 0.98):
            raise ValueError("El índice de modulación μ debe estar en [0.05, 0.98] para evitar sobremodulación.")
        self.carrier_freq_hz = float(carrier_freq_hz)
        self.mod_index = float(mod_index)
        self.target_fs_hz = int(target_fs_hz)

    def modulate(
        self,
        source: Any,
        carrier_freq_hz: Optional[float] = None,
        source_fs_hz: int = 16000,
    ) -> ModulatedWaveform:
        fc = float(carrier_freq_hz) if carrier_freq_hz is not None else self.carrier_freq_hz
        msg, fs_in = _extract_1d_message(source, default_fs_hz=source_fs_hz)
        msg_up, fs_out = _ensure_carrier_sampling(msg, fs_in, fc, self.target_fs_hz)

        t = np.arange(len(msg_up), dtype=np.float64) / float(fs_out)
        ac = 1.0 / self.mod_index
        s_am = (ac + msg_up) * np.cos(2.0 * np.pi * fc * t)
        peak = float(np.max(np.abs(s_am))) or 1.0
        s_norm = (s_am / peak * 0.92).astype(np.float32)

        return ModulatedWaveform(
            samples=s_norm,
            sampling_rate_hz=fs_out,
            carrier_freq_hz=fc,
            modulation_type="AM-DSB-FC",
            is_digital=False,
            metadata={
                "mod_index": self.mod_index,
                "source_fs_hz": fs_in,
                "message_samples": msg_up.astype(np.float32),
            },
        )


class FMModulator(BaseModulator):
    """Modulador de Frecuencia (FM): s(t) = cos(2π fc t + 2π Δf ∫ m(τ) dτ)."""

    def __init__(
        self,
        carrier_freq_hz: float = 4000.0,
        freq_dev_hz: float = 1200.0,
        target_fs_hz: int = 48000,
    ) -> None:
        self.carrier_freq_hz = float(carrier_freq_hz)
        self.freq_dev_hz = float(freq_dev_hz)
        self.target_fs_hz = int(target_fs_hz)

    def modulate(
        self,
        source: Any,
        carrier_freq_hz: Optional[float] = None,
        source_fs_hz: int = 16000,
    ) -> ModulatedWaveform:
        fc = float(carrier_freq_hz) if carrier_freq_hz is not None else self.carrier_freq_hz
        msg, fs_in = _extract_1d_message(source, default_fs_hz=source_fs_hz)
        msg_up, fs_out = _ensure_carrier_sampling(msg, fs_in, fc + self.freq_dev_hz, self.target_fs_hz)

        t = np.arange(len(msg_up), dtype=np.float64) / float(fs_out)
        integral_m = np.cumsum(msg_up) / float(fs_out)
        phase = 2.0 * np.pi * fc * t + 2.0 * np.pi * self.freq_dev_hz * integral_m
        s_fm = (0.92 * np.cos(phase)).astype(np.float32)

        return ModulatedWaveform(
            samples=s_fm,
            sampling_rate_hz=fs_out,
            carrier_freq_hz=fc,
            modulation_type="FM",
            is_digital=False,
            metadata={
                "freq_dev_hz": self.freq_dev_hz,
                "source_fs_hz": fs_in,
                "message_samples": msg_up.astype(np.float32),
            },
        )
