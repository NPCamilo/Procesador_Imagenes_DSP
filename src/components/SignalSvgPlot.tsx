"use client";

import React, { useId, useMemo } from "react";

interface PolylinePlotProps {
  title: string;
  values: number[];
  xValues?: number[];
  strokeColor?: string;
  yLabel?: string;
  xLabel?: string;
  minY?: number;
  maxY?: number;
}

export function SignalPolylinePlot({
  title,
  values,
  xValues,
  strokeColor = "#56B4E9",
  yLabel = "Amp",
  xLabel = "Muestras",
  minY,
  maxY,
}: PolylinePlotProps) {
  const gradId = useId();
  const width = 560;
  const height = 196;
  const padLeft = 36;
  const padRight = 18;
  const padY = 26;

  const { points, areaPoints, yLo, yHi, peak } = useMemo(() => {
    if (!values || values.length === 0) {
      return { points: "", areaPoints: "", yLo: 0, yHi: 1, peak: 0 };
    }
    const lo = minY ?? Math.min(...values);
    const hi = maxY ?? Math.max(...values);
    const span = Math.abs(hi - lo) < 1e-6 ? 1 : hi - lo;
    const innerW = width - padLeft - padRight;
    const innerH = height - padY * 2;

    const coords = values.map((v, idx) => {
      const xNorm = values.length > 1 ? idx / (values.length - 1) : 0;
      const yNorm = Math.max(0, Math.min(1, (v - lo) / span));
      const px = padLeft + xNorm * innerW;
      const py = height - padY - yNorm * innerH;
      return `${px.toFixed(1)},${py.toFixed(1)}`;
    });

    const baselineY = (height - padY).toFixed(1);
    const firstX = padLeft.toFixed(1);
    const lastX = (padLeft + innerW).toFixed(1);

    return {
      points: coords.join(" "),
      areaPoints: `${firstX},${baselineY} ${coords.join(" ")} ${lastX},${baselineY}`,
      yLo: lo,
      yHi: hi,
      peak: Math.max(...values.map((v) => Math.abs(v))),
    };
  }, [values, minY, maxY]);

  if (!values || values.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-zinc-900/75 p-4 text-xs text-zinc-400 backdrop-blur-md">
        {title}: sin datos muestreados
      </div>
    );
  }

  const xStart = xValues && xValues.length > 0 ? Math.round(xValues[0]) : 0;
  const xEnd =
    xValues && xValues.length > 0 ? Math.round(xValues[xValues.length - 1]) : values.length;

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/75 p-4 backdrop-blur-md">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="font-display text-xs font-semibold tracking-tight text-zinc-100">
          {title}
        </span>
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-zinc-400">
          <span>
            {yLabel} [{yLo.toFixed(1)} .. {yHi.toFixed(1)}]
          </span>
          <span className="rounded border border-white/10 bg-zinc-950/70 px-1.5 py-0.5 text-zinc-300">
            |Pico| {peak.toFixed(2)}
          </span>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-44 w-full rounded-lg border border-white/5 bg-zinc-950/90"
        role="img"
        aria-label={title}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.28" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Horizontal gridlines */}
        {[0.25, 0.5, 0.75].map((ratio) => {
          const gy = padY + ratio * (height - padY * 2);
          return (
            <line
              key={ratio}
              x1={padLeft}
              y1={gy}
              x2={width - padRight}
              y2={gy}
              stroke="#27272a"
              strokeDasharray="3 4"
            />
          );
        })}

        {/* Axes */}
        <line x1={padLeft} y1={padY} x2={padLeft} y2={height - padY} stroke="#3f3f46" />
        <line
          x1={padLeft}
          y1={height - padY}
          x2={width - padRight}
          y2={height - padY}
          stroke="#3f3f46"
        />

        {/* Area & Waveform */}
        <polygon points={areaPoints} fill={`url(#${gradId})`} />
        <polyline
          fill="none"
          stroke={strokeColor}
          strokeWidth="1.9"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={points}
        />

        {/* Axis Annotations */}
        <text x={padLeft - 6} y={padY + 4} fill="#71717a" fontSize="9.5" textAnchor="end">
          {yHi.toFixed(0)}
        </text>
        <text
          x={padLeft - 6}
          y={height - padY}
          fill="#71717a"
          fontSize="9.5"
          textAnchor="end"
        >
          {yLo.toFixed(0)}
        </text>
        <text x={padLeft} y={height - 8} fill="#a1a1aa" fontSize="10" fontFamily="monospace">
          {xStart}
        </text>
        <text
          x={width - padRight}
          y={height - 8}
          fill="#a1a1aa"
          fontSize="10"
          fontFamily="monospace"
          textAnchor="end"
        >
          {xEnd} {xLabel}
        </text>
      </svg>
    </div>
  );
}

interface ConstellationProps {
  title: string;
  points: [number, number][];
}

export function ConstellationPlot({ title, points }: ConstellationProps) {
  const size = 228;
  const pad = 24;
  const maxCoord = points.length
    ? Math.max(1.2, ...points.flatMap(([i, q]) => [Math.abs(i), Math.abs(q)])) * 1.15
    : 3.5;

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/75 p-4 backdrop-blur-md">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-display text-xs font-semibold text-zinc-100">{title}</span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-emerald-400">
          {points.length} símbolos I/Q
        </span>
      </div>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="mx-auto h-44 w-44 rounded-lg border border-white/5 bg-zinc-950/90"
        role="img"
        aria-label={title}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={(size / 2 - pad) * 0.65}
          fill="none"
          stroke="#27272a"
          strokeDasharray="3 4"
        />
        <line x1={pad} y1={size / 2} x2={size - pad} y2={size / 2} stroke="#3f3f46" />
        <line x1={size / 2} y1={pad} x2={size / 2} y2={size - pad} stroke="#3f3f46" />
        {points.map(([i, q], idx) => {
          const cx = size / 2 + (i / maxCoord) * (size / 2 - pad);
          const cy = size / 2 - (q / maxCoord) * (size / 2 - pad);
          return (
            <circle
              key={idx}
              cx={cx}
              cy={cy}
              r="3.2"
              fill="#009E73"
              opacity="0.86"
            />
          );
        })}
        <text x={size - 10} y={size / 2 - 6} fill="#71717a" fontSize="9.5" textAnchor="end">
          I
        </text>
        <text x={size / 2 + 6} y={pad + 4} fill="#71717a" fontSize="9.5">
          Q
        </text>
      </svg>
    </div>
  );
}
