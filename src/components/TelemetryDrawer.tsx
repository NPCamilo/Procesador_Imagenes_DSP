"use client";

import React, { useEffect, useRef } from "react";
import { CheckCircle2, X } from "lucide-react";
import type { DemoData } from "@/types/dsp";

export type TelemetryFocus = "spectral" | "digital" | "rf" | "all";

interface TelemetryDrawerProps {
  open: boolean;
  focus: TelemetryFocus;
  data: DemoData;
  onClose: () => void;
}

export function TelemetryDrawer({
  open,
  focus,
  data,
  onClose,
}: TelemetryDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const { fase1, fase2, fase3_4_5 } = data;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
      className="fixed inset-y-0 right-0 m-0 ml-auto h-full max-h-none w-[min(100vw,540px)] rounded-l-2xl border-l border-(--hairline) bg-(--surface-elevated) p-0 text-(--ink) shadow-2xl"
    >
      <div className="flex h-full flex-col">
        <header className="flex items-center justify-between border-b border-(--hairline) px-6 py-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-sky-500">
              Ficha Técnica · Datos Explícitos DSP
            </p>
            <h2 className="font-display text-lg font-bold text-(--ink)">
              Telemetría y Trama Digital
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar ficha técnica"
            className="rounded-lg border border-(--hairline) bg-(--surface) p-2 text-(--ink-muted) transition hover:text-(--ink) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6 text-xs">
          {/* Block 1: Spectral & Red Segmentation */}
          <section
            className={`space-y-3 ${
              focus === "spectral" ? "rounded-xl ring-1 ring-sky-500/40 p-3 -m-3" : ""
            }`}
          >
            <h3 className="font-mono text-[11px] uppercase tracking-widest text-sky-500">
              01 · Muestreo Espacial & Segmentación HSV
            </h3>
            <dl className="divide-y divide-(--hairline) border-y border-(--hairline)">
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Resolución captura</dt>
                <dd className="font-mono font-medium">
                  {fase1.sampling.width_px}×{fase1.sampling.height_px} (
                  {fase1.sampling.total_pixels.toLocaleString()} px)
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">fs espacial / Nyquist</dt>
                <dd className="font-mono font-medium">
                  {fase1.sampling.spatial_sampling_rate_px} px⁻¹ /{" "}
                  {fase1.sampling.spatial_nyquist_limit_cycles_per_px} cyc/px
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">f_max espacial</dt>
                <dd className="font-mono font-medium">
                  {fase1.sampling.f_max_spatial_cycles_per_px} cyc/px
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Equivalente 1D Scanline</dt>
                <dd className="font-mono font-medium">
                  {fase1.sampling.equivalent_1d_sample_rate_hz.toLocaleString()} Hz (f_max{" "}
                  {fase1.sampling.f_max_1d_hz} Hz)
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Veredicto Nyquist</dt>
                <dd className="font-mono font-medium text-emerald-600 dark:text-emerald-400">
                  {fase1.sampling.nyquist_1d_verdict}
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Componentes rojas conexas</dt>
                <dd className="font-mono font-medium">
                  {fase1.red_filter.num_components} regiones · Top:{" "}
                  {fase1.red_filter.largest_area_px.toLocaleString()} px (
                  {fase1.red_filter.largest_area_percent}%)
                </dd>
              </div>
            </dl>
          </section>

          {/* Block 2: Quantization & Raw Stream */}
          <section
            className={`space-y-3 ${
              focus === "digital" ? "rounded-xl ring-1 ring-amber-500/40 p-3 -m-3" : ""
            }`}
          >
            <h3 className="font-mono text-[11px] uppercase tracking-widest text-amber-500">
              02 · Resolución [Byte / Bit] & Códec
            </h3>
            <dl className="divide-y divide-(--hairline) border-y border-(--hairline)">
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Resolución de trabajo</dt>
                <dd className="font-mono font-medium">{fase2.working_resolution}</dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Stream 4 bits / muestra</dt>
                <dd className="font-mono font-medium">
                  {fase2.stream_4bits.total_bytes.toLocaleString()} B (
                  {fase2.stream_4bits.total_bits.toLocaleString()} bits)
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">SQNR Empírica / Teórica</dt>
                <dd className="font-mono font-medium">
                  {fase2.stream_4bits.sqnr_empirical_db} dB /{" "}
                  {fase2.stream_4bits.sqnr_theoretical_db} dB
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">DPCM + Zlib (Lossless)</dt>
                <dd className="font-mono font-medium">
                  {fase2.compression_lossless.ratio}× ({fase2.compression_lossless.savings_percent}% ·{" "}
                  {fase2.compression_lossless.compressed_bytes.toLocaleString()} B)
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">DCT 8×8 + Zlib (Lossy)</dt>
                <dd className="font-mono font-medium">
                  {fase2.compression_dct.ratio}× ({fase2.compression_dct.savings_percent}% · PSNR{" "}
                  {fase2.compression_dct.psnr_db} dB)
                </dd>
              </div>
            </dl>

            <div className="rounded-xl border border-(--hairline) bg-(--surface) p-3.5 font-mono text-[11px]">
              <p className="text-(--ink-muted)">BIN[0..63]</p>
              <p className="mt-1 break-all text-sky-600 dark:text-sky-300">
                {fase2.stream_4bits.first_64_bits}
              </p>
              <p className="mt-2.5 text-(--ink-muted)">HEX[0..N]</p>
              <p className="mt-1 break-all text-amber-600 dark:text-amber-300">
                {fase2.stream_4bits.first_bytes_hex}
              </p>
            </div>
          </section>

          {/* Block 3: Transceiver & Image/Audio Fidelity */}
          <section
            className={`space-y-3 ${
              focus === "rf" ? "rounded-xl ring-1 ring-emerald-500/40 p-3 -m-3" : ""
            }`}
          >
            <h3 className="font-mono text-[11px] uppercase tracking-widest text-emerald-500">
              03 · Enlace RF, CRC32 & Fidelidad
            </h3>
            <dl className="divide-y divide-(--hairline) border-y border-(--hairline)">
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Esquema / Tasa muestreo</dt>
                <dd className="font-mono font-medium">
                  {fase3_4_5.tx_manifest.scheme} @{" "}
                  {fase3_4_5.tx_manifest.sampling_rate_hz.toLocaleString()} Hz (
                  {fase3_4_5.tx_manifest.audio_duration_s} s)
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Sync offset / BER BFSK / 16-QAM</dt>
                <dd className="font-mono font-medium">
                  {fase3_4_5.sync_offset_samples} · {fase3_4_5.ber_bfsk} · {fase3_4_5.qam_ber}
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Integridad CRC32</dt>
                <dd className="inline-flex items-center gap-1 font-mono font-medium text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" /> {fase3_4_5.tx_manifest.crc32_hex}
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">PSNR / SSIM / MSE / Pearson</dt>
                <dd className="font-mono font-medium">
                  {fase3_4_5.image_metrics.psnr_db} dB · {fase3_4_5.image_metrics.ssim} ·{" "}
                  {fase3_4_5.image_metrics.mse} · {fase3_4_5.image_metrics.pearson_corr}
                </dd>
              </div>
              <div className="flex justify-between py-2">
                <dt className="text-(--ink-muted)">Audio SNR / Pearson r / RMSE</dt>
                <dd className="font-mono font-medium">
                  {fase3_4_5.audio_metrics.snr_db} dB · {fase3_4_5.audio_metrics.pearson_corr} ·{" "}
                  {fase3_4_5.audio_metrics.rmse}
                </dd>
              </div>
            </dl>
          </section>
        </div>
      </div>
    </dialog>
  );
}
