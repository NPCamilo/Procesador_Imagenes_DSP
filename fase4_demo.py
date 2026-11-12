"""
Script demostrativo de Fase 4 (Punto 5: Demodulación, Sincronización y Recuperación):
  - Modula la foto filtrada/comprimida y simula canal (ideal y con ruido AWGN opcional)
  - Carga el audio WAV modulado como un receptor independiente (blind sync por preámbulo)
  - Demodula BFSK, MFSK, ASK, BPSK, 16-QAM, AM y FM
  - Verifica BER = 0.0 y CRC32 OK, exporta gráficas y audio demodulado reproducible
"""

from __future__ import annotations

import argparse
import json
import os
import numpy as np

from dsp_img.core.audio_wav import play_wav_or_samples, wav_bytes_to_samples
from dsp_img.core.codec import METHOD_LOSSY_DCT, ImageCompressor
from dsp_img.core.contracts import ModulatedWaveform
from dsp_img.core.image_io import load_image
from dsp_img.core.primitives import pearson_correlation, unpack_bits
from dsp_img.core.red_filter import isolate_largest_red_region
from dsp_img.demodulation import (
    AMDemodulator,
    DigitalPassbandDemodulator,
    FMDemodulator,
    export_demodulated_audio,
    plot_demodulated_recovery,
)
from dsp_img.modulation import (
    AMModulator,
    DigitalPassbandModulator,
    FMModulator,
    export_modulated_audio,
)


def _add_awgn(samples: np.ndarray, snr_db_target: Optional[float], seed: int = 42) -> np.ndarray:
    """Agrega ruido blanco gaussiano si se especifica un SNR objetivo."""
    if snr_db_target is None:
        return samples
    rng = np.random.default_rng(seed)
    sig_power = float(np.mean(samples.astype(np.float64) ** 2))
    noise_power = sig_power / (10.0 ** (snr_db_target / 10.0))
    noise = rng.normal(0.0, np.sqrt(noise_power), size=len(samples))
    noisy = samples.astype(np.float64) + noise
    peak = float(np.max(np.abs(noisy))) or 1.0
    return (noisy / max(1.0, peak)).astype(np.float32)


