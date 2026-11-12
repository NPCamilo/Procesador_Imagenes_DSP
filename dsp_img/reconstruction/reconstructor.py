"""
Reconstructor DAC de audio e imagen (PNG y SVG) a partir de datos digitalizados/demodulados.
"""

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np
from scipy import signal as sp_signal

from ..core.audio_wav import save_wav
from ..core.codec import ImageCompressor
from ..core.contracts import (
    BaseReconstructor,
    DemodulatedResult,
    ImageSignal,
    QuantizedStream,
    ReconstructionMetrics,
)
from ..core.image_io import save_image_png
from ..core.primitives import reconstruct_sinc, reconstruct_zoh
from .metrics import evaluate_image_fidelity
from .svg_vectorizer import save_image_svg


class SignalReconstructor(BaseReconstructor):
    """Reconstruye la señal audible (DAC Sinc / ZOH) y la imagen final en PNG + SVG."""

    def __init__(self, dac_method: str = "sinc", lpf_cutoff_ratio: float = 0.42) -> None:
        if dac_method not in ("sinc", "zoh_filtered"):
            raise ValueError("El método DAC debe ser 'sinc' o 'zoh_filtered'.")
        self.dac_method = dac_method
        self.lpf_cutoff_ratio = float(lpf_cutoff_ratio)

    def reconstruct_audio(
        self,
        samples: np.ndarray,
        target_rate_hz: int = 16000,
        upsample_factor: int = 4,
    ) -> np.ndarray:
        """
        Aplica reconstrucción DAC continua (Sinc Whittaker-Shannon o ZOH filtrado)
        sobre un arreglo de muestras discretas 1D.
        """
        x_m = np.asarray(samples, dtype=np.float64).ravel()
        if len(x_m) < 2:
            return x_m.astype(np.float32)

        fs_in = float(target_rate_hz) / float(max(1, upsample_factor))
        t_m = np.arange(len(x_m), dtype=np.float64) / fs_in
        t_eval = np.arange(len(x_m) * max(1, upsample_factor), dtype=np.float64) / float(target_rate_hz)

        if self.dac_method == "sinc":
            reconstructed = reconstruct_sinc(t_eval, t_m, x_m, fs=fs_in, n_pulses=32)
        else:
            zoh = reconstruct_zoh(t_eval, t_m, x_m)
            b, a = sp_signal.butter(4, min(0.9, self.lpf_cutoff_ratio), btype="low")
            reconstructed = sp_signal.filtfilt(b, a, zoh)

        # Ventana suave en extremos para evitar chasquidos en reproducción
        fade = min(128, len(reconstructed) // 10)
        if fade > 2:
            ramp = np.linspace(0.0, 1.0, fade)
            reconstructed[:fade] *= ramp
            reconstructed[-fade:] *= ramp[::-1]

        peak = float(np.max(np.abs(reconstructed))) or 1.0
        return np.clip(reconstructed / peak * 0.90, -1.0, 1.0).astype(np.float32)

    def image_to_audible_scanline(
        self,
        image: ImageSignal,
        sample_rate_hz: int = 16000,
        duration_s: float = 2.5,
        upsample_factor: int = 4,
    ) -> np.ndarray:
        """
        Convierte la señal de imagen (barrido de luminancia) en una onda sonora
        audible mediante DAC para comparación auditiva Original vs Reconstruida.
        """
        bipolar = image.to_1d_bipolar().astype(np.float64)
        bipolar = bipolar - float(np.mean(bipolar))
        base_samples_needed = max(64, int((sample_rate_hz * duration_s) / max(1, upsample_factor)))

        # Seleccionar un tramo representativo y repetir suavemente si hace falta
        if len(bipolar) >= base_samples_needed:
            # Tomar franja centrada alrededor de la mitad vertical (rostro/camiseta/estantería)
            mid = len(bipolar) // 2
            start = max(0, mid - base_samples_needed // 2)
            discrete = bipolar[start : start + base_samples_needed]
        else:
            reps = int(np.ceil(base_samples_needed / len(bipolar)))
            discrete = np.tile(bipolar, reps)[:base_samples_needed]

        return self.reconstruct_audio(discrete, target_rate_hz=sample_rate_hz, upsample_factor=upsample_factor)

    def reconstruct_from_quantized(self, stream: QuantizedStream) -> ImageSignal:
        """Reconstruye una imagen desde un flujo digital cuantizado `QuantizedStream`."""
        pixels = np.clip(stream.reconstructed_values.reshape(stream.original_shape), 0.0, 1.0)
        return ImageSignal(
            pixels=pixels,
            sample_rate_1d_hz=stream.sample_rate_hz,
            metadata={"reconstructed_from": "QuantizedStream", "bits": stream.bits_per_sample},
        )

    def reconstruct_from_demodulated(
        self,
        demodulated: DemodulatedResult,
        compressor: Optional[ImageCompressor] = None,
    ) -> ImageSignal:
        """Descomprime y reconstruye la señal de imagen a partir de `DemodulatedResult`."""
        raw_bytes = demodulated.metadata.get("recovered_bytes")
        if not raw_bytes:
            raise ValueError("El resultado demodulado no contiene bytes de paquete `.dspimg` válidos.")
        codec = compressor or ImageCompressor()
        rec_img = codec.decompress(raw_bytes)
        rec_img.metadata["demodulation_type"] = demodulated.demodulation_type
        rec_img.metadata["crc_valid"] = demodulated.crc_valid
        return rec_img

    def export_artifacts(
        self,
        reconstructed: ImageSignal,
        rec_audio: np.ndarray,
        audio_sample_rate_hz: int,
        png_path: str,
        svg_path: str,
        wav_path: str,
        svg_color_levels: int = 16,
    ) -> Tuple[str, str, str]:
        """Exporta PNG, SVG vectorial y WAV reconstruido a disco."""
        out_png = save_image_png(reconstructed, png_path)
        out_svg = save_image_svg(reconstructed, svg_path, color_levels=svg_color_levels)
        out_wav = save_wav(wav_path, rec_audio, audio_sample_rate_hz, bit_depth=16)
        return out_png, out_svg, out_wav

    def evaluate(
        self,
        original: ImageSignal,
        reconstructed: ImageSignal,
        compression_ratio: float = 1.0,
    ) -> ReconstructionMetrics:
        return evaluate_image_fidelity(original, reconstructed, compression_ratio=compression_ratio)
