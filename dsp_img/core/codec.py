"""
Motor de Compresión y Descompresión de Señales de Imagen (.dspimg).

Implementa dos métodos seleccionables sobre el contrato `BaseCompressor`:
  1. `lossless_dpcm_zlib`: Codificación diferencial espacial (DPCM) + empaquetado de bits + DEFLATE/Zlib.
     Garantiza reconstrucción bit-a-bit idéntica a la imagen cuantizada.
  2. `lossy_dct_zlib`: Conversión RGB -> YCbCr (4:2:0), DCT 2D por bloques 8×8, cuantización
     frecuencial matricial y entropía Zlib para lograr alta compresión rumbo a transmisión audible.

Incluye cabecera binaria compacta de 22 bytes con CRC32 para detectar errores de canal
y permitir el intercambio directo con compañeros.
"""

from __future__ import annotations

import os
import struct
import zlib
from typing import Dict, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
from scipy.fft import dctn, idctn

from .contracts import BaseCompressor, CompressedPacket, ImageSignal
from .primitives import pack_bits, pearson_correlation, psnr_db, rmse, unpack_bits
from .quantization import quantize_image
from .theme import apply_plot_theme, style_axis

MAGIC = b"IMDSP1"
VERSION = 1
HEADER_STRUCT = struct.Struct("<6sBBHHBBII")  # 22 bytes totales

METHOD_LOSSLESS = "lossless_dpcm_zlib"
METHOD_LOSSY_DCT = "lossy_dct_zlib"

_Q_LUMA = np.array(
    [
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99],
    ],
    dtype=np.float64,
)

