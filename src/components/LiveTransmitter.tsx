"use client";

import React, { useState } from "react";
import { Upload, Play, Download, Loader2 } from "lucide-react";
import type { LiveTxResponse } from "@/types/dsp";
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
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSubmit}
        className="grid gap-4 rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 md:grid-cols-4"
      >
        <div className="md:col-span-2">
          <label className="mb-1 block text-xs font-medium text-zinc-300">
            Fotografía JPG / JPEG / PNG (opcional — si se omite usa Selfie DSP)
          </label>
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-300 hover:border-sky-500">
            <Upload className="h-4 w-4 text-sky-400" />
            <span>{file ? file.name : "Seleccionar fotografía o usar Selfie DSP por defecto"}</span>
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-300">Esquema de Modulación</label>
          <select
            value={scheme}
            onChange={(e) => setScheme(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
          >
            <option value="BFSK">BFSK (1500 bps)</option>
            <option value="MFSK">MFSK 4-FSK (2000 bps)</option>
            <option value="ASK">ASK (1500 bps)</option>
            <option value="BPSK">BPSK (1500 bps)</option>
            <option value="16-QAM">16-QAM (6000 bps)</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-300">Compresión</label>
          <select
            value={compression}
            onChange={(e) => setCompression(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
          >
            <option value="lossy_dct_zlib">DCT 8×8 + Zlib (Alta compresión)</option>
            <option value="lossless_dpcm_zlib">DPCM + Zlib (Sin pérdida)</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-300">Resolución [Byte/Bit]: {bits} bits</label>
          <input
            type="range"
            min={1}
            max={8}
            value={bits}
            onChange={(e) => setBits(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-300">Calidad DCT: {quality}</label>
          <input
            type="range"
            min={25}
            max={95}
            value={quality}
            onChange={(e) => setQuality(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-300">
            Resolución TX ({txDim} px) & Aliasing NQS ({nqsFactor}×)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              min={32}
              max={88}
              value={txDim}
              onChange={(e) => setTxDim(Number(e.target.value))}
              className="w-1/2 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-100"
            />
            <input
              type="number"
              min={2}
              max={16}
              value={nqsFactor}
              onChange={(e) => setNqsFactor(Number(e.target.value))}
              className="w-1/2 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs text-zinc-100"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-300">Ruido AWGN SNR (dB, opcional)</label>
          <input
            type="text"
            placeholder="Ideal (vacío) o ej. 16"
            value={snrDb}
            onChange={(e) => setSnrDb(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-100"
          />
        </div>

        <div className="flex items-center justify-between md:col-span-4">
          <label className="flex items-center gap-2 text-xs text-zinc-300">
            <input
              type="checkbox"
              checked={applyRed}
              onChange={(e) => setApplyRed(e.target.checked)}
              className="rounded border-zinc-700"
            />
            Aplicar filtro selectivo de color rojo de mayor área antes de comprimir
          </label>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-xs font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {loading ? "Procesando en Python..." : "Ejecutar Pipeline Completo"}
          </button>
        </div>
      </form>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/60 p-4 text-xs text-red-200">{error}</div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
              <p className="text-[11px] uppercase text-zinc-400">Rojo Mayor Área</p>
              <p className="text-lg font-bold text-zinc-100">{result.fase1.red_filter.largest_area_percent}%</p>
              <p className="text-xs text-zinc-400">{result.fase1.red_filter.num_components} componentes</p>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
              <p className="text-[11px] uppercase text-zinc-400">Compresión {result.fase2.compression.method}</p>
              <p className="text-lg font-bold text-zinc-100">{result.fase2.compression.compression_ratio}×</p>
              <p className="text-xs text-sky-400">{result.fase2.compression.compressed_bytes} Bytes</p>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
              <p className="text-[11px] uppercase text-zinc-400">Canal & Demodulación</p>
              <p className="text-lg font-bold text-zinc-100">
                BER = {result.fase3_4.ber !== null ? result.fase3_4.ber.toExponential(1) : "N/A"}
              </p>
              <p className="text-xs text-emerald-400">
                {result.fase3_4.crc_valid ? "CRC32 OK" : "CRC32 ERROR (Mucho ruido)"}
              </p>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
              <p className="text-[11px] uppercase text-zinc-400">Calidad Reconstruida</p>
              <p className="text-lg font-bold text-zinc-100">
                {result.fase5.metrics ? `${result.fase5.metrics.psnr_db} dB` : "Fallo CRC"}
              </p>
              <p className="text-xs text-amber-400">
                {result.fase5.metrics ? `SSIM ${result.fase5.metrics.ssim}` : "Sin reconstrucción"}
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-5">
            {[
              { label: "Original", src: result.fase1.original_png },
              { label: "Rojo Mayor Área", src: result.fase1.red_splash_png },
              { label: `Aliasing NQS (${nqsFactor}×)`, src: result.fase2.nqs_aliased_png },
              { label: `Cuantizada (${bits} bits)`, src: result.fase2.quantized_png },
              { label: "Reconstruida PNG", src: result.fase5.reconstructed_png || result.fase5.source_tx_png },
            ].map((item) => (
              <figure key={item.label} className="rounded-lg border border-zinc-800 bg-zinc-950 p-2">
                <img src={item.src} alt={item.label} className="h-44 w-full rounded object-contain" />
                <figcaption className="mt-1 text-center text-[11px] text-zinc-300">{item.label}</figcaption>
              </figure>
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

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
              <p className="mb-1 text-xs font-semibold text-sky-400">Audio Modulado ({result.fase3_4.manifest.audio_duration_s} s)</p>
              <audio controls className="w-full" src={result.fase3_4.modulated_wav_url} />
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
              <p className="mb-1 text-xs font-semibold text-emerald-400">Audio Demodulado (Banda Base)</p>
              <audio controls className="w-full" src={result.fase3_4.demodulated_wav_url} />
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
              <p className="mb-1 text-xs font-semibold text-zinc-200">Audio Original Scanline 1D</p>
              <audio controls className="w-full" src={result.fase5.orig_audio_wav_url} />
            </div>
            {result.fase5.reconstructed_audio_wav_url && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                <p className="mb-1 text-xs font-semibold text-amber-400">Audio Reconstruido DAC</p>
                <audio controls className="w-full" src={result.fase5.reconstructed_audio_wav_url} />
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
            {result.fase3_4.constellation_iq.length > 0 && (
              <ConstellationPlot title="Constelación I/Q Recibida" points={result.fase3_4.constellation_iq} />
            )}
            {result.fase5.reconstructed_svg && (
              <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-2">
                <p className="mb-1 text-xs font-semibold text-zinc-200">Salida Vectorial SVG en vivo</p>
                <div
                  className="max-h-40 overflow-hidden [&>svg]:h-36 [&>svg]:w-auto"
                  dangerouslySetInnerHTML={{ __html: result.fase5.reconstructed_svg }}
                />
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => downloadBase64(result.fase5.peer_zip_b64, "paquete_envio_companero.zip", "application/zip")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-500"
              >
                <Download className="h-3.5 w-3.5" /> Descargar ZIP para Compañero
              </button>
              <button
                type="button"
                onClick={() => downloadBase64(result.fase5.dspimg_b64, "paquete_comprimido.dspimg", "application/octet-stream")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-xs font-semibold text-zinc-100 hover:bg-zinc-700"
              >
                <Download className="h-3.5 w-3.5" /> Descargar .dspimg
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
