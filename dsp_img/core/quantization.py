"""
Digitalización y cuantización uniforme con técnica de resolución [Byte / Bit] (Punto 3).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np

from .contracts import ImageSignal, QuantizedStream
from .primitives import (
    dither_signal,
    pack_bits,
    quantize_uniform,
    snr_db,
    sqnr_theoretical_db,
)
from .theme import apply_plot_theme, style_axis


def _levels_to_bitstream(levels: np.ndarray, bits_per_sample: int) -> np.ndarray:
    """Convierte un arreglo 1D de índices enteros en un flujo continuo de bits MSB-first."""
    flat = np.asarray(levels, dtype=np.int64).ravel()
    if bits_per_sample <= 8:
        uint_arr = flat.astype(np.uint8)
        unpacked = np.unpackbits(uint_arr, bitorder="big").reshape(len(flat), 8)
        return unpacked[:, 8 - bits_per_sample :].reshape(-1).astype(np.uint8)
    shifts = np.arange(bits_per_sample - 1, -1, -1, dtype=np.int64)
    return ((flat[:, None] >> shifts) & 1).reshape(-1).astype(np.uint8)


def quantize_image(
    image: ImageSignal,
    bits_per_sample: int = 8,
    use_dither: bool = False,
    seed: int = 0,
) -> Tuple[ImageSignal, QuantizedStream]:
    """
    Cuantiza la señal de imagen aplicando la técnica de resolución [Byte / Bit].

    Soporta resoluciones de 1 a 16 bits por canal (por defecto 8 bits = 1 Byte/canal,
    4 bits = 0.5 Byte/canal, 2 bits, 1 bit).
    """
    flat = image.pixels.reshape(-1).astype(np.float32)
    span = 1.0  # Rango normalizado de imagen [0.0, 1.0]
    delta_est = span / (2**bits_per_sample)

    if use_dither:
        noise = dither_signal(len(flat), delta=delta_est, kind="tpdf", seed=seed)
        flat_proc = np.clip(flat + noise, 0.0, 1.0)
    else:
        flat_proc = flat

    levels, reconstructed, delta = quantize_uniform(
        flat_proc, bits=bits_per_sample, v_min=0.0, v_max=1.0, saturate=True
    )

    error = flat - reconstructed
    empirical_sqnr = snr_db(flat, error)
    theoretical_sqnr = sqnr_theoretical_db(bits_per_sample)
    bitstream = _levels_to_bitstream(levels, bits_per_sample)

    stream = QuantizedStream(
        bitstream=bitstream,
        quantized_levels=levels,
        reconstructed_values=reconstructed,
        bits_per_sample=bits_per_sample,
        sample_rate_hz=image.sample_rate_1d_hz,
        original_shape=image.shape,
        v_min=0.0,
        v_max=1.0,
        delta=delta,
        sqnr_empirical_db=empirical_sqnr,
        sqnr_theoretical_db=theoretical_sqnr,
    )

    quantized_pixels = np.clip(reconstructed.reshape(image.shape), 0.0, 1.0)
    quantized_img = ImageSignal(
        pixels=quantized_pixels,
        sample_rate_1d_hz=image.sample_rate_1d_hz,
        dpi=image.dpi,
        filename=image.filename,
        metadata={
            **image.metadata,
            "bits_per_sample": bits_per_sample,
            "bytes_per_sample": bits_per_sample / 8.0,
            "sqnr_empirical_db": round(empirical_sqnr, 2),
        },
    )
    return quantized_img, stream


def format_digital_preview(stream: QuantizedStream, num_bytes: int = 24) -> Dict[str, Any]:
    """Genera una vista legible del resultado digital en bits, bytes y niveles."""
    raw_bytes = stream.to_bytes()
    preview_bytes = raw_bytes[:num_bytes]
    return {
        "bits_per_sample": stream.bits_per_sample,
        "bytes_per_sample": stream.bits_per_sample / 8.0,
        "quantization_levels": 2**stream.bits_per_sample,
        "delta": round(stream.delta, 6),
        "total_samples": int(len(stream.quantized_levels)),
        "total_bits": stream.total_bits,
        "total_bytes": stream.total_bytes,
        "sqnr_empirical_db": round(stream.sqnr_empirical_db, 2),
        "sqnr_theoretical_db": round(stream.sqnr_theoretical_db, 2),
        "first_64_bits": "".join(str(int(b)) for b in stream.bitstream[:64]),
        "first_bytes_hex": " ".join(f"{byte:02X}" for byte in preview_bytes),
        "first_12_levels": [int(v) for v in stream.quantized_levels[:12]],
    }


def save_digital_stream(stream: QuantizedStream, base_filepath: str) -> Tuple[str, str]:
    """Guarda la trama digital empaquetada (.bin) junto con sus metadatos (.json)."""
    root, _ = os.path.splitext(base_filepath)
    bin_path = os.path.abspath(f"{root}.bin")
    meta_path = os.path.abspath(f"{root}_metadata.json")
    os.makedirs(os.path.dirname(bin_path), exist_ok=True)

    raw_bytes = stream.to_bytes()
    with open(bin_path, "wb") as f_bin:
        f_bin.write(raw_bytes)

    meta = {
        **format_digital_preview(stream),
        "sample_rate_hz": stream.sample_rate_hz,
        "original_shape": list(stream.original_shape),
        "v_min": stream.v_min,
        "v_max": stream.v_max,
    }
    with open(meta_path, "w", encoding="utf-8") as f_json:
        json.dump(meta, f_json, indent=2, ensure_ascii=False)

    return bin_path, meta_path


def load_digital_stream(base_filepath: str) -> QuantizedStream:
    """Carga un `QuantizedStream` desde sus archivos `.bin` y `_metadata.json`."""
    root, _ = os.path.splitext(base_filepath)
    bin_path = f"{root}.bin"
    meta_path = f"{root}_metadata.json"

    with open(meta_path, "r", encoding="utf-8") as f_json:
        meta = json.load(f_json)
    with open(bin_path, "rb") as f_bin:
        raw_bytes = f_bin.read()

    stream = QuantizedStream.from_bytes(
        raw_bytes=raw_bytes,
        total_bits=meta["total_bits"],
        bits_per_sample=meta["bits_per_sample"],
        sample_rate_hz=meta["sample_rate_hz"],
        original_shape=tuple(meta["original_shape"]),
        v_min=meta.get("v_min", 0.0),
        v_max=meta.get("v_max", 1.0),
    )
    stream.sqnr_empirical_db = float(meta.get("sqnr_empirical_db", 0.0))
    return stream


def plot_quantization_resolution_study(
    image: ImageSignal,
    bits_list: Iterable[int] = (8, 4, 2, 1),
    save_path: Optional[str] = None,
    show: bool = False,
    theme_mode: str = "dark",
) -> plt.Figure:
    """
    Visualiza la técnica de resolución [Byte / Bit]:
      - Fila superior: Imágenes cuantizadas a 8, 4, 2 y 1 bits/canal.
      - Fila inferior: Escalera de cuantización 1D (4 bits), ruido e[n] y curva SQNR.
    """
    palette = apply_plot_theme(theme_mode)
    bits_tuple = tuple(bits_list)
    results: List[Tuple[int, ImageSignal, QuantizedStream]] = [
        (b, *quantize_image(image, bits_per_sample=b)) for b in bits_tuple
    ]

    fig = plt.figure(figsize=(15, 8.5), constrained_layout=True)
    grid = fig.add_gridspec(2, 4, height_ratios=[1.15, 1.0])

    for col, (b, q_img, q_stream) in enumerate(results[:4]):
        ax = fig.add_subplot(grid[0, col])
        ax.imshow(q_img.to_uint8())
        byte_label = f"{b / 8:.2g} Byte/canal"
        ax.set_title(
            f"{b} bits ({byte_label})\n{2**b} niveles | SQNR={q_stream.sqnr_empirical_db:.1f} dB",
            color=palette["ink"],
            fontsize=9.5,
        )
        ax.set_xlabel("X [px]")
        ax.set_ylabel("Y [px]")
        ax.grid(False)

    # Panel inferior izquierdo (2 cols): Escalera 1D sobre una fila a 4 bits
    ax_stair = fig.add_subplot(grid[1, :2])
    style_axis(ax_stair, palette)
    lum = image.to_luminance()
    row_orig = lum[image.height // 2, :80]
    _, row_q4, delta4 = quantize_uniform(row_orig, bits=4, v_min=0.0, v_max=1.0)
    x_idx = np.arange(len(row_orig))
    ax_stair.plot(x_idx, row_orig, color=palette["primary"], linewidth=1.2, label="Original x[n]")
    ax_stair.step(x_idx, row_q4, where="mid", color=palette["accent"], linewidth=1.3, label="Cuantizada 4 bits")
    ax_stair.set_title(
        f"Efecto Escalera de Cuantización (4 bits/canal, Δ = {delta4:.4f})",
        color=palette["ink"],
        fontsize=10,
    )
    ax_stair.set_xlabel("Índice espacial de píxel n [muestras]")
    ax_stair.set_ylabel("Amplitud normalizada [0, 1]")
    ax_stair.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    # Panel inferior derecho (2 cols): SQNR empírico vs teórico (6.02b + 1.76 dB)
    ax_sqnr = fig.add_subplot(grid[1, 2:])
    style_axis(ax_sqnr, palette)
    bs = [b for b, _, _ in results]
    emp = [s.sqnr_empirical_db for _, _, s in results]
    teo = [s.sqnr_theoretical_db for _, _, s in results]
    ax_sqnr.plot(bs, teo, marker="s", linestyle="--", color=palette["ok"], linewidth=1.5, label="SQNR Teórico (6.02·b + 1.76 dB)")
    ax_sqnr.plot(bs, emp, marker="o", linestyle="-", color=palette["secondary"], linewidth=1.8, label="SQNR Medido en Imagen")
    ax_sqnr.set_title("Curva de Calidad SQNR vs Resolución [Bits / Muestra]", color=palette["ink"], fontsize=10)
    ax_sqnr.set_xlabel("Resolución b [bits por canal]")
    ax_sqnr.set_ylabel("SQNR [dB]")
    ax_sqnr.set_xticks(bs)
    ax_sqnr.legend(facecolor=palette["legend_bg"], edgecolor=palette["spine"], labelcolor=palette["ink"], fontsize=8)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        fig.savefig(save_path, dpi=300, facecolor=palette["bg"])
    if show:
        plt.show()
    else:
        plt.close(fig)
    return fig
