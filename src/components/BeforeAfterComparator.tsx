"use client";

import { useState } from "react";

interface BeforeAfterComparatorProps {
  beforeSrc: string;
  afterSrc: string;
  beforeLabel?: string;
  afterLabel?: string;
  resolutionText: string;
  redPercent: number;
  componentsCount: number;
  onInspectImage?: (src: string, title: string, caption?: string) => void;
}

export function BeforeAfterComparator({
  beforeSrc,
  afterSrc,
  beforeLabel = "Señal Original RGB",
  afterLabel = "Filtro Rojo Dominante",
  resolutionText,
  redPercent,
  componentsCount,
  onInspectImage,
}: BeforeAfterComparatorProps) {
  const [split, setSplit] = useState(54);

  return (
    <div className="group relative [perspective:1200px]">
      {/* Halftone / Dither corner matrix accent behind hardware frame (Ditther skill) */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-4 -top-4 h-36 w-36 rounded-3xl bg-[radial-gradient(#38bdf8_1px,transparent_1px)] opacity-25 [background-size:6px_6px] [mask-image:radial-gradient(circle_at_top_right,#000_25%,transparent_75%)]"
      />

      {/* 3D Perspective Hardware Studio Frame (Ultramock skill) */}
      <div className="relative overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/90 shadow-[0_32px_90px_-18px_rgba(0,0,0,0.85)] backdrop-blur-md transition-transform duration-700 ease-out [transform-style:preserve-3d] [transform:rotateX(5deg)_rotateY(-5deg)] group-hover:[transform:rotateX(0deg)_rotateY(0deg)]">
        {/* Specular top highlight rim */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-20 rounded-2xl bg-gradient-to-tr from-transparent via-white/[0.03] to-white/[0.11]"
        />

        {/* Studio Chassis Titlebar */}
        <div className="relative z-10 flex items-center justify-between border-b border-white/10 bg-zinc-950/80 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
            <span className="ml-2 font-mono text-[11px] tracking-wider text-zinc-400">
              dsp://selfie_dsp.jpeg · {resolutionText}
            </span>
          </div>
          <span className="rounded-full border border-sky-400/30 bg-sky-500/10 px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-widest text-sky-300">
            {componentsCount} comp · {redPercent}%
          </span>
        </div>

        {/* Interactive Split Comparison Viewport */}
        <div className="relative aspect-[3/4] max-h-[420px] w-full select-none overflow-hidden bg-zinc-950">
          {/* Base Layer: Filtered Dominant Red */}
          <img
            src={afterSrc}
            alt={afterLabel}
            className="h-full w-full object-cover"
            draggable={false}
          />

          {/* Overlay Layer clipped to split %: Original RGB */}
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
          >
            <img
              src={beforeSrc}
              alt={beforeLabel}
              className="h-full w-full object-cover"
              draggable={false}
            />
          </div>

          {/* Vertical Divider Line + Handle */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute bottom-0 top-0 z-10 w-0.5 bg-white/90 shadow-[0_0_16px_rgba(255,255,255,0.75)]"
            style={{ left: `${split}%` }}
          >
            <div className="absolute left-1/2 top-1/2 flex h-9 w-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/40 bg-zinc-950/90 font-mono text-xs text-zinc-100 shadow-lg backdrop-blur">
              ⇄
            </div>
          </div>

          {/* Corner Labels */}
          <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-md border border-white/15 bg-zinc-950/80 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-zinc-200 backdrop-blur-sm">
            {beforeLabel}
          </div>
          <div className="pointer-events-none absolute right-3 top-3 z-10 rounded-md border border-red-400/25 bg-zinc-950/80 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-red-200 backdrop-blur-sm">
            {afterLabel}
          </div>

          {/* Invisible accessible range input covering viewport for smooth drag + keyboard */}
          <input
            type="range"
            min={5}
            max={95}
            value={split}
            aria-label="Comparar imagen original RGB frente a filtro rojo dominante"
            onChange={(e) => setSplit(Number(e.target.value))}
            className="absolute inset-0 z-30 h-full w-full cursor-ew-resize opacity-0"
          />
        </div>

        {/* Bottom Studio Control Bar */}
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 border-t border-white/10 bg-zinc-950/85 px-4 py-2.5">
          <span className="font-mono text-[11px] text-zinc-400">
            Arrastra horizontalmente ({split}% / {100 - split}%)
          </span>
          {onInspectImage && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() =>
                  onInspectImage(
                    beforeSrc,
                    beforeLabel,
                    `Captura fuente sin procesar · ${resolutionText}`
                  )
                }
                className="rounded-md border border-white/10 bg-zinc-800/80 px-2.5 py-1 text-xs font-medium text-zinc-200 transition hover:-translate-y-0.5 hover:border-white/25 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              >
                Ampliar RGB
              </button>
              <button
                type="button"
                onClick={() =>
                  onInspectImage(
                    afterSrc,
                    afterLabel,
                    `Región roja conexa más grande (${componentsCount} componentes detectados, ${redPercent}% del área)`
                  )
                }
                className="rounded-md border border-red-500/25 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-200 transition hover:-translate-y-0.5 hover:bg-red-500/20 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
              >
                Ampliar Filtro
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
