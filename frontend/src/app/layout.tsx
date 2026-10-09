import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Estudio — tu plataforma de estudio",
  description: "Indexa tus documentos, recibe tips diarios por correo, pregunta con respuestas 100% citadas y estudia con flashcards y simulacros",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
