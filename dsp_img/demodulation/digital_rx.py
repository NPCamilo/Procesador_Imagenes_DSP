"""
Demoduladores digitales pasabanda (BFSK, MFSK, ASK, BPSK, 16-QAM).

Recuperan los bits transmitidos desde una instancia `ModulatedWaveform` o desde
muestras cargadas de un archivo WAV, calculando BER, constelación recibida y
verificación CRC32 del paquete comprimido `.dspimg`.
"""

from __future__ import annotations

import zlib
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ..core.codec import HEADER_STRUCT, MAGIC, VERSION
from ..core.contracts import BaseDemodulator, DemodulatedResult, ModulatedWaveform
from ..modulation.digital import SUPPORTED_DIGITAL_SCHEMES
from .sync import extract_framed_payload, find_frame_start_by_preamble

_GRAY_LEVELS = np.array([-3.0, -1.0, 1.0, 3.0], dtype=np.float64)
_GRAY_TO_BITS = {
    -3.0: (0, 0),
    -1.0: (0, 1),
    1.0: (1, 1),
    3.0: (1, 0),
}


def _check_dspimg_crc(payload_bytes: Optional[bytes]) -> Optional[bool]:
    """Verifica el CRC32 interno del paquete `.dspimg` si los bytes contienen su cabecera."""
    if payload_bytes is None or len(payload_bytes) < HEADER_STRUCT.size:
        return None
    header = payload_bytes[: HEADER_STRUCT.size]
    magic, version, _, _, _, _, _, payload_len, expected_crc = HEADER_STRUCT.unpack(header)
    if magic != MAGIC or version != VERSION:
        return False
    body = payload_bytes[HEADER_STRUCT.size : HEADER_STRUCT.size + payload_len]
    if len(body) != payload_len:
        return False
    actual_crc = zlib.crc32(header[:-4] + body) & 0xFFFFFFFF
    return actual_crc == expected_crc


def _decode_nearest_gray(val: float) -> Tuple[int, int]:
    """Asigna un nivel I/Q recibido al par de bits Gray más cercano en {-3, -1, 1, 3}."""
    idx = int(np.argmin(np.abs(_GRAY_LEVELS - val)))
    return _GRAY_TO_BITS[float(_GRAY_LEVELS[idx])]


