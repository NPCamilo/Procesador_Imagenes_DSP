"use client";

import React, { useState } from "react";

interface OptimizedPictureProps {
  src: string;
  alt: string;
  className?: string;
  priority?: boolean;
  draggable?: boolean;
}

export function toWebpSrc(src: string): string | null {
  if (!src || src.startsWith("data:") || src.endsWith(".svg") || src.endsWith(".webp")) {
    return null;
  }
  return src.replace(/\.png$/i, ".webp");
}

export function OptimizedPicture({
  src,
  alt,
  className = "",
  priority = false,
  draggable = true,
}: OptimizedPictureProps) {
  const [loaded, setLoaded] = useState(false);
  const webp = toWebpSrc(src);

  return (
    <picture className="block h-full w-full">
      {webp && <source srcSet={webp} type="image/webp" />}
      <img
        src={src}
        alt={alt}
        loading={priority ? "eager" : "lazy"}
        decoding="async"
        fetchPriority={priority ? "high" : "auto"}
        draggable={draggable}
        onLoad={() => setLoaded(true)}
        className={`${className} transition-opacity duration-300 ${
          loaded ? "opacity-100" : "opacity-0"
        }`}
      />
    </picture>
  );
}
