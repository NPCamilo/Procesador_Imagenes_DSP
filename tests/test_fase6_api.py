"""Pruebas de integración de la API FastAPI Serverless (Fase 6)."""

import io
import json
import os
import unittest
from fastapi.testclient import TestClient

from api.index import app


class TestFase6API(unittest.TestCase):
    """Valida todos los endpoints de `/api/*` antes de desplegar en Vercel."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health_and_demo_endpoints(self) -> None:
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("BFSK", body["supported_schemes"])

        if os.path.exists(os.path.join("public", "demo", "datos_demo.json")):
            demo_res = self.client.get("/api/demo")
            self.assertEqual(demo_res.status_code, 200)
            demo = demo_res.json()
            self.assertEqual(demo["fase3_4_5"]["ber_bfsk"], 0.0)
            self.assertTrue(demo["fase3_4_5"]["crc_valid"])

    def test_live_tx_pipeline_and_rx_peer_demodulate(self) -> None:
        # 1. Ejecutar TX en vivo usando selfie por defecto y 16-QAM (respuesta rápida y <4.5 MB)
        tx_res = self.client.post(
            "/api/tx/pipeline",
            data={
                "scheme": "16-QAM",
                "compression_method": "lossy_dct_zlib",
                "bits_per_sample": "4",
                "quality": "80",
                "tx_max_dim": "64",
                "apply_red_filter": "true",
                "nqs_factor": "8",
            },
        )
        self.assertEqual(tx_res.status_code, 200, msg=tx_res.text)
        # Verificar que el JSON completo no excede el límite de payload de Vercel (4.5 MB)
        self.assertLess(len(tx_res.content), 4_200_000)

        payload = tx_res.json()
        self.assertEqual(payload["fase3_4"]["ber"], 0.0)
        self.assertTrue(payload["fase3_4"]["crc_valid"])
        self.assertIn("<svg", payload["fase5"]["reconstructed_svg"])
        self.assertGreater(payload["fase5"]["metrics"]["ssim"], 0.88)

        # 2. Tomar el .zip generado y enviarlo al endpoint Receptor (Modo Compañero)
        import base64

        zip_bytes = base64.b64decode(payload["fase5"]["peer_zip_b64"])
        rx_res = self.client.post(
            "/api/rx/demodulate",
            files={"file": ("paquete_companero.zip", io.BytesIO(zip_bytes), "application/zip")},
            data={"scheme": "16-QAM"},
        )
        self.assertEqual(rx_res.status_code, 200, msg=rx_res.text)
        rx_data = rx_res.json()
        self.assertTrue(rx_data["summary"]["crc_valid"])
        self.assertTrue(rx_data["reconstructed_png"].startswith("data:image/png;base64,"))
        self.assertIn("<svg", rx_data["reconstructed_svg"])
        self.assertTrue(rx_data["reconstructed_audio_wav_url"].startswith("data:audio/wav;base64,"))

        # 3. Probar recepción directa con solo el paquete .dspimg
        dspimg_bytes = base64.b64decode(payload["fase5"]["dspimg_b64"])
        rx_pkt_res = self.client.post(
            "/api/rx/demodulate",
            files={"file": ("paquete.dspimg", io.BytesIO(dspimg_bytes), "application/octet-stream")},
            data={"scheme": "BFSK"},
        )
        self.assertEqual(rx_pkt_res.status_code, 200, msg=rx_pkt_res.text)
        self.assertTrue(rx_pkt_res.json()["summary"]["crc_valid"])


if __name__ == "__main__":
    unittest.main()
