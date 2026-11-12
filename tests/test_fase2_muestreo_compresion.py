"""Pruebas unitarias de Fase 2: muestreo NQS, cuantización Byte/Bit y compresor .dspimg."""

import os
import tempfile
import unittest
import numpy as np

from dsp_img.core.codec import (
    METHOD_LOSSLESS,
    METHOD_LOSSY_DCT,
    ImageCompressor,
    load_compressed_packet,
    plot_compression_comparison,
    save_compressed_packet,
)
from dsp_img.core.contracts import ImageSignal
from dsp_img.core.image_io import load_image
from dsp_img.core.primitives import psnr_db, rmse
from dsp_img.core.quantization import (
    format_digital_preview,
    load_digital_stream,
    plot_quantization_resolution_study,
    quantize_image,
    save_digital_stream,
)
from dsp_img.core.red_filter import isolate_largest_red_region
from dsp_img.core.sampling_nqs import (
    plot_nqs_sampling_study,
    sample_image_nqs,
    simulate_1d_nqs_sampling,
)


def _make_textured_test_image(h: int = 93, w: int = 117) -> ImageSignal:
    """Crea una imagen con gradientes y franjas de alta frecuencia (dimensiones no múltiplo de 8)."""
    y, x = np.mgrid[0:h, 0:w]
    r = 0.5 + 0.4 * np.sin(2.0 * np.pi * x / 18.0) * np.cos(2.0 * np.pi * y / 22.0)
    g = np.clip(y / float(h), 0.0, 1.0)
    b = np.clip(x / float(w), 0.0, 1.0)
    rgb = np.stack([np.clip(r, 0.0, 1.0), g, b], axis=2).astype(np.float32)
    return ImageSignal(pixels=rgb, sample_rate_1d_hz=16000)


