"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Loader2,
  Maximize2,
  Radio,
  Upload,
} from "lucide-react";
import type { PeerRxResponse } from "@/types/dsp";
import { ImageLightboxDialog, type LightboxAsset } from "./ImageLightboxDialog";
import { ConstellationPlot, SignalPolylinePlot } from "./SignalSvgPlot";

export function PeerReceiver() {
  const [file, setFile] = useState<File | null>(null);
  const [scheme, setScheme] = useState("BFSK");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PeerRxResponse | null>(null);
  const [inspectAsset, setInspectAsset] = useState<LightboxAsset | null>(null);

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
    <div className="min-w-0 space-y-8">
      <form
        onSubmit={handleReceive}
        className="space-y-6 rounded-2xl border border-(--hairline) bg-(--surface) p-5 sm:p-6"
      >
        <div className="border-b border-(--hairline) pb-4">
          <p className="font-mono text-[11px] uppercase tracking-widest text-emerald-600 dark:text-emerald-400">
            Receptor Ciego · Descompresión & Sincronización
          </p>
          <h3 className="mt-0.5 font-display text-xl font-bold text-(--ink)">
            Receptor Compañero (RX)
          </h3>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="min-w-0 md:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-(--ink)">
              Archivo recibido de compañero (.wav modulado, .dspimg o .zip completo)
            </label>
            <label className="flex cursor-pointer items-center gap-2.5 rounded-xl border border-dashed border-(--hairline) bg-(--surface-elevated) px-3.5 py-2.5 text-xs text-(--ink-muted) transition hover:border-emerald-500/60 hover:text-(--ink)">
              <Upload className="h-4 w-4 shrink-0 text-emerald-500" />
              <span className="truncate">
                {file
                  ? file.name
                  : "Subir senal_modulada.wav, paquete.dspimg o paquete_envio_companero.zip"}
              </span>
              <input
                type="file"
                accept=".wav,.dspimg,.zip"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>

          <div className="min-w-0">
            <label className="mb-1.5 block text-xs font-medium text-(--ink)">
              Esquema (si es .wav suelto)
            </label>
            <select
              value={scheme}
              onChange={(e) => setScheme(e.target.value)}
              className="w-full rounded-xl border border-(--hairline) bg-(--surface-elevated) px-3 py-2.5 text-xs text-(--ink) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
            >
              <option value="BFSK">BFSK</option>
              <option value="MFSK">MFSK</option>
              <option value="ASK">ASK</option>
              <option value="BPSK">BPSK</option>
              <option value="16-QAM">16-QAM</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end border-t border-(--hairline) pt-4">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-full bg-emerald-500 px-5 py-2.5 text-xs font-semibold text-zinc-950 transition hover:bg-emerald-400 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />}
            {loading ? "Demodulando y Reconstruyendo..." : "Demodular y Reconstruir Imagen"}
          </button>
        </div>
      </form>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-500/35 bg-red-500/10 p-4 text-xs text-red-700 dark:text-red-200"
        >
          {error}
        </div>
      )}

      {!result && !loading && !error && (
        <div className="rounded-2xl border border-dashed border-(--hairline) bg-(--surface) p-8 text-center">
          <p className="font-display text-sm font-semibold text-(--ink)">
            Esperando paquete de transmisión
          </p>
          <p className="mx-auto mt-1 max-w-xl text-xs leading-relaxed text-(--ink-muted)">
            Descarga <span className="font-mono text-(--ink)">paquete_envio_companero.zip</span> o{" "}
            <span className="font-mono text-(--ink)">.dspimg</span> desde la exhibición o el Lab TX
            y súbelo aquí para reconstruir imagen y audio en vivo.
          </p>
        </div>
      )}

      {result && (
        <div className="animate-reveal space-y-6 rounded-2xl border border-(--hairline) bg-(--surface) p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-(--hairline) pb-4">
            <div className="flex items-center gap-2.5 text-sm font-semibold text-(--ink)">
              {result.summary.crc_valid ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-500" />
              )}
              <span>
                Modo: {result.summary.mode} · Resolución:{" "}
                {result.summary.reconstructed_resolution.join("×")} px · Sync offset:{" "}
                {result.summary.sync_offset_samples} muestras
              </span>
            </div>
            <div className="flex gap-2">
              <a
                href={result.reconstructed_png}
                download="imagen_demodulada.png"
                className="inline-flex items-center gap-1.5 rounded-full border border-(--hairline) bg-(--surface-elevated) px-3.5 py-2 text-xs font-semibold text-(--ink) transition hover:border-sky-500/50"
              >
                <Download className="h-3.5 w-3.5 text-sky-500" /> PNG
              </a>
              <button
                type="button"
                onClick={downloadSvg}
                className="inline-flex items-center gap-1.5 rounded-full border border-(--hairline) bg-(--surface-elevated) px-3.5 py-2 text-xs font-semibold text-(--ink) transition hover:border-emerald-500/50"
              >
                <Download className="h-3.5 w-3.5 text-emerald-500" /> SVG
              </button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <button
              type="button"
              onClick={() =>
                setInspectAsset({ src: result.reconstructed_png, title: "Imagen Recuperada (PNG)" })
              }
              className="group relative rounded-xl border border-(--hairline) bg-zinc-950 p-4 text-left transition hover:border-emerald-500/50"
            >
              <div className="mb-2.5 flex items-center justify-between">
                <p className="text-xs font-semibold text-zinc-200">Imagen Recuperada (PNG)</p>
                <Maximize2 className="h-3.5 w-3.5 text-zinc-400 group-hover:text-emerald-300" />
              </div>
              <img
                src={result.reconstructed_png}
                alt="Demodulada PNG"
                className="mx-auto max-h-72 rounded-lg"
              />
            </button>

            <div className="rounded-xl border border-(--hairline) bg-zinc-950 p-4">
              <p className="mb-2.5 text-xs font-semibold text-zinc-200">
                Imagen Recuperada (SVG Vectorial)
              </p>
              <div
                className="flex max-h-72 justify-center overflow-hidden [&>svg]:max-h-64 [&>svg]:w-auto"
                dangerouslySetInnerHTML={{ __html: result.reconstructed_svg }}
              />
            </div>
          </div>

          <div className="min-w-0 overflow-hidden rounded-xl border border-(--hairline) bg-(--surface-elevated) p-4">
            <p className="mb-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              Audio Reconstruido desde Datos Demodulados
            </p>
            <audio
              controls
              preload="metadata"
              className="h-9 w-full min-w-0 max-w-full"
              src={result.reconstructed_audio_wav_url}
            />
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

      <ImageLightboxDialog asset={inspectAsset} onClose={() => setInspectAsset(null)} />
    </div>
  );
}
