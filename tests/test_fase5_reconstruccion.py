"""Pruebas unitarias y E2E de Fase 5: reconstrucción DAC, PNG, SVG vectorial, métricas e intercambio TX/RX."""

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np

from dsp_img.core.contracts import ImageSignal
from dsp_img.core.image_io import load_image
from dsp_img.exchange import (
    package_for_peer_bytes,
    package_for_peer_files,
    receive_from_peer_bytes,
    receive_from_peer_file,
)
from dsp_img.reconstruction import (
    SignalReconstructor,
    compute_ssim,
    evaluate_audio_fidelity,
    image_to_svg_string,
    plot_full_reconstruction_comparison,
    save_image_svg,
)


def _make_sample_image(h: int = 48, w: int = 64) -> ImageSignal:
    arr = np.full((h, w, 3), fill_value=140, dtype=np.uint8)
    arr[10:40, 15:50] = [210, 25, 30]
    arr[5:12, 5:20] = [90, 90, 90]
    return ImageSignal(pixels=arr, sample_rate_1d_hz=16000)


class TestFase5Reconstruccion(unittest.TestCase):
    """Valida DAC audio, SVG vectorial genuino, métricas e intercambio entre pares."""

    def test_vector_svg_generation_is_genuine_and_scalable(self) -> None:
        img = _make_sample_image(32, 48)
        svg = image_to_svg_string(img, color_levels=8, pixel_scale=4)

        root = ET.fromstring(svg)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertNotIn("<image", svg)
        self.assertNotIn("base64", svg)
        rects = [el for el in root if el.tag.endswith("rect")]
        self.assertGreater(len(rects), 5)

        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = save_image_svg(img, os.path.join(tmpdir, "out.svg"))
            self.assertTrue(os.path.exists(svg_path))
            self.assertGreater(os.path.getsize(svg_path), 150)

    def test_dac_audio_reconstruction_and_ssim_metrics(self) -> None:
        img = _make_sample_image(48, 64)
        rec = SignalReconstructor(dac_method="sinc")
        audio_sinc = rec.image_to_audible_scanline(img, sample_rate_hz=16000, duration_s=0.4)
        rec_zoh = SignalReconstructor(dac_method="zoh_filtered")
        audio_zoh = rec_zoh.image_to_audible_scanline(img, sample_rate_hz=16000, duration_s=0.4)

        self.assertEqual(len(audio_sinc), len(audio_zoh))
        self.assertLessEqual(float(np.max(np.abs(audio_sinc))), 1.0)
        self.assertAlmostEqual(compute_ssim(img.pixels, img.pixels), 1.0, places=5)

        aud_metrics = evaluate_audio_fidelity(audio_sinc, audio_zoh)
        self.assertGreater(aud_metrics["pearson_corr"], 0.90)

    def test_peer_exchange_tx_to_rx_wav_zip_and_dspimg(self) -> None:
        selfie_path = os.path.join("data", "input", "selfie_dsp.jpeg")
        if not os.path.exists(selfie_path):
            self.skipTest("No se encontró data/input/selfie_dsp.jpeg")

        with open(selfie_path, "rb") as handle:
            raw_jpeg = handle.read()

        # TX en memoria (como en Vercel)
        tx = package_for_peer_bytes(
            raw_jpeg, scheme="MFSK", quality=65, max_dim=72, apply_red_filter=True
        )
        self.assertGreater(tx["packet"].compression_ratio, 3.0)

        # RX desde ZIP completo
        rx_zip = receive_from_peer_bytes(tx["zip_bytes"], filename="paquete.zip")
        self.assertTrue(rx_zip["summary"]["crc_valid"])
        self.assertIn("<svg", rx_zip["svg_text"])
        self.assertGreater(len(rx_zip["png_bytes"]), 500)

        # RX ciego únicamente desde el archivo WAV modulado (sin manifest)
        rx_wav = receive_from_peer_bytes(tx["wav_bytes"], filename="audio.wav", scheme="MFSK")
        self.assertTrue(rx_wav["summary"]["crc_valid"])

        # Verificar métricas de reconstrucción y figura comparativa
        reconstructor = SignalReconstructor(dac_method="sinc")
        src_img = tx["source_image"]
        rec_img = rx_wav["reconstructed_image"]
        img_m = reconstructor.evaluate(
            src_img, rec_img, compression_ratio=tx["packet"].compression_ratio
        )
        self.assertGreater(img_m.psnr_db, 28.0)
        self.assertGreater(img_m.ssim, 0.85)

        orig_aud = reconstructor.image_to_audible_scanline(src_img, sample_rate_hz=16000, duration_s=1.0)
        rec_aud = reconstructor.image_to_audible_scanline(rec_img, sample_rate_hz=16000, duration_s=1.0)
        aud_m = evaluate_audio_fidelity(orig_aud, rec_aud)
        self.assertGreater(aud_m["pearson_corr"], 0.90)

        with tempfile.TemporaryDirectory() as tmpdir:
            fig_path = os.path.join(tmpdir, "compare.png")
            plot_full_reconstruction_comparison(
                src_img, rec_img, orig_aud, rec_aud, 16000, img_m, aud_m, save_path=fig_path
            )
            self.assertTrue(os.path.exists(fig_path))
            self.assertGreater(os.path.getsize(fig_path), 1000)

            tx_files = package_for_peer_files(selfie_path, os.path.join(tmpdir, "tx"), scheme="BFSK", max_dim=64)
            rx_files = receive_from_peer_file(tx_files["paths"]["zip"], os.path.join(tmpdir, "rx"))
            for p in rx_files["paths"].values():
                self.assertTrue(os.path.exists(p))

            from pipeline_cli import run_full_pipeline

            cli_rep = run_full_pipeline(
                image_path=selfie_path,
                output_dir=os.path.join(tmpdir, "cli_full"),
                scheme="16-QAM",
                max_dim=64,
                quality=82,
            )
            self.assertTrue(cli_rep["crc_valid"])
            self.assertGreater(cli_rep["image_metrics"]["ssim"], 0.90)


if __name__ == "__main__":
    unittest.main()
