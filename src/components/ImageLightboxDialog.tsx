"use client";

import { useEffect, useRef } from "react";
import { toWebpSrc } from "./OptimizedPicture";

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
      className="m-auto w-[min(94vw,1080px)] rounded-2xl border border-(--hairline) bg-(--surface-elevated) p-0 text-(--ink) shadow-2xl"
    >
      {asset && (
        <div className="flex flex-col">
          <div className="flex items-center justify-between gap-4 border-b border-(--hairline) px-5 py-3.5">
            <div>
              <h3 className="font-display text-base font-semibold text-(--ink)">
                {asset.title}
              </h3>
              {asset.caption && (
                <p className="mt-0.5 font-mono text-xs text-(--ink-muted)">{asset.caption}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <a
                href={asset.src}
                download
                className="rounded-lg border border-(--hairline) bg-(--surface) px-3 py-1.5 text-xs font-medium text-(--ink) transition hover:-translate-y-0.5 hover:border-sky-500/60 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
              >
                Descargar
              </a>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-(--hairline) bg-(--surface) px-3 py-1.5 text-xs font-medium text-(--ink-muted) transition hover:text-(--ink) active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
              >
                Cerrar (ESC)
              </button>
            </div>
          </div>

          <div className="flex max-h-[78vh] items-center justify-center overflow-auto bg-black/5 p-4 dark:bg-zinc-950/70 sm:p-6">
            <picture className="flex justify-center">
              {toWebpSrc(asset.src) && (
                <source srcSet={toWebpSrc(asset.src) as string} type="image/webp" />
              )}
              <img
                src={asset.src}
                alt={asset.title}
                decoding="async"
                className="max-h-[70vh] w-auto rounded-lg border border-white/10 object-contain shadow-lg"
              />
            </picture>
          </div>
        </div>
      )}
    </dialog>
  );
}
