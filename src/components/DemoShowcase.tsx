"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  Cpu,
  Download,
  FileCode2,
  Image as ImageIcon,
  Maximize2,
  Radio,
  Volume2,
} from "lucide-react";
import type { DemoData } from "@/types/dsp";
import { BeforeAfterComparator } from "./BeforeAfterComparator";
import { ImageLightboxDialog, type LightboxAsset } from "./ImageLightboxDialog";

interface DemoShowcaseProps {
  data: DemoData;
  onSwitchTab?: (tab: "demo" | "tx" | "rx") => void;
}

function AtkinsonDitherCanvas({ src }: { src: string }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = src;
    img.onload = () => {
      const targetW = 192;
      const ratio = img.height / img.width || 1;
      const targetH = Math.max(64, Math.round(targetW * ratio));
      canvas.width = targetW;
      canvas.height = targetH;

      ctx.drawImage(img, 0, 0, targetW, targetH);
      const imgData = ctx.getImageData(0, 0, targetW, targetH);
      const data = imgData.data;

      // Atkinson 1-bit dithering on luminance channel (Ditther skill)
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
          data[p] = bit ? 228 : 12;
          data[p + 1] = bit ? 242 : 14;
          data[p + 2] = bit ? 254 : 18;
          data[p + 3] = 255;
        }
      }

      ctx.putImageData(imgData, 0, 0);
    };
  }, [src]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="Previsualización 1-bit con algoritmo de dithering Atkinson"
      className="mx-auto max-h-56 w-auto rounded-lg border border-white/10 [image-rendering:pixelated]"
    />
  );
}