def run_fase4(
    image_path: str = "data/input/selfie_dsp.jpeg",
    output_dir: str = "data/output/fase4",
    scheme: str = "BFSK",
    work_max_dim: int = 96,
    dct_quality: int = 65,
    snr_db: Optional[float] = None,
    play: bool = False,
    show: bool = False,
) -> dict:
    """Ejecuta el ciclo TX -> Canal -> RX Demodulación completo y guarda artefactos."""
    os.makedirs(output_dir, exist_ok=True)

    img = load_image(image_path, max_dim=work_max_dim)
    splash = isolate_largest_red_region(img).filtered
    compressor = ImageCompressor(method=METHOD_LOSSY_DCT, quality=dct_quality)
    pkt = compressor.compress(splash)
    tx_bits = unpack_bits(pkt.wire_bytes)

    sps = 48 if scheme.upper() == "MFSK" else 32
    mod = DigitalPassbandModulator(scheme=scheme, sampling_rate_hz=48000, samples_per_symbol=sps)
    tx_wave = mod.modulate(pkt)

    # Exportar a WAV y recargar como receptor ciego (sin pasar metadata TX al demodulador)
    wav_tx_path = export_modulated_audio(tx_wave, os.path.join(output_dir, f"tx_{mod.scheme.lower()}.wav"))
    with open(wav_tx_path, "rb") as handle:
        rx_samples, rx_fs, _ = wav_bytes_to_samples(handle.read())
    rx_samples = _add_awgn(rx_samples, snr_db_target=snr_db)

    blind_wave = ModulatedWaveform(
        samples=rx_samples,
        sampling_rate_hz=rx_fs,
        carrier_freq_hz=mod.carrier_freq_hz,
        modulation_type=mod.scheme,
        is_digital=True,
        metadata={"samples_per_symbol": sps, "fsk_freqs_hz": list(mod.fsk_freqs_hz)},
    )

    demod = DigitalPassbandDemodulator(scheme=mod.scheme, sampling_rate_hz=rx_fs, samples_per_symbol=sps)
    rx_result = demod.demodulate(blind_wave, reference_bits=tx_bits, has_framing=True, auto_sync=True)

    wav_rx_path = export_demodulated_audio(
        rx_result, os.path.join(output_dir, f"demodulada_{mod.scheme.lower()}.wav")
    )
    fig_rx = os.path.join(output_dir, f"01_demodulacion_{mod.scheme.lower()}.png")
    plot_demodulated_recovery(
        blind_wave, rx_result, reference_bits=tx_bits, save_path=fig_rx, show=show
    )

    # Comparativa rápida en todos los esquemas digitales + AM/FM
    schemes_summary = {}
    for alt in ("BFSK", "MFSK", "ASK", "BPSK", "16-QAM"):
        alt_sps = 48 if alt == "MFSK" else 32
        m = DigitalPassbandModulator(scheme=alt, sampling_rate_hz=48000, samples_per_symbol=alt_sps)
        w = m.modulate(pkt)
        d = DigitalPassbandDemodulator(scheme=alt, sampling_rate_hz=48000, samples_per_symbol=alt_sps)
        r = d.demodulate(w, reference_bits=tx_bits, has_framing=True, auto_sync=True)
        schemes_summary[alt] = {
            "ber": r.bit_error_rate,
            "crc_valid": r.crc_valid,
            "sync_offset_samples": r.sync_offset_samples,
        }
        if alt == "16-QAM":
            fig_qam = os.path.join(output_dir, "02_demodulacion_16qam_constelacion.png")
            plot_demodulated_recovery(w, r, reference_bits=tx_bits, save_path=fig_qam, show=False)

    # Demodulación analógica AM y FM
    am_wave = AMModulator(carrier_freq_hz=4000.0, mod_index=0.8).modulate(splash)
    am_rx = AMDemodulator(method="coherent", cutoff_freq_hz=3500.0).demodulate(am_wave)
    am_ref = am_wave.metadata["message_samples"]
    am_corr = pearson_correlation(am_ref, am_rx.recovered_signal_1d)
    fig_am = os.path.join(output_dir, "03_demodulacion_am.png")
    export_demodulated_audio(am_rx, os.path.join(output_dir, "demodulada_am.wav"))
    plot_demodulated_recovery(am_wave, am_rx, reference_analog=am_ref, save_path=fig_am, show=False)

    fm_wave = FMModulator(carrier_freq_hz=4000.0, freq_dev_hz=1200.0).modulate(splash)
    fm_rx = FMDemodulator(cutoff_freq_hz=3500.0).demodulate(fm_wave)
    fm_ref = fm_wave.metadata["message_samples"]
    fm_corr = pearson_correlation(fm_ref, fm_rx.recovered_signal_1d)
    fig_fm = os.path.join(output_dir, "04_demodulacion_fm.png")
    export_demodulated_audio(fm_rx, os.path.join(output_dir, "demodulada_fm.wav"))
    plot_demodulated_recovery(fm_wave, fm_rx, reference_analog=fm_ref, save_path=fig_fm, show=False)

    report = {
        "primary_scheme": mod.scheme,
        "snr_channel_db": snr_db,
        "sync_offset_samples": rx_result.sync_offset_samples,
        "ber": rx_result.bit_error_rate,
        "crc32_valid": rx_result.crc_valid,
        "recovered_bytes": len(rx_result.metadata.get("recovered_bytes") or b""),
        "all_digital_schemes": schemes_summary,
        "analog_am_pearson_r": round(am_corr, 4),
        "analog_fm_pearson_r": round(fm_corr, 4),
        "artifacts": {
            "demodulated_wav": wav_rx_path,
            "fig_primary": fig_rx,
            "fig_am": fig_am,
            "fig_fm": fig_fm,
        },
    }

    report_path = os.path.join(output_dir, "fase4_reporte.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print("=== FASE 4: DEMODULACION Y RECUPERACION DE INFORMACION ===")
    print(
        f"Demodulación principal  : {mod.scheme} | Sync offset = {rx_result.sync_offset_samples} muestras | "
        f"BER = {rx_result.bit_error_rate:.2e} | CRC32 = {'OK' if rx_result.crc_valid else 'ERROR'}"
    )
    print(f"Resumen 5 esquemas      : " + ", ".join(f"{k}(BER={v['ber']:.0f}, CRC={v['crc_valid']})" for k, v in schemes_summary.items()))
    print(f"AM Pearson r            : {am_corr:.4f} | FM Pearson r = {fm_corr:.4f}")
    print(f"Audio demodulado WAV    : {wav_rx_path}")
    print(f"Reporte guardado en     : {os.path.abspath(report_path)}")

    if play:
        print("Reproduciendo muestra de la señal banda base demodulada...")
        preview = rx_result.recovered_signal_1d[: min(len(rx_result.recovered_signal_1d), rx_fs * 4)]
        play_wav_or_samples((preview, rx_fs), async_play=False)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Fase 4: Demodulación y Verificación BER/CRC")
    parser.add_argument("--image", default="data/input/selfie_dsp.jpeg", help="Ruta a imagen JPG/JPEG")
    parser.add_argument("--out", default="data/output/fase4", help="Directorio de salida")
    parser.add_argument("--scheme", default="BFSK", help="Esquema principal: BFSK, MFSK, ASK, BPSK, 16-QAM")
    parser.add_argument("--max-dim", type=int, default=96, help="Dimensión máxima de trabajo")
    parser.add_argument("--quality", type=int, default=65, help="Calidad DCT")
    parser.add_argument("--snr", type=float, default=None, help="SNR de ruido AWGN en dB (opcional)")
    parser.add_argument("--play", action="store_true", help="Reproducir señal demodulada")
    parser.add_argument("--show", action="store_true", help="Mostrar gráficas en pantalla")
    args = parser.parse_args()
    run_fase4(
        image_path=args.image,
        output_dir=args.out,
        scheme=args.scheme,
        work_max_dim=args.max_dim,
        dct_quality=args.quality,
        snr_db=args.snr,
        play=args.play,
        show=args.show,
    )


if __name__ == "__main__":
    main()
