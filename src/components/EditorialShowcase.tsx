"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUpRight,
  Cpu,
  Download,
  FileCode2,
  Image as ImageIcon,
  Maximize2,
  SlidersHorizontal,
} from "lucide-react";
import type { DemoData } from "@/types/dsp";
import { AudibleSignalConsole, type AudioTrackItem } from "./AudibleSignalConsole";
import { BeforeAfterComparator } from "./BeforeAfterComparator";
import { ImageLightboxDialog, type LightboxAsset } from "./ImageLightboxDialog";
import { OptimizedPicture, toWebpSrc } from "./OptimizedPicture";
import type { TelemetryFocus } from "./TelemetryDrawer";

interface EditorialShowcaseProps {
  data: DemoData;
  onJumpWorkbench: (mode: "tx" | "rx") => void;
  onOpenTelemetry: (focus: TelemetryFocus) => void;
}

function AtkinsonDitherCanvas({ src }: { src: string }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let cancelled = false;

    const runDither = () => {
      if (cancelled) return;
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.decoding = "async";
      img.src = toWebpSrc(src) || src;
      img.onload = () => {
        if (cancelled) return;
        const targetW = 200;
        const ratio = img.height / img.width || 1;
        const targetH = Math.max(64, Math.round(targetW * ratio));
        canvas.width = targetW;
        canvas.height = targetH;

        ctx.drawImage(img, 0, 0, targetW, targetH);
        const imgData = ctx.getImageData(0, 0, targetW, targetH);
        const data = imgData.data;

        const lum = new Float32Array(targetW * targetH);
        for (let i = 0; i < targetW * targetH; i++) {
          const idx = i * 4;
          lum[i] = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];
        }

        for (let y = 0; y < targetH; y++) {
          for (let x = 0; x < targetW; x++) {
            const i = y * targetW + x;
            const oldVal = lum[i];
            const newVal = oldVal < 128 ? 0 : 255;
            const err = (oldVal - newVal) / 8;

            const push = (nx: number, ny: number) => {
              if (nx >= 0 && nx < targetW && ny >= 0 && ny < targetH) {
                lum[ny * targetW + nx] += err;
              }
            };

            push(x + 1, y);
            push(x + 2, y);
            push(x - 1, y + 1);
            push(x, y + 1);
            push(x + 1, y + 1);
            push(x, y + 2);

            const p = i * 4;
            const bit = newVal === 255;
            data[p] = bit ? 228 : 14;
            data[p + 1] = bit ? 242 : 16;
            data[p + 2] = bit ? 254 : 20;
            data[p + 3] = 255;
          }
        }

        ctx.putImageData(imgData, 0, 0);
      };
    };

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          runDither();
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(canvas);

    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [src]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="Previsualización 1-bit con algoritmo de dithering Atkinson"
      className="mx-auto max-h-80 w-auto rounded-lg border border-(--hairline) [image-rendering:pixelated]"
    />
  );
}

