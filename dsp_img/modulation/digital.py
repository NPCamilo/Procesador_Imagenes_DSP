"""
Moduladores digitales pasabanda (ASK, BFSK, MFSK, BPSK, QAM) con salida audible.

Cada esquema hereda de `BaseModulator` y genera un `ModulatedWaveform`
directamente exportable a `.wav` para escuchar los bits o enviarlo a un compañero.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple
import numpy as np

from ..core.contracts import BaseModulator, ModulatedWaveform
from .framing import FULL_PREAMBLE_BITS, build_framed_bitstream

SUPPORTED_DIGITAL_SCHEMES = ("BFSK", "MFSK", "ASK", "BPSK", "16-QAM")

_GRAY_2BIT = {(0, 0): -3.0, (0, 1): -1.0, (1, 1): 1.0, (1, 0): 3.0}


def _pad_bits_to_multiple(bits: np.ndarray, k: int) -> Tuple[np.ndarray, int]:
    """Rellena bits con ceros al final para agrupar símbolos de `k` bits."""
    rem = len(bits) % k
    if rem == 0:
        return bits, 0
    pad_len = k - rem
    return np.pad(bits, (0, pad_len), mode="constant"), pad_len


def _smooth_envelope_edges(envelope: np.ndarray, sps: int, edge_frac: float = 0.12) -> np.ndarray:
    """Suaviza transiciones de amplitud por símbolo sin atenuar los extremos."""
    edge = max(1, int(sps * edge_frac))
    if edge * 2 >= sps:
        return envelope
    kernel = np.hanning(2 * edge + 1)
    kernel /= np.sum(kernel)
    padded = np.pad(envelope, edge, mode="edge")
    return np.convolve(padded, kernel, mode="valid")


class DigitalPassbandModulator(BaseModulator):
    """
    Modulador digital unificado para ASK, BFSK, MFSK (4-FSK), BPSK y 16-QAM.

    Los parámetros por defecto usan `sampling_rate_hz=48000` y ciclos enteros
    por símbolo para garantizar ortogonalidad estricta en banda audible.
    """

    def __init__(
        self,
        scheme: str = "BFSK",
        sampling_rate_hz: int = 48000,
        samples_per_symbol: int = 32,
        carrier_freq_hz: float = 3000.0,
        fsk_freqs_hz: Optional[Tuple[float, ...]] = None,
        ask_low_amp: float = 0.2,
        leading_silence_s: float = 0.02,
    ) -> None:
        normalized = scheme.upper().strip()
        if normalized in ("FSK", "2-FSK"):
            normalized = "BFSK"
        elif normalized in ("4-FSK", "4FSK"):
            normalized = "MFSK"
        elif normalized in ("PSK", "2-PSK"):
            normalized = "BPSK"
        elif normalized in ("QAM", "QAM16", "QAM-16"):
            normalized = "16-QAM"

        if normalized not in SUPPORTED_DIGITAL_SCHEMES:
            raise ValueError(
                f"Esquema {scheme!r} no soportado. Use uno de: {SUPPORTED_DIGITAL_SCHEMES}."
            )

        self.scheme = normalized
        self.sampling_rate_hz = int(sampling_rate_hz)
        self.samples_per_symbol = int(samples_per_symbol)
        self.carrier_freq_hz = float(carrier_freq_hz)
        self.ask_low_amp = float(np.clip(ask_low_amp, 0.0, 0.8))
        self.leading_silence_s = max(0.0, float(leading_silence_s))

        if fsk_freqs_hz is not None:
            self.fsk_freqs_hz = tuple(float(f) for f in fsk_freqs_hz)
        elif self.scheme == "MFSK":
            # 4 tonos ortogonales si sps=48 y fs=48000 (1, 2, 3, 4 ciclos/símbolo)
            self.fsk_freqs_hz = (1000.0, 2000.0, 3000.0, 4000.0)
        else:
            # BFSK ortogonal con sps=32 y fs=48000 (1 y 2 ciclos/símbolo)
            self.fsk_freqs_hz = (1500.0, 3000.0)

        max_tone = max(self.fsk_freqs_hz) if "FSK" in self.scheme else self.carrier_freq_hz
        if self.sampling_rate_hz < 4.0 * max_tone:
            raise ValueError(
                f"fs={self.sampling_rate_hz} Hz debe ser >= 4×f_portadora ({4.0 * max_tone} Hz) para evitar aliasing."
            )

    def modulate(
        self,
        source: Any,
        carrier_freq_hz: Optional[float] = None,
        add_framing: bool = True,
    ) -> ModulatedWaveform:
        """Convierte una trama de bits / paquete `.dspimg` en una onda pasabanda audible."""
        fc = float(carrier_freq_hz) if carrier_freq_hz is not None else self.carrier_freq_hz
        if add_framing:
            bits, payload_bytes_len = build_framed_bitstream(source)
            preamble_len = len(FULL_PREAMBLE_BITS)
        else:
            from .framing import extract_payload_bytes_and_bits

            raw, bits = extract_payload_bytes_and_bits(source)
            payload_bytes_len = len(raw)
            preamble_len = 0

        fs = self.sampling_rate_hz
        sps = self.samples_per_symbol
        bits_per_sym = 1
        extra_meta: Dict[str, Any] = {}

        if self.scheme == "BFSK":
            f0, f1 = self.fsk_freqs_hz[0], self.fsk_freqs_hz[1]
            inst_freqs = np.repeat(np.where(bits == 1, f1, f0), sps)
            phase = 2.0 * np.pi * np.cumsum(inst_freqs) / float(fs)
            wave = np.cos(phase)
            extra_meta["fsk_freqs_hz"] = [f0, f1]

        elif self.scheme == "MFSK":
            bits_per_sym = 2
            padded, pad_bits = _pad_bits_to_multiple(bits, 2)
            sym_idx = padded.reshape(-1, 2)
            sym_vals = (sym_idx[:, 0] << 1) | sym_idx[:, 1]
            freqs_arr = np.array(self.fsk_freqs_hz[:4], dtype=np.float64)
            inst_freqs = np.repeat(freqs_arr[sym_vals], sps)
            phase = 2.0 * np.pi * np.cumsum(inst_freqs) / float(fs)
            wave = np.cos(phase)
            extra_meta["fsk_freqs_hz"] = list(self.fsk_freqs_hz[:4])
            extra_meta["pad_bits"] = pad_bits

        elif self.scheme == "ASK":
            amps = np.where(bits == 1, 1.0, self.ask_low_amp)
            env = _smooth_envelope_edges(np.repeat(amps, sps), sps)
            t = np.arange(len(env), dtype=np.float64) / float(fs)
            wave = env * np.cos(2.0 * np.pi * fc * t)
            extra_meta["ask_low_amp"] = self.ask_low_amp

        elif self.scheme == "BPSK":
            nrz = np.where(bits == 1, 1.0, -1.0)
            env = _smooth_envelope_edges(np.repeat(nrz, sps), sps, edge_frac=0.08)
            t = np.arange(len(env), dtype=np.float64) / float(fs)
            wave = env * np.cos(2.0 * np.pi * fc * t)
            extra_meta["constellation_iq"] = [(-1.0, 0.0), (1.0, 0.0)]

        else:  # 16-QAM
            bits_per_sym = 4
            padded, pad_bits = _pad_bits_to_multiple(bits, 4)
            groups = padded.reshape(-1, 4)
            i_syms = np.array([_GRAY_2BIT[(int(b0), int(b1))] for b0, b1 in groups[:, :2]])
            q_syms = np.array([_GRAY_2BIT[(int(b2), int(b3))] for b2, b3 in groups[:, 2:]])
            # Normalizar constelación 16-QAM para que el pico no exceda 1.0
            scale = 1.0 / (3.0 * np.sqrt(2.0))
            i_wave = np.repeat(i_syms * scale, sps)
            q_wave = np.repeat(q_syms * scale, sps)
            t = np.arange(len(i_wave), dtype=np.float64) / float(fs)
            wave = i_wave * np.cos(2.0 * np.pi * fc * t) - q_wave * np.sin(2.0 * np.pi * fc * t)
            pts = np.unique(np.column_stack([i_syms * scale, q_syms * scale]), axis=0)
            extra_meta["constellation_iq"] = [(float(x), float(y)) for x, y in pts]
            extra_meta["pad_bits"] = pad_bits

        lead_samples = int(round(self.leading_silence_s * fs))
        if lead_samples > 0:
            wave = np.concatenate([np.zeros(lead_samples, dtype=np.float64), wave])

        peak = float(np.max(np.abs(wave))) or 1.0
        wave_norm = (wave / peak * 0.92).astype(np.float32)
        baud_rate = float(fs / sps)
        bit_rate = baud_rate * bits_per_sym

        return ModulatedWaveform(
            samples=wave_norm,
            sampling_rate_hz=fs,
            carrier_freq_hz=fc if "FSK" not in self.scheme else float(np.mean(self.fsk_freqs_hz)),
            modulation_type=self.scheme,
            is_digital=True,
            baud_rate=baud_rate,
            preamble_bits=preamble_len,
            metadata={
                "samples_per_symbol": sps,
                "bits_per_symbol": bits_per_sym,
                "bit_rate_bps": bit_rate,
                "total_frame_bits": int(len(bits)),
                "payload_bytes_len": int(payload_bytes_len),
                "has_framing": add_framing,
                "lead_silence_samples": lead_samples,
                **extra_meta,
            },
        )
