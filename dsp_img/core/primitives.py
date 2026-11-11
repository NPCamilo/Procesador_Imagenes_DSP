"""
Primitivas matemáticas y métricas fundamentales de Procesamiento Digital de Señales.

Adaptado y unificado a partir de las librerías validadas del curso en
`Generos_Musicales_ADC_DAC/nucleo/primitivas.py` y `Proyecto_Comunicaciones_DSP`.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
import numpy as np

DB_PER_BIT = 6.0206
FULL_SCALE_PENALTY_DB = 1.76
ACTIVE_THRESHOLD = 1e-12


def pack_bits(bitstream: np.ndarray) -> bytes:
    """Empaqueta un arreglo 1D de bits (0/1) en bytes (rellenando el último byte con ceros)."""
    bits = np.asarray(bitstream, dtype=np.uint8).reshape(-1)
    if len(bits) == 0:
        return b""
    remainder = len(bits) % 8
    if remainder:
        bits = np.pad(bits, (0, 8 - remainder), mode="constant")
    return np.packbits(bits, bitorder="big").tobytes()


def unpack_bits(raw_bytes: bytes, total_bits: int | None = None) -> np.ndarray:
    """Desempaqueta una secuencia de bytes en un arreglo 1D de bits (uint8 0/1)."""
    if not raw_bytes:
        return np.zeros(0, dtype=np.uint8)
    byte_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    bits = np.unpackbits(byte_arr, bitorder="big")
    if total_bits is not None:
        return bits[:total_bits]
    return bits


def sqnr_theoretical_db(bits: int) -> float:
    """SQNR teórico para cuantizador uniforme a plena escala: 6.0206*B + 1.76 dB."""
    if bits < 1:
        raise ValueError(f"Se requiere bits >= 1, se recibió {bits}.")
    return FULL_SCALE_PENALTY_DB + DB_PER_BIT * bits


def quantizer_params(bits: int, span: float) -> Dict[str, Any]:
    """Calcula niveles, paso de cuantización Δ y varianza teórica para B bits."""
    if bits < 1 or bits > 16:
        raise ValueError(f"Resolución de {bits} bits fuera de rango [1, 16].")
    if span <= 0.0:
        raise ValueError(f"El rango dinámico debe ser positivo; se recibió {span}.")
    levels = 2**bits
    delta = span / levels
    return {
        "bits": bits,
        "levels": levels,
        "span": span,
        "delta": delta,
        "max_error": delta / 2.0,
        "theoretical_variance": (delta**2) / 12.0,
        "sqnr_theoretical_db": sqnr_theoretical_db(bits),
    }


def quantize_uniform(
    x: np.ndarray,
    bits: int,
    v_min: float = -1.0,
    v_max: float = 1.0,
    saturate: bool = True,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Cuantizador uniforme de punto medio (mid-rise con centros de celda).

    Devuelve `(indices_enteros, valores_cuantizados, paso_delta)`.
    """
    arr = np.asarray(x, dtype=np.float64)
    span = v_max - v_min
    params = quantizer_params(bits, span)
    delta = float(params["delta"])
    num_levels = int(params["levels"])

    indices = np.floor((arr - v_min) / delta).astype(np.int64)
    if saturate:
        indices = np.clip(indices, 0, num_levels - 1)
    quantized = (v_min + (indices.astype(np.float64) + 0.5) * delta).astype(np.float32)
    return indices, quantized, delta


def dither_signal(
    n: int,
    delta: float,
    kind: str = "tpdf",
    seed: int = 0,
    amplitude: float = 1.0,
) -> np.ndarray:
    """Genera ruido de dither uniforme o triangular (TPDF) para descorrelacionar el error."""
    if delta <= 0.0 or n < 0 or amplitude <= 0.0:
        raise ValueError("Parámetros inválidos para dither.")
    rng = np.random.default_rng(seed)
    if kind == "uniform":
        return ((rng.random(n) - 0.5) * 2.0 * amplitude * delta).astype(np.float32)
    if kind == "tpdf":
        return (((rng.random(n) - 0.5) + (rng.random(n) - 0.5)) * amplitude * delta).astype(
            np.float32
        )
    raise ValueError(f"Tipo de dither desconocido: {kind!r}. Use 'uniform' o 'tpdf'.")


