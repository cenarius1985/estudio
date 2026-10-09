import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Estudio Doctorado · Tesis MRI-UTE",
  description: "Plataforma de estudio: tips diarios, chat fiel a los documentos, flashcards y simulacros",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
