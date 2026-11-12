"use client";

import { useEffect, useRef } from "react";

interface AsciiSignalBackdropProps {
  active?: boolean;
}

const ASCII_RAMP = " .:-=+*#%@";

export function AsciiSignalBackdrop({ active = true }: AsciiSignalBackdropProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    let animId = 0;
    let width = 0;
    let height = 0;
    let cols = 0;
    let rows = 0;
    const cell = 22;

    const pointer = {
      x: 0.5,
      y: 0.35,
      targetX: 0.5,
      targetY: 0.35,
      energy: 0,
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.font = '600 12px "JetBrains Mono", ui-monospace, monospace';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      cols = Math.ceil(width / cell) + 1;
      rows = Math.ceil(height / cell) + 1;
    };

    const drawFrame = (timeSec: number) => {
      ctx.clearRect(0, 0, width, height);

      pointer.x += (pointer.targetX - pointer.x) * 0.08;
      pointer.y += (pointer.targetY - pointer.y) * 0.08;
      pointer.energy *= 0.96;

      const px = pointer.x * width;
      const py = pointer.y * height;

      for (let r = 0; r < rows; r++) {
        const y = r * cell + cell * 0.5;
        for (let c = 0; c < cols; c++) {
          const x = c * cell + cell * 0.5;

          const dx = x - px;
          const dy = y - py;
          const dist = Math.sqrt(dx * dx + dy * dy);

          // Superposition of a drifting carrier + radial pointer interference ripple
          const carrier =
            Math.sin(c * 0.22 + timeSec * 1.15) *
            Math.cos(r * 0.19 - timeSec * 0.85);
          const harmonic = Math.sin((c + r) * 0.12 - timeSec * 0.7) * 0.45;
          const ripple =
            dist < 320
              ? Math.sin(dist * 0.045 - timeSec * 4.5) *
                (1 - dist / 320) *
                (0.75 + pointer.energy * 0.65)
              : 0;

          const amplitude = (carrier + harmonic + ripple + 1.45) / 2.9;
          const clamped = Math.max(0, Math.min(0.999, amplitude));
          const charIdx = Math.floor(clamped * ASCII_RAMP.length);

          if (charIdx <= 1) continue;

          const ch = ASCII_RAMP[charIdx];
          const isBoosted = dist < 240 && charIdx >= 6;
          ctx.fillStyle = isBoosted
            ? "rgba(56, 189, 248, 0.34)"
            : charIdx >= 7
              ? "rgba(244, 63, 94, 0.22)"
              : `rgba(161, 161, 170, ${(0.06 + clamped * 0.14).toFixed(3)})`;
          ctx.fillText(ch, x, y);
        }
      }
    };

    const onPointerMove = (e: PointerEvent) => {
      if (width <= 0 || height <= 0) return;
      pointer.targetX = e.clientX / width;
      pointer.targetY = e.clientY / height;
      pointer.energy = 1;
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove, { passive: true });

    if (!active || mediaQuery.matches) {
      drawFrame(0.8);
      return () => {
        window.removeEventListener("resize", resize);
        window.removeEventListener("pointermove", onPointerMove);
      };
    }

    let lastRender = 0;
    const loop = (now: number) => {
      // Cap around ~30fps for ultra-low CPU overhead while scrolling/computing
      if (now - lastRender >= 33) {
        drawFrame(now * 0.001);
        lastRender = now;
      }
      animId = window.requestAnimationFrame(loop);
    };

    animId = window.requestAnimationFrame(loop);

    return () => {
      window.cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
    };
  }, [active]);

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-zinc-950 [contain:strict]"
    >
      {/* Tier 1: Subtle technical grid masked toward viewport center */}
      <div className="absolute inset-0 bg-[radial-gradient(#ffffff12_1px,transparent_1px)] [background-size:24px_24px] [mask-image:radial-gradient(ellipse_75%_65%_at_50%_20%,#000_55%,transparent_100%)]" />

      {/* Tier 2: Interactive ASCII RF Interference Matrix */}
      <canvas
        ref={canvasRef}
        className={`absolute inset-0 transition-opacity duration-500 [mask-image:radial-gradient(ellipse_85%_80%_at_50%_35%,#000_50%,transparent_100%)] ${
          active ? "opacity-100" : "opacity-35"
        }`}
      />

      {/* Tier 3: Atmospheric radial glow orbs (Backgrounds Supply) */}
      <div className="absolute -left-32 -top-40 h-[520px] w-[520px] rounded-full bg-sky-500/12 blur-[130px]" />
      <div className="absolute -right-24 top-16 h-[460px] w-[460px] rounded-full bg-red-600/10 blur-[140px]" />
      <div className="absolute bottom-0 left-1/3 h-[380px] w-[560px] rounded-full bg-emerald-500/8 blur-[140px]" />

      {/* Tier 4: Monochromatic SVG Fractal Noise Texture (prevents gradient banding) */}
      <svg className="absolute inset-0 h-full w-full opacity-[0.03] mix-blend-overlay">
        <filter id="dsp-noise-grain">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.82"
            numOctaves="3"
            stitchTiles="stitch"
          />
        </filter>
        <rect width="100%" height="100%" filter="url(#dsp-noise-grain)" />
      </svg>
    </div>
  );
}