def rmse(x_real: np.ndarray, x_hat: np.ndarray) -> float:
    """Raíz del error cuadrático medio entre dos arreglos de igual forma."""
    a = np.asarray(x_real, dtype=np.float64)
    b = np.asarray(x_hat, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"Formas incompatibles: {a.shape} vs {b.shape}.")
    if a.size == 0:
        raise ValueError("No se puede evaluar RMSE sobre un arreglo vacío.")
    return float(np.sqrt(np.mean((a - b) ** 2)))


def nrmse_by_range(x_real: np.ndarray, x_hat: np.ndarray) -> float:
    """RMSE normalizado respecto al rango dinámico (max - min) de la referencia."""
    a = np.asarray(x_real, dtype=np.float64)
    span = float(a.max() - a.min())
    base = rmse(a, x_hat)
    return base / span if span > 0.0 else base


def snr_db(x_real: np.ndarray, x_error: np.ndarray) -> float:
    """Relación señal a error en decibelios protegida contra casos degenerados."""
    a = np.asarray(x_real, dtype=np.float64)
    err = np.asarray(x_error, dtype=np.float64)
    if a.shape != err.shape:
        raise ValueError(f"Formas incompatibles: {a.shape} vs {err.shape}.")
    rms_sig = float(np.sqrt(np.mean(a**2)))
    rms_err = float(np.sqrt(np.mean(err**2)))
    if rms_err == 0.0 and rms_sig == 0.0:
        return 0.0
    if rms_err == 0.0:
        return float("inf")
    if rms_sig == 0.0:
        return -300.0
    return float(20.0 * np.log10(rms_sig / rms_err))


def psnr_db(x_real: np.ndarray, x_hat: np.ndarray, peak: float = 1.0) -> float:
    """Peak Signal-to-Noise Ratio (PSNR) en dB."""
    a = np.asarray(x_real, dtype=np.float64)
    b = np.asarray(x_hat, dtype=np.float64)
    mse = float(np.mean((a - b) ** 2))
    if mse <= 1e-15:
        return float("inf")
    return float(10.0 * np.log10((peak**2) / mse))


def pearson_correlation(x_real: np.ndarray, x_hat: np.ndarray) -> float:
    """Coeficiente de correlación lineal de Pearson en [-1, 1]."""
    a = np.asarray(x_real, dtype=np.float64).ravel()
    b = np.asarray(x_hat, dtype=np.float64).ravel()
    va = a - np.mean(a)
    vb = b - np.mean(b)
    denom = float(np.sqrt(np.sum(va**2) * np.sum(vb**2)))
    if denom <= ACTIVE_THRESHOLD:
        return 0.0
    return float(np.clip(np.sum(va * vb) / denom, -1.0, 1.0))


