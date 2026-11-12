"use client";

import React, { useEffect, useState } from "react";
import { Activity, Cpu, Radio } from "lucide-react";
import type { DemoData } from "@/types/dsp";
import { DemoShowcase } from "@/components/DemoShowcase";
import { LiveTransmitter } from "@/components/LiveTransmitter";
import { PeerReceiver } from "@/components/PeerReceiver";

type TabId = "demo" | "tx" | "rx";

export default function HomePage() {
  const [tab, setTab] = useState<TabId>("demo");
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
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 bg-zinc-900/70">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-wider text-sky-400">
              Comunicaciones I · Universidad Tecnológica de Pereira
            </p>
            <h1 className="text-xl font-bold tracking-tight text-zinc-100">
              Procesador, Compresor y Transceptor DSP de Imágenes
            </h1>
          </div>

          <nav className="flex flex-wrap gap-2" aria-label="Modos de operación">
            <button
              type="button"
              onClick={() => setTab("demo")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
                tab === "demo"
                  ? "bg-sky-600 text-white"
                  : "border border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              <Activity className="h-4 w-4" /> Demostración Oficial
            </button>
            <button
              type="button"
              onClick={() => setTab("tx")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
                tab === "tx"
                  ? "bg-sky-600 text-white"
                  : "border border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              <Cpu className="h-4 w-4" /> Laboratorio TX en Vivo
            </button>
            <button
              type="button"
              onClick={() => setTab("rx")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
                tab === "rx"
                  ? "bg-emerald-600 text-white"
                  : "border border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              <Radio className="h-4 w-4" /> Receptor Compañero (RX)
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        {tab === "demo" && (
          <>
            {demoError && (
              <div className="rounded-lg border border-red-800 bg-red-950/60 p-4 text-sm text-red-200">
                {demoError}
              </div>
            )}
            {!demoData && !demoError && (
              <p className="text-sm text-zinc-400">Cargando resultados precalculados...</p>
            )}
            {demoData && <DemoShowcase data={demoData} />}
          </>
        )}

        {tab === "tx" && <LiveTransmitter />}
        {tab === "rx" && <PeerReceiver />}
      </main>
    </div>
  );
}
