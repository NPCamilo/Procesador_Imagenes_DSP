"""Pruebas unitarias de Fase 3: framing y moduladores digitales/analógicos audibles."""

import os
import tempfile
import unittest
import numpy as np
from scipy import signal as sp_signal

from dsp_img.core.audio_wav import wav_bytes_to_samples
from dsp_img.core.codec import METHOD_LOSSY_DCT, ImageCompressor
from dsp_img.core.contracts import ImageSignal
from dsp_img.core.primitives import compute_spectrum
from dsp_img.modulation import (
    AMModulator,
    DigitalPassbandModulator,
    FMModulator,
    SUPPORTED_DIGITAL_SCHEMES,
    build_framed_bitstream,
    export_modulated_audio,
    plot_modulated_signal,
)


class TestFase3Modulacion(unittest.TestCase):
    """Valida espectros, amplitud normalizada, framing y exportación WAV audible."""

    def test_framing_overhead_and_bit_values(self) -> None:
        payload = b"UTP-DSP-TEST"
        frame, length = build_framed_bitstream(payload)
        self.assertEqual(length, len(payload))
        # 48 bits de preámbulo/sync + 32 bits de longitud + 8*len(payload)
        self.assertEqual(len(frame), 48 + 32 + len(payload) * 8)
        self.assertTrue(np.all((frame == 0) | (frame == 1)))

    def test_all_digital_schemes_spectral_peaks_and_wav(self) -> None:
        rng = np.random.default_rng(7)
        bits = rng.integers(0, 2, size=240, dtype=np.uint8)

        for scheme in SUPPORTED_DIGITAL_SCHEMES:
            sps = 48 if scheme == "MFSK" else 32
            mod = DigitalPassbandModulator(
                scheme=scheme, sampling_rate_hz=48000, samples_per_symbol=sps, leading_silence_s=0.0
            )
            wave = mod.modulate(bits, add_framing=False)
            self.assertTrue(wave.is_digital)
            self.assertLessEqual(float(np.max(np.abs(wave.samples))), 1.0)
            self.assertGreater(wave.duration_s, 0.02)

            freqs, mag, _ = compute_spectrum(wave.samples, sample_rate=wave.sampling_rate_hz)
            peak_freq = float(freqs[int(np.argmax(mag))])

            if scheme == "BFSK":
                self.assertTrue(any(abs(peak_freq - f) < 80.0 for f in (1500.0, 3000.0)))
            elif scheme == "MFSK":
                self.assertTrue(any(abs(peak_freq - f) < 80.0 for f in (1000.0, 2000.0, 3000.0, 4000.0)))
            elif scheme == "ASK":
                self.assertAlmostEqual(peak_freq, 3000.0, delta=150.0)
            else:
                # BPSK y 16-QAM son señales de portadora suprimida: su centroide espectral
                # y pico quedan dentro del lóbulo principal [fc - Baud, fc + Baud].
                centroid = float(np.sum(freqs * (mag**2)) / np.sum(mag**2))
                self.assertAlmostEqual(centroid, 3000.0, delta=350.0)
                self.assertAlmostEqual(peak_freq, 3000.0, delta=wave.baud_rate)

            if scheme in ("BPSK", "16-QAM"):
                self.assertIn("constellation_iq", wave.metadata)

        # Verificar exportación WAV y gráfica sobre 16-QAM
        mod_qam = DigitalPassbandModulator(scheme="16-QAM", sampling_rate_hz=48000, samples_per_symbol=32)
        wave_qam = mod_qam.modulate(b"IMAGEN_COMPRIMIDA")
        with tempfile.TemporaryDirectory() as tmpdir:
            wav_p = os.path.join(tmpdir, "qam.wav")
            fig_p = os.path.join(tmpdir, "qam.png")
            export_modulated_audio(wave_qam, wav_p)
            plot_modulated_signal(wave_qam, source_bits=bits[:64], save_path=fig_p)
            self.assertTrue(os.path.exists(wav_p) and os.path.getsize(wav_p) > 500)
            self.assertTrue(os.path.exists(fig_p) and os.path.getsize(fig_p) > 1000)
            with open(wav_p, "rb") as handle:
                loaded, sr, _ = wav_bytes_to_samples(handle.read())
            self.assertEqual(sr, 48000)
            self.assertEqual(len(loaded), len(wave_qam.samples))

    def test_analog_am_and_fm_modulators(self) -> None:
        fs_msg = 16000
        t = np.linspace(0.0, 0.05, int(fs_msg * 0.05), endpoint=False)
        msg = np.sin(2.0 * np.pi * 300.0 * t)

        am = AMModulator(carrier_freq_hz=4000.0, mod_index=0.75, target_fs_hz=48000)
        fm = FMModulator(carrier_freq_hz=4000.0, freq_dev_hz=1000.0, target_fs_hz=48000)

        w_am = am.modulate(msg, source_fs_hz=fs_msg)
        w_fm = fm.modulate(msg, source_fs_hz=fs_msg)

        self.assertFalse(w_am.is_digital)
        self.assertGreaterEqual(w_am.sampling_rate_hz, 4 * 4000)

        freqs_am, mag_am, _ = compute_spectrum(w_am.samples, w_am.sampling_rate_hz)
        self.assertAlmostEqual(float(freqs_am[int(np.argmax(mag_am))]), 4000.0, delta=60.0)

        # FM debe mantener envolvente prácticamente constante en la zona interior
        env_fm = np.abs(sp_signal.hilbert(w_fm.samples))
        interior = env_fm[100:-100]
        self.assertLess(float(np.std(interior)), 0.05)

    def test_compressed_image_packet_to_bfsk_audio(self) -> None:
        rng = np.random.default_rng(12)
        arr = rng.integers(0, 255, size=(32, 32, 3), dtype=np.uint8)
        img = ImageSignal(pixels=arr)
        pkt = ImageCompressor(method=METHOD_LOSSY_DCT, quality=60).compress(img)

        mod = DigitalPassbandModulator(scheme="BFSK", sampling_rate_hz=48000, samples_per_symbol=32)
        wave = mod.modulate(pkt)
        self.assertGreater(wave.duration_s, 0.5)
        self.assertEqual(wave.metadata["payload_bytes_len"], pkt.compressed_bytes_count)


if __name__ == "__main__":
    unittest.main()
