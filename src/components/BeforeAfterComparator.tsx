"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Play, Sparkles } from "lucide-react";
import { OptimizedPicture } from "./OptimizedPicture";

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

type CropMode = "portrait" | "native" | "contain";

const CROP_CONFIG: Record<
  CropMode,
  { label: string; frameClass: string; imgClass: string }
> = {
  portrait: {
    label: "Encuadre 4:5",
    frameClass: "aspect-[4/5] max-h-[450px]",
    imgClass: "object-cover object-[50%_20%]",
  },
  native: {
    label: "Sensor 3:4",
    frameClass: "aspect-[3/4] max-h-[450px]",
    imgClass: "object-cover object-center",
  },
  contain: {
    label: "Completa",
    frameClass: "aspect-[3/4] max-h-[450px]",
    imgClass: "object-contain bg-zinc-950",
  },
};

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
  const [cropMode, setCropMode] = useState<CropMode>("portrait");
  const [sweeping, setSweeping] = useState(false);

  const frameRef = useRef<HTMLDivElement | null>(null);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const readoutRef = useRef<HTMLSpanElement | null>(null);

  const stateRef = useRef({
    split: 54,
    targetSplit: 54,
    dragging: false,
    tiltX: 2.5,
    tiltY: -3.5,
    targetTiltX: 2.5,
    targetTiltY: -3.5,
    sweepStart: 0,
    sweeping: false,
  });

  const rafRef = useRef<number | null>(null);

  const applyVars = useCallback(() => {
    const s = stateRef.current;
    const viewport = viewportRef.current;
    const frame = frameRef.current;
    const readout = readoutRef.current;

    if (viewport) {
      viewport.style.setProperty("--split", `${s.split.toFixed(2)}%`);
      viewport.setAttribute("aria-valuenow", String(Math.round(s.split)));
    }
    if (frame) {
      frame.style.setProperty("--rx", `${s.tiltX.toFixed(2)}deg`);
      frame.style.setProperty("--ry", `${s.tiltY.toFixed(2)}deg`);
    }
    if (readout) {
      const leftPct = Math.round(s.split);
      readout.textContent = `${leftPct}% RGB / ${100 - leftPct}% Rojo`;
    }
  }, []);

  const startLoop = useCallback(() => {
    if (rafRef.current !== null) return;

    const tick = (now: number) => {
      const s = stateRef.current;

      if (s.sweeping) {
        if (s.sweepStart === 0) s.sweepStart = now;
        const elapsed = (now - s.sweepStart) / 1000;
        const duration = 2.2;
        if (elapsed >= duration) {
          s.sweeping = false;
          s.targetSplit = 54;
          setSweeping(false);
        } else {
          // Smooth sinusoidal sweep across 18% <-> 84% and back to 54%
          const p = elapsed / duration;
          s.targetSplit = 54 - Math.sin(p * Math.PI * 2) * 34;
        }
      }

      const dSplit = s.targetSplit - s.split;
      const dTx = s.targetTiltX - s.tiltX;
      const dTy = s.targetTiltY - s.tiltY;

      s.split += dSplit * 0.24;
      s.tiltX += dTx * 0.14;
      s.tiltY += dTy * 0.14;

      applyVars();

      const settled =
        !s.sweeping &&
        !s.dragging &&
        Math.abs(dSplit) < 0.04 &&
        Math.abs(dTx) < 0.03 &&
        Math.abs(dTy) < 0.03;

      if (settled) {
        s.split = s.targetSplit;
        s.tiltX = s.targetTiltX;
        s.tiltY = s.targetTiltY;
        applyVars();
        rafRef.current = null;
        return;
      }

      rafRef.current = window.requestAnimationFrame(tick);
    };

    rafRef.current = window.requestAnimationFrame(tick);
  }, [applyVars]);

  useEffect(() => {
    applyVars();
    return () => {
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current);
      }
    };
  }, [applyVars]);

  const updateSplitFromClientX = (clientX: number) => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const rect = viewport.getBoundingClientRect();
    if (rect.width <= 0) return;
    const pct = ((clientX - rect.left) / rect.width) * 100;
    const clamped = Math.max(4, Math.min(96, pct));
    stateRef.current.targetSplit = clamped;
    if (stateRef.current.dragging) {
      stateRef.current.split = clamped;
      applyVars();
    } else {
      startLoop();
    }
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    stateRef.current.sweeping = false;
    setSweeping(false);
    stateRef.current.dragging = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    updateSplitFromClientX(e.clientX);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0 && window.matchMedia("(hover: hover)").matches) {
      const nx = (e.clientX - rect.left) / rect.width - 0.5;
      const ny = (e.clientY - rect.top) / rect.height - 0.5;
      stateRef.current.targetTiltX = -ny * 5;
      stateRef.current.targetTiltY = nx * 6;
      startLoop();
    }
    if (stateRef.current.dragging) {
      updateSplitFromClientX(e.clientX);
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    stateRef.current.dragging = false;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // Ignore if capture already released
    }
  };

  const handlePointerLeave = () => {
    stateRef.current.dragging = false;
    stateRef.current.targetTiltX = 2.5;
    stateRef.current.targetTiltY = -3.5;
    startLoop();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      stateRef.current.targetSplit = Math.max(4, stateRef.current.targetSplit - 4);
      startLoop();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      stateRef.current.targetSplit = Math.min(96, stateRef.current.targetSplit + 4);
      startLoop();
    }
  };

  const triggerSweep = () => {
    stateRef.current.sweeping = true;
    stateRef.current.sweepStart = 0;
    setSweeping(true);
    startLoop();
  };

  const activeCrop = CROP_CONFIG[cropMode];

  return (
    <div className="group relative min-w-0 max-w-full [perspective:1200px]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-3xl bg-[radial-gradient(#38bdf8_1px,transparent_1px)] opacity-25 [background-size:6px_6px] [mask-image:radial-gradient(circle_at_top_right,#000_25%,transparent_75%)] sm:-right-4 sm:-top-4 sm:h-36 sm:w-36"
      />

      {/* 3D Perspective Studio Frame driven by GPU CSS vars (--rx / --ry) */}
      <div
        ref={frameRef}
        onPointerLeave={handlePointerLeave}
        className="relative overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/95 shadow-[0_28px_80px_-18px_rgba(0,0,0,0.85)] will-change-transform md:[transform-style:preserve-3d] md:[transform:rotateX(var(--rx,2.5deg))_rotateY(var(--ry,-3.5deg))]"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-20 rounded-2xl bg-gradient-to-tr from-transparent via-white/[0.03] to-white/[0.11]"
        />

        {/* Studio Chassis Header */}
        <div className="relative z-10 flex items-center justify-between gap-2 border-b border-white/10 bg-zinc-950/90 px-3 py-2.5 sm:px-4">
          <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-red-500/85" />
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-amber-400/85" />
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-400/85" />
            <span className="ml-1 truncate font-mono text-[10px] tracking-wider text-zinc-400 sm:ml-2 sm:text-[11px]">
              dsp://selfie_dsp.jpeg · {resolutionText}
            </span>
          </div>
          <span className="shrink-0 rounded-full border border-sky-400/30 bg-sky-500/10 px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-widest text-sky-300">
            {componentsCount} comp · {redPercent}%
          </span>
        </div>

        {/* Crop Mode & Sweep Controls Bar */}
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 border-b border-white/10 bg-zinc-950/60 px-3 py-2 sm:px-4">
          <div className="flex items-center gap-1" role="group" aria-label="Modo de recorte">
            {(Object.keys(CROP_CONFIG) as CropMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setCropMode(mode)}
                className={`rounded-lg px-2 py-1 font-mono text-[10px] font-medium transition active:scale-[0.97] ${
                  cropMode === mode
                    ? "bg-sky-500 text-zinc-950"
                    : "text-zinc-400 hover:bg-white/10 hover:text-zinc-200"
                }`}
              >
                {CROP_CONFIG[mode].label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={triggerSweep}
            disabled={sweeping}
            className="inline-flex items-center gap-1 rounded-lg border border-white/15 bg-zinc-900 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-zinc-200 transition hover:border-sky-400/50 hover:text-white active:scale-[0.97] disabled:opacity-60"
          >
            {sweeping ? (
              <Sparkles className="h-3 w-3 text-sky-400" />
            ) : (
              <Play className="h-3 w-3 text-sky-400" />
            )}
            {sweeping ? "Barriendo..." : "Barrido"}
          </button>
        </div>

        {/* Zero-Re-Render 120fps Interactive Split Comparison Viewport */}
        <div
          ref={viewportRef}
          role="slider"
          tabIndex={0}
          aria-label="Comparar imagen original RGB frente a filtro rojo dominante"
          aria-valuemin={4}
          aria-valuemax={96}
          aria-valuenow={54}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onKeyDown={handleKeyDown}
          style={{ touchAction: "none" }}
          className={`relative mx-auto w-full cursor-ew-resize select-none overflow-hidden bg-zinc-950 transition-[aspect-ratio] duration-500 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${activeCrop.frameClass}`}
        >
          {/* Base Layer: Filtered Dominant Red */}
          <OptimizedPicture
            src={afterSrc}
            alt={afterLabel}
            priority
            draggable={false}
            className={`h-full w-full transition-[object-position] duration-500 ${activeCrop.imgClass}`}
          />

          {/* Overlay Layer clipped via GPU clip-path CSS var */}
          <div
            aria-hidden="true"
            style={{ clipPath: "inset(0 calc(100% - var(--split, 54%)) 0 0)" }}
            className="pointer-events-none absolute inset-0 will-change-[clip-path]"
          >
            <OptimizedPicture
              src={beforeSrc}
              alt={beforeLabel}
              priority
              draggable={false}
              className={`h-full w-full transition-[object-position] duration-500 ${activeCrop.imgClass}`}
            />
          </div>

          {/* 100% GPU Transform Divider Slider (0 layout reflow!) */}
          <div
            aria-hidden="true"
            style={{ transform: "translate3d(var(--split, 54%), 0, 0)" }}
            className="pointer-events-none absolute inset-0 z-10 will-change-transform"
          >
            <div className="relative h-full w-0.5 -translate-x-1/2 bg-white/95 shadow-[0_0_18px_rgba(255,255,255,0.8)]">
              <div className="absolute left-1/2 top-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/45 bg-zinc-950/90 font-mono text-xs text-zinc-100 shadow-xl backdrop-blur-sm">
                ⇄
              </div>
            </div>
          </div>

          {/* Corner Labels */}
          <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-md border border-white/15 bg-zinc-950/80 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-zinc-200 backdrop-blur-sm">
            {beforeLabel}
          </div>
          <div className="pointer-events-none absolute right-3 top-3 z-10 rounded-md border border-red-400/25 bg-zinc-950/80 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-red-200 backdrop-blur-sm">
            {afterLabel}
          </div>
        </div>

        {/* Bottom Studio Control Bar */}
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 border-t border-white/10 bg-zinc-950/90 px-4 py-2.5">
          <span ref={readoutRef} className="font-mono text-[11px] text-zinc-400">
            54% RGB / 46% Rojo
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
                className="rounded-lg border border-white/10 bg-zinc-800/80 px-2.5 py-1 text-xs font-medium text-zinc-200 transition hover:-translate-y-0.5 hover:border-white/25 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
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
                className="rounded-lg border border-red-500/25 bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-200 transition hover:-translate-y-0.5 hover:bg-red-500/20 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
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
