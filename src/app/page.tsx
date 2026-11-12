"use client";

import React, { useEffect, useState } from "react";
import { Activity, Cpu, ExternalLink, Radio, Sparkles } from "lucide-react";
import type { DemoData } from "@/types/dsp";
import { AsciiSignalBackdrop } from "@/components/AsciiSignalBackdrop";
import { DemoShowcase } from "@/components/DemoShowcase";
import { LiveTransmitter } from "@/components/LiveTransmitter";
import { PeerReceiver } from "@/components/PeerReceiver";

type TabId = "demo" | "tx" | "rx";

export default function HomePage() {
  const [tab, setTab] = useState<TabId>("demo");
  const [asciiActive, setAsciiActive] = useState(true);
  const [demoData, setDemoData] = useState<DemoData | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/demo/datos_demo.json")
      .then((res) => {
        if (!res.ok) throw new Error("No se encontró datos_demo.json");
        return res.json();
      })
      .then((json: DemoData) => setDemoData(json))
      .catch((err) => setDemoError(err instanceof Error ? err.message : "Error cargando demo"));
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col text-zinc-100">
      <AsciiSignalBackdrop active={asciiActive} />

      <header className="sticky top-0 z-40 border-b border-white/10 bg-zinc-950/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-sky-400">
              Comunicaciones I · Universidad Tecnológica de Pereira
            </p>
            <h1 className="font-display text-lg font-bold tracking-tight text-white sm:text-xl">
              Procesador, Compresor y Transceptor DSP de Imágenes
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <nav className="flex flex-wrap gap-1.5" aria-label="Modos de operación">
              <button
                type="button"
                onClick={() => setTab("demo")}
                className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
                  tab === "demo"
                    ? "bg-sky-500 text-zinc-950 shadow-md shadow-sky-500/20"
                    : "border border-white/10 bg-zinc-900/80 text-zinc-300 hover:border-white/25 hover:text-white"
                }`}
              >
                <Activity className="h-3.5 w-3.5" /> Demostración Oficial
              </button>
              <button
                type="button"
                onClick={() => setTab("tx")}
                className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
                  tab === "tx"
                    ? "bg-sky-500 text-zinc-950 shadow-md shadow-sky-500/20"
                    : "border border-white/10 bg-zinc-900/80 text-zinc-300 hover:border-white/25 hover:text-white"
                }`}
              >
                <Cpu className="h-3.5 w-3.5" /> Laboratorio TX
              </button>
              <button
                type="button"
                onClick={() => setTab("rx")}
                className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                  tab === "rx"
                    ? "bg-emerald-500 text-zinc-950 shadow-md shadow-emerald-500/20"
                    : "border border-white/10 bg-zinc-900/80 text-zinc-300 hover:border-white/25 hover:text-white"
                }`}
              >
                <Radio className="h-3.5 w-3.5" /> Receptor RX
              </button>
            </nav>

            <button
              type="button"
              onClick={() => setAsciiActive((v) => !v)}
              aria-pressed={asciiActive}
              title="Alternar campo interactivo ASCII de portadora"
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-zinc-900/75 px-3 py-2 font-mono text-[11px] text-zinc-300 transition hover:border-sky-400/40 hover:text-white active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <Sparkles
                className={`h-3.5 w-3.5 ${asciiActive ? "text-sky-400" : "text-zinc-500"}`}
              />
              ASCII {asciiActive ? "ON" : "OFF"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        {tab === "demo" && (
          <>
            {demoError && (
              <div
                role="alert"
                className="rounded-2xl border border-red-500/30 bg-red-950/60 p-5 text-sm text-red-200 backdrop-blur"
              >
                {demoError}
              </div>
            )}
            {!demoData && !demoError && (
              <div className="space-y-6">
                <div className="h-72 animate-pulse rounded-3xl border border-white/10 bg-zinc-900/60" />
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {[0, 1, 2, 3].map((k) => (
                    <div
                      key={k}
                      className="h-28 animate-pulse rounded-2xl border border-white/10 bg-zinc-900/60"
                    />
                  ))}
                </div>
              </div>
            )}
            {demoData && <DemoShowcase data={demoData} onSwitchTab={setTab} />}
          </>
        )}

        {tab === "tx" && <LiveTransmitter />}
        {tab === "rx" && <PeerReceiver />}
      </main>

      <footer className="mt-12 border-t border-white/10 bg-zinc-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-5 text-xs text-zinc-400 sm:px-6">
          <p className="font-mono text-[11px]">
            UTP · Comunicaciones I · Motor Python DSP + Next.js App Router
          </p>
          <a
            href="https://github.com/NPCamilo/Procesador_Imagenes_DSP"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 font-mono text-[11px] text-zinc-300 transition hover:text-sky-400"
          >
            GitHub: NPCamilo/Procesador_Imagenes_DSP <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </footer>
    </div>
  );
}
