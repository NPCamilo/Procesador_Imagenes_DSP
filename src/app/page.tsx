"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Cpu,
  ExternalLink,
  Moon,
  Radio,
  SlidersHorizontal,
  Sparkles,
  Sun,
} from "lucide-react";
import type { DemoData } from "@/types/dsp";
import { AsciiSignalBackdrop } from "@/components/AsciiSignalBackdrop";
import { EditorialShowcase } from "@/components/EditorialShowcase";
import { LiveTransmitter } from "@/components/LiveTransmitter";
import { PeerReceiver } from "@/components/PeerReceiver";
import { TelemetryDrawer, type TelemetryFocus } from "@/components/TelemetryDrawer";

const SECTION_LINKS = [
  { id: "captura", code: "00", label: "Captura & Comparador" },
  { id: "espectro", code: "01", label: "Espectro & Rojo" },
  { id: "digital", code: "02", label: "NQS, Bits & Códec" },
  { id: "modulacion", code: "03", label: "Consola Audio & RF" },
  { id: "reconstruccion", code: "04", label: "Salida PNG / SVG" },
  { id: "workbench", code: "05", label: "Laboratorio TX / RX" },
] as const;

export default function HomePage() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [asciiActive, setAsciiActive] = useState(true);
  const [activeSection, setActiveSection] = useState<string>("captura");
  const [workbenchMode, setWorkbenchMode] = useState<"tx" | "rx">("tx");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerFocus, setDrawerFocus] = useState<TelemetryFocus>("all");

  const [demoData, setDemoData] = useState<DemoData | null>(null);
  const [demoError, setDemoError] = useState<string | null>(null);

  // Sync Tailwind .dark class on root & persist user preference (defaults to Dark Mode)
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("dsp-theme");
      if (saved === "light" || saved === "dark") {
        setTheme(saved);
        document.documentElement.classList.toggle("dark", saved === "dark");
        return;
      }
    } catch {
      // Ignore storage access errors
    }
    document.documentElement.classList.add("dark");
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      document.documentElement.classList.toggle("dark", next === "dark");
      try {
        window.localStorage.setItem("dsp-theme", next);
      } catch {
        // Ignore storage errors
      }
      return next;
    });
  }, []);

  useEffect(() => {
    fetch("/demo/datos_demo.json")
      .then((res) => {
        if (!res.ok) throw new Error("No se encontró datos_demo.json");
        return res.json();
      })
      .then((json: DemoData) => setDemoData(json))
      .catch((err) => setDemoError(err instanceof Error ? err.message : "Error cargando demo"));
  }, []);

  // Track visible section cleanly in the Sticky Index Rail
  useEffect(() => {
    if (!demoData) return;
    const ids = SECTION_LINKS.map((s) => s.id);
    const elements = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);

    if (elements.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]?.target.id) {
          setActiveSection(visible[0].target.id);
        }
      },
      { rootMargin: "-18% 0px -55% 0px", threshold: [0.1, 0.35, 0.6] }
    );

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [demoData]);

  const jumpToWorkbench = useCallback((mode: "tx" | "rx") => {
    setWorkbenchMode(mode);
    const target = document.getElementById("workbench");
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, []);

  const openTelemetry = useCallback((focus: TelemetryFocus) => {
    setDrawerFocus(focus);
    setDrawerOpen(true);
  }, []);

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-clip text-(--ink)">
      <AsciiSignalBackdrop active={asciiActive} theme={theme} />

      {/* SLIM TOP ARCHITECTURAL HEADER */}
      <header className="sticky top-0 z-40 border-b border-(--hairline) bg-(--canvas)/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1380px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="truncate font-mono text-[10px] uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
              Comunicaciones I · Universidad Tecnológica de Pereira
            </p>
            <h1 className="truncate font-display text-sm font-bold tracking-tight text-(--ink) sm:text-base">
              Procesador, Compresor y Transceptor DSP
            </h1>
          </div>

          <nav className="hidden items-center gap-1.5 sm:flex" aria-label="Accesos principales">
            <a
              href="#captura"
              className="rounded-full px-3 py-1.5 text-xs font-medium text-(--ink-muted) transition hover:text-(--ink)"
            >
              Exhibición
            </a>
            <button
              type="button"
              onClick={() => jumpToWorkbench("tx")}
              className="inline-flex items-center gap-1.5 rounded-full border border-(--hairline) bg-(--surface) px-3.5 py-1.5 text-xs font-medium text-(--ink) transition hover:border-sky-500/50"
            >
              <Cpu className="h-3.5 w-3.5 text-sky-500" /> Lab TX
            </button>
            <button
              type="button"
              onClick={() => jumpToWorkbench("rx")}
              className="inline-flex items-center gap-1.5 rounded-full border border-(--hairline) bg-(--surface) px-3.5 py-1.5 text-xs font-medium text-(--ink) transition hover:border-emerald-500/50"
            >
              <Radio className="h-3.5 w-3.5 text-emerald-500" /> Receptor RX
            </button>
          </nav>
        </div>
      </header>

      {/* DUAL-COLUMN ARCHITECTURAL FLOW + PERSISTENT STICKY RAIL */}
      <div className="mx-auto w-full max-w-[1380px] flex-1 px-4 pt-6 sm:px-6 sm:pt-10 lg:grid lg:grid-cols-12 lg:gap-12">
        <main className="min-w-0 lg:col-span-9">
          {demoError && (
            <div
              role="alert"
              className="rounded-2xl border border-red-500/35 bg-red-500/10 p-5 text-sm text-red-700 dark:text-red-200"
            >
              {demoError}
            </div>
          )}

          {!demoData && !demoError && (
            <div className="space-y-8 py-8">
              <div className="h-80 animate-pulse rounded-3xl bg-(--surface)" />
              <div className="h-56 animate-pulse rounded-2xl bg-(--surface)" />
            </div>
          )}

          {demoData && (
            <EditorialShowcase
              data={demoData}
              onJumpWorkbench={jumpToWorkbench}
              onOpenTelemetry={openTelemetry}
            />
          )}

          {/* 05 · INTEGRATED WORKBENCH BELOW THE ICONIC SHOWCASE */}
          <section
            id="workbench"
            className="scroll-mt-24 border-t border-(--hairline) py-16 lg:py-24"
          >
            <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
                  05 · Banco de Ejecución en Vivo
                </p>
                <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-(--ink) sm:text-3xl">
                  Laboratorio Transmisor (TX) y Receptor Compañero (RX).
                </h2>
              </div>

              <div
                className="inline-flex gap-1 rounded-full border border-(--hairline) bg-(--surface) p-1"
                role="tablist"
                aria-label="Modo de banco interactivo"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={workbenchMode === "tx"}
                  onClick={() => setWorkbenchMode("tx")}
                  className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                    workbenchMode === "tx"
                      ? "bg-(--ink) text-(--canvas)"
                      : "text-(--ink-muted) hover:text-(--ink)"
                  }`}
                >
                  <Cpu className="h-3.5 w-3.5" /> Laboratorio TX
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={workbenchMode === "rx"}
                  onClick={() => setWorkbenchMode("rx")}
                  className={`inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                    workbenchMode === "rx"
                      ? "bg-emerald-500 text-zinc-950"
                      : "text-(--ink-muted) hover:text-(--ink)"
                  }`}
                >
                  <Radio className="h-3.5 w-3.5" /> Receptor RX
                </button>
              </div>
            </div>

            <div key={workbenchMode} className="animate-reveal">
              {workbenchMode === "tx" ? <LiveTransmitter /> : <PeerReceiver />}
            </div>
          </section>
        </main>

        {/* STICKY RIGHT INDEX & AMBIENT CONTROL RAIL (Always beside every section on desktop) */}
        <aside className="hidden lg:col-span-3 lg:block" aria-label="Navegación y controles">
          <div className="sticky top-24 space-y-6 border-l border-(--hairline) pl-6">
            {/* Environment Toggles: Theme + ASCII Matrix right next to all content */}
            <div className="space-y-2.5">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-(--ink-muted)">
                Entorno Visual
              </p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={toggleTheme}
                  aria-pressed={theme === "light"}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-(--hairline) bg-(--surface) px-3 py-2 font-mono text-[11px] font-medium text-(--ink) transition hover:border-sky-500/50 active:scale-[0.98]"
                >
                  {theme === "dark" ? (
                    <>
                      <Sun className="h-3.5 w-3.5 text-amber-400" /> Claro
                    </>
                  ) : (
                    <>
                      <Moon className="h-3.5 w-3.5 text-sky-600" /> Oscuro
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setAsciiActive((v) => !v)}
                  aria-pressed={asciiActive}
                  className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-(--hairline) bg-(--surface) px-3 py-2 font-mono text-[11px] font-medium text-(--ink) transition hover:border-sky-500/50 active:scale-[0.98]"
                >
                  <Sparkles
                    className={`h-3.5 w-3.5 ${
                      asciiActive ? "text-sky-500" : "text-(--ink-muted)"
                    }`}
                  />
                  ASCII {asciiActive ? "ON" : "OFF"}
                </button>
              </div>
            </div>

            {/* In-page Sticky Section Tracker */}
            <nav className="space-y-1.5" aria-label="Mapa de secciones">
              <p className="mb-2.5 font-mono text-[10px] uppercase tracking-[0.2em] text-(--ink-muted)">
                En esta página
              </p>
              {SECTION_LINKS.map((item) => {
                const isActive = activeSection === item.id;
                return (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    className={`flex items-center gap-2.5 rounded-lg py-1.5 pl-2.5 pr-2 text-xs transition ${
                      isActive
                        ? "bg-(--surface) font-semibold text-(--ink)"
                        : "text-(--ink-muted) hover:text-(--ink)"
                    }`}
                  >
                    <span
                      className={`font-mono text-[10px] ${
                        isActive ? "text-sky-500" : "text-(--ink-muted)"
                      }`}
                    >
                      {item.code}
                    </span>
                    <span className="truncate">{item.label}</span>
                  </a>
                );
              })}
            </nav>

            {/* Secondary Technical Drawer Trigger + Direct Tool Shortcuts */}
            <div className="space-y-2 border-t border-(--hairline) pt-5">
              {demoData && (
                <button
                  type="button"
                  onClick={() => openTelemetry("all")}
                  className="flex w-full items-center justify-between rounded-xl border border-(--hairline) bg-(--surface) px-3.5 py-2.5 text-left font-mono text-[11px] text-(--ink) transition hover:border-sky-500/50"
                >
                  <span className="inline-flex items-center gap-2">
                    <SlidersHorizontal className="h-3.5 w-3.5 text-sky-500" />
                    Ficha Técnica DSP
                  </span>
                  <span className="text-[10px] text-(--ink-muted)">BIN/HEX</span>
                </button>
              )}

              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => jumpToWorkbench("tx")}
                  className="rounded-xl border border-(--hairline) px-3 py-2 text-center font-mono text-[11px] text-(--ink-muted) transition hover:border-sky-500/50 hover:text-(--ink)"
                >
                  Ir a Lab TX
                </button>
                <button
                  type="button"
                  onClick={() => jumpToWorkbench("rx")}
                  className="rounded-xl border border-(--hairline) px-3 py-2 text-center font-mono text-[11px] text-(--ink-muted) transition hover:border-emerald-500/50 hover:text-(--ink)"
                >
                  Ir a RX
                </button>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* MOBILE / TABLET FLOATING CONTROL DOCK (Beside every section cleanly) */}
      <div className="fixed inset-x-3 bottom-3 z-40 lg:hidden">
        <div className="mx-auto flex max-w-md items-center justify-between gap-1 rounded-full border border-(--hairline) bg-(--surface-elevated)/90 px-2.5 py-1.5 shadow-2xl backdrop-blur-xl">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label="Cambiar tema claro o oscuro"
            className="inline-flex items-center gap-1 rounded-full px-2.5 py-1.5 font-mono text-[11px] text-(--ink)"
          >
            {theme === "dark" ? (
              <Sun className="h-3.5 w-3.5 text-amber-400" />
            ) : (
              <Moon className="h-3.5 w-3.5 text-sky-600" />
            )}
            <span>{theme === "dark" ? "Claro" : "Oscuro"}</span>
          </button>

          <button
            type="button"
            onClick={() => setAsciiActive((v) => !v)}
            className="inline-flex items-center gap-1 rounded-full px-2.5 py-1.5 font-mono text-[11px] text-(--ink)"
          >
            <Sparkles
              className={`h-3.5 w-3.5 ${asciiActive ? "text-sky-500" : "text-(--ink-muted)"}`}
            />
            <span>ASCII</span>
          </button>

          {demoData && (
            <button
              type="button"
              onClick={() => openTelemetry("all")}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-1.5 font-mono text-[11px] text-(--ink)"
            >
              <SlidersHorizontal className="h-3.5 w-3.5 text-sky-500" />
              <span>Ficha</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => jumpToWorkbench("tx")}
            className="rounded-full bg-(--ink) px-3 py-1.5 font-mono text-[11px] font-semibold text-(--canvas)"
          >
            TX/RX
          </button>
        </div>
      </div>

      {/* Telemetry Specs Drawer (Progressive Disclosure) */}
      {demoData && (
        <TelemetryDrawer
          open={drawerOpen}
          focus={drawerFocus}
          data={demoData}
          onClose={() => setDrawerOpen(false)}
        />
      )}

      {/* GROUNDED FOOTER */}
      <footer className="mt-8 border-t border-(--hairline) bg-(--canvas)/80 pb-24 lg:pb-6">
        <div className="mx-auto flex max-w-[1380px] flex-wrap items-center justify-between gap-4 px-4 py-6 text-xs text-(--ink-muted) sm:px-6">
          <p className="font-mono text-[11px]">
            UTP · Comunicaciones I · Motor Python DSP + Next.js App Router
          </p>
          <a
            href="https://github.com/NPCamilo/Procesador_Imagenes_DSP"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 font-mono text-[11px] text-(--ink) transition hover:text-sky-500"
          >
            GitHub: NPCamilo/Procesador_Imagenes_DSP <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </footer>
    </div>
  );
}
