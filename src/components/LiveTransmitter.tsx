"use client";

import React, { useState } from "react";
import { Download, Loader2, Maximize2, Play, Sliders, Upload } from "lucide-react";
import type { LiveTxResponse } from "@/types/dsp";
import { ImageLightboxDialog, type LightboxAsset } from "./ImageLightboxDialog";
import { ConstellationPlot, SignalPolylinePlot } from "./SignalSvgPlot";

function downloadBase64(b64: string, filename: string, mime: string) {
  const raw = atob(b64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  const blob = new Blob([bytes], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function LiveTransmitter() {
  const [file, setFile] = useState<File | null>(null);
  const [scheme, setScheme] = useState("BFSK");
  const [compression, setCompression] = useState("lossy_dct_zlib");
  const [bits, setBits] = useState(4);
  const [quality, setQuality] = useState(80);
  const [txDim, setTxDim] = useState(64);
  const [nqsFactor, setNqsFactor] = useState(8);
  const [applyRed, setApplyRed] = useState(true);
  const [snrDb, setSnrDb] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LiveTxResponse | null>(null);
  const [inspectAsset, setInspectAsset] = useState<LightboxAsset | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      if (file) form.append("file", file);
      form.append("scheme", scheme);
      form.append("compression_method", compression);
      form.append("bits_per_sample", String(bits));
      form.append("quality", String(quality));
      form.append("tx_max_dim", String(txDim));
      form.append("nqs_factor", String(nqsFactor));
      form.append("apply_red_filter", String(applyRed));
      if (snrDb.trim() !== "") form.append("snr_db", snrDb.trim());

      const res = await fetch("/api/tx/pipeline", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al ejecutar el pipeline DSP");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado en el servidor DSP");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-reveal space-y-8">
      <form
        onSubmit={handleSubmit}
        className="space-y-6 rounded-2xl border border-white/10 bg-zinc-900/75 p-6 shadow-xl backdrop-blur-md"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-widest text-sky-400">
              Banco de Pruebas en Tiempo Real · FastAPI DSP
            </p>
            <h2 className="mt-0.5 font-display text-xl font-bold text-white">
              Laboratorio Transmisor y Simulador de Canal
            </h2>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-zinc-950/75 px-3 py-1 font-mono text-[11px] text-zinc-300">
            <Sliders className="h-3.5 w-3.5 text-sky-400" /> {scheme} · {bits} bits
          </span>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-zinc-300">
              Fotografía JPG / JPEG / PNG (opcional — si se omite usa Selfie DSP)
            </label>
            <label className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-dashed border-white/20 bg-zinc-950/80 px-3.5 py-2.5 text-xs text-zinc-300 transition hover:border-sky-400/60 hover:text-white">
              <Upload className="h-4 w-4 shrink-0 text-sky-400" />
              <span className="truncate">
                {file ? file.name : "Seleccionar fotografía o usar Selfie DSP por defecto"}
              </span>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-300">
              Esquema de Modulación
            </label>
            <select
              value={scheme}
              onChange={(e) => setScheme(e.target.value)}
              className="w-full rounded-xl border border-white/15 bg-zinc-950/85 px-3 py-2.5 text-xs text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <option value="BFSK">BFSK (1500 bps)</option>
              <option value="MFSK">MFSK 4-FSK (2000 bps)</option>
              <option value="ASK">ASK (1500 bps)</option>
              <option value="BPSK">BPSK (1500 bps)</option>
              <option value="16-QAM">16-QAM (6000 bps)</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-300">Compresión</label>
            <select
              value={compression}
              onChange={(e) => setCompression(e.target.value)}
              className="w-full rounded-xl border border-white/15 bg-zinc-950/85 px-3 py-2.5 text-xs text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <option value="lossy_dct_zlib">DCT 8×8 + Zlib (Alta compresión)</option>
              <option value="lossless_dpcm_zlib">DPCM + Zlib (Sin pérdida)</option>
            </select>
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/60 p-3">
            <label className="mb-1.5 flex items-center justify-between text-xs font-medium text-zinc-300">
              <span>Resolución [Byte/Bit]</span>
              <span className="font-mono text-sky-400">{bits} bits</span>
            </label>
            <input
              type="range"
              min={1}
              max={8}
              value={bits}
              onChange={(e) => setBits(Number(e.target.value))}
              className="w-full accent-sky-400"
            />
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/60 p-3">
            <label className="mb-1.5 flex items-center justify-between text-xs font-medium text-zinc-300">
              <span>Calidad DCT</span>
              <span className="font-mono text-sky-400">{quality}%</span>
            </label>
            <input
              type="range"
              min={25}
              max={95}
              value={quality}
              onChange={(e) => setQuality(Number(e.target.value))}
              className="w-full accent-sky-400"
            />
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/60 p-3">
            <label className="mb-1.5 block text-xs font-medium text-zinc-300">
              Resolución TX ({txDim} px) & Aliasing NQS ({nqsFactor}×)
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min={32}
                max={88}
                value={txDim}
                onChange={(e) => setTxDim(Number(e.target.value))}
                className="w-1/2 rounded-lg border border-white/15 bg-zinc-900 px-2.5 py-1 font-mono text-xs text-zinc-100"
              />
              <input
                type="number"
                min={2}
                max={16}
                value={nqsFactor}
                onChange={(e) => setNqsFactor(Number(e.target.value))}
                className="w-1/2 rounded-lg border border-white/15 bg-zinc-900 px-2.5 py-1 font-mono text-xs text-zinc-100"
              />
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-zinc-950/60 p-3">
            <label className="mb-1.5 block text-xs font-medium text-zinc-300">
              Ruido AWGN SNR (dB, opcional)
            </label>
            <input
              type="text"
              placeholder="Ideal (vacío) o ej. 16"
              value={snrDb}
              onChange={(e) => setSnrDb(e.target.value)}
              className="w-full rounded-lg border border-white/15 bg-zinc-900 px-2.5 py-1 font-mono text-xs text-zinc-100 placeholder:text-zinc-500"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-4">
          <label className="flex cursor-pointer items-center gap-2.5 text-xs text-zinc-300">
            <input
              type="checkbox"
              checked={applyRed}
              onChange={(e) => setApplyRed(e.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-zinc-950 accent-red-500"
            />
            Aplicar filtro selectivo de color rojo de mayor área antes de comprimir
          </label>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-2.5 text-xs font-semibold text-zinc-950 shadow-lg shadow-sky-500/20 transition hover:-translate-y-0.5 hover:bg-sky-400 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {loading ? "Procesando en Python..." : "Ejecutar Pipeline Completo"}
          </button>
        </div>
      </form>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-500/30 bg-red-950/60 p-4 text-xs text-red-200 backdrop-blur"
        >
          {error}
        </div>
      )}

      {!result && !loading && !error && (
        <div className="rounded-2xl border border-dashed border-white/15 bg-zinc-900/40 p-8 text-center backdrop-blur-sm">
          <p className="font-display text-sm font-semibold text-zinc-200">
            Banco TX listo para transmitir
          </p>
          <p className="mx-auto mt-1 max-w-xl text-xs leading-relaxed text-zinc-400">
            Sube tu propia imagen o deja la fotografía por defecto{" "}
            <span className="font-mono text-zinc-300">Selfie DSP</span>, ajusta la cuantización{" "}
            <span className="font-mono text-zinc-300">[Byte / Bit]</span> y el esquema pasabanda, y
            presiona <strong className="text-sky-300">Ejecutar Pipeline Completo</strong> para
            generar trama, audio modulado y paquete compartible.
          </p>
        </div>
      )}

      {result && (
        <div className="animate-reveal space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <article className="rounded-2xl border border-white/10 bg-zinc-900/75 p-4 backdrop-blur-md">
              <p className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
                Rojo Mayor Área
              </p>
              <p className="mt-1 font-display text-xl font-bold text-white">
                {result.fase1.red_filter.largest_area_percent}%
              </p>
              <p className="mt-1 text-xs text-zinc-400">
                {result.fase1.red_filter.num_components} componentes
              </p>
            </article>
            <article className="rounded-2xl border border-white/10 bg-zinc-900/75 p-4 backdrop-blur-md">
              <p className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
                Compresión {result.fase2.compression.method}
              </p>
              <p className="mt-1 font-display text-xl font-bold text-white">
                {result.fase2.compression.compression_ratio}×
              </p>
              <p className="mt-1 text-xs text-sky-400">
                {result.fase2.compression.compressed_bytes} Bytes
              </p>
            </article>
            <article className="rounded-2xl border border-white/10 bg-zinc-900/75 p-4 backdrop-blur-md">
              <p className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
                Canal & Demodulación
              </p>
              <p className="mt-1 font-display text-xl font-bold text-white">
                BER = {result.fase3_4.ber !== null ? result.fase3_4.ber.toExponential(1) : "N/A"}
              </p>
              <p className="mt-1 text-xs text-emerald-400">
                {result.fase3_4.crc_valid ? "CRC32 OK" : "CRC32 ERROR (Mucho ruido)"}
              </p>
            </article>
            <article className="rounded-2xl border border-white/10 bg-zinc-900/75 p-4 backdrop-blur-md">
              <p className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
                Calidad Reconstruida
              </p>
              <p className="mt-1 font-display text-xl font-bold text-white">
                {result.fase5.metrics ? `${result.fase5.metrics.psnr_db} dB` : "Fallo CRC"}
              </p>
              <p className="mt-1 text-xs text-amber-300">
                {result.fase5.metrics ? `SSIM ${result.fase5.metrics.ssim}` : "Sin reconstrucción"}
              </p>
            </article>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {[
              { label: "Original", src: result.fase1.original_png },
              { label: "Rojo Mayor Área", src: result.fase1.red_splash_png },
              { label: `Aliasing NQS (${nqsFactor}×)`, src: result.fase2.nqs_aliased_png },
              { label: `Cuantizada (${bits} bits)`, src: result.fase2.quantized_png },
              {
                label: "Reconstruida PNG",
                src: result.fase5.reconstructed_png || result.fase5.source_tx_png,
              },
            ].map((item) => (
              <button
                key={item.label}
                type="button"
                onClick={() => setInspectAsset({ src: item.src, title: item.label })}
                className="group relative overflow-hidden rounded-xl border border-white/10 bg-zinc-950/80 p-2.5 text-center transition hover:-translate-y-0.5 hover:border-sky-400/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              >
                <span className="absolute right-3 top-3 rounded bg-zinc-950/80 p-1 text-zinc-300 opacity-0 transition group-hover:opacity-100">
                  <Maximize2 className="h-3 w-3" />
                </span>
                <img
                  src={item.src}
                  alt={item.label}
                  className="h-44 w-full rounded-lg object-contain"
                />
                <span className="mt-2 block text-[11px] font-medium text-zinc-300">
                  {item.label}
                </span>
              </button>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <SignalPolylinePlot
              title={`Señal Modulada ${result.fase3_4.manifest.scheme} (Zoom)`}
              values={result.fase3_4.modulated_zoom}
              minY={-1}
              maxY={1}
            />
            <SignalPolylinePlot
              title="Espectro Pasabanda |S(f)| [dBFS]"
              values={result.fase3_4.spectrum_db}
              xValues={result.fase3_4.spectrum_freqs}
              xLabel="Hz"
              strokeColor="#CC79A7"
              minY={-65}
              maxY={5}
            />
          </div>

          <div className="grid min-w-0 gap-4 md:grid-cols-2">
            <div className="min-w-0 overflow-hidden rounded-xl border border-sky-500/20 bg-zinc-950/85 p-3.5">
              <p className="mb-2 text-xs font-semibold text-sky-400">
                Audio Modulado ({result.fase3_4.manifest.audio_duration_s} s)
              </p>
              <audio controls preload="metadata" className="h-9 w-full min-w-0 max-w-full" src={result.fase3_4.modulated_wav_url} />
            </div>
            <div className="min-w-0 overflow-hidden rounded-xl border border-emerald-500/20 bg-zinc-950/85 p-3.5">
              <p className="mb-2 text-xs font-semibold text-emerald-400">
                Audio Demodulado (Banda Base)
              </p>
              <audio controls preload="metadata" className="h-9 w-full min-w-0 max-w-full" src={result.fase3_4.demodulated_wav_url} />
            </div>
            <div className="min-w-0 overflow-hidden rounded-xl border border-white/10 bg-zinc-950/85 p-3.5">
              <p className="mb-2 text-xs font-semibold text-zinc-200">Audio Original Scanline 1D</p>
              <audio controls preload="metadata" className="h-9 w-full min-w-0 max-w-full" src={result.fase5.orig_audio_wav_url} />
            </div>
            {result.fase5.reconstructed_audio_wav_url && (
              <div className="min-w-0 overflow-hidden rounded-xl border border-amber-500/20 bg-zinc-950/85 p-3.5">
                <p className="mb-2 text-xs font-semibold text-amber-400">
                  Audio Reconstruido DAC
                </p>
                <audio
                  controls
                  preload="metadata"
                  className="h-9 w-full min-w-0 max-w-full"
                  src={result.fase5.reconstructed_audio_wav_url}
                />
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-white/10 bg-zinc-900/75 p-5 backdrop-blur-md">
            {result.fase3_4.constellation_iq.length > 0 && (
              <ConstellationPlot
                title="Constelación I/Q Recibida"
                points={result.fase3_4.constellation_iq}
              />
            )}
            {result.fase5.reconstructed_svg && (
              <div className="rounded-xl border border-white/10 bg-zinc-950/85 p-3">
                <p className="mb-2 text-xs font-semibold text-zinc-200">
                  Salida Vectorial SVG en vivo
                </p>
                <div
                  className="flex max-h-40 justify-center overflow-hidden [&>svg]:h-36 [&>svg]:w-auto"
                  dangerouslySetInnerHTML={{ __html: result.fase5.reconstructed_svg }}
                />
              </div>
            )}
            <div className="flex flex-wrap gap-2.5">
              <button
                type="button"
                onClick={() =>
                  downloadBase64(
                    result.fase5.peer_zip_b64,
                    "paquete_envio_companero.zip",
                    "application/zip"
                  )
                }
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-4 py-2.5 text-xs font-semibold text-zinc-950 transition hover:-translate-y-0.5 hover:bg-emerald-400 active:scale-[0.98]"
              >
                <Download className="h-3.5 w-3.5" /> Descargar ZIP Compañero
              </button>
              <button
                type="button"
                onClick={() =>
                  downloadBase64(
                    result.fase5.dspimg_b64,
                    "paquete_comprimido.dspimg",
                    "application/octet-stream"
                  )
                }
                className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-zinc-950/80 px-4 py-2.5 text-xs font-semibold text-zinc-100 transition hover:-translate-y-0.5 hover:border-white/30 active:scale-[0.98]"
              >
                <Download className="h-3.5 w-3.5 text-sky-400" /> Descargar .dspimg
              </button>
            </div>
          </div>
        </div>
      )}

      <ImageLightboxDialog asset={inspectAsset} onClose={() => setInspectAsset(null)} />
    </div>
  );
}
