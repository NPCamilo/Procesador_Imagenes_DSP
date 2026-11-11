"""
Contratos de datos e interfaces abstractas para todo el pipeline DSP de imágenes.

Cada fase del proyecto comunica datos exclusivamente mediante estas estructuras
para garantizar validación independiente en GitHub y desacople total de la web.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .primitives import pack_bits, unpack_bits


@dataclass
class ImageSignal:
    """Representación normalizada de una señal de imagen 2D (RGB o escala de grises)."""

    pixels: np.ndarray
    sample_rate_1d_hz: int = 16000
    dpi: Optional[Tuple[float, float]] = None
    filename: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        arr = np.asarray(self.pixels)
        if arr.ndim == 2:
            arr = arr[:, :, np.newaxis]
        if arr.ndim != 3 or arr.shape[2] not in (1, 3):
            raise ValueError(
                f"Se esperaba arreglo (H, W) o (H, W, 1|3); se recibió {arr.shape}."
            )
        if np.issubdtype(arr.dtype, np.integer):
            arr = arr.astype(np.float32) / 255.0
        else:
            arr = np.clip(arr.astype(np.float32), 0.0, 1.0)
        self.pixels = arr

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])

    @property
    def channels(self) -> int:
        return int(self.pixels.shape[2])

    @property
    def shape(self) -> Tuple[int, int, int]:
        return (self.height, self.width, self.channels)

    @property
    def num_pixels(self) -> int:
        return self.height * self.width

    def to_uint8(self) -> np.ndarray:
        """Retorna la matriz cuantizada a enteros [0, 255] uint8."""
        scaled = np.rint(np.clip(self.pixels, 0.0, 1.0) * 255.0).astype(np.uint8)
        return scaled[:, :, 0] if self.channels == 1 else scaled

    def to_luminance(self) -> np.ndarray:
        """Calcula luminancia Rec. 601 en rango [0.0, 1.0] con forma (H, W)."""
        if self.channels == 1:
            return self.pixels[:, :, 0]
        r, g, b = self.pixels[:, :, 0], self.pixels[:, :, 1], self.pixels[:, :, 2]
        return (0.299 * r + 0.587 * g + 0.114 * b).astype(np.float32)

    def to_1d_bipolar(self) -> np.ndarray:
        """Serializa por barrido horizontal a señal 1D centrada en [-1.0, 1.0]."""
        flat = self.to_luminance().reshape(-1)
        return (flat * 2.0 - 1.0).astype(np.float32)


@dataclass
class RedSplashResult:
    """Resultado del filtrado selectivo que conserva solo el rojo de mayor área."""

    original: ImageSignal
    filtered: ImageSignal
    largest_mask: np.ndarray
    all_red_mask: np.ndarray
    num_red_components: int
    largest_area_px: int
    largest_area_ratio: float
    component_areas_px: List[int] = field(default_factory=list)


@dataclass
class SamplingReport:
    """Caracterización espacial y temporal equivalente bajo el criterio Nyquist-Shannon."""

    spatial_fs_per_px: float
    nyquist_spatial_cycles_per_px: float
    f_max_spatial_cycles_per_px: float
    equivalent_fs_hz: int
    f_max_1d_hz: float
    nyquist_diagnosis: Dict[str, Any]
    dpi: Optional[Tuple[float, float]] = None


@dataclass
class QuantizedStream:
    """Flujo digital cuantizado con resolución configurable [Byte / Bit]."""

    bitstream: np.ndarray
    quantized_levels: np.ndarray
    reconstructed_values: np.ndarray
    bits_per_sample: int
    sample_rate_hz: int
    original_shape: Tuple[int, ...]
    v_min: float
    v_max: float
    delta: float
    sqnr_empirical_db: float
    sqnr_theoretical_db: float

    @property
    def total_bits(self) -> int:
        return int(len(self.bitstream))

    @property
    def total_bytes(self) -> int:
        return int(np.ceil(self.total_bits / 8))

    def to_bytes(self) -> bytes:
        """Empaqueta el arreglo de bits (0/1) en bytes MSB-first."""
        return pack_bits(self.bitstream)

    @staticmethod
    def from_bytes(
        raw_bytes: bytes,
        total_bits: int,
        bits_per_sample: int,
        sample_rate_hz: int,
        original_shape: Tuple[int, ...],
        v_min: float = 0.0,
        v_max: float = 1.0,
    ) -> "QuantizedStream":
        """Reconstruye los niveles cuantizados desde un flujo de bytes empaquetados."""
        bits = unpack_bits(raw_bytes, total_bits=total_bits)
        num_samples = total_bits // bits_per_sample
        reshaped = bits[: num_samples * bits_per_sample].reshape(
            num_samples, bits_per_sample
        )
        powers = 1 << np.arange(bits_per_sample - 1, -1, -1, dtype=np.int64)
        levels = np.dot(reshaped.astype(np.int64), powers)

        num_levels = 2**bits_per_sample
        span = v_max - v_min
        delta = span / num_levels
        reconstructed = (v_min + (levels.astype(np.float64) + 0.5) * delta).astype(
            np.float32
        )

        return QuantizedStream(
            bitstream=bits,
            quantized_levels=levels,
            reconstructed_values=reconstructed,
            bits_per_sample=bits_per_sample,
            sample_rate_hz=sample_rate_hz,
            original_shape=original_shape,
            v_min=v_min,
            v_max=v_max,
            delta=float(delta),
            sqnr_empirical_db=0.0,
            sqnr_theoretical_db=6.0206 * bits_per_sample + 1.76,
        )


@dataclass
class CompressedPacket:
    """Paquete binario comprimido con integridad CRC32 para intercambio entre pares."""

    wire_bytes: bytes
    payload_bytes: bytes
    method: str
    original_shape: Tuple[int, int, int]
    bits_per_sample: int
    crc32: int
    raw_bytes_count: int
    compressed_bytes_count: int

    @property
    def compression_ratio(self) -> float:
        if self.compressed_bytes_count <= 0:
            return 0.0
        return float(self.raw_bytes_count / self.compressed_bytes_count)

    @property
    def savings_percent(self) -> float:
        if self.raw_bytes_count <= 0:
            return 0.0
        return float((1.0 - self.compressed_bytes_count / self.raw_bytes_count) * 100.0)


@dataclass
class ModulatedWaveform:
    """Forma de onda pasabanda audible (analógica o digital) lista para WAV o canal."""

    samples: np.ndarray
    sampling_rate_hz: int
    carrier_freq_hz: float
    modulation_type: str
    is_digital: bool
    baud_rate: float = 0.0
    preamble_bits: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.samples = np.asarray(self.samples, dtype=np.float32)

    @property
    def duration_s(self) -> float:
        return len(self.samples) / self.sampling_rate_hz if self.sampling_rate_hz > 0 else 0.0

    @property
    def time_vector(self) -> np.ndarray:
        return np.linspace(0.0, self.duration_s, len(self.samples), endpoint=False)


@dataclass
class DemodulatedResult:
    """Resultado recuperado tras la sincronización y demodulación en recepción."""

    recovered_signal_1d: np.ndarray
    sampling_rate_hz: int
    demodulation_type: str
    detected_bits: Optional[np.ndarray] = None
    bit_error_rate: Optional[float] = None
    crc_valid: Optional[bool] = None
    sync_offset_samples: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconstructionMetrics:
    """Métricas objetivas de fidelidad de imagen, audio y compresión."""

    mse: float
    rmse: float
    psnr_db: float
    ssim: float
    pearson_corr: float
    snr_db: float
    compression_ratio: float = 1.0


class BaseCompressor(ABC):
    """Contrato abstracto para compresión y descompresión de señales de imagen."""

    @abstractmethod
    def compress(self, image: ImageSignal, bits_per_sample: int = 8, **kwargs) -> CompressedPacket:
        """Comprime la imagen y genera un paquete binario verificable."""

    @abstractmethod
    def decompress(self, packet_bytes: bytes) -> ImageSignal:
        """Valida integridad y reconstruye la señal de imagen desde bytes comprimidos."""


class BaseModulator(ABC):
    """Contrato abstracto para moduladores analógicos y digitales pasabanda."""

    @abstractmethod
    def modulate(self, source: Any, carrier_freq_hz: float, **kwargs) -> ModulatedWaveform:
        """Modula un flujo binario o señal 1D generando una onda pasabanda audible."""


class BaseDemodulator(ABC):
    """Contrato abstracto para demodulación y recuperación de información."""

    @abstractmethod
    def demodulate(self, waveform: ModulatedWaveform, **kwargs) -> DemodulatedResult:
        """Recupera la señal banda base y/o bits desde la onda modulada."""


class BaseReconstructor(ABC):
    """Contrato abstracto para reconstrucción DAC, exportación PNG/SVG y métricas."""

    @abstractmethod
    def reconstruct_audio(self, samples: np.ndarray, target_rate_hz: int, **kwargs) -> np.ndarray:
        """Reconstruye una señal continua equivalente mediante Sinc o ZOH filtrado."""

    @abstractmethod
    def evaluate(
        self, original: ImageSignal, reconstructed: ImageSignal, compression_ratio: float = 1.0
    ) -> ReconstructionMetrics:
        """Calcula MSE, RMSE, PSNR, SSIM, correlación de Pearson y SNR."""