_Q_CHROMA = np.array(
    [
        [17, 18, 24, 47, 99, 99, 99, 99],
        [18, 21, 26, 66, 99, 99, 99, 99],
        [24, 26, 56, 99, 99, 99, 99, 99],
        [47, 66, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
    ],
    dtype=np.float64,
)


def _scaled_q_matrix(base: np.ndarray, quality: int) -> np.ndarray:
    """Escala la matriz de cuantización según calidad [1..100] tipo JPEG."""
    q = int(np.clip(quality, 1, 100))
    scale = (5000.0 / q) if q < 50 else (200.0 - 2.0 * q)
    scaled = np.floor((base * scale + 50.0) / 100.0)
    return np.clip(scaled, 1.0, 255.0)


def _rgb_to_ycbcr(rgb_u8: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convierte RGB [0..255] a planos Y, Cb, Cr float64 centrados en 0."""
    rgb = rgb_u8.astype(np.float64)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b - 128.0
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b
    return y, cb, cr


def _ycbcr_to_rgb(y: np.ndarray, cb: np.ndarray, cr: np.ndarray) -> np.ndarray:
    """Convierte planos Y, Cb, Cr centrados en 0 a RGB uint8 [0..255]."""
    y_shift = y + 128.0
    r = y_shift + 1.402 * cr
    g = y_shift - 0.344136 * cb - 0.714136 * cr
    b = y_shift + 1.772 * cb
    stacked = np.stack([r, g, b], axis=2)
    return np.clip(np.rint(stacked), 0, 255).astype(np.uint8)


def _pad_multiple(plane: np.ndarray, mult: int) -> np.ndarray:
    """Rellena por replicación de borde para obtener dimensiones múltiplos de `mult`."""
    h, w = plane.shape
    pad_h = (mult - (h % mult)) % mult
    pad_w = (mult - (w % mult)) % mult
    if pad_h == 0 and pad_w == 0:
        return plane
    return np.pad(plane, ((0, pad_h), (0, pad_w)), mode="edge")


def _encode_dct_plane(plane: np.ndarray, q_mat: np.ndarray) -> bytes:
    """Transforma un plano 2D en bloques 8×8 DCT cuantizados y ordenados por frecuencia."""
    padded = _pad_multiple(plane, 8)
    ph, pw = padded.shape
    blocks = padded.reshape(ph // 8, 8, pw // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 8, 8)
    coeffs = dctn(blocks, axes=(-2, -1), norm="ortho")
    q_coeffs = np.rint(coeffs / q_mat[np.newaxis, :, :]).astype(np.int16)
    # Transponer (64, N_bloques) agrupa las altas frecuencias nulas para maximizar Zlib
    freq_grouped = q_coeffs.reshape(-1, 64).T.copy()
    return freq_grouped.tobytes()


def _decode_dct_plane(raw_bytes: bytes, out_h: int, out_w: int, q_mat: np.ndarray) -> np.ndarray:
    """Reconstruye un plano 2D desde sus bloques DCT cuantizados."""
    pad_h = out_h + (8 - (out_h % 8)) % 8
    pad_w = out_w + (8 - (out_w % 8)) % 8
    n_blocks = (pad_h // 8) * (pad_w // 8)
    freq_grouped = np.frombuffer(raw_bytes, dtype=np.int16).reshape(64, n_blocks)
    q_coeffs = freq_grouped.T.reshape(n_blocks, 8, 8).astype(np.float64)
    blocks = idctn(q_coeffs * q_mat[np.newaxis, :, :], axes=(-2, -1), norm="ortho")
    plane = blocks.reshape(pad_h // 8, pad_w // 8, 8, 8).transpose(0, 2, 1, 3).reshape(pad_h, pad_w)
    return plane[:out_h, :out_w]


def _downsample_2x(plane: np.ndarray) -> np.ndarray:
    """Submuestreo cromático 4:2:0 promediando bloques 2×2."""
    padded = _pad_multiple(plane, 2)
    h, w = padded.shape
    return padded.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def _upsample_2x(plane: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    """Interpolación bilineal sencilla por repetición 2×2 hacia dimensiones originales."""
    up = np.repeat(np.repeat(plane, 2, axis=0), 2, axis=1)
    return up[:target_h, :target_w]


class ImageCompressor(BaseCompressor):
    """Compresor y descompresor modular de señales de imagen con integridad CRC32."""

    def __init__(self, method: str = METHOD_LOSSLESS, quality: int = 75) -> None:
        if method not in (METHOD_LOSSLESS, METHOD_LOSSY_DCT):
            raise ValueError(f"Método desconocido: {method!r}.")
        self.method = method
        self.quality = int(np.clip(quality, 1, 100))

    def compress(
        self,
        image: ImageSignal,
        bits_per_sample: int = 8,
        method: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> CompressedPacket:
        """Comprime la imagen al formato binario autodescriptivo `.dspimg`."""
        chosen_method = method or self.method
        chosen_quality = int(np.clip(quality if quality is not None else self.quality, 1, 100))
        is_rgb = image.channels == 3
        raw_bytes_count = image.height * image.width * image.channels

        if chosen_method == METHOD_LOSSLESS:
            if bits_per_sample < 1 or bits_per_sample > 8:
                raise ValueError("El modo sin pérdida DPCM soporta entre 1 y 8 bits por canal.")
            _, q_stream = quantize_image(image, bits_per_sample=bits_per_sample)
            levels = q_stream.quantized_levels.reshape(image.shape)
            mod_base = 2**bits_per_sample
            residuals = np.empty_like(levels)
            residuals[:, 0, :] = levels[:, 0, :]
            residuals[:, 1:, :] = (levels[:, 1:, :] - levels[:, :-1, :]) % mod_base

            if bits_per_sample == 8:
                packed = residuals.astype(np.uint8).tobytes()
            else:
                flat_res = residuals.ravel()
                shifts = np.arange(bits_per_sample - 1, -1, -1, dtype=np.int64)
                res_bits = ((flat_res[:, None] >> shifts) & 1).reshape(-1).astype(np.uint8)
                packed = pack_bits(res_bits)
            payload = zlib.compress(packed, level=9)
        else:
            q_luma = _scaled_q_matrix(_Q_LUMA, chosen_quality)
            q_chroma = _scaled_q_matrix(_Q_CHROMA, chosen_quality)
            u8 = image.to_uint8()
            if is_rgb:
                y, cb, cr = _rgb_to_ycbcr(u8)
                cb_sub = _downsample_2x(cb)
                cr_sub = _downsample_2x(cr)
                b_y = _encode_dct_plane(y, q_luma)
                b_cb = _encode_dct_plane(cb_sub, q_chroma)
                b_cr = _encode_dct_plane(cr_sub, q_chroma)
                lengths = struct.pack("<III", len(b_y), len(b_cb), len(b_cr))
                payload = zlib.compress(lengths + b_y + b_cb + b_cr, level=9)
            else:
                y = u8.astype(np.float64) - 128.0
                b_y = _encode_dct_plane(y, q_luma)
                lengths = struct.pack("<III", len(b_y), 0, 0)
                payload = zlib.compress(lengths + b_y, level=9)

        flags = (1 if is_rgb else 0) | ((1 if chosen_method == METHOD_LOSSY_DCT else 0) << 1)
        payload_len = len(payload)
        header_no_crc = HEADER_STRUCT.pack(
            MAGIC,
            VERSION,
            flags,
            image.width,
            image.height,
            bits_per_sample,
            chosen_quality,
            payload_len,
            0,
        )
        crc32 = zlib.crc32(header_no_crc[:-4] + payload) & 0xFFFFFFFF
        header = HEADER_STRUCT.pack(
            MAGIC,
            VERSION,
            flags,
            image.width,
            image.height,
            bits_per_sample,
            chosen_quality,
            payload_len,
            crc32,
        )
        wire_bytes = header + payload

        return CompressedPacket(
            wire_bytes=wire_bytes,
            payload_bytes=payload,
            method=chosen_method,
            original_shape=image.shape,
            bits_per_sample=bits_per_sample,
            crc32=crc32,
            raw_bytes_count=raw_bytes_count,
            compressed_bytes_count=len(wire_bytes),
        )

    def decompress(self, packet_bytes: bytes, sample_rate_1d_hz: int = 16000) -> ImageSignal:
        """Verifica magia y CRC32, descomprime el flujo y reconstruye la imagen."""
        if len(packet_bytes) < HEADER_STRUCT.size:
            raise ValueError("Paquete .dspimg truncado: cabecera incompleta.")

        header_raw = packet_bytes[: HEADER_STRUCT.size]
        (
            magic,
            version,
            flags,
            width,
            height,
            bits_per_sample,
            quality,
            payload_len,
            expected_crc,
        ) = HEADER_STRUCT.unpack(header_raw)

        if magic != MAGIC or version != VERSION:
            raise ValueError("Formato de paquete .dspimg inválido o versión no soportada.")

        payload = packet_bytes[HEADER_STRUCT.size : HEADER_STRUCT.size + payload_len]
        if len(payload) != payload_len:
            raise ValueError("Paquete .dspimg incompleto respecto a `payload_len`.")

        actual_crc = zlib.crc32(header_raw[:-4] + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError(
                f"Fallo de integridad CRC32: esperado 0x{expected_crc:08X}, recibido 0x{actual_crc:08X}."
            )

        is_rgb = bool(flags & 0x01)
        is_dct = bool((flags >> 1) & 0x01)
        channels = 3 if is_rgb else 1
        decompressed = zlib.decompress(payload)

        if not is_dct:
            mod_base = 2**bits_per_sample
            total_vals = height * width * channels
            if bits_per_sample == 8:
                residuals = np.frombuffer(decompressed, dtype=np.uint8).astype(np.int64)
            else:
                bits = unpack_bits(decompressed, total_bits=total_vals * bits_per_sample)
                powers = 1 << np.arange(bits_per_sample - 1, -1, -1, dtype=np.int64)
                residuals = np.dot(bits.reshape(total_vals, bits_per_sample).astype(np.int64), powers)

            residuals = residuals.reshape((height, width, channels))
            levels = np.cumsum(residuals, axis=1) % mod_base
            delta = 1.0 / mod_base
            pixels = np.clip((levels.astype(np.float64) + 0.5) * delta, 0.0, 1.0).astype(np.float32)
            method_name = METHOD_LOSSLESS
        else:
            len_y, len_cb, len_cr = struct.unpack("<III", decompressed[:12])
            body = decompressed[12:]
            q_luma = _scaled_q_matrix(_Q_LUMA, quality)
            q_chroma = _scaled_q_matrix(_Q_CHROMA, quality)
            y = _decode_dct_plane(body[:len_y], height, width, q_luma)
            if is_rgb:
                cb_h, cb_w = (height + 1) // 2, (width + 1) // 2
                cb_sub = _decode_dct_plane(body[len_y : len_y + len_cb], cb_h, cb_w, q_chroma)
                cr_sub = _decode_dct_plane(
                    body[len_y + len_cb : len_y + len_cb + len_cr], cb_h, cb_w, q_chroma
                )
                cb = _upsample_2x(cb_sub, height, width)
                cr = _upsample_2x(cr_sub, height, width)
                pixels = _ycbcr_to_rgb(y, cb, cr)
            else:
                pixels = np.clip(np.rint(y + 128.0), 0, 255).astype(np.uint8)
            method_name = METHOD_LOSSY_DCT

        return ImageSignal(
            pixels=pixels,
            sample_rate_1d_hz=sample_rate_1d_hz,
            metadata={
                "compressed_method": method_name,
                "bits_per_sample": bits_per_sample,
                "quality": quality,
                "crc32_hex": f"0x{expected_crc:08X}",
            },
        )


def save_compressed_packet(packet: CompressedPacket, filepath: str) -> str:
    """Escribe los bytes del paquete `.dspimg` en disco."""
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as handle:
        handle.write(packet.wire_bytes)
    return abs_path


def load_compressed_packet(filepath: str) -> bytes:
    """Lee los bytes crudos de un paquete `.dspimg` desde disco."""
    with open(filepath, "rb") as handle:
        return handle.read()


def plot_compression_comparison(
    original: ImageSignal,
    pkt_lossless: CompressedPacket,
    rec_lossless: ImageSignal,
    pkt_dct: CompressedPacket,
    rec_dct: ImageSignal,
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """Compara visual y cuantitativamente la señal original vs DPCM sin pérdida vs DCT."""
    palette = apply_plot_theme(theme_mode)
    psnr_ll = psnr_db(original.pixels, rec_lossless.pixels)
    psnr_dct = psnr_db(original.pixels, rec_dct.pixels)
    r_ll = pearson_correlation(original.pixels, rec_lossless.pixels)
    r_dct = pearson_correlation(original.pixels, rec_dct.pixels)

    fig, axes = plt.subplots(1, 4, figsize=(16, 5.2), constrained_layout=True)

    axes[0].imshow(original.to_uint8())
    axes[0].set_title(
        f"1. Referencia\n{pkt_lossless.raw_bytes_count:,} Bytes sin comprimir",
        color=palette["ink"],
        fontsize=9.5,
    )

    axes[1].imshow(rec_lossless.to_uint8())
    axes[1].set_title(
        f"2. DPCM + Zlib ({pkt_lossless.bits_per_sample}b)\n"
        f"{pkt_lossless.compressed_bytes_count:,} B (CR={pkt_lossless.compression_ratio:.2f}× | PSNR={psnr_ll:.1f} dB)",
        color=palette["ink"],
        fontsize=9.2,
    )

    axes[2].imshow(rec_dct.to_uint8())
    axes[2].set_title(
        f"3. DCT 8×8 + Zlib\n"
        f"{pkt_dct.compressed_bytes_count:,} B (CR={pkt_dct.compression_ratio:.2f}× | PSNR={psnr_dct:.1f} dB)",
        color=palette["ink"],
        fontsize=9.2,
    )

    for col in range(3):
        axes[col].set_xlabel("X [px]")
        axes[col].set_ylabel("Y [px]")
        axes[col].grid(False)

    ax_bar = axes[3]
    style_axis(ax_bar, palette)
    labels = ["Crudo\n(8b RGB)", f"DPCM+Zlib\n({pkt_lossless.bits_per_sample}b)", "DCT 8×8\n+Zlib"]
    sizes_kb = [
        pkt_lossless.raw_bytes_count / 1024.0,
        pkt_lossless.compressed_bytes_count / 1024.0,
        pkt_dct.compressed_bytes_count / 1024.0,
    ]
    colors = [palette["muted"], palette["ok"], palette["primary"]]
    bars = ax_bar.bar(labels, sizes_kb, color=colors, width=0.58)
    for bar, kb in zip(bars, sizes_kb):
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + max(sizes_kb) * 0.02,
            f"{kb:.1f} KB",
            ha="center",
            va="bottom",
            color=palette["ink"],
            fontsize=8.5,
        )
    ax_bar.set_title(
        f"4. Ahorro de Espacio\n(r_DPCM={r_ll:.4f}, r_DCT={r_dct:.4f})",
        color=palette["ink"],
        fontsize=9.5,
    )
    ax_bar.set_ylabel("Tamaño [KB]")
    ax_bar.set_ylim(0.0, max(sizes_kb) * 1.16)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
