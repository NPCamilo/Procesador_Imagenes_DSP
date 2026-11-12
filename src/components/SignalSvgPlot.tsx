"use client";

import React from "react";

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
  const width = 520;
  const height = 180;
  const pad = 28;

  if (!values || values.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4 text-xs text-zinc-400">
        {title}: sin datos
      </div>
    );
  }

  const yLo = minY ?? Math.min(...values);
  const yHi = maxY ?? Math.max(...values);
  const ySpan = Math.abs(yHi - yLo) < 1e-6 ? 1 : yHi - yLo;

  const points = values
    .map((v, idx) => {
      const xNorm = values.length > 1 ? idx / (values.length - 1) : 0;
      const yNorm = (v - yLo) / ySpan;
      const px = pad + xNorm * (width - pad * 2);
      const py = height - pad - yNorm * (height - pad * 2);
      return `${px.toFixed(1)},${py.toFixed(1)}`;
    })
    .join(" ");

  const xStart = xValues && xValues.length > 0 ? xValues[0] : 0;
  const xEnd = xValues && xValues.length > 0 ? xValues[xValues.length - 1] : values.length;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="font-semibold text-zinc-100">{title}</span>
        <span className="font-mono text-[11px] text-zinc-400">
          {yLabel} [{yLo.toFixed(1)} .. {yHi.toFixed(1)}]
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-40 w-full rounded bg-zinc-950">
        <line x1={pad} y1={height / 2} x2={width - pad} y2={height / 2} stroke="#27272a" strokeDasharray="3 3" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#3f3f46" />
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#3f3f46" />
        <polyline fill="none" stroke={strokeColor} strokeWidth="1.8" points={points} />
        <text x={pad} y={height - 8} fill="#a1a1aa" fontSize="10">
          {xStart}
        </text>
        <text x={width - pad} y={height - 8} fill="#a1a1aa" fontSize="10" textAnchor="end">
          {xEnd} ({xLabel})
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
  const size = 220;
  const pad = 22;
  const maxCoord = points.length
    ? Math.max(1.2, ...points.flatMap(([i, q]) => [Math.abs(i), Math.abs(q)])) * 1.15
    : 3.5;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-3">
      <div className="mb-2 text-xs font-semibold text-zinc-100">{title}</div>
      <svg viewBox={`0 0 ${size} ${size}`} className="mx-auto h-40 w-40 rounded bg-zinc-950">
        <line x1={pad} y1={size / 2} x2={size - pad} y2={size / 2} stroke="#3f3f46" />
        <line x1={size / 2} y1={pad} x2={size / 2} y2={size - pad} stroke="#3f3f46" />
        {points.map(([i, q], idx) => {
          const cx = size / 2 + (i / maxCoord) * (size / 2 - pad);
          const cy = size / 2 - (q / maxCoord) * (size / 2 - pad);
          return <circle key={idx} cx={cx} cy={cy} r="3.2" fill="#009E73" opacity="0.85" />;
        })}
      </svg>
    </div>
  );
}
