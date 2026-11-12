"""Pruebas de integración de la API FastAPI Serverless (Fase 6)."""

import asyncio
import base64
import io
import json
import os
import unittest
from fastapi import UploadFile

from api.index import (
    demodulate_peer_upload,
    get_precomputed_demo,
    health,
    run_tx_pipeline,
)


class TestFase6API(unittest.TestCase):
    """Valida todos los handlers de `/api/*` antes y después de desplegar en Vercel."""

    def test_health_and_demo_endpoints(self) -> None:
        body = health()
        self.assertEqual(body["status"], "ok")
        self.assertIn("BFSK", body["supported_schemes"])

        if os.path.exists(os.path.join("public", "demo", "datos_demo.json")):
            demo = get_precomputed_demo()
            self.assertEqual(demo["fase3_4_5"]["ber_bfsk"], 0.0)
            self.assertTrue(demo["fase3_4_5"]["crc_valid"])

    def test_live_tx_pipeline_and_rx_peer_demodulate(self) -> None:
        # 1. Ejecutar TX en vivo usando selfie por defecto y 16-QAM
        payload = asyncio.run(
            run_tx_pipeline(
                file=None,
                scheme="16-QAM",
                compression_method="lossy_dct_zlib",
                bits_per_sample=4,
                quality=80,
                tx_max_dim=64,
                apply_red_filter=True,
                nqs_factor=8,
                snr_db=None,
            )
        )
        # Verificar tamaño JSON serializado por debajo del límite de Vercel (4.5 MB)
        serialized = json.dumps(payload).encode("utf-8")
        self.assertLess(len(serialized), 4_200_000)

        self.assertEqual(payload["fase3_4"]["ber"], 0.0)
        self.assertTrue(payload["fase3_4"]["crc_valid"])
        self.assertIn("<svg", payload["fase5"]["reconstructed_svg"])
        self.assertGreater(payload["fase5"]["metrics"]["ssim"], 0.88)

        # 2. Enviar el .zip generado al endpoint Receptor (Modo Compañero)
        zip_bytes = base64.b64decode(payload["fase5"]["peer_zip_b64"])
        zip_upload = UploadFile(filename="paquete_companero.zip", file=io.BytesIO(zip_bytes))
        rx_data = asyncio.run(demodulate_peer_upload(file=zip_upload, scheme="16-QAM"))
        self.assertTrue(rx_data["summary"]["crc_valid"])
        self.assertTrue(rx_data["reconstructed_png"].startswith("data:image/png;base64,"))
        self.assertIn("<svg", rx_data["reconstructed_svg"])
        self.assertTrue(rx_data["reconstructed_audio_wav_url"].startswith("data:audio/wav;base64,"))

        # 3. Probar recepción directa con solo el paquete .dspimg
        dspimg_bytes = base64.b64decode(payload["fase5"]["dspimg_b64"])
        pkt_upload = UploadFile(filename="paquete.dspimg", file=io.BytesIO(dspimg_bytes))
        rx_pkt = asyncio.run(demodulate_peer_upload(file=pkt_upload, scheme="BFSK"))
        self.assertTrue(rx_pkt["summary"]["crc_valid"])


if __name__ == "__main__":
    unittest.main()