export function EditorialShowcase({
  data,
  onJumpWorkbench,
  onOpenTelemetry,
}: EditorialShowcaseProps) {
  const { fase1, fase2, fase3_4_5, assets } = data;

  const [spectralIdx, setSpectralIdx] = useState(0);
  const [digitalIdx, setDigitalIdx] = useState(0);
  const [rfIdx, setRfIdx] = useState(0);
  const [outputTab, setOutputTab] = useState<"png" | "svg" | "dither" | "compare">("png");
  const [svgScale, setSvgScale] = useState(1);
  const [inspectAsset, setInspectAsset] = useState<LightboxAsset | null>(null);

  const openLightbox = (src: string, title: string, caption?: string) => {
    setInspectAsset({ src, title, caption });
  };

  const spectralSteps = [
    {
      code: "01.A",
      title: "Descomposición Espacial RGB",
      summary:
        "Lectura directa desde JPEG móvil con corrección EXIF, aislamiento de canales R/G/B e histograma de luminancia.",
      src: assets.fig_original,
    },
    {
      code: "01.B",
      title: "Filtro Rojo de Mayor Área Conexa",
      summary: `Segmentación HSV y etiquetado topológico: conserva únicamente la camiseta roja (${fase1.red_filter.largest_area_percent}%), llevando los otros ${fase1.red_filter.num_components - 1} objetos rojos a escala de grises.`,
      src: assets.fig_red_filter,
    },
    {
      code: "01.C",
      title: "Frecuencia de Muestreo 2D / 1D",
      summary: `Identificación del límite Nyquist espacial (${fase1.sampling.spatial_nyquist_limit_cycles_per_px} cyc/px) y mapeo temporal a ${fase1.sampling.equivalent_1d_sample_rate_hz.toLocaleString()} Hz.`,
      src: assets.fig_sampling,
    },
  ];

  const digitalSteps = [
    {
      label: "Muestreo NQS",
      title: "Teorema de Nyquist-Shannon y Submuestreo",
      summary:
        "Evaluación controlada de aliasing espacial al reducir la frecuencia de muestreo frente al filtro pasabajas antialiasing.",
      src: assets.fig_nqs,
    },
    {
      label: "Resolución [Byte/Bit]",
      title: "Cuantización Uniforme y Curva SQNR",
      summary: `Conversión analógico-digital desde 1 hasta 8 bits/muestra con verificación de SQNR empírica (${fase2.stream_4bits.sqnr_empirical_db} dB a 4 bits).`,
      src: assets.fig_quantization,
    },
    {
      label: "DPCM vs DCT 8×8",
      title: "Compresión Sin Pérdida vs Transformada Coseno",
      summary: `El códec híbrido DCT 8×8 + Zlib alcanza ${fase2.compression_dct.ratio}× (${fase2.compression_dct.savings_percent}% de ahorro) preservando PSNR de ${fase2.compression_dct.psnr_db} dB.`,
      src: assets.fig_compression,
    },
  ];

  const rfFigures = [
    {
      label: "Modulación BFSK",
      title: "Portadora Audible BFSK & Espectro Pasabanda",
      src: assets.fig_mod_bfsk,
    },
    {
      label: "Demodulación Coherente",
      title: "Sincronización por Correlación y Recuperación",
      src: assets.fig_demod_bfsk,
    },
    {
      label: "Constelación 16-QAM",
      title: `Diagrama I/Q 16-QAM (BER = ${fase3_4_5.qam_ber})`,
      src: assets.fig_demod_qam,
    },
  ];

  const audioTracks: AudioTrackItem[] = [
    {
      id: "bfsk_tx",
      code: "01 / TX",
      title: "Bits Modulados (BFSK)",
      subtitle: `${fase3_4_5.tx_manifest.audio_duration_s} s · Tonos portadores de la trama comprimida`,
      src: assets.wav_modulated_bfsk,
      accentClass: "text-sky-500",
    },
    {
      id: "bfsk_rx",
      code: "02 / RX",
      title: "Señal Demodulada",
      subtitle: `Recuperación coherente con BER = ${fase3_4_5.ber_bfsk}`,
      src: assets.wav_demodulated_bfsk,
      accentClass: "text-emerald-500",
    },
    {
      id: "am",
      code: "03 / AM",
      title: "Portadora Analógica AM",
      subtitle: "Modulación por envolvente de amplitud sobre scanline 1D",
      src: assets.wav_modulated_am,
      accentClass: "text-amber-500",
    },
    {
      id: "fm",
      code: "04 / FM",
      title: "Portadora Analógica FM",
      subtitle: "Desviación instantánea de frecuencia en banda audible",
      src: assets.wav_modulated_fm,
      accentClass: "text-rose-500",
    },
    {
      id: "orig_audio",
      code: "05 / REF",
      title: "Scanline 1D Original",
      subtitle: "Señal luminancia unidimensional previa al canal",
      src: assets.wav_audio_original,
      accentClass: "text-sky-500",
    },
    {
      id: "dac_audio",
      code: "06 / DAC",
      title: "Audio DAC Reconstruido",
      subtitle: `Interpolación Sinc final · SNR = ${fase3_4_5.audio_metrics.snr_db} dB`,
      src: assets.wav_audio_reconstructed,
      accentClass: "text-emerald-500",
    },
  ];

  const activeSpectral = spectralSteps[spectralIdx];
  const activeDigital = digitalSteps[digitalIdx];
  const activeRf = rfFigures[rfIdx];

  return (
    <div className="min-w-0">
      {/* 00 · EDITORIAL HERO (No enclosing box, typographic hairline strip + 3D comparator) */}
      <section
        id="captura"
        className="animate-reveal scroll-mt-24 grid min-w-0 items-center gap-10 pb-16 pt-4 lg:grid-cols-12 lg:gap-12 lg:pb-24"
      >
        <div className="min-w-0 space-y-7 lg:col-span-6">
          <p className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Comunicación Digital de Imágenes · UTP
          </p>

          <h2 className="font-display text-4xl font-bold tracking-tight text-(--ink) sm:text-5xl lg:text-[3.15rem] lg:leading-[1.06]">
            Señal visual comprimida, modulada en audio y reconstruida.
          </h2>

          <p className="max-w-xl text-sm leading-relaxed text-(--ink-muted) sm:text-base">
            Pipeline completo sobre{" "}
            <span className="font-mono text-(--ink)">{data.project.source_image}</span>:
            aislamiento topológico de color rojo dominante, cuantización{" "}
            <span className="font-mono text-(--ink)">[Byte / Bit]</span>, compresión DCT 8×8,
            modulación pasabanda audible y recuperación vectorial SVG/PNG.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => onJumpWorkbench("tx")}
              className="inline-flex items-center gap-2 rounded-full bg-(--ink) px-5 py-2.5 text-xs font-semibold text-(--canvas) transition hover:opacity-90 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
            >
              <Cpu className="h-3.5 w-3.5" /> Abrir Laboratorio TX
            </button>
            <a
              href="#espectro"
              className="inline-flex items-center gap-1.5 rounded-full border border-(--hairline) px-4 py-2.5 text-xs font-medium text-(--ink) transition hover:border-sky-500/50 active:scale-[0.98]"
            >
              Recorrer exhibición <ArrowDown className="h-3.5 w-3.5" />
            </a>
            <button
              type="button"
              onClick={() => onOpenTelemetry("all")}
              className="inline-flex items-center gap-1.5 px-2 py-2 font-mono text-[11px] text-(--ink-muted) underline decoration-(--hairline) underline-offset-4 transition hover:text-(--ink)"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" /> Ficha técnica completa
            </button>
          </div>

          {/* Minimalist Typographic Metric Hairlines (Zero Box Clutter) */}
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 border-t border-(--hairline) pt-6 sm:grid-cols-4">
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-widest text-(--ink-muted)">
                Captura
              </dt>
              <dd className="mt-1 font-display text-lg font-semibold text-(--ink)">
                {fase1.sampling.width_px}×{fase1.sampling.height_px}
              </dd>
            </div>
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-widest text-(--ink-muted)">
                Ratio DCT
              </dt>
              <dd className="mt-1 font-display text-lg font-semibold text-sky-600 dark:text-sky-400">
                {fase2.compression_dct.ratio}×
              </dd>
            </div>
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-widest text-(--ink-muted)">
                Error Canal
              </dt>
              <dd className="mt-1 font-display text-lg font-semibold text-emerald-600 dark:text-emerald-400">
                {fase3_4_5.ber_bfsk} BER
              </dd>
            </div>
            <div>
              <dt className="font-mono text-[10px] uppercase tracking-widest text-(--ink-muted)">
                Fidelidad
              </dt>
              <dd className="mt-1 font-display text-lg font-semibold text-(--ink)">
                {fase3_4_5.image_metrics.psnr_db} dB
              </dd>
            </div>
          </dl>
        </div>

        <div className="min-w-0 lg:col-span-6">
          <BeforeAfterComparator
            beforeSrc={assets.original_png}
            afterSrc={assets.red_splash_png}
            resolutionText={`${fase1.sampling.width_px}×${fase1.sampling.height_px}`}
            redPercent={fase1.red_filter.largest_area_percent}
            componentsCount={fase1.red_filter.num_components}
            onInspectImage={openLightbox}
          />
        </div>
      </section>

      {/* 01 · SPECTRAL & RED SEGMENTATION (Asymmetric Scrollytelling Step Selector + Single Stage) */}
      <section
        id="espectro"
        className="station-deferred scroll-mt-24 border-t border-(--hairline) py-16 lg:py-24"
      >
        <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
              01 · Adquisición, Rojo Dominante & Muestreo
            </p>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-(--ink) sm:text-3xl">
              Aislamiento de la camiseta roja y análisis Nyquist.
            </h2>
          </div>
          <button
            type="button"
            onClick={() => onOpenTelemetry("spectral")}
            className="inline-flex items-center gap-1 font-mono text-xs text-(--ink-muted) transition hover:text-(--ink)"
          >
            Ver datos espectrales <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="grid items-start gap-8 lg:grid-cols-12 lg:gap-10">
          <div className="min-w-0 space-y-2 lg:col-span-4">
            {spectralSteps.map((step, idx) => {
              const active = spectralIdx === idx;
              return (
                <button
                  key={step.code}
                  type="button"
                  onClick={() => setSpectralIdx(idx)}
                  className={`w-full border-l-2 py-3.5 pl-4 pr-2 text-left transition-all ${
                    active
                      ? "border-sky-500 text-(--ink)"
                      : "border-transparent text-(--ink-muted) hover:border-(--hairline) hover:text-(--ink)"
                  }`}
                >
                  <span className="font-mono text-[10px] uppercase tracking-widest text-sky-600 dark:text-sky-400">
                    {step.code}
                  </span>
                  <h3 className="mt-1 font-display text-base font-semibold text-(--ink)">
                    {step.title}
                  </h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-(--ink-muted)">
                    {step.summary}
                  </p>
                </button>
              );
            })}
          </div>

          <div className="min-w-0 lg:col-span-8">
            <button
              type="button"
              onClick={() =>
                openLightbox(activeSpectral.src, activeSpectral.title, activeSpectral.summary)
              }
              className="group relative block w-full overflow-hidden rounded-2xl border border-(--hairline) bg-zinc-950 p-2 text-left transition hover:border-sky-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
            >
              <div className="relative aspect-[16/10] w-full overflow-hidden rounded-xl bg-zinc-950">
                <OptimizedPicture
                  key={activeSpectral.src}
                  src={activeSpectral.src}
                  alt={activeSpectral.title}
                  className="h-full w-full object-contain"
                />
              </div>
              <span className="absolute right-4 top-4 inline-flex items-center gap-1 rounded-full border border-white/15 bg-zinc-950/85 px-3 py-1 font-mono text-[10px] text-zinc-200 transition group-hover:border-sky-400/60">
                <Maximize2 className="h-3 w-3" /> Inspeccionar
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* 02 · NQS, [BYTE / BIT] & COMPRESSION (Top Segmented Control + Inverted Split) */}
      <section
        id="digital"
        className="station-deferred scroll-mt-24 border-t border-(--hairline) py-16 lg:py-24"
      >
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-amber-600 dark:text-amber-400">
              02 · Digitalización & Compresión
            </p>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-(--ink) sm:text-3xl">
              Muestreo NQS, resolución [Byte / Bit] y códec híbrido.
            </h2>
          </div>

          <div
            className="inline-flex flex-wrap gap-1 rounded-full border border-(--hairline) bg-(--surface) p-1"
            role="tablist"
            aria-label="Estudios de digitalización"
          >
            {digitalSteps.map((st, idx) => (
              <button
                key={st.label}
                type="button"
                role="tab"
                aria-selected={digitalIdx === idx}
                onClick={() => setDigitalIdx(idx)}
                className={`rounded-full px-3.5 py-1.5 font-mono text-[11px] transition ${
                  digitalIdx === idx
                    ? "bg-(--ink) font-semibold text-(--canvas)"
                    : "text-(--ink-muted) hover:text-(--ink)"
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid items-center gap-8 lg:grid-cols-12 lg:gap-10">
          <div className="min-w-0 lg:col-span-7">
            <button
              type="button"
              onClick={() =>
                openLightbox(activeDigital.src, activeDigital.title, activeDigital.summary)
              }
              className="group relative block w-full overflow-hidden rounded-2xl border border-(--hairline) bg-zinc-950 p-2 text-left transition hover:border-amber-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
            >
              <div className="relative aspect-[16/10] w-full overflow-hidden rounded-xl bg-zinc-950">
                <OptimizedPicture
                  key={activeDigital.src}
                  src={activeDigital.src}
                  alt={activeDigital.title}
                  className="h-full w-full object-contain"
                />
              </div>
              <span className="absolute right-4 top-4 inline-flex items-center gap-1 rounded-full border border-white/15 bg-zinc-950/85 px-3 py-1 font-mono text-[10px] text-zinc-200">
                <Maximize2 className="h-3 w-3" /> Zoom
              </span>
            </button>
          </div>

          <div className="min-w-0 space-y-6 lg:col-span-5">
            <div>
              <h3 className="font-display text-xl font-bold text-(--ink)">
                {activeDigital.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-(--ink-muted)">
                {activeDigital.summary}
              </p>
            </div>

            <dl className="divide-y divide-(--hairline) border-y border-(--hairline) text-xs">
              <div className="flex items-center justify-between py-3">
                <dt className="text-(--ink-muted)">Trama 4 bits / muestra</dt>
                <dd className="font-mono font-semibold text-(--ink)">
                  {fase2.stream_4bits.total_bytes.toLocaleString()} Bytes · SQNR{" "}
                  {fase2.stream_4bits.sqnr_empirical_db} dB
                </dd>
              </div>
              <div className="flex items-center justify-between py-3">
                <dt className="text-(--ink-muted)">DPCM + Zlib (Lossless)</dt>
                <dd className="font-mono font-semibold text-(--ink)">
                  {fase2.compression_lossless.ratio}× ({fase2.compression_lossless.savings_percent}%)
                </dd>
              </div>
              <div className="flex items-center justify-between py-3">
                <dt className="text-(--ink-muted)">DCT 8×8 + Zlib</dt>
                <dd className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                  {fase2.compression_dct.ratio}× ({fase2.compression_dct.savings_percent}%)
                </dd>
              </div>
            </dl>

            <button
              type="button"
              onClick={() => onOpenTelemetry("digital")}
              className="inline-flex items-center gap-1.5 font-mono text-xs text-amber-600 transition hover:underline dark:text-amber-400"
            >
              Inspeccionar bits (BIN) y HEX en ficha técnica <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </section>

      {/* 03 · AUDIBLE MODULATION CONSOLE (Unified OP-1 / ElevenLabs Style Deck + RF Stage) */}
      <section
        id="modulacion"
        className="station-deferred scroll-mt-24 border-t border-(--hairline) py-16 lg:py-24"
      >
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-emerald-600 dark:text-emerald-400">
              03 · Transceptor Audible & Constelación
            </p>
            <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-(--ink) sm:text-3xl">
              Escucha de bits modulados, canal pasabanda y sincronización.
            </h2>
          </div>
          <button
            type="button"
            onClick={() => onOpenTelemetry("rf")}
            className="inline-flex items-center gap-1 font-mono text-xs text-(--ink-muted) transition hover:text-(--ink)"
          >
            Ver métricas RF y CRC32 <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="space-y-8">
          <AudibleSignalConsole tracks={audioTracks} />

          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-1.5">
                {rfFigures.map((fig, idx) => (
                  <button
                    key={fig.label}
                    type="button"
                    onClick={() => setRfIdx(idx)}
                    className={`rounded-full border px-3.5 py-1.5 font-mono text-[11px] transition ${
                      rfIdx === idx
                        ? "border-emerald-500/50 bg-emerald-500/15 font-semibold text-emerald-700 dark:text-emerald-300"
                        : "border-(--hairline) text-(--ink-muted) hover:text-(--ink)"
                    }`}
                  >
                    {fig.label}
                  </button>
                ))}
              </div>
              <span className="font-mono text-[11px] text-(--ink-muted)">
                Sync: {fase3_4_5.sync_offset_samples} muestras · CRC32{" "}
                {fase3_4_5.tx_manifest.crc32_hex}
              </span>
            </div>

            <button
              type="button"
              onClick={() => openLightbox(activeRf.src, activeRf.title)}
              className="group relative block w-full overflow-hidden rounded-2xl border border-(--hairline) bg-zinc-950 p-2 text-left transition hover:border-emerald-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
            >
              <div className="relative aspect-[16/9] max-h-[460px] w-full overflow-hidden rounded-xl bg-zinc-950">
                <OptimizedPicture
                  key={activeRf.src}
                  src={activeRf.src}
                  alt={activeRf.title}
                  className="h-full w-full object-contain"
                />
              </div>
              <span className="absolute right-4 top-4 inline-flex items-center gap-1 rounded-full border border-white/15 bg-zinc-950/85 px-3 py-1 font-mono text-[10px] text-zinc-200">
                <Maximize2 className="h-3 w-3" /> Zoom
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* 04 · UNIFIED RECONSTRUCTION & EXPORT INSPECTOR */}
      <section
        id="reconstruccion"
        className="station-deferred scroll-mt-24 border-t border-(--hairline) py-16 lg:py-24"
      >
        <div className="grid items-center gap-10 lg:grid-cols-12">
          <div className="min-w-0 space-y-5 lg:col-span-7">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="inline-flex flex-wrap gap-1 rounded-full border border-(--hairline) bg-(--surface) p-1">
                {(
                  [
                    { id: "png", label: "PNG Recibido" },
                    { id: "svg", label: "SVG Vectorial" },
                    { id: "dither", label: "Atkinson 1-Bit" },
                    { id: "compare", label: "Comparativa" },
                  ] as const
                ).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setOutputTab(item.id)}
                    className={`rounded-full px-3 py-1 font-mono text-[11px] transition ${
                      outputTab === item.id
                        ? "bg-(--ink) font-semibold text-(--canvas)"
                        : "text-(--ink-muted) hover:text-(--ink)"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {outputTab === "svg" && (
                <div className="flex gap-1">
                  {[1, 2, 4].map((z) => (
                    <button
                      key={z}
                      type="button"
                      onClick={() => setSvgScale(z)}
                      className={`rounded-lg border px-2 py-0.5 font-mono text-[11px] ${
                        svgScale === z
                          ? "border-sky-500 bg-sky-500 text-zinc-950"
                          : "border-(--hairline) text-(--ink-muted)"
                      }`}
                    >
                      {z}×
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="relative flex min-h-[320px] items-center justify-center overflow-auto rounded-2xl border border-(--hairline) bg-zinc-950 p-4">
              {outputTab === "png" && (
                <button
                  type="button"
                  onClick={() =>
                    openLightbox(assets.reconstructed_png, "Imagen Reconstruida (PNG)")
                  }
                  className="group relative"
                >
                  <OptimizedPicture
                    src={assets.reconstructed_png}
                    alt="Reconstruida PNG"
                    className="max-h-72 w-auto rounded-lg object-contain"
                  />
                </button>
              )}

              {outputTab === "svg" && (
                <img
                  src={assets.reconstructed_svg}
                  alt="Reconstruida SVG Vectorial"
                  style={{ transform: `scale(${svgScale})`, transformOrigin: "center" }}
                  className="max-h-72 transition-transform duration-300"
                />
              )}

              {outputTab === "dither" && (
                <AtkinsonDitherCanvas src={assets.reconstructed_png} />
              )}

              {outputTab === "compare" && (
                <button
                  type="button"
                  onClick={() =>
                    openLightbox(
                      assets.fig_comparison,
                      "Comparativa Visual & Auditiva Final",
                      `PSNR ${fase3_4_5.image_metrics.psnr_db} dB · SSIM ${fase3_4_5.image_metrics.ssim}`
                    )
                  }
                  className="w-full"
                >
                  <OptimizedPicture
                    src={assets.fig_comparison}
                    alt="Comparativa Original vs Reconstruida"
                    className="max-h-80 w-full rounded-lg object-contain"
                  />
                </button>
              )}
            </div>
          </div>

          <div className="min-w-0 space-y-6 lg:col-span-5">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-rose-600 dark:text-rose-400">
                04 · Reconstrucción & Envío
              </p>
              <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-(--ink) sm:text-3xl">
                Entrega PNG, vector SVG y paquete demodulable.
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-(--ink-muted)">
                Verifica gráficamente y auditivamente la recuperación frente a la señal fuente,
                o descarga el paquete listo para que un compañero lo demodule en el Receptor RX.
              </p>
            </div>

            <dl className="divide-y divide-(--hairline) border-y border-(--hairline) text-xs">
              <div className="flex justify-between py-2.5">
                <dt className="text-(--ink-muted)">PSNR / SSIM visual</dt>
                <dd className="font-mono font-semibold text-(--ink)">
                  {fase3_4_5.image_metrics.psnr_db} dB · {fase3_4_5.image_metrics.ssim}
                </dd>
              </div>
              <div className="flex justify-between py-2.5">
                <dt className="text-(--ink-muted)">Audio SNR / Correlación r</dt>
                <dd className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                  {fase3_4_5.audio_metrics.snr_db} dB · {fase3_4_5.audio_metrics.pearson_corr}
                </dd>
              </div>
            </dl>

            <div className="flex flex-wrap gap-2.5">
              <a
                href={assets.peer_zip}
                download
                className="inline-flex items-center gap-1.5 rounded-full bg-(--ink) px-4 py-2 text-xs font-semibold text-(--canvas) transition hover:opacity-90"
              >
                <Download className="h-3.5 w-3.5" /> ZIP Compañero
              </a>
              <a
                href={assets.reconstructed_png}
                download
                className="inline-flex items-center gap-1.5 rounded-full border border-(--hairline) px-4 py-2 text-xs font-medium text-(--ink) transition hover:border-sky-500/50"
              >
                <ImageIcon className="h-3.5 w-3.5 text-sky-500" /> PNG
              </a>
              <a
                href={assets.reconstructed_svg}
                download
                className="inline-flex items-center gap-1.5 rounded-full border border-(--hairline) px-4 py-2 text-xs font-medium text-(--ink) transition hover:border-emerald-500/50"
              >
                <FileCode2 className="h-3.5 w-3.5 text-emerald-500" /> SVG
              </a>
            </div>
          </div>
        </div>
      </section>

      <ImageLightboxDialog asset={inspectAsset} onClose={() => setInspectAsset(null)} />
    </div>
  );
}