class TestFase2MuestreoCompresion(unittest.TestCase):
    """Valida muestreo NQS, cuantización [Byte/Bit] y códec .dspimg."""

    def test_spatial_and_1d_nqs_sampling(self) -> None:
        img = _make_textured_test_image(96, 128)
        sub_aa = sample_image_nqs(img, spatial_factor=4, apply_antialias=True)
        sub_raw = sample_image_nqs(img, spatial_factor=4, apply_antialias=False)
        self.assertEqual((sub_aa.height, sub_aa.width), (24, 32))
        self.assertEqual((sub_raw.height, sub_raw.width), (24, 32))

        row = img.to_luminance()[48, :]
        t_d, x_d, fs_d = simulate_1d_nqs_sampling(row, fs_hz=16000, downsample_factor=4)
        self.assertEqual(fs_d, 4000)
        self.assertEqual(len(t_d), len(x_d))
        self.assertEqual(len(x_d), 32)

    def test_quantization_byte_bit_sqnr_and_bin_serialization(self) -> None:
        img = _make_textured_test_image(64, 64)
        q1_img, s1 = quantize_image(img, bits_per_sample=1)
        q4_img, s4 = quantize_image(img, bits_per_sample=4)
        q8_img, s8 = quantize_image(img, bits_per_sample=8)

        self.assertLess(s1.sqnr_empirical_db, s4.sqnr_empirical_db)
        self.assertLess(s4.sqnr_empirical_db, s8.sqnr_empirical_db)
        self.assertEqual(s8.total_bytes, 64 * 64 * 3)
        self.assertEqual(s4.total_bytes, (64 * 64 * 3 * 4) // 8)
        self.assertGreater(psnr_db(img.pixels, q8_img.pixels), 45.0)
        self.assertLess(psnr_db(img.pixels, q1_img.pixels), psnr_db(img.pixels, q4_img.pixels))

        preview = format_digital_preview(s4)
        self.assertEqual(preview["bits_per_sample"], 4)
        self.assertEqual(len(preview["first_64_bits"]), 64)

        with tempfile.TemporaryDirectory() as tmpdir:
            base = os.path.join(tmpdir, "test_stream")
            bin_p, meta_p = save_digital_stream(s4, base)
            self.assertTrue(os.path.exists(bin_p) and os.path.exists(meta_p))
            loaded = load_digital_stream(base)
            np.testing.assert_array_equal(loaded.quantized_levels, s4.quantized_levels)
            np.testing.assert_array_equal(loaded.bitstream, s4.bitstream)

    def test_lossless_dpcm_codec_exact_reconstruction(self) -> None:
        img = _make_textured_test_image(77, 91)  # Dimensiones impares
        compressor = ImageCompressor(method=METHOD_LOSSLESS)

        for bits in (4, 8):
            q_ref, _ = quantize_image(img, bits_per_sample=bits)
            pkt = compressor.compress(img, bits_per_sample=bits)
            rec = compressor.decompress(pkt.wire_bytes)

            self.assertEqual(rec.shape, img.shape)
            self.assertGreater(pkt.compression_ratio, 1.0)
            self.assertLess(rmse(q_ref.pixels, rec.pixels), 1e-6)

    def test_lossy_dct_codec_and_crc_tamper_detection(self) -> None:
        img = _make_textured_test_image(93, 117)
        compressor = ImageCompressor(method=METHOD_LOSSY_DCT, quality=75)
        pkt = compressor.compress(img, quality=75)
        rec = compressor.decompress(pkt.wire_bytes)

        self.assertEqual(rec.shape, img.shape)
        self.assertGreater(pkt.compression_ratio, 3.0)
        self.assertGreater(psnr_db(img.pixels, rec.pixels), 28.0)

        # Corromper 1 byte del payload debe disparar error CRC32
        corrupted = bytearray(pkt.wire_bytes)
        corrupted[-3] ^= 0x55
        with self.assertRaises(ValueError):
            compressor.decompress(bytes(corrupted))

        with tempfile.TemporaryDirectory() as tmpdir:
            pkt_path = os.path.join(tmpdir, "sample.dspimg")
            save_compressed_packet(pkt, pkt_path)
            loaded_bytes = load_compressed_packet(pkt_path)
            rec_disk = compressor.decompress(loaded_bytes)
            self.assertLess(rmse(rec.pixels, rec_disk.pixels), 1e-6)

    def test_plots_and_real_selfie_compression(self) -> None:
        selfie_path = os.path.join("data", "input", "selfie_dsp.jpeg")
        if not os.path.exists(selfie_path):
            self.skipTest("No se encontró data/input/selfie_dsp.jpeg")

        work = load_image(selfie_path, max_dim=160)
        splash = isolate_largest_red_region(work).filtered

        comp_ll = ImageCompressor(method=METHOD_LOSSLESS)
        pkt_ll = comp_ll.compress(splash, bits_per_sample=4)
        rec_ll = comp_ll.decompress(pkt_ll.wire_bytes)

        comp_dct = ImageCompressor(method=METHOD_LOSSY_DCT, quality=70)
        pkt_dct = comp_dct.compress(splash, quality=70)
        rec_dct = comp_dct.decompress(pkt_dct.wire_bytes)

        self.assertGreater(pkt_ll.compression_ratio, 1.5)
        self.assertGreater(pkt_dct.compression_ratio, 5.0)
        self.assertGreater(psnr_db(splash.pixels, rec_dct.pixels), 28.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = os.path.join(tmpdir, "nqs.png")
            f2 = os.path.join(tmpdir, "quant.png")
            f3 = os.path.join(tmpdir, "comp.png")
            plot_nqs_sampling_study(splash, save_path=f1)
            plot_quantization_resolution_study(splash, save_path=f2)
            plot_compression_comparison(splash, pkt_ll, rec_ll, pkt_dct, rec_dct, save_path=f3)
            for path in (f1, f2, f3):
                self.assertTrue(os.path.exists(path))
                self.assertGreater(os.path.getsize(path), 1000)


if __name__ == "__main__":
    unittest.main()
