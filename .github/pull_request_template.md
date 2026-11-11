## Resumen del Módulo / Fase
<!-- Describe qué fase del proyecto estás integrando y qué requisitos de Comunicaciones I cubre. -->

### Fase Asociada
- [ ] Fase 0: Fundación, Contratos y CI
- [ ] Fase 1: Ingesta JPG/JPEG, Filtro Rojo Mayor Área y Análisis de Muestreo
- [ ] Fase 2: Muestreo NQS, Digitalización [Byte/Bit] y Compresión/Descompresión
- [ ] Fase 3: Modulación y Síntesis Audible en Bits
- [ ] Fase 4: Demodulación, Sincronización y Recuperación
- [ ] Fase 5: Reconstrucción (Audio, PNG, SVG) e Intercambio con Compañero
- [ ] Fase 6: Aplicación Web Serverless en Vercel
- [ ] Fase 7: Diseño UI/UX y Publicación Final

### Lista de Validación Técnica
- [ ] Pruebas unitarias pasando localmente (`python -m unittest discover -s tests -v`).
- [ ] Workflow de GitHub Actions CI en verde.
- [ ] Los módulos respetan los contratos definidos en `dsp_img/core/contracts.py`.
- [ ] Sin rutas absolutas hardcodeadas ni archivos temporales sin ignorar.
- [ ] Gráficas exportadas con ejes rotulados, unidades y paleta accesible.
