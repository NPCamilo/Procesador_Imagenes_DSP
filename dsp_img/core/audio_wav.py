"""
Utilidades de entrada/salida WAV en disco y memoria para señales moduladas y audio reconstruido.

Diseñado sin dependencias externas fuera de NumPy/SciPy para funcionar tanto
en Windows local como en funciones serverless de solo lectura en Vercel.
"""

from __future__ import annotations

import io
import os
import platform
import tempfile
import time
from typing import Tuple, Union
import numpy as np
from scipy.io import wavfile


def samples_to_wav_bytes(samples: np.ndarray, sample_rate_hz: int, bit_depth: int = 16) -> bytes:
    """Codifica un arreglo normalizado [-1.0, 1.0] a bytes WAV PCM en memoria."""
    if sample_rate_hz <= 0:
        raise ValueError(f"La frecuencia de muestreo debe ser positiva; se recibió {sample_rate_hz}.")
    clipped = np.clip(np.asarray(samples, dtype=np.float32).ravel(), -1.0, 1.0)
    buffer = io.BytesIO()
    if bit_depth == 16:
        wavfile.write(buffer, int(sample_rate_hz), (clipped * 32767.0).astype(np.int16))
    elif bit_depth == 32:
        wavfile.write(buffer, int(sample_rate_hz), clipped.astype(np.float32))
    elif bit_depth == 8:
        wavfile.write(buffer, int(sample_rate_hz), ((clipped + 1.0) * 127.5).astype(np.uint8))
    else:
        raise ValueError(f"Profundidad de bits {bit_depth} no soportada. Use 8, 16 o 32.")
    return buffer.getvalue()


def wav_bytes_to_samples(raw_wav: bytes) -> Tuple[np.ndarray, int, int]:
    """Decodifica bytes WAV a `(samples_float32_mono, sample_rate_hz, bit_depth)`."""
    sample_rate_hz, raw_data = wavfile.read(io.BytesIO(raw_wav))
    if raw_data.dtype == np.int16:
        bit_depth = 16
        arr = raw_data.astype(np.float32) / 32768.0
    elif raw_data.dtype == np.int32:
        bit_depth = 32
        arr = raw_data.astype(np.float32) / 2147483648.0
    elif raw_data.dtype == np.uint8:
        bit_depth = 8
        arr = (raw_data.astype(np.float32) - 128.0) / 128.0
    else:
        bit_depth = 32
        arr = raw_data.astype(np.float32)

    if arr.ndim > 1:
        arr = np.mean(arr, axis=1)
    return np.clip(arr, -1.0, 1.0).astype(np.float32), int(sample_rate_hz), bit_depth


def save_wav(filepath: str, samples: np.ndarray, sample_rate_hz: int, bit_depth: int = 16) -> str:
    """Guarda muestras normalizadas en un archivo WAV en disco."""
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    wav_bytes = samples_to_wav_bytes(samples, sample_rate_hz, bit_depth=bit_depth)
    with open(abs_path, "wb") as handle:
        handle.write(wav_bytes)
    return abs_path


def load_wav(filepath: str) -> Tuple[np.ndarray, int, int]:
    """Carga un archivo WAV desde disco a muestras float32 mono."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No se encontró el archivo WAV: {filepath}")
    with open(filepath, "rb") as handle:
        return wav_bytes_to_samples(handle.read())


def play_wav_or_samples(
    source: Union[str, Tuple[np.ndarray, int]], async_play: bool = False
) -> bool:
    """Reproduce audio localmente usando controladores nativos cuando están disponibles."""
    temp_path = None
    try:
        if isinstance(source, tuple):
            samples, sr = source
            temp_path = os.path.join(
                tempfile.gettempdir(), f"dsp_img_play_{int(time.time() * 1000)}.wav"
            )
            save_wav(temp_path, samples, sr)
            target = temp_path
        else:
            target = source

        if not os.path.exists(target):
            return False

        if platform.system() == "Windows":
            import winsound

            flags = winsound.SND_FILENAME | (winsound.SND_ASYNC if async_play else 0)
            winsound.PlaySound(target, flags)
            return True
        return False
    except Exception:
        return False
    finally:
        if temp_path and not async_play and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