def compute_spectrum(
    samples: np.ndarray, sample_rate: float, window: str = "hann"
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calcula el espectro unilateral calibrado (freqs, magnitud lineal, magnitud dBFS)."""
    x = np.asarray(samples, dtype=np.float64).ravel()
    n = len(x)
    if n == 0 or sample_rate <= 0:
        raise ValueError("La señal no puede estar vacía y sample_rate debe ser positivo.")

    if window == "hann":
        win = np.hanning(n)
    elif window == "hamming":
        win = np.hamming(n)
    else:
        win = np.ones(n)

    coherent_gain = float(np.sum(win) / n)
    fft_vals = np.fft.rfft(x * win)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

    mag_linear = np.abs(fft_vals) / (n * max(coherent_gain, 1e-12))
    if len(mag_linear) > 2:
        mag_linear[1:-1] *= 2.0

    peak = float(np.max(mag_linear)) + 1e-12
    mag_db = 20.0 * np.log10(np.clip(mag_linear / peak, 1e-6, 1.0))
    return freqs, mag_linear, mag_db


def estimate_max_frequency(
    freqs: np.ndarray, mag_linear: np.ndarray, energy_threshold: float = 0.99
) -> float:
    """Estima f_max donde se acumula el porcentaje dado de energía espectral."""
    energy = np.asarray(mag_linear, dtype=np.float64) ** 2
    total = float(np.sum(energy))
    if total <= ACTIVE_THRESHOLD:
        return float(freqs[-1]) if len(freqs) else 0.0
    cumulative = np.cumsum(energy) / total
    idx = min(int(np.searchsorted(cumulative, energy_threshold)), len(freqs) - 1)
    return float(freqs[idx])


def diagnostico_nyquist(fmax: float, fs: float, tol: float = 1e-9) -> Dict[str, Any]:
    """Evalúa formalmente el criterio de Nyquist-Shannon fs >= 2*fmax."""
    fn = fs / 2.0
    fs_min = 2.0 * fmax
    margin = fn - fmax
    satisfied = margin >= -tol
    borderline = abs(margin) <= max(tol, 1e-9 * max(fn, fmax, 1.0))
    if borderline:
        verdict = "LIMITE (fs = 2*f_max): al borde de aliasing"
    elif satisfied:
        verdict = f"CUMPLE (margen {margin:.3g} Hz)"
    else:
        verdict = f"NO CUMPLE (faltan {-margin:.3g} Hz -> ALIASING)"
    return {
        "f_nyquist": fn,
        "fs_minima": fs_min,
        "margen_hz": margin,
        "margen_rel": (fs / fs_min) if fs_min > 0 else float("inf"),
        "cumple": bool(satisfied),
        "caso_limite": bool(borderline),
        "veredicto": verdict,
    }


def _sinc_neighborhood(
    t_samples: np.ndarray, t_eval: np.ndarray, n_pulses: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Indices de vecindario centrado alrededor de la muestra más cercana para cada t."""
    total_samples = len(t_samples)
    width = int(max(1, min(n_pulses, total_samples)))
    if total_samples == 1:
        center = np.zeros(len(t_eval), dtype=int)
    else:
        pos = np.clip(np.searchsorted(t_samples, t_eval), 1, total_samples - 1)
        left = t_samples[pos - 1]
        right = t_samples[pos]
        center = np.where((t_eval - left) <= (right - t_eval), pos - 1, pos).astype(int)
    idx = center[:, None] + (np.arange(width) - width // 2)[None, :]
    return idx, (idx >= 0) & (idx < total_samples)


def reconstruct_sinc(
    t_eval: np.ndarray,
    t_samples: np.ndarray,
    x_samples: np.ndarray,
    fs: float | None = None,
    n_pulses: int = 64,
) -> np.ndarray:
    """Reconstrucción de Whittaker-Shannon mediante suma finita de senos cardinales."""
    t_arr = np.asarray(t_eval, dtype=np.float64)
    x_arr = np.asarray(x_samples, dtype=np.float64)
    if len(x_arr) == 0:
        return np.zeros_like(t_arr)
    if fs is None or fs <= 0:
        if len(t_samples) < 2:
            raise ValueError("Se requieren al menos 2 muestras o especificar fs.")
        fs = float(1.0 / (t_samples[1] - t_samples[0]))

    idx, valid = _sinc_neighborhood(t_samples, t_arr, n_pulses)
    safe_idx = np.clip(idx, 0, len(x_arr) - 1)
    u = fs * (t_arr[:, None] - t_samples[safe_idx])
    weights = np.where(valid, x_arr[safe_idx], 0.0)
    return np.sum(weights * np.sinc(u), axis=1)


def reconstruct_zoh(
    t_eval: np.ndarray, t_samples: np.ndarray, x_samples: np.ndarray
) -> np.ndarray:
    """Retenedor de orden cero (Zero-Order Hold)."""
    t_arr = np.asarray(t_eval, dtype=np.float64)
    x_arr = np.asarray(x_samples, dtype=np.float64)
    if len(x_arr) == 0:
        return np.zeros_like(t_arr)
    idx = np.clip(np.searchsorted(t_samples, t_arr, side="right") - 1, 0, len(x_arr) - 1)
    return x_arr[idx]
