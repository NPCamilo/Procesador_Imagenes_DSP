"""Pruebas unitarias de Fase 1: carga JPEG/EXIF, filtro rojo de mayor área y frecuencia de muestreo."""

import io
import os
import tempfile
import unittest
import numpy as np
from PIL import Image

from dsp_img.core.analyzer import (
    analyze_sampling_frequency,
    plot_sampling_frequency_analysis,
    summarize_sampling_metrics,
)
from dsp_img.core.contracts import ImageSignal
from dsp_img.core.image_io import load_image, plot_original_reproduction, save_image_png
from dsp_img.core.red_filter import isolate_largest_red_region, plot_red_splash_comparison


def _build_synthetic_multi_object_scene() -> np.ndarray:
    """Construye una escena con una camiseta roja grande, dos objetos rojos pequeños y colores varios."""
    canvas = np.full((160, 160, 3), fill_value=60, dtype=np.uint8)
    # Fondo azul y verde (objetos varios)
    canvas[10:40, 10:40] = [30, 120, 210]
    canvas[10:45, 110:150] = [40, 170, 80]
    # Tono piel cálido (no debe confundirse con rojo saturado)
    canvas[30:65, 65:95] = [215, 170, 140]
    # Objeto rojo pequeño #1 (12x12 = 144 px)
    canvas[15:27, 50:62] = [220, 25, 25]
    # Objeto rojo mediano #2 (20x18 = 360 px)
    canvas[60:80, 125:143] = [210, 20, 30]
    # Camiseta roja principal (60x80 = 4800 px)
    canvas[90:150, 40:120] = [215, 20, 25]
    return canvas


class TestFase1IngestaFiltro(unittest.TestCase):
    """Valida los Puntos 1 y 2 de forma determinista y sobre la selfie real."""

    def test_load_image_from_bytes_and_exif_transpose(self) -> None:
        arr = np.zeros((40, 80, 3), dtype=np.uint8)
        arr[:, :, 0] = 200
        pil_img = Image.fromarray(arr, mode="RGB")
        exif = pil_img.getexif()
        exif[274] = 6  # Orientation: Rotate 90 CW -> (80x40) debe quedar (40x80) tras transponer
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", exif=exif.tobytes())

        loaded = load_image(buf.getvalue(), sample_rate_1d_hz=22050)
        self.assertEqual(loaded.width, 40)
        self.assertEqual(loaded.height, 80)
        self.assertEqual(loaded.sample_rate_1d_hz, 22050)

    def test_largest_red_region_filter_keeps_only_dominant_red(self) -> None:
        scene = _build_synthetic_multi_object_scene()
        img = ImageSignal(pixels=scene)
        result = isolate_largest_red_region(img)

        self.assertEqual(result.num_red_components, 3)
        self.assertGreater(result.largest_area_px, 4000)

        out_uint8 = result.filtered.to_uint8()

        # La camiseta grande debe conservar rojo dominante (R >> G, B)
        shirt_px = out_uint8[120, 80]
        self.assertGreater(int(shirt_px[0]) - int(shirt_px[1]), 150)

        # Los otros objetos rojos más pequeños deben quedar en gris exacto (R == G == B)
        small_red_1 = out_uint8[20, 55]
        small_red_2 = out_uint8[70, 132]
        self.assertEqual(int(small_red_1[0]), int(small_red_1[1]))
        self.assertEqual(int(small_red_1[1]), int(small_red_1[2]))
        self.assertEqual(int(small_red_2[0]), int(small_red_2[1]))
        self.assertEqual(int(small_red_2[1]), int(small_red_2[2]))

        # Los objetos azul/verde/piel también deben quedar en escala de grises
        blue_obj = out_uint8[25, 25]
        skin_obj = out_uint8[45, 80]
        self.assertEqual(int(blue_obj[0]), int(blue_obj[1]))
        self.assertEqual(int(skin_obj[0]), int(skin_obj[1]))

    def test_sampling_frequency_analysis_and_plots(self) -> None:
        scene = _build_synthetic_multi_object_scene()
        img = ImageSignal(pixels=scene, sample_rate_1d_hz=16000)
        splash = isolate_largest_red_region(img)
        report = analyze_sampling_frequency(img)
        summary = summarize_sampling_metrics(img, report)

        self.assertEqual(report.spatial_fs_per_px, 1.0)
        self.assertEqual(report.nyquist_spatial_cycles_per_px, 0.5)
        self.assertGreater(report.f_max_spatial_cycles_per_px, 0.0)
        self.assertLessEqual(report.f_max_spatial_cycles_per_px, 0.5)
        self.assertTrue(report.nyquist_diagnosis["spatial_nyquist_satisfied"])
        self.assertEqual(summary["equivalent_1d_sample_rate_hz"], 16000)

        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = os.path.join(tmpdir, "orig.png")
            p2 = os.path.join(tmpdir, "splash.png")
            p3 = os.path.join(tmpdir, "sampling.png")
            p4 = os.path.join(tmpdir, "saved.png")
            plot_original_reproduction(img, save_path=p1)
            plot_red_splash_comparison(splash, save_path=p2)
            plot_sampling_frequency_analysis(img, report, save_path=p3)
            save_image_png(splash.filtered, p4)
            for path in (p1, p2, p3, p4):
                self.assertTrue(os.path.exists(path))
                self.assertGreater(os.path.getsize(path), 100)
            with Image.open(p4) as saved_img:
                self.assertEqual(saved_img.size, (160, 160))

    def test_real_selfie_dsp_photo_pipeline(self) -> None:
        selfie_path = os.path.join("data", "input", "selfie_dsp.jpeg")
        if not os.path.exists(selfie_path):
            self.skipTest("No se encontró data/input/selfie_dsp.jpeg")

        img = load_image(selfie_path)
        self.assertEqual((img.width, img.height), (1200, 1599))

        splash = isolate_largest_red_region(img)
        # En la selfie real hay varias componentes rojas (camiseta + adornos + lomos)
        self.assertGreaterEqual(splash.num_red_components, 2)
        # La camiseta debe ocupar al menos 10% de la fotografía
        self.assertGreater(splash.largest_area_ratio, 0.10)

        out_uint8 = splash.filtered.to_uint8()
        # Región superior izquierda (Papá Noel rojo descartado) debe quedar en gris
        santa_region = out_uint8[150:220, 80:160]
        self.assertTrue(np.all(santa_region[:, :, 0] == santa_region[:, :, 1]))


if __name__ == "__main__":
    unittest.main()