export function DemoShowcase({ data, onSwitchTab }: DemoShowcaseProps) {
  const [svgScale, setSvgScale] = useState<number>(1);
  const [inspectAsset, setInspectAsset] = useState<LightboxAsset | null>(null);
  const { fase1, fase2, fase3_4_5, assets } = data;

  const openLightbox = (src: string, title: string, caption?: string) => {
    setInspectAsset({ src, title, caption });
  };

  return (
    <div className="min-w-0 space-y-10 sm:space-y-12">
      {/* BENTO HERO SECTION (Phases 4, 5, 6, 8) */}
      <section className="animate-reveal grid min-w-0 items-center gap-8 overflow-hidden rounded-3xl border border-white/10 bg-zinc-900/65 p-4 shadow-2xl backdrop-blur-xl sm:p-8 lg:grid-cols-12 lg:gap-10">
        <div className="min-w-0 space-y-6 lg:col-span-7">
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-400/25 bg-sky-500/10 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-sky-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            Pipeline Validado · 6 Etapas DSP · UTP
          </div>

          <div className="space-y-3">
            <h2 className="font-display text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.65rem] lg:leading-[1.12]">
              De fotografía móvil a portadora audible y reconstrucción vectorial.
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-zinc-300 sm:text-base">
              Sistema completo de procesamiento digital de señales para{" "}
              <span className="font-mono text-zinc-100">{data.project.source_image}</span>:
              aislamiento de la mayor componente roja conexa, análisis Nyquist-Shannon (NQS),
              cuantización <span className="font-mono text-sky-300">[Byte / Bit]</span>,
              compresión DCT 8×8, modulación audible BFSK/16-QAM y reconstrucción PNG/SVG.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {onSwitchTab && (
              <>
                <button
                  type="button"
                  onClick={() => onSwitchTab("tx")}
                  className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-4 py-2.5 text-xs font-semibold text-zinc-950 shadow-lg shadow-sky-500/20 transition hover:-translate-y-0.5 hover:bg-sky-400 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                >
                  <Cpu className="h-4 w-4" /> Abrir Laboratorio TX en Vivo
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => onSwitchTab("rx")}
                  className="inline-flex items-center gap-2 rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-2.5 text-xs font-semibold text-emerald-200 transition hover:-translate-y-0.5 hover:bg-emerald-500/20 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
                >
                  <Radio className="h-4 w-4" /> Modo Receptor RX
                </button>
              </>
            )}
            <a
              href={assets.peer_zip}
              download
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-zinc-950/70 px-4 py-2.5 text-xs font-semibold text-zinc-200 transition hover:-translate-y-0.5 hover:border-white/30 hover:text-white active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <Download className="h-4 w-4 text-sky-400" /> Paquete Compañero (.zip)
            </a>
          </div>

          {/* Quick hardware specs micro-strip */}
          <dl className="grid grid-cols-1 gap-3 border-t border-white/10 pt-5 sm:grid-cols-3 sm:gap-4">
            <div className="min-w-0">
              <dt className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
                Muestreo 1D Eq.
              </dt>
              <dd className="mt-1 font-mono text-sm font-semibold text-zinc-100">
                {fase1.sampling.equivalent_1d_sample_rate_hz.toLocaleString()} Hz
              </dd>
            </div>
            <div className="min-w-0">
              <dt className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
                Integridad CRC32
              </dt>
              <dd className="mt-1 font-mono text-sm font-semibold text-emerald-400">
                {fase3_4_5.tx_manifest.crc32_hex}
              </dd>
            </div>
            <div className="min-w-0">
              <dt className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
                Audio DAC SNR
              </dt>
              <dd className="mt-1 font-mono text-sm font-semibold text-amber-300">
                {fase3_4_5.audio_metrics.snr_db} dB
              </dd>
            </div>
          </dl>
        </div>

        <div className="min-w-0 lg:col-span-5">
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

      {/* KPI TELEMETRY BENTO GRID */}
      <section aria-label="Indicadores clave del sistema DSP" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article
          style={{ animationDelay: "60ms" }}
          className="animate-reveal rounded-2xl border border-white/10 bg-zinc-900/75 p-5 backdrop-blur-md transition hover:-translate-y-0.5 hover:border-white/20"
        >
          <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
            Resolución & Camiseta
          </p>
          <p className="mt-2 font-display text-2xl font-bold tracking-tight text-white">
            {fase1.sampling.width_px}×{fase1.sampling.height_px}
          </p>
          <p className="mt-1.5 text-xs text-emerald-400">
            Rojo dominante: {fase1.red_filter.largest_area_percent}% ({fase1.red_filter.num_components} regiones)
          </p>
        </article>

        <article
          style={{ animationDelay: "120ms" }}
          className="animate-reveal rounded-2xl border border-white/10 bg-zinc-900/75 p-5 backdrop-blur-md transition hover:-translate-y-0.5 hover:border-white/20"
        >
          <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
            Compresión DCT 8×8
          </p>
          <p className="mt-2 font-display text-2xl font-bold tracking-tight text-white">
            {fase2.compression_dct.ratio}×
          </p>
          <p className="mt-1.5 text-xs text-sky-400">
            Ahorro {fase2.compression_dct.savings_percent}% ·{" "}
            {fase2.compression_dct.compressed_bytes.toLocaleString()} B
          </p>
        </article>

        <article
          style={{ animationDelay: "180ms" }}
          className="animate-reveal rounded-2xl border border-white/10 bg-zinc-900/75 p-5 backdrop-blur-md transition hover:-translate-y-0.5 hover:border-white/20"
        >
          <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
            Transmisión {fase3_4_5.tx_manifest.scheme}
          </p>
          <p className="mt-2 font-display text-2xl font-bold tracking-tight text-white">
            BER = {fase3_4_5.ber_bfsk}
          </p>
          <p className="mt-1.5 flex items-center gap-1.5 text-xs text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" /> CRC32 {fase3_4_5.tx_manifest.crc32_hex} OK
          </p>
        </article>

        <article
          style={{ animationDelay: "240ms" }}
          className="animate-reveal rounded-2xl border border-white/10 bg-zinc-900/75 p-5 backdrop-blur-md transition hover:-translate-y-0.5 hover:border-white/20"
        >
          <p className="font-mono text-[11px] uppercase tracking-widest text-zinc-400">
            Fidelidad Reconstruida
          </p>
          <p className="mt-2 font-display text-2xl font-bold tracking-tight text-white">
            {fase3_4_5.image_metrics.psnr_db} dB
          </p>
          <p className="mt-1.5 text-xs text-amber-300">
            SSIM {fase3_4_5.image_metrics.ssim} · Audio r = {fase3_4_5.audio_metrics.pearson_corr}
          </p>
        </article>
      </section>

      {/* STATION 01-02: CAPTURE, RED FILTER & SAMPLING */}
      <section className="space-y-6 rounded-2xl border border-white/10 bg-zinc-900/65 p-6 backdrop-blur-md sm:p-8">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-sky-400">
              Estación 01 – 02 · Captura & Análisis Espectral
            </p>
            <h3 className="mt-1 font-display text-xl font-bold text-white">
              Reproducción RGB, Filtro de Mayor Área Roja y Frecuencia de Muestreo
            </h3>
          </div>
          <p className="font-mono text-xs text-zinc-400">
            fs = {fase1.sampling.spatial_sampling_rate_px} px⁻¹ · Nyquist ={" "}
            {fase1.sampling.spatial_nyquist_limit_cycles_per_px} cyc/px ·{" "}
            {fase1.sampling.nyquist_1d_verdict}
          </p>
        </header>

        <div className="grid gap-4 md:grid-cols-3">
          {[
            {
              src: assets.fig_original,
              title: "Canales RGB y Perfil Espectral Original",
              desc: "Descomposición espacial R/G/B e histograma de intensidad.",
            },
            {
              src: assets.fig_red_filter,
              title: "Segmentación HSV y Mayor Componente Conexa",
              desc: `${fase1.red_filter.largest_area_px.toLocaleString()} px aislados frente a ${fase1.red_filter.num_components} regiones.`,
            },
            {
              src: assets.fig_sampling,
              title: "Análisis de Frecuencia de Muestreo 2D / 1D",
              desc: `Criterio Nyquist con fs eq. ${fase1.sampling.equivalent_1d_sample_rate_hz.toLocaleString()} Hz.`,
            },
          ].map((fig) => (
            <button
              key={fig.title}
              type="button"
              onClick={() => openLightbox(fig.src, fig.title, fig.desc)}
              className="group relative flex flex-col overflow-hidden rounded-xl border border-white/10 bg-zinc-950/75 text-left transition hover:-translate-y-0.5 hover:border-sky-400/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <div className="relative overflow-hidden">
                <img
                  src={fig.src}
                  alt={fig.title}
                  className="aspect-[16/10] w-full object-cover transition duration-500 group-hover:scale-[1.02]"
                />
                <span className="absolute right-2.5 top-2.5 inline-flex items-center gap-1 rounded-md border border-white/15 bg-zinc-950/80 px-2 py-1 font-mono text-[10px] text-zinc-200 backdrop-blur">
                  <Maximize2 className="h-3 w-3" /> Zoom
                </span>
              </div>
              <div className="p-3.5">
                <p className="text-xs font-semibold text-zinc-100">{fig.title}</p>
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">{fig.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* STATION 03: NQS SAMPLING, QUANTIZATION & COMPRESSION */}
      <section className="space-y-6 rounded-2xl border border-white/10 bg-zinc-900/65 p-6 backdrop-blur-md sm:p-8">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-amber-400">
              Estación 03 · Muestreo NQS, Resolución [Byte / Bit] & Compresión
            </p>
            <h3 className="mt-1 font-display text-xl font-bold text-white">
              Teorema de Nyquist-Shannon, Cuantización Uniforme y Códec Híbrido
            </h3>
          </div>
          <p className="font-mono text-xs text-zinc-400">
            SQNR Empírica = {fase2.stream_4bits.sqnr_empirical_db} dB · Teórica ={" "}
            {fase2.stream_4bits.sqnr_theoretical_db} dB
          </p>
        </header>

        <div className="grid min-w-0 gap-4 lg:grid-cols-3">
          <div className="min-w-0 overflow-hidden rounded-xl border border-white/10 bg-zinc-950/80 p-4 font-mono text-xs lg:col-span-2">
            <p className="text-[10px] uppercase tracking-widest text-zinc-400">
              Trama Digital Cuantizada (4 bits/muestra · {fase2.working_resolution})
            </p>
            <div className="mt-2 break-all text-sky-300 [overflow-wrap:anywhere]">
              <span className="text-zinc-500">BIN[0..63]: </span>
              {fase2.stream_4bits.first_64_bits}
            </div>
            <div className="mt-1.5 break-all text-amber-300 [overflow-wrap:anywhere]">
              <span className="text-zinc-500">HEX: </span>
              {fase2.stream_4bits.first_bytes_hex}
            </div>
          </div>

          <div className="min-w-0 rounded-xl border border-white/10 bg-zinc-950/80 p-4 text-xs">
            <p className="font-mono text-[10px] uppercase tracking-widest text-zinc-400">
              Comparativa Lossless vs DCT
            </p>
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-zinc-300">
              <span>DPCM + Zlib (Sin pérdida):</span>
              <span className="font-mono font-semibold text-zinc-100">
                {fase2.compression_lossless.ratio}× ({fase2.compression_lossless.savings_percent}%)
              </span>
            </div>
            <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-zinc-300">
              <span>DCT 8×8 + Zlib:</span>
              <span className="font-mono font-semibold text-emerald-400">
                {fase2.compression_dct.ratio}× ({fase2.compression_dct.savings_percent}%)
              </span>
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {[
            { src: assets.fig_nqs, title: "Estudio NQS y Aliasing Espacial" },
            { src: assets.fig_quantization, title: "Resolución Digital [Byte / Bit] y SQNR" },
            { src: assets.fig_compression, title: "Rendimiento Compresión DPCM vs DCT" },
          ].map((fig) => (
            <button
              key={fig.title}
              type="button"
              onClick={() => openLightbox(fig.src, fig.title)}
              className="group relative overflow-hidden rounded-xl border border-white/10 bg-zinc-950/75 text-left transition hover:-translate-y-0.5 hover:border-amber-400/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
            >
              <img
                src={fig.src}
                alt={fig.title}
                className="aspect-[16/10] w-full object-cover transition duration-500 group-hover:scale-[1.02]"
              />
              <span className="absolute right-2.5 top-2.5 inline-flex items-center gap-1 rounded-md border border-white/15 bg-zinc-950/80 px-2 py-1 font-mono text-[10px] text-zinc-200 backdrop-blur">
                <Maximize2 className="h-3 w-3" /> Zoom
              </span>
              <div className="p-3.5 text-xs font-semibold text-zinc-100">{fig.title}</div>
            </button>
          ))}
        </div>
      </section>

      {/* STATION 04-05: AUDIBLE MODULATION & DEMODULATION */}
      <section className="space-y-6 rounded-2xl border border-white/10 bg-zinc-900/65 p-6 backdrop-blur-md sm:p-8">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-emerald-400">
              Estación 04 – 05 · Transceptor Pasabanda & Audio de Bits
            </p>
            <h3 className="mt-1 font-display text-xl font-bold text-white">
              Modulación Audible en Bits, Sincronización Ciega y Demodulación
            </h3>
          </div>
          <p className="font-mono text-xs text-zinc-400">
            {fase3_4_5.tx_manifest.scheme} · {fase3_4_5.tx_manifest.audio_duration_s} s @{" "}
            {fase3_4_5.tx_manifest.sampling_rate_hz.toLocaleString()} Hz · Sync ={" "}
            {fase3_4_5.sync_offset_samples} muestras
          </p>
        </header>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              title: "Bits Modulados (BFSK)",
              color: "text-sky-400 border-sky-500/20",
              src: assets.wav_modulated_bfsk,
            },
            {
              title: "Señal Demodulada (BFSK)",
              color: "text-emerald-400 border-emerald-500/20",
              src: assets.wav_demodulated_bfsk,
            },
            {
              title: "Portadora Analógica AM",
              color: "text-amber-400 border-amber-500/20",
              src: assets.wav_modulated_am,
            },
            {
              title: "Portadora Analógica FM",
              color: "text-rose-400 border-rose-500/20",
              src: assets.wav_modulated_fm,
            },
          ].map((track) => (
            <div
              key={track.title}
              className={`min-w-0 overflow-hidden rounded-xl border bg-zinc-950/85 p-3.5 ${track.color}`}
            >
              <p className="mb-2.5 flex items-center gap-1.5 text-xs font-semibold">
                <Volume2 className="h-4 w-4 shrink-0" /> {track.title}
              </p>
              <audio
                controls
                preload="metadata"
                className="h-9 w-full min-w-0 max-w-full"
                src={track.src}
              />
            </div>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {[
            { src: assets.fig_mod_bfsk, title: "Modulación BFSK: Portadora y Espectro" },
            { src: assets.fig_demod_bfsk, title: "Demodulación Coherente y Correlación" },
            {
              src: assets.fig_demod_qam,
              title: `Constelación 16-QAM (BER = ${fase3_4_5.qam_ber})`,
            },
          ].map((fig) => (
            <button
              key={fig.title}
              type="button"
              onClick={() => openLightbox(fig.src, fig.title)}
              className="group relative overflow-hidden rounded-xl border border-white/10 bg-zinc-950/75 text-left transition hover:-translate-y-0.5 hover:border-emerald-400/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
            >
              <img
                src={fig.src}
                alt={fig.title}
                className="aspect-[16/10] w-full object-cover transition duration-500 group-hover:scale-[1.02]"
              />
              <span className="absolute right-2.5 top-2.5 inline-flex items-center gap-1 rounded-md border border-white/15 bg-zinc-950/80 px-2 py-1 font-mono text-[10px] text-zinc-200 backdrop-blur">
                <Maximize2 className="h-3 w-3" /> Zoom
              </span>
              <div className="p-3.5 text-xs font-semibold text-zinc-100">{fig.title}</div>
            </button>
          ))}
        </div>
      </section>

      {/* STATION 06: RECONSTRUCTION PNG, SVG, DAC AUDIO, DITHER PREVIEW & EXCHANGE */}
      <section className="space-y-6 rounded-2xl border border-white/10 bg-zinc-900/65 p-6 backdrop-blur-md sm:p-8">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-rose-400">
              Estación 06 · Reconstrucción Final & Envío
            </p>
            <h3 className="mt-1 font-display text-xl font-bold text-white">
              Audio DAC, Imagen PNG, Vectorial SVG, Trama Dither 1-Bit & Comparativa
            </h3>
            <p className="mt-1 text-xs text-zinc-400">
              Audio SNR = {fase3_4_5.audio_metrics.snr_db} dB · Visual PSNR ={" "}
              {fase3_4_5.image_metrics.psnr_db} dB · SSIM = {fase3_4_5.image_metrics.ssim}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <a
              href={assets.peer_zip}
              download
              className="inline-flex items-center gap-1.5 rounded-xl bg-sky-500 px-3.5 py-2 text-xs font-semibold text-zinc-950 transition hover:-translate-y-0.5 hover:bg-sky-400 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <Download className="h-3.5 w-3.5" /> ZIP Compañero
            </a>
            <a
              href={assets.reconstructed_png}
              download
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-zinc-950/80 px-3.5 py-2 text-xs font-semibold text-zinc-100 transition hover:-translate-y-0.5 hover:border-white/30 active:scale-[0.98]"
            >
              <ImageIcon className="h-3.5 w-3.5 text-sky-400" /> PNG
            </a>
            <a
              href={assets.reconstructed_svg}
              download
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-zinc-950/80 px-3.5 py-2 text-xs font-semibold text-zinc-100 transition hover:-translate-y-0.5 hover:border-white/30 active:scale-[0.98]"
            >
              <FileCode2 className="h-3.5 w-3.5 text-emerald-400" /> SVG Vectorial
            </a>
          </div>
        </header>

        <div className="grid min-w-0 gap-4 md:grid-cols-2">
          <div className="min-w-0 overflow-hidden rounded-xl border border-sky-500/20 bg-zinc-950/85 p-4">
            <p className="mb-2.5 text-xs font-semibold text-sky-400">
              Audio Señal Original (Scanline 1D)
            </p>
            <audio
              controls
              preload="metadata"
              className="h-9 w-full min-w-0 max-w-full"
              src={assets.wav_audio_original}
            />
          </div>
          <div className="min-w-0 overflow-hidden rounded-xl border border-emerald-500/20 bg-zinc-950/85 p-4">
            <p className="mb-2.5 text-xs font-semibold text-emerald-400">
              Audio Señal Reconstruida (DAC Sinc)
            </p>
            <audio
              controls
              preload="metadata"
              className="h-9 w-full min-w-0 max-w-full"
              src={assets.wav_audio_reconstructed}
            />
          </div>
        </div>

        <div className="grid min-w-0 gap-4 md:grid-cols-3">
          <div className="min-w-0 rounded-xl border border-white/10 bg-zinc-950/80 p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold text-zinc-100">Imagen Reconstruida (PNG)</p>
              <button
                type="button"
                onClick={() =>
                  openLightbox(assets.reconstructed_png, "Imagen Reconstruida (PNG)")
                }
                className="font-mono text-[10px] uppercase text-sky-400 hover:text-sky-300"
              >
                Ampliar
              </button>
            </div>
            <img
              src={assets.reconstructed_png}
              alt="Reconstruida PNG"
              className="mx-auto max-h-56 rounded-lg border border-white/10"
            />
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/80 p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold text-zinc-100">
                Vectorial SVG (Zoom {svgScale}×)
              </p>
              <div className="flex gap-1">
                {[1, 2, 4].map((z) => (
                  <button
                    key={z}
                    type="button"
                    onClick={() => setSvgScale(z)}
                    className={`rounded-md px-2 py-0.5 font-mono text-[11px] transition ${
                      svgScale === z
                        ? "bg-sky-500 font-semibold text-zinc-950"
                        : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                    }`}
                  >
                    {z}×
                  </button>
                ))}
              </div>
            </div>
            <div className="flex max-h-56 justify-center overflow-auto rounded-lg border border-white/5 bg-zinc-900/70 p-2">
              <img
                src={assets.reconstructed_svg}
                alt="Reconstruida SVG"
                style={{ transform: `scale(${svgScale})`, transformOrigin: "top left" }}
                className="mx-auto max-h-52"
              />
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/80 p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold text-zinc-100">Atkinson 1-Bit Dither</p>
              <span className="font-mono text-[10px] uppercase tracking-wider text-zinc-400">
                Difusión de error
              </span>
            </div>
            <AtkinsonDitherCanvas src={assets.reconstructed_png} />
          </div>
        </div>

        <button
          type="button"
          onClick={() =>
            openLightbox(
              assets.fig_comparison,
              "Comparativa Integral Visual & Auditiva",
              `PSNR ${fase3_4_5.image_metrics.psnr_db} dB · SSIM ${fase3_4_5.image_metrics.ssim} · Audio SNR ${fase3_4_5.audio_metrics.snr_db} dB`
            )
          }
          className="group relative w-full overflow-hidden rounded-xl border border-white/10 bg-zinc-950/80 p-3 text-left transition hover:border-sky-400/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        >
          <div className="mb-2 flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-zinc-200">
              Panel Comparativo Visual & Auditivo Completo
            </span>
            <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase text-sky-400">
              <Maximize2 className="h-3 w-3" /> Inspeccionar pantalla completa
            </span>
          </div>
          <img
            src={assets.fig_comparison}
            alt="Comparativa Final"
            className="w-full rounded-lg object-contain transition duration-500 group-hover:scale-[1.005]"
          />
        </button>
      </section>

      <ImageLightboxDialog asset={inspectAsset} onClose={() => setInspectAsset(null)} />
    </div>
  );
}
