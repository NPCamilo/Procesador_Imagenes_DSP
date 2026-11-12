"""
Sincronización de trama y extracción de payload desde ondas moduladas o archivos WAV.
"""

from __future__ import annotations

import struct
from typing import Optional, Tuple
import numpy as np
from scipy import signal as sp_signal

from ..core.primitives import pack_bits
from ..modulation.digital import DigitalPassbandModulator
from ..modulation.framing import FULL_PREAMBLE_BITS, SYNC_BITS


def find_frame_start_by_preamble(
    samples: np.ndarray,
    scheme: str,
    sampling_rate_hz: int = 48000,
    samples_per_symbol: int = 32,
    carrier_freq_hz: float = 3000.0,
    fsk_freqs_hz: Optional[Tuple[float, ...]] = None,
    ask_low_amp: float = 0.2,
    search_window_s: float = 3.0,
) -> int:
    """
    Localiza el índice de muestra donde inicia el preámbulo mediante filtro acoplado.

    Permite recibir un archivo `.wav` crudo enviado por un compañero (incluso con
    silencio inicial arbitrario) y alinear exactamente la ventana de símbolos.
    """
    sig = np.asarray(samples, dtype=np.float64).ravel()
    if len(sig) == 0:
        raise ValueError("La forma de onda recibida está vacía.")

    # Detección gruesa de inicio de energía para limitar búsqueda sin perder robustez
    abs_sig = np.abs(sig)
    peak = float(np.max(abs_sig)) or 1.0
    active_indices = np.flatnonzero(abs_sig > 0.08 * peak)
    coarse_start = max(0, int(active_indices[0]) - samples_per_symbol * 4) if len(active_indices) else 0

    ref_mod = DigitalPassbandModulator(
        scheme=scheme,
        sampling_rate_hz=sampling_rate_hz,
        samples_per_symbol=samples_per_symbol,
        carrier_freq_hz=carrier_freq_hz,
        fsk_freqs_hz=fsk_freqs_hz,
        ask_low_amp=ask_low_amp,
        leading_silence_s=0.0,
    )
    ref_preamble = ref_mod.modulate(FULL_PREAMBLE_BITS, add_framing=False).samples.astype(np.float64)
    ref_len = len(ref_preamble)

    window_end = min(len(sig), coarse_start + int(search_window_s * sampling_rate_hz) + ref_len)
    segment = sig[coarse_start:window_end]
    if len(segment) < ref_len:
        return coarse_start

    # Correlación normalizada por ventana deslizante
    corr = sp_signal.correlate(segment, ref_preamble, mode="valid", method="fft")
    # Para BPSK/ASK/QAM puede existir inversión de signo si hubo desfase de 180°,
    # pero en ASK/FSK/nuestro canal directo la correlación positiva máxima marca el inicio exacto.
    if scheme.upper() in ("ASK", "BFSK", "MFSK"):
        best_rel = int(np.argmax(corr))
    else:
        best_rel = int(np.argmax(np.abs(corr)))
    return coarse_start + best_rel


def extract_framed_payload(bits: np.ndarray) -> Tuple[np.ndarray, Optional[bytes], bool]:
    """
    Parsea una secuencia de bits demodulados que comienza en el preámbulo:
      [48b Preámbulo+Sync] + [32b Longitud en bytes] + [Payload]

    Devuelve `(payload_bits, payload_bytes, sync_ok)`.
    """
    arr = np.asarray(bits, dtype=np.uint8).ravel()
    preamble_len = len(FULL_PREAMBLE_BITS)
    header_total = preamble_len + 32
    if len(arr) < header_total:
        return np.zeros(0, dtype=np.uint8), None, False

    # Verificar la palabra sync de 32 bits (tolerando <= 2 bits erróneos en canal ruidoso)
    rx_sync = arr[16:preamble_len]
    sync_matches = int(np.sum(rx_sync == SYNC_BITS))
    sync_ok = sync_matches >= 30

    len_bits = arr[preamble_len:header_total]
    len_bytes = pack_bits(len_bits)
    payload_len_bytes = struct.unpack(">I", len_bytes)[0]
    payload_len_bits = payload_len_bytes * 8

    available = len(arr) - header_total
    if payload_len_bytes == 0 or payload_len_bits > available:
        return arr[header_total:], None, False

    payload_bits = arr[header_total : header_total + payload_len_bits]
    payload_bytes = pack_bits(payload_bits)
    return payload_bits, payload_bytes, sync_ok
