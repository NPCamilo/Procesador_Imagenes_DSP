"""
Encapsulado de trama física con preámbulo de sincronización para transmisión audible.

Estructura de la trama enviada por el modulador digital:
  [Preámbulo alternante 16b] + [Palabra Sync 32b: 0xD391A54B] + [Longitud bytes 32b] + [Payload bits]
"""

from __future__ import annotations

import struct
from typing import Any, Tuple
import numpy as np

from ..core.contracts import CompressedPacket, QuantizedStream
from ..core.primitives import pack_bits, unpack_bits

SYNC_WORD = 0xD391A54B
PREAMBLE_ALT_BITS = np.tile(np.array([1, 0], dtype=np.uint8), 8)  # 16 bits
SYNC_BITS = unpack_bits(struct.pack(">I", SYNC_WORD), total_bits=32)  # 32 bits
FULL_PREAMBLE_BITS = np.concatenate([PREAMBLE_ALT_BITS, SYNC_BITS])  # 48 bits


def extract_payload_bytes_and_bits(source: Any) -> Tuple[bytes, np.ndarray]:
    """
    Extrae bytes y arreglo 1D de bits desde `CompressedPacket`, `QuantizedStream`,
    `bytes` o un arreglo binario `np.ndarray`.
    """
    if isinstance(source, CompressedPacket):
        raw = source.wire_bytes
        return raw, unpack_bits(raw)
    if isinstance(source, QuantizedStream):
        raw = source.to_bytes()
        return raw, source.bitstream.astype(np.uint8)
    if isinstance(source, (bytes, bytearray)):
        raw = bytes(source)
        return raw, unpack_bits(raw)

    arr = np.asarray(source, dtype=np.uint8).ravel()
    if not np.all((arr == 0) | (arr == 1)):
        raise ValueError("El flujo binario de entrada solo puede contener valores 0 y 1.")
    return pack_bits(arr), arr


def build_framed_bitstream(source: Any) -> Tuple[np.ndarray, int]:
    """
    Construye la trama completa lista para modulación digital.

    Devuelve `(frame_bits_uint8, payload_byte_count)`.
    """
    raw_bytes, _ = extract_payload_bytes_and_bits(source)
    payload_len = len(raw_bytes)
    len_bits = unpack_bits(struct.pack(">I", payload_len), total_bits=32)
    payload_bits = unpack_bits(raw_bytes, total_bits=payload_len * 8)
    frame = np.concatenate([FULL_PREAMBLE_BITS, len_bits, payload_bits]).astype(np.uint8)
    return frame, payload_len
