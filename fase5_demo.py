"""
Script demostrativo de Fase 5 (Punto 6 completo):
  - Reconstruye señal de audio (DAC Sinc), PNG y SVG vectorial real desde los datos demodulados
  - Compara visual y auditivamente señal original vs reconstruida
  - Genera el paquete comprimido y modulado (`paquete_envio_companero.zip`) y valida recepción
"""

from __future__ import annotations

import argparse
from pipeline_cli import run_full_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo Fase 5: Reconstrucción PNG/SVG/Audio y Paquete TX/RX")
    parser.add_argument("--image", default="data/input/selfie_dsp.jpeg")
    parser.add_argument("--out", default="data/output/fase5")
    parser.add_argument("--scheme", default="BFSK")
    parser.add_argument("--max-dim", type=int, default=96)
    parser.add_argument("--quality", type=int, default=82)
    parser.add_argument("--play", action="store_true", help="Reproducir audio original vs reconstruido")
    args = parser.parse_args()
    run_full_pipeline(
        image_path=args.image,
        output_dir=args.out,
        scheme=args.scheme,
        max_dim=args.max_dim,
        quality=args.quality,
        play=args.play,
    )


if __name__ == "__main__":
    main()
