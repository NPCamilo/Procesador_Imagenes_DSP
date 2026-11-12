"use client";

import React, { useState } from "react";
import { Download, Volume2, CheckCircle2, Image as ImageIcon, FileCode2 } from "lucide-react";
import type { DemoData } from "@/types/dsp";

export function DemoShowcase({ data }: { data: DemoData }) {
  const [svgScale, setSvgScale] = useState<number>(1);
  const { fase1, fase2, fase3_4_5, assets } = data;

  return (
    <div className="space-y-8">
      {/* KPI Resumen Superior */}
      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <article className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="font-mono text-xs uppercase tracking-wider text-zinc-400">Resolución & Camiseta</p>
          <p className="mt-1 text-xl font-bold text-zinc-100">
            {fase1.sampling.width_px}×{fase1.sampling.height_px}
          </p>
          <p className="mt-1 text-xs text-emerald-400">
            Rojo dominante: {fase1.red_filter.largest_area_percent}% ({fase1.red_filter.num_components} regiones)
          </p>
        </article>
        <article className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="font-mono text-xs uppercase tracking-wider text-zinc-400">Compresión DCT</p>
          <p className="mt-1 text-xl font-bold text-zinc-100">{fase2.compression_dct.ratio}×</p>
          <p className="mt-1 text-xs text-sky-400">
            Ahorro {fase2.compression_dct.savings_percent}% · {fase2.compression_dct.compressed_bytes.toLocaleString()} B
          </p>
        </article>
        <article className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="font-mono text-xs uppercase tracking-wider text-zinc-400">Transmisión {fase3_4_5.tx_manifest.scheme}</p>
          <p className="mt-1 text-xl font-bold text-zinc-100">BER = {fase3_4_5.ber_bfsk}</p>
          <p className="mt-1 flex items-center gap-1 text-xs text-emerald-400">
            <CheckCircle2 className="h-3.5 w-3.5" /> CRC32 {fase3_4_5.tx_manifest.crc32_hex} OK
          </p>
        </article>
        <article className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="font-mono text-xs uppercase tracking-wider text-zinc-400">Fidelidad Reconstruida</p>
          <p className="mt-1 text-xl font-bold text-zinc-100">{fase3_4_5.image_metrics.psnr_db} dB</p>
          <p className="mt-1 text-xs text-amber-400">
            SSIM {fase3_4_5.image_metrics.ssim} · Audio r = {fase3_4_5.audio_metrics.pearson_corr}
          </p>
        </article>
      </section>

      {/* Puntos 1 y 2 */}
      <section className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <header>
          <h2 className="text-lg font-bold text-zinc-100">Puntos 1 y 2 · Captura, Filtro Rojo de Mayor Área y Muestreo</h2>
          <p className="text-sm text-zinc-400">
            fs espacial = {fase1.sampling.spatial_sampling_rate_px} px⁻¹ (Nyquist = {fase1.sampling.spatial_nyquist_limit_cycles_per_px} ciclos/px, f_max = {fase1.sampling.f_max_spatial_cycles_per_px} ciclos/px) · Equivalent 1D = {fase1.sampling.equivalent_1d_sample_rate_hz.toLocaleString()} Hz ({fase1.sampling.nyquist_1d_verdict})
          </p>
        </header>
        <div className="grid gap-4 md:grid-cols-2">
          <figure className="space-y-2">
            <img src={assets.original_png} alt="Original Selfie DSP" className="w-full rounded-lg border border-zinc-800" />
            <figcaption className="text-xs text-zinc-400">Señal original RGB tomada con cámara móvil (espacio con múltiples objetos).</figcaption>
          </figure>
          <figure className="space-y-2">
            <img src={assets.red_splash_png} alt="Filtro Rojo Mayor Area" className="w-full rounded-lg border border-zinc-800" />
            <figcaption className="text-xs text-zinc-400">
              Solo la componente roja de mayor área ({fase1.red_filter.largest_area_px.toLocaleString()} px) permanece en color; los demás objetos rojos y el entorno quedan en gris.
            </figcaption>
          </figure>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <img src={assets.fig_original} alt="Canales RGB" className="w-full rounded-lg border border-zinc-800" />
          <img src={assets.fig_red_filter} alt="Detección de regiones rojas" className="w-full rounded-lg border border-zinc-800" />
          <img src={assets.fig_sampling} alt="Análisis de frecuencia de muestreo" className="w-full rounded-lg border border-zinc-800" />
        </div>
      </section>

      {/* Punto 3 */}
      <section className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <header>
          <h2 className="text-lg font-bold text-zinc-100">Punto 3 · Muestreo NQS, Resolución [Byte / Bit] y Compresión</h2>
          <p className="text-sm text-zinc-400">
            Trama 4 bits: {fase2.stream_4bits.total_bytes.toLocaleString()} Bytes · SQNR = {fase2.stream_4bits.sqnr_empirical_db} dB (Teórica: {fase2.stream_4bits.sqnr_theoretical_db} dB)
          </p>
        </header>
        <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 font-mono text-xs text-zinc-300">
          <div>Primeros 64 bits: <span className="text-sky-400">{fase2.stream_4bits.first_64_bits}</span></div>
          <div className="mt-1">Primeros Bytes HEX: <span className="text-amber-400">{fase2.stream_4bits.first_bytes_hex}</span></div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <img src={assets.fig_nqs} alt="Estudio NQS" className="w-full rounded-lg border border-zinc-800" />
          <img src={assets.fig_quantization} alt="Resolución Byte/Bit" className="w-full rounded-lg border border-zinc-800" />
          <img src={assets.fig_compression} alt="Compresión DPCM vs DCT" className="w-full rounded-lg border border-zinc-800" />
        </div>
      </section>

      {/* Puntos 4 y 5 */}
      <section className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <header>
          <h2 className="text-lg font-bold text-zinc-100">Puntos 4 y 5 · Modulación Audible en Bits y Demodulación</h2>
          <p className="text-sm text-zinc-400">
            Audio modulado {fase3_4_5.tx_manifest.scheme} ({fase3_4_5.tx_manifest.audio_duration_s} s @ {fase3_4_5.tx_manifest.sampling_rate_hz.toLocaleString()} Hz) · Sync offset = {fase3_4_5.sync_offset_samples} muestras · BER = {fase3_4_5.ber_bfsk}
          </p>
        </header>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-sky-400">
              <Volume2 className="h-4 w-4" /> Bits Modulados (BFSK)
            </p>
            <audio controls className="w-full" src={assets.wav_modulated_bfsk} />
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
              <Volume2 className="h-4 w-4" /> Señal Demodulada (BFSK)
            </p>
            <audio controls className="w-full" src={assets.wav_demodulated_bfsk} />
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-amber-400">
              <Volume2 className="h-4 w-4" /> Portadora Analógica AM
            </p>
            <audio controls className="w-full" src={assets.wav_modulated_am} />
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-purple-400">
              <Volume2 className="h-4 w-4" /> Portadora Analógica FM
            </p>
            <audio controls className="w-full" src={assets.wav_modulated_fm} />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <img src={assets.fig_mod_bfsk} alt="Modulación BFSK" className="w-full rounded-lg border border-zinc-800" />
          <img src={assets.fig_demod_bfsk} alt="Demodulación BFSK" className="w-full rounded-lg border border-zinc-800" />
          <img src={assets.fig_demod_qam} alt="Constelación 16-QAM" className="w-full rounded-lg border border-zinc-800" />
        </div>
      </section>

      {/* Punto 6 */}
      <section className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-zinc-100">Punto 6 · Reconstrucción PNG, SVG Vectorial, Audio DAC y Paquete de Envío</h2>
            <p className="text-sm text-zinc-400">
              Comparativa auditiva (SNR {fase3_4_5.audio_metrics.snr_db} dB) y visual (PSNR {fase3_4_5.image_metrics.psnr_db} dB, SSIM {fase3_4_5.image_metrics.ssim}).
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              href={assets.peer_zip}
              download
              className="inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-2 text-xs font-semibold text-white hover:bg-sky-500"
            >
              <Download className="h-3.5 w-3.5" /> Descargar ZIP Compañero
            </a>
            <a
              href={assets.reconstructed_png}
              download
              className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs font-semibold text-zinc-100 hover:bg-zinc-700"
            >
              <ImageIcon className="h-3.5 w-3.5" /> PNG
            </a>
            <a
              href={assets.reconstructed_svg}
              download
              className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs font-semibold text-zinc-100 hover:bg-zinc-700"
            >
              <FileCode2 className="h-3.5 w-3.5" /> SVG Vectorial
            </a>
          </div>
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 text-xs font-semibold text-sky-400">Audio Señal Original (Scanline 1D)</p>
            <audio controls className="w-full" src={assets.wav_audio_original} />
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 text-xs font-semibold text-emerald-400">Audio Señal Reconstruida (DAC Sinc)</p>
            <audio controls className="w-full" src={assets.wav_audio_reconstructed} />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 text-xs font-semibold text-zinc-200">Imagen Reconstruida (PNG)</p>
            <img src={assets.reconstructed_png} alt="Reconstruida PNG" className="mx-auto max-h-64 rounded" />
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-semibold text-zinc-200">Vectorial SVG (Zoom {svgScale}×)</p>
              <div className="flex gap-1">
                {[1, 2, 4].map((z) => (
                  <button
                    key={z}
                    type="button"
                    onClick={() => setSvgScale(z)}
                    className={`rounded px-2 py-0.5 text-[11px] ${
                      svgScale === z ? "bg-sky-600 text-white" : "bg-zinc-800 text-zinc-300"
                    }`}
                  >
                    {z}×
                  </button>
                ))}
              </div>
            </div>
            <div className="max-h-64 overflow-auto rounded bg-zinc-900 p-2">
              <img
                src={assets.reconstructed_svg}
                alt="Reconstruida SVG"
                style={{ transform: `scale(${svgScale})`, transformOrigin: "top left" }}
                className="mx-auto max-h-56"
              />
            </div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-2 text-xs font-semibold text-zinc-200">Comparativa Visual & Auditiva</p>
            <img src={assets.fig_comparison} alt="Comparativa Final" className="w-full rounded" />
          </div>
        </div>
      </section>
    </div>
  );
}
