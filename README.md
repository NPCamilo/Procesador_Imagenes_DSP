# Procesador, Compresor y Transceptor DSP de Señales de Imagen

**Asignatura:** Comunicaciones I — Universidad Tecnológica de Pereira (UTP)

Sistema modular en Python diseñado para validar paso a paso la cadena completa de procesamiento, compresión, modulación audible, demodulación, reconstrucción en PNG/SVG e intercambio entre compañeros sobre señales de imagen JPG/JPEG, preparando posteriormente su despliegue serverless en **Vercel**.

---

## Arquitectura por Fases y Validación en GitHub

| Fase | Módulo | Requisito del Proyecto | Estado |
| :--- | :--- | :--- | :---: |
| **Fase 0** | `dsp_img/core/` + CI | Contratos, primitivas DSP, tema Okabe-Ito, WAV I/O, GitHub Actions | **Completada** |
| **Fase 1** | `image_io`, `red_filter`, `analyzer` | Carga JPG/JPEG, reproducción, filtro de color rojo de mayor área, $f_s$ | **Completada** |
| **Fase 2** | `sampling_nqs`, `quantization`, `codec` | Muestreo NQS, resolución `[Byte / Bit]`, compresión/descompresión `.dspimg` | **Completada** |
| **Fase 3** | `dsp_img/modulation/` | Modulación (`AM, FM, ASK, FSK, PSK, QAM, MFSK`) y audio audible de bits | **Completada** |
| **Fase 4** | `dsp_img/demodulation/` | Sincronización, demodulación, cálculo de BER y reproducción demodulada | *Siguiente* |
| **Fase 5** | `dsp_img/reconstruction/` | Reconstrucción de audio, exportación PNG/SVG vectorial, métricas e intercambio TX/RX | *Pendiente* |
| **Fase 6** | App Web Serverless | Endpoints/vistas funcionando en Vercel Preview | *Pendiente* |
| **Fase 7** | UI/UX Final | Diseño de producto final y publicación en producción | *Pendiente* |

---

## Ejecución de Pruebas Locales

```bash
python -m unittest discover -s tests -v
```
