"""
Métricas objetivas de fidelidad para reconstrucción de imagen (PSNR, SSIM, MSE, r)
y comparación auditiva 1D (SNR, MSE, Pearson).
"""

from __future__ import annotations

from typing import Dict
import numpy as np
from scipy import ndimage

from ..core.contracts import ImageSignal, ReconstructionMetrics
from ..core.primitives import pearson_correlation, psnr_db, rmse, snr_db


def compute_ssim(img_a: np.ndarray, img_b: np.ndarray, data_range: float = 1.0) -> float:
    """
    Calcula el Índice de Similitud Estructural (SSIM) usando ventana gaussiana σ=1.5.

    Opera sobre imágenes 2D (luminancia) o 3D RGB promediando los canales.
    """
    a = np.asarray(img_a, dtype=np.float64)
    b = np.asarray(img_b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"Formas incompatibles para SSIM: {a.shape} vs {b.shape}.")

    c1 = (0.01 * data_range) ** 2
    c2 = (0.03 * data_range) ** 2

    def _channel_ssim(x: np.ndarray, y: np.ndarray) -> float:
        mu_x = ndimage.gaussian_filter(x, sigma=1.5, mode="reflect")
        mu_y = ndimage.gaussian_filter(y, sigma=1.5, mode="reflect")
        mu_x2 = mu_x * mu_x
        mu_y2 = mu_y * mu_y
        mu_xy = mu_x * mu_y

        sigma_x2 = np.maximum(0.0, ndimage.gaussian_filter(x * x, sigma=1.5, mode="reflect") - mu_x2)
        sigma_y2 = np.maximum(0.0, ndimage.gaussian_filter(y * y, sigma=1.5, mode="reflect") - mu_y2)
        sigma_xy = ndimage.gaussian_filter(x * y, sigma=1.5, mode="reflect") - mu_xy

        num = (2.0 * mu_xy + c1) * (2.0 * sigma_xy + c2)
        den = (mu_x2 + mu_y2 + c1) * (sigma_x2 + sigma_y2 + c2)
        ssim_map = num / np.maximum(den, 1e-12)
        return float(np.mean(ssim_map))

    if a.ndim == 2:
        return _channel_ssim(a, b)
    scores = [_channel_ssim(a[:, :, ch], b[:, :, ch]) for ch in range(a.shape[2])]
    return float(np.mean(scores))


def evaluate_image_fidelity(
    original: ImageSignal,
    reconstructed: ImageSignal,
    compression_ratio: float = 1.0,
) -> ReconstructionMetrics:
    """Evalúa todas las métricas cuantitativas de imagen entre original y reconstruida."""
    a = original.pixels.astype(np.float64)
    b = reconstructed.pixels.astype(np.float64)
    if a.shape != b.shape:
        raise ValueError(f"Dimensiones incompatibles: {a.shape} vs {b.shape}.")

    err = a - b
    mse_val = float(np.mean(err**2))
    rmse_val = rmse(a, b)
    psnr_val = psnr_db(a, b, peak=1.0)
    ssim_val = compute_ssim(a, b, data_range=1.0)
    corr_val = pearson_correlation(a, b)
    snr_val = snr_db(a, err)

    return ReconstructionMetrics(
        mse=mse_val,
        rmse=rmse_val,
        psnr_db=psnr_val,
        ssim=ssim_val,
        pearson_corr=corr_val,
        snr_db=snr_val,
        compression_ratio=compression_ratio,
    )


def evaluate_audio_fidelity(original_audio: np.ndarray, reconstructed_audio: np.ndarray) -> Dict[str, float]:
    """Calcula MSE, SNR (dB) y correlación entre la señal sonora original y la reconstruida."""
    n = min(len(original_audio), len(reconstructed_audio))
    x = np.asarray(original_audio[:n], dtype=np.float64)
    y = np.asarray(reconstructed_audio[:n], dtype=np.float64)
    err = x - y
    return {
        "mse": float(np.mean(err**2)),
        "rmse": rmse(x, y),
        "snr_db": snr_db(x, err),
        "pearson_corr": pearson_correlation(x, y),
    }