class DigitalPassbandDemodulator(BaseDemodulator):
    """Demodulador digital vectorizado para BFSK, MFSK (4-FSK), ASK, BPSK y 16-QAM."""

    def __init__(
        self,
        scheme: Optional[str] = None,
        sampling_rate_hz: int = 48000,
        samples_per_symbol: int = 32,
        carrier_freq_hz: float = 3000.0,
        fsk_freqs_hz: Optional[Tuple[float, ...]] = None,
        ask_low_amp: float = 0.2,
    ) -> None:
        self.scheme = self._normalize_scheme(scheme) if scheme else None
        self.sampling_rate_hz = int(sampling_rate_hz)
        self.samples_per_symbol = int(samples_per_symbol)
        self.carrier_freq_hz = float(carrier_freq_hz)
        self.fsk_freqs_hz = tuple(float(f) for f in fsk_freqs_hz) if fsk_freqs_hz else None
        self.ask_low_amp = float(ask_low_amp)

    @staticmethod
    def _normalize_scheme(scheme: str) -> str:
        norm = scheme.upper().strip()
        aliases = {
            "FSK": "BFSK",
            "2-FSK": "BFSK",
            "4-FSK": "MFSK",
            "4FSK": "MFSK",
            "PSK": "BPSK",
            "2-PSK": "BPSK",
            "QAM": "16-QAM",
            "QAM16": "16-QAM",
            "QAM-16": "16-QAM",
        }
        norm = aliases.get(norm, norm)
        if norm not in SUPPORTED_DIGITAL_SCHEMES:
            raise ValueError(f"Esquema {scheme!r} no soportado.")
        return norm

    def demodulate(
        self,
        waveform: ModulatedWaveform,
        reference_bits: Optional[np.ndarray] = None,
        has_framing: Optional[bool] = None,
        auto_sync: bool = True,
    ) -> DemodulatedResult:
        """
        Demodula una onda digital pasabanda y recupera bits, señal banda base y CRC32.
        """
        meta = waveform.metadata
        scheme = self.scheme or self._normalize_scheme(waveform.modulation_type)
        fs = int(waveform.sampling_rate_hz or self.sampling_rate_hz)
        sps = int(meta.get("samples_per_symbol", self.samples_per_symbol))
        fc = float(waveform.carrier_freq_hz or self.carrier_freq_hz)
        framed = bool(meta.get("has_framing", True)) if has_framing is None else has_framing

        fsk_freqs = tuple(meta["fsk_freqs_hz"]) if "fsk_freqs_hz" in meta else self.fsk_freqs_hz
        if fsk_freqs is None:
            fsk_freqs = (1000.0, 2000.0, 3000.0, 4000.0) if scheme == "MFSK" else (1500.0, 3000.0)

        samples = np.asarray(waveform.samples, dtype=np.float64)
        if auto_sync and framed:
            sync_offset = find_frame_start_by_preamble(
                samples,
                scheme=scheme,
                sampling_rate_hz=fs,
                samples_per_symbol=sps,
                carrier_freq_hz=fc,
                fsk_freqs_hz=fsk_freqs,
                ask_low_amp=float(meta.get("ask_low_amp", self.ask_low_amp)),
            )
        else:
            sync_offset = int(meta.get("lead_silence_samples", 0))

        aligned = samples[sync_offset:]
        num_symbols = len(aligned) // sps
        if num_symbols == 0:
            raise ValueError("No hay suficientes muestras tras la sincronización para demodular un símbolo.")

        blocks = aligned[: num_symbols * sps].reshape(num_symbols, sps)
        t_sym = np.arange(sps, dtype=np.float64) / float(fs)
        extra_meta: Dict[str, Any] = {}

        if scheme in ("BFSK", "MFSK"):
            tones = fsk_freqs[:2] if scheme == "BFSK" else fsk_freqs[:4]
            energies = np.zeros((num_symbols, len(tones)), dtype=np.float64)
            for idx, freq in enumerate(tones):
                c_ref = np.cos(2.0 * np.pi * freq * t_sym)
                s_ref = np.sin(2.0 * np.pi * freq * t_sym)
                i_proj = blocks @ c_ref
                q_proj = blocks @ s_ref
                energies[:, idx] = i_proj**2 + q_proj**2

            decisions = np.argmax(energies, axis=1)
            if scheme == "BFSK":
                raw_bits = decisions.astype(np.uint8)
                e0 = np.sqrt(energies[:, 0])
                e1 = np.sqrt(energies[:, 1])
                soft_bb = np.repeat((e1 - e0) / (e1 + e0 + 1e-12), sps)
            else:
                b_hi = (decisions >> 1) & 1
                b_lo = decisions & 1
                raw_bits = np.column_stack([b_hi, b_lo]).reshape(-1).astype(np.uint8)
                soft_bb = np.repeat((decisions.astype(np.float64) - 1.5) / 1.5, sps)
            extra_meta["tone_energies_preview"] = energies[:24].tolist()

        elif scheme == "ASK":
            # Ventana central para evitar suavizado de bordes
            margin = max(1, int(sps * 0.15))
            core = slice(margin, sps - margin) if (sps - 2 * margin) >= 4 else slice(0, sps)
            t_core = t_sym[core]
            c_ref = np.cos(2.0 * np.pi * fc * t_core)
            s_ref = np.sin(2.0 * np.pi * fc * t_core)
            envelopes = np.sqrt((blocks[:, core] @ c_ref) ** 2 + (blocks[:, core] @ s_ref) ** 2) * (
                2.0 / len(t_core)
            )
            if framed and len(envelopes) >= 16:
                # Calibrar umbral usando el preámbulo alternante [1,0,1,0...]
                pre_env = envelopes[:16]
                threshold = 0.5 * (float(np.mean(pre_env[0::2])) + float(np.mean(pre_env[1::2])))
            else:
                threshold = 0.5 * (float(np.max(envelopes)) + float(np.min(envelopes)))
            raw_bits = (envelopes >= threshold).astype(np.uint8)
            soft_bb = np.repeat((envelopes - threshold) / (float(np.max(envelopes)) + 1e-12), sps)
            extra_meta["ask_threshold"] = float(threshold)

        elif scheme == "BPSK":
            margin = max(1, int(sps * 0.12))
            core = slice(margin, sps - margin) if (sps - 2 * margin) >= 4 else slice(0, sps)
            t_core = t_sym[core]
            c_ref = np.cos(2.0 * np.pi * fc * t_core) * (2.0 / len(t_core))
            s_ref = -np.sin(2.0 * np.pi * fc * t_core) * (2.0 / len(t_core))
            i_rx = blocks[:, core] @ c_ref
            q_rx = blocks[:, core] @ s_ref
            # Resolver ambigüedad de 180° si el primer bit del preámbulo [1,0,1,0...] salió invertido
            if framed and len(i_rx) >= 4 and (i_rx[0] < 0 < i_rx[1]):
                i_rx = -i_rx
                q_rx = -q_rx
            raw_bits = (i_rx >= 0.0).astype(np.uint8)
            soft_bb = np.repeat(i_rx / (float(np.max(np.abs(i_rx))) + 1e-12), sps)
            extra_meta["rx_constellation_iq"] = [(float(i), float(q)) for i, q in zip(i_rx[:256], q_rx[:256])]

        else:  # 16-QAM
            c_ref = np.cos(2.0 * np.pi * fc * t_sym) * (2.0 / sps)
            s_ref = -np.sin(2.0 * np.pi * fc * t_sym) * (2.0 / sps)
            i_rx = blocks @ c_ref
            q_rx = blocks @ s_ref
            # Los primeros 4 símbolos del preámbulo alternante (1,0,1,0) transmiten (+3, +3)
            if framed and len(i_rx) >= 4:
                gain_i = float(np.mean(i_rx[:4])) / 3.0
                gain_q = float(np.mean(q_rx[:4])) / 3.0
                gain = 0.5 * (abs(gain_i) + abs(gain_q))
                if gain > 1e-6:
                    i_scaled = i_rx / gain
                    q_scaled = q_rx / gain
                else:
                    i_scaled, q_scaled = i_rx, q_rx
            else:
                peak_iq = max(float(np.max(np.abs(i_rx))), float(np.max(np.abs(q_rx))), 1e-9)
                i_scaled = i_rx / peak_iq * 3.0
                q_scaled = q_rx / peak_iq * 3.0

            decoded_bits: List[int] = []
            for iv, qv in zip(i_scaled, q_scaled):
                b0, b1 = _decode_nearest_gray(float(iv))
                b2, b3 = _decode_nearest_gray(float(qv))
                decoded_bits.extend([b0, b1, b2, b3])
            raw_bits = np.asarray(decoded_bits, dtype=np.uint8)
            soft_bb = np.repeat(i_scaled / 3.0, sps)
            extra_meta["rx_constellation_iq"] = [
                (float(i), float(q)) for i, q in zip(i_scaled[:256], q_scaled[:256])
            ]

        # Recortar relleno de bits final si existía en símbolos multi-bit (MFSK / 16-QAM)
        total_expected = meta.get("total_frame_bits")
        if total_expected is not None and int(total_expected) <= len(raw_bits):
            raw_bits = raw_bits[: int(total_expected)]

        payload_bytes: Optional[bytes] = None
        payload_bits = raw_bits
        sync_ok = True
        if framed:
            payload_bits, payload_bytes, sync_ok = extract_framed_payload(raw_bits)

        crc_valid = _check_dspimg_crc(payload_bytes) if framed else None

        ber: Optional[float] = None
        if reference_bits is not None:
            ref = np.asarray(reference_bits, dtype=np.uint8).ravel()
            compare_len = min(len(ref), len(payload_bits))
            if compare_len > 0:
                ber = float(np.mean(ref[:compare_len] != payload_bits[:compare_len]))

        return DemodulatedResult(
            recovered_signal_1d=np.clip(soft_bb, -1.0, 1.0).astype(np.float32),
            sampling_rate_hz=fs,
            demodulation_type=f"{scheme}-Demod",
            detected_bits=payload_bits,
            bit_error_rate=ber,
            crc_valid=crc_valid,
            sync_offset_samples=sync_offset,
            metadata={
                "scheme": scheme,
                "sync_ok": sync_ok,
                "recovered_bytes": payload_bytes,
                "num_recovered_bits": int(len(payload_bits)),
                "frame_bits": raw_bits,
                **extra_meta,
            },
        )
