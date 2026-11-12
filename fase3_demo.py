"""
Script demostrativo de Fase 3 (Punto 4: Modulación y Síntesis Audible en Bits):
  - Comprime la fotografía filtrada (`selfie_solo_rojo`) en paquete `.dspimg`
  - Modula la trama de bits con BFSK (audible principal), MFSK (4-FSK), ASK, BPSK, 16-QAM
  - Modula también el perfil 1D en AM y FM como comparativa analógica
  - Exporta gráficas diagnósticas y archivos `.wav` escuchables en `data/output/fase3/`
"""

from __future__ import annotations

import argparse
import json
import os

from dsp_img.core.audio_wav import play_wav_or_samples
from dsp_img.core.codec import METHOD_LOSSY_DCT, ImageCompressor
from dsp_img.core.image_io import load_image
from dsp_img.core.primitives import unpack_bits
from dsp_img.core.red_filter import isolate_largest_red_region
from dsp_img.modulation.analog import AMModulator, FMModulator
from dsp_img.modulation.digital import DigitalPassbandModulator
from dsp_img.modulation.visualize import export_modulated_audio, plot_modulated_signal


def run_fase3(
    image_path: str = "data/input/selfie_dsp.jpeg",
    output_dir: str = "data/output/fase3",
    scheme: str = "BFSK",
    work_max_dim: int = 96,
    dct_quality: int = 65,
    play: bool = False,
    show: bool = False,
) -> dict:
    """Ejecuta la Fase 3 completa y exporta gráficas y audios WAV modulados."""
    os.makedirs(output_dir, exist_ok=True)

    img = load_image(image_path, max_dim=work_max_dim)
    splash = isolate_largest_red_region(img).filtered
    pkt = ImageCompressor(method=METHOD_LOSSY_DCT, quality=dct_quality).compress(splash)
    bits = unpack_bits(pkt.wire_bytes)

    # Esquema digital principal seleccionado (BFSK / MFSK / ASK / BPSK / 16-QAM)
    sps = 48 if scheme.upper() == "MFSK" else 32
    mod_main = DigitalPassbandModulator(scheme=scheme, sampling_rate_hz=48000, samples_per_symbol=sps)
    wave_main = mod_main.modulate(pkt)

    wav_main = export_modulated_audio(
        wave_main, os.path.join(output_dir, f"modulada_{mod_main.scheme.lower()}.wav")
    )
    fig_main = os.path.join(output_dir, f"01_modulacion_{mod_main.scheme.lower()}.png")
    plot_modulated_signal(wave_main, source_bits=bits, zoom_ms=15.0, save_path=fig_main, show=show)

    # Muestras rápidas de los demás esquemas solicitados en el enunciado (sobre primeros 128 bits)
    sample_bits = bits[:128]
    comparative = {}
    for alt_scheme in ("ASK", "BFSK", "MFSK", "BPSK", "16-QAM"):
        alt_sps = 48 if alt_scheme == "MFSK" else 32
        m = DigitalPassbandModulator(scheme=alt_scheme, sampling_rate_hz=48000, samples_per_symbol=alt_sps)
        w = m.modulate(sample_bits, add_framing=False)
        fig_alt = os.path.join(output_dir, f"comp_{alt_scheme.lower().replace('-', '')}.png")
        wav_alt = export_modulated_audio(
            w, os.path.join(output_dir, f"preview_{alt_scheme.lower().replace('-', '')}.wav")
        )
        plot_modulated_signal(w, source_bits=sample_bits, zoom_ms=12.0, save_path=fig_alt, show=False)
        comparative[alt_scheme] = {
            "bit_rate_bps": round(w.metadata["bit_rate_bps"], 1),
            "duration_s": round(w.duration_s, 3),
            "wav": wav_alt,
            "fig": fig_alt,
        }

    # Comparativa analógica AM y FM sobre fila representativa de la imagen
    am_wave = AMModulator(carrier_freq_hz=4000.0, mod_index=0.8).modulate(splash)
    fm_wave = FMModulator(carrier_freq_hz=4000.0, freq_dev_hz=1200.0).modulate(splash)
    fig_am = os.path.join(output_dir, "02_modulacion_am.png")
    fig_fm = os.path.join(output_dir, "03_modulacion_fm.png")
    wav_am = export_modulated_audio(am_wave, os.path.join(output_dir, "modulada_am.wav"))
    wav_fm = export_modulated_audio(fm_wave, os.path.join(output_dir, "modulada_fm.wav"))
    plot_modulated_signal(am_wave, zoom_ms=12.0, save_path=fig_am, show=False)
    plot_modulated_signal(fm_wave, zoom_ms=12.0, save_path=fig_fm, show=False)

    report = {
        "working_image": f"{splash.width}x{splash.height}",
        "compressed_packet_bytes": pkt.compressed_bytes_count,
        "compression_ratio": round(pkt.compression_ratio, 2),
        "primary_modulation": {
            "scheme": mod_main.scheme,
            "sampling_rate_hz": wave_main.sampling_rate_hz,
            "baud_rate": wave_main.baud_rate,
            "bit_rate_bps": wave_main.metadata["bit_rate_bps"],
            "duration_s": round(wave_main.duration_s, 3),
            "wav_file": wav_main,
            "fig_file": fig_main,
        },
        "digital_schemes_preview": comparative,
        "analog_schemes": {
            "AM": {"duration_s": round(am_wave.duration_s, 3), "wav": wav_am, "fig": fig_am},
            "FM": {"duration_s": round(fm_wave.duration_s, 3), "wav": wav_fm, "fig": fig_fm},
        },
    }

    report_path = os.path.join(output_dir, "fase3_reporte.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print("=== FASE 3: MODULACION PASABANDA Y AUDIO EN BITS ===")
    print(
        f"Paquete comprimido      : {pkt.compressed_bytes_count:,} B "
        f"(Ratio {pkt.compression_ratio:.2f}x | {len(bits):,} bits)"
    )
    print(
        f"Modulación principal    : {mod_main.scheme} @ {wave_main.metadata['bit_rate_bps']:.0f} bps "
        f"(fs = {wave_main.sampling_rate_hz:,} Hz | Duración audio = {wave_main.duration_s:.2f} s)"
    )
    print(f"Audio WAV generado      : {wav_main}")
    print(f"Reporte guardado en     : {os.path.abspath(report_path)}")

    if play:
        print("Reproduciendo los primeros segundos de la señal modulada en bits...")
        preview_samples = wave_main.samples[: min(len(wave_main.samples), wave_main.sampling_rate_hz * 4)]
        play_wav_or_samples((preview_samples, wave_main.sampling_rate_hz), async_play=False)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Fase 3: Modulación Audible de Imagen Comprimida")
    parser.add_argument("--image", default="data/input/selfie_dsp.jpeg", help="Ruta a imagen JPG/JPEG")
    parser.add_argument("--out", default="data/output/fase3", help="Directorio de salida")
    parser.add_argument("--scheme", default="BFSK", help="Esquema principal: BFSK, MFSK, ASK, BPSK, 16-QAM")
    parser.add_argument("--max-dim", type=int, default=96, help="Dimensión máxima para trama de audio")
    parser.add_argument("--quality", type=int, default=65, help="Calidad DCT 8x8")
    parser.add_argument("--play", action="store_true", help="Reproducir audio modulado por altavoz")
    parser.add_argument("--show", action="store_true", help="Mostrar gráficas en pantalla")
    args = parser.parse_args()
    run_fase3(
        image_path=args.image,
        output_dir=args.out,
        scheme=args.scheme,
        work_max_dim=args.max_dim,
        dct_quality=args.quality,
        play=args.play,
        show=args.show,
    )


if __name__ == "__main__":
    main()
