import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Procesador DSP de Imágenes | Comunicaciones I — UTP",
  description:
    "Sistema modular de compresión, muestreo Nyquist-Shannon, cuantización Byte/Bit, modulación audible, demodulación y reconstrucción PNG/SVG.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
