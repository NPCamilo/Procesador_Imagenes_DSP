"use client";

import React, { useState } from "react";
import { Radio, Upload, Loader2, CheckCircle2, AlertTriangle, Download } from "lucide-react";
import type { PeerRxResponse } from "@/types/dsp";
import { ConstellationPlot, SignalPolylinePlot } from "./SignalSvgPlot";

export function PeerReceiver() {
  const [file, setFile] = useState<File | null>(null);
  const [scheme, setScheme] = useState("BFSK");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PeerRxResponse | null>(null);

  async function handleReceive(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Selecciona primero un archivo .wav, .dspimg o .zip enviado por tu compañero.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("scheme", scheme);
      const res = await fetch("/api/rx/demodulate", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "No se pudo demodular el archivo");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado");
    } finally {
      setLoading(false);
    }
  }

  function downloadSvg() {
    if (!result) return;
    const blob = new Blob([result.reconstructed_svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "imagen_demodulada.svg";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleReceive}
        className="grid gap-4 rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 md:grid-cols-3"
      >
        <div className="md:col-span-2">
          <label className="mb-1 block text-xs font-medium text-zinc-300">
            Archivo recibido de compañero (.wav modulado, .dspimg o .zip completo)
          </label>
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-300 hover:border-emerald-500">
            <Upload className="h-4 w-4 text-emerald-400" />
            <span>{file ? file.name : "Subir senal_modulada.wav, paquete.dspimg o paquete_envio_companero.zip"}</span>
            <input
              type="file"
              accept=".wav,.dspimg,.zip"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-zinc-300">Esquema (si es .wav suelto)</label>
          <select
            value={scheme}
            onChange={(e) => setScheme(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-xs text-zinc-100"
          >
            <option value="BFSK">BFSK</option>
            <option value="MFSK">MFSK</option>
            <option value="ASK">ASK</option>
            <option value="BPSK">BPSK</option>
            <option value="16-QAM">16-QAM</option>
          </select>
        </div>

        <div className="flex justify-end md:col-span-3">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />}
            {loading ? "Demodulando y Reconstruyendo..." : "Demodular y Reconstruir Imagen"}
          </button>
        </div>
      </form>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/60 p-4 text-xs text-red-200">{error}</div>
      )}

      {result && (
        <div className="space-y-6 rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
              {result.summary.crc_valid ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-400" />
              )}
              <span>
                Modo: {result.summary.mode} · Resolución: {result.summary.reconstructed_resolution.join("×")} px · Sync offset: {result.summary.sync_offset_samples} muestras
              </span>
            </div>
            <div className="flex gap-2">
              <a
                href={result.reconstructed_png}
                download="imagen_demodulada.png"
                className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-100 hover:bg-zinc-700"
              >
                <Download className="h-3.5 w-3.5" /> PNG
              </a>
              <button
                type="button"
                onClick={downloadSvg}
                className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-xs text-zinc-100 hover:bg-zinc-700"
              >
                <Download className="h-3.5 w-3.5" /> SVG
              </button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <p className="mb-2 text-xs font-semibold text-zinc-300">Imagen Recuperada (PNG)</p>
              <img src={result.reconstructed_png} alt="Demodulada PNG" className="mx-auto max-h-72 rounded" />
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-4">
              <p className="mb-2 text-xs font-semibold text-zinc-300">Imagen Recuperada (SVG Vectorial)</p>
              <div
                className="flex max-h-72 justify-center overflow-hidden [&>svg]:max-h-64 [&>svg]:w-auto"
                dangerouslySetInnerHTML={{ __html: result.reconstructed_svg }}
              />
            </div>
          </div>

          <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
            <p className="mb-1 text-xs font-semibold text-emerald-400">Audio Reconstruido desde Datos Demodulados</p>
            <audio controls className="w-full" src={result.reconstructed_audio_wav_url} />
          </div>

          {result.demodulated_zoom.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              <SignalPolylinePlot
                title="Banda Base Demodulada (Zoom)"
                values={result.demodulated_zoom}
                strokeColor="#009E73"
                minY={-1}
                maxY={1}
              />
              {result.constellation_iq.length > 0 && (
                <ConstellationPlot title="Constelación RX" points={result.constellation_iq} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
