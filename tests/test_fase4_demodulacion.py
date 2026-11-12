"""Pruebas unitarias de Fase 4: sincronización, demodulación digital/analógica y resiliencia AWGN."""

import os
import tempfile
import unittest
import numpy as np

from dsp_img.core.audio_wav import samples_to_wav_bytes, wav_bytes_to_samples
from dsp_img.core.codec import METHOD_LOSSY_DCT, ImageCompressor
from dsp_img.core.contracts import ImageSignal, ModulatedWaveform
from dsp_img.core.primitives import pearson_correlation, psnr_db, unpack_bits
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
    SUPPORTED_DIGITAL_SCHEMES,
)


def _add_noise(samples: np.ndarray, snr_db: float, seed: int = 9) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p_sig = float(np.mean(samples.astype(np.float64) ** 2))
    p_noise = p_sig / (10.0 ** (snr_db / 10.0))
    return (samples.astype(np.float64) + rng.normal(0.0, np.sqrt(p_noise), len(samples))).astype(
        np.float32
    )


class TestFase4Demodulacion(unittest.TestCase):
    """Valida TX->RX completo en los 5 esquemas digitales y AM/FM."""

    def test_all_digital_schemes_zero_ber_and_crc_recovery(self) -> None:
        y, x = np.mgrid[0:48, 0:48]
        rgb = np.stack(
            [
                np.clip(0.5 + 0.4 * np.sin(2.0 * np.pi * x / 16.0), 0.0, 1.0),
                np.clip(y / 48.0, 0.0, 1.0),
                np.clip(x / 48.0, 0.0, 1.0),
            ],
            axis=2,
        ).astype(np.float32)
        img = ImageSignal(pixels=rgb)
        comp = ImageCompressor(method=METHOD_LOSSY_DCT, quality=65)
        pkt = comp.compress(img)
        tx_bits = unpack_bits(pkt.wire_bytes)

        for scheme in SUPPORTED_DIGITAL_SCHEMES:
            sps = 48 if scheme == "MFSK" else 32
            mod = DigitalPassbandModulator(
                scheme=scheme, sampling_rate_hz=48000, samples_per_symbol=sps, leading_silence_s=0.025
            )
            tx_wave = mod.modulate(pkt)

            # Simular receptor ciego leyendo bytes WAV puros (sin pasar metadata TX)
            wav_bytes = samples_to_wav_bytes(tx_wave.samples, tx_wave.sampling_rate_hz)
            rx_samples, rx_fs, _ = wav_bytes_to_samples(wav_bytes)
            blind_wave = ModulatedWaveform(
                samples=rx_samples,
                sampling_rate_hz=rx_fs,
                carrier_freq_hz=mod.carrier_freq_hz,
                modulation_type=scheme,
                is_digital=True,
                metadata={"samples_per_symbol": sps, "fsk_freqs_hz": list(mod.fsk_freqs_hz)},
            )

            demod = DigitalPassbandDemodulator(
                scheme=scheme, sampling_rate_hz=rx_fs, samples_per_symbol=sps
            )
            rx_res = demod.demodulate(
                blind_wave, reference_bits=tx_bits, has_framing=True, auto_sync=True
            )

            self.assertEqual(rx_res.bit_error_rate, 0.0, msg=f"BER != 0 en {scheme}")
            self.assertTrue(rx_res.crc_valid, msg=f"CRC inválido en {scheme}")
            self.assertEqual(rx_res.metadata["recovered_bytes"], pkt.wire_bytes)

            rec_img = comp.decompress(rx_res.metadata["recovered_bytes"])
            self.assertEqual(rec_img.shape, img.shape)
            self.assertGreater(psnr_db(img.pixels, rec_img.pixels), 20.0)

    def test_awgn_noise_resilience_bfsk_and_bpsk(self) -> None:
        comp = ImageCompressor(method=METHOD_LOSSY_DCT, quality=60)
        rng = np.random.default_rng(99)
        img = ImageSignal(pixels=rng.integers(0, 255, size=(32, 32, 3), dtype=np.uint8))
        pkt = comp.compress(img)
        tx_bits = unpack_bits(pkt.wire_bytes)

        for scheme in ("BFSK", "BPSK"):
            mod = DigitalPassbandModulator(scheme=scheme, sampling_rate_hz=48000, samples_per_symbol=32)
            tx_wave = mod.modulate(pkt)
            noisy_samples = _add_noise(tx_wave.samples, snr_db=16.0)
            noisy_wave = ModulatedWaveform(
                samples=noisy_samples,
                sampling_rate_hz=48000,
                carrier_freq_hz=mod.carrier_freq_hz,
                modulation_type=scheme,
                is_digital=True,
                metadata={"samples_per_symbol": 32, "fsk_freqs_hz": list(mod.fsk_freqs_hz)},
            )
            demod = DigitalPassbandDemodulator(scheme=scheme, sampling_rate_hz=48000, samples_per_symbol=32)
            rx = demod.demodulate(noisy_wave, reference_bits=tx_bits, has_framing=True, auto_sync=True)
            self.assertEqual(rx.bit_error_rate, 0.0, msg=f"Falló bajo AWGN 16dB en {scheme}")
            self.assertTrue(rx.crc_valid)

    def test_analog_am_and_fm_demodulation_and_exports(self) -> None:
        fs = 16000
        t = np.linspace(0.0, 0.1, int(fs * 0.1), endpoint=False)
        msg = 0.6 * np.sin(2.0 * np.pi * 220.0 * t) + 0.35 * np.cos(2.0 * np.pi * 510.0 * t)

        am_wave = AMModulator(carrier_freq_hz=4000.0, mod_index=0.8).modulate(msg, source_fs_hz=fs)
        fm_wave = FMModulator(carrier_freq_hz=4000.0, freq_dev_hz=1200.0).modulate(msg, source_fs_hz=fs)

        am_rx_coh = AMDemodulator(method="coherent", cutoff_freq_hz=2000.0).demodulate(am_wave)
        am_rx_env = AMDemodulator(method="envelope", cutoff_freq_hz=2000.0).demodulate(am_wave)
        fm_rx = FMDemodulator(cutoff_freq_hz=2000.0).demodulate(fm_wave)

        # Ignorar bordes transitorios de filtros/Hilbert
        sl = slice(400, -400)
        r_am_coh = pearson_correlation(am_wave.metadata["message_samples"][sl], am_rx_coh.recovered_signal_1d[sl])
        r_am_env = pearson_correlation(am_wave.metadata["message_samples"][sl], am_rx_env.recovered_signal_1d[sl])
        r_fm = pearson_correlation(fm_wave.metadata["message_samples"][sl], fm_rx.recovered_signal_1d[sl])

        self.assertGreater(r_am_coh, 0.96)
        self.assertGreater(r_am_env, 0.94)
        self.assertGreater(r_fm, 0.95)

        with tempfile.TemporaryDirectory() as tmpdir:
            wav_p = os.path.join(tmpdir, "demod_am.wav")
            fig_p = os.path.join(tmpdir, "demod_am.png")
            export_demodulated_audio(am_rx_coh, wav_p)
            plot_demodulated_recovery(
                am_wave, am_rx_coh, reference_analog=am_wave.metadata["message_samples"], save_path=fig_p
            )
            self.assertTrue(os.path.exists(wav_p) and os.path.getsize(wav_p) > 500)
            self.assertTrue(os.path.exists(fig_p) and os.path.getsize(fig_p) > 1000)


if __name__ == "__main__":
    unittest.main()
