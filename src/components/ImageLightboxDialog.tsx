"use client";

import { useEffect, useRef } from "react";

export interface LightboxAsset {
  src: string;
  title: string;
  caption?: string;
}

interface ImageLightboxDialogProps {
  asset: LightboxAsset | null;
  onClose: () => void;
}

export function ImageLightboxDialog({ asset, onClose }: ImageLightboxDialogProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (asset && !dialog.open) {
      dialog.showModal();
    } else if (!asset && dialog.open) {
      dialog.close();
    }
  }, [asset]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
      className="m-auto w-[min(94vw,1080px)] rounded-2xl border border-white/15 bg-zinc-950/95 p-0 text-zinc-100 shadow-2xl backdrop-blur-xl"
    >
      {asset && (
        <div className="flex flex-col">
          <div className="flex items-center justify-between gap-4 border-b border-white/10 px-5 py-3.5">
            <div>
              <h3 className="font-display text-base font-semibold text-white">
                {asset.title}
              </h3>
              {asset.caption && (
                <p className="mt-0.5 font-mono text-xs text-zinc-400">{asset.caption}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <a
                href={asset.src}
                download
                className="rounded-lg border border-white/15 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-200 transition hover:-translate-y-0.5 hover:border-sky-400/50 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              >
                Descargar
              </a>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-white/15 bg-zinc-900 px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:bg-zinc-800 hover:text-white active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              >
                Cerrar (ESC)
              </button>
            </div>
          </div>

          <div className="flex max-h-[78vh] items-center justify-center overflow-auto bg-zinc-900/60 p-4 sm:p-6">
            <img
              src={asset.src}
              alt={asset.title}
              className="max-h-[70vh] w-auto rounded-lg border border-white/10 object-contain shadow-lg"
            />
          </div>
        </div>
      )}
    </dialog>
  );
}
