"""Pruebas unitarias de Fase 0: contratos, primitivas DSP, tema visual y WAV I/O."""

import os
import tempfile
import unittest
import numpy as np

from dsp_img.core.audio_wav import (
    load_wav,
    samples_to_wav_bytes,
    save_wav,
    wav_bytes_to_samples,
)
from dsp_img.core.contracts import ImageSignal, QuantizedStream
from dsp_img.core.primitives import (
    compute_spectrum,
    diagnostico_nyquist,
    dither_signal,
    estimate_max_frequency,
    pack_bits,
    pearson_correlation,
    psnr_db,
    quantize_uniform,
    reconstruct_sinc,
    reconstruct_zoh,
    rmse,
    snr_db,
    sqnr_theoretical_db,
    unpack_bits,
)
from dsp_img.core.theme import apply_plot_theme


class TestFase0Fundacion(unittest.TestCase):
    """Valida que el núcleo base y los contratos operen con exactitud matemática."""

    def test_image_signal_normalization_and_1d(self) -> None:
        rgb = np.array([[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [255, 255, 255]]], dtype=np.uint8)
        sig = ImageSignal(pixels=rgb, sample_rate_1d_hz=16000)

        self.assertEqual(sig.shape, (2, 2, 3))
        self.assertEqual(sig.num_pixels, 4)
        np.testing.assert_array_equal(sig.to_uint8(), rgb)

        bipolar = sig.to_1d_bipolar()
        self.assertEqual(bipolar.shape, (4,))
        self.assertTrue(np.all((bipolar >= -1.0) & (bipolar <= 1.0)))

    def test_bit_pack_unpack_roundtrip(self) -> None:
        rng = np.random.default_rng(42)
        bits = rng.integers(0, 2, size=137, dtype=np.uint8)
        packed = pack_bits(bits)
        unpacked = unpack_bits(packed, total_bits=len(bits))
        np.testing.assert_array_equal(unpacked, bits)

    def test_quantization_and_sqnr_progression(self) -> None:
        t = np.linspace(0.0, 0.1, 2000, endpoint=False)
        x = np.sin(2.0 * np.pi * 100.0 * t)

        _, x_q4, delta4 = quantize_uniform(x, bits=4, v_min=-1.0, v_max=1.0)
        _, x_q8, delta8 = quantize_uniform(x, bits=8, v_min=-1.0, v_max=1.0)

        self.assertLessEqual(np.max(np.abs(x - x_q4)), delta4 / 2.0 + 1e-6)
        self.assertLessEqual(np.max(np.abs(x - x_q8)), delta8 / 2.0 + 1e-6)

        snr4 = snr_db(x, x - x_q4)
        snr8 = snr_db(x, x - x_q8)
        self.assertGreater(snr8, snr4)
        self.assertAlmostEqual(sqnr_theoretical_db(8), 49.9248, places=3)

    def test_quantized_stream_byte_roundtrip(self) -> None:
        bits = np.array([1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0], dtype=np.uint8)
        raw = pack_bits(bits)
        stream = QuantizedStream.from_bytes(
            raw_bytes=raw,
            total_bits=len(bits),
            bits_per_sample=4,
            sample_rate_hz=8000,
            original_shape=(2, 2, 1),
        )
        np.testing.assert_array_equal(stream.quantized_levels, np.array([11, 4, 14, 2]))
        self.assertEqual(stream.total_bytes, 2)
        self.assertEqual(stream.to_bytes(), raw)

    def test_spectrum_nyquist_and_sinc_exact_at_samples(self) -> None:
        fs = 1000.0
        t = np.arange(0.0, 1.0, 1.0 / fs)
        x = 0.8 * np.sin(2.0 * np.pi * 120.0 * t)

        freqs, mag, _ = compute_spectrum(x, sample_rate=fs)
        peak_freq = freqs[int(np.argmax(mag))]
        self.assertAlmostEqual(peak_freq, 120.0, delta=2.0)

        fmax = estimate_max_frequency(freqs, mag, energy_threshold=0.99)
        diag_ok = diagnostico_nyquist(fmax=fmax, fs=fs)
        diag_bad = diagnostico_nyquist(fmax=fmax, fs=150.0)
        self.assertTrue(diag_ok["cumple"])
        self.assertFalse(diag_bad["cumple"])

        # Reconstrucción Sinc debe coincidir exactamente en los instantes muestreados
        t_m = np.arange(0.0, 0.2, 1.0 / 200.0)
        x_m = np.cos(2.0 * np.pi * 25.0 * t_m)
        x_hat_at_samples = reconstruct_sinc(t_m, t_m, x_m, fs=200.0, n_pulses=32)
        self.assertLess(rmse(x_m, x_hat_at_samples), 1e-12)

        x_zoh = reconstruct_zoh(t_m, t_m, x_m)
        self.assertLess(rmse(x_m, x_zoh), 1e-12)

    def test_dither_and_fidelity_metrics(self) -> None:
        noise = dither_signal(1000, delta=0.01, kind="tpdf", seed=123)
        self.assertEqual(len(noise), 1000)
        self.assertLessEqual(np.max(np.abs(noise)), 0.01 + 1e-6)

        a = np.linspace(0.0, 1.0, 100)
        b = a * 0.99 + 0.005
        self.assertGreater(psnr_db(a, b), 35.0)
        self.assertGreater(pearson_correlation(a, b), 0.999)

    def test_wav_memory_and_disk_roundtrip(self) -> None:
        sr = 16000
        t = np.linspace(0.0, 0.05, int(sr * 0.05), endpoint=False)
        samples = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)

        raw_wav = samples_to_wav_bytes(samples, sample_rate_hz=sr, bit_depth=16)
        loaded_mem, sr_mem, depth_mem = wav_bytes_to_samples(raw_wav)
        self.assertEqual(sr_mem, sr)
        self.assertEqual(depth_mem, 16)
        self.assertLess(rmse(samples, loaded_mem), 1e-4)

        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = os.path.join(tmpdir, "test.wav")
            save_wav(wav_path, samples, sr)
            loaded_disk, sr_disk, _ = load_wav(wav_path)
            self.assertEqual(sr_disk, sr)
            self.assertLess(rmse(samples, loaded_disk), 1e-4)

    def test_theme_application(self) -> None:
        dark = apply_plot_theme("dark")
        light = apply_plot_theme("light")
        self.assertIn("primary", dark)
        self.assertNotEqual(dark["bg"], light["bg"])


if __name__ == "__main__":
    unittest.main()
