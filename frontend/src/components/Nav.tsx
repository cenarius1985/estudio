"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { salir } from "@/lib/api";

const ITEMS = [
  { href: "/", label: "Panel", icono: "📊" },
  { href: "/documentos", label: "Documentos", icono: "📁" },
  { href: "/tips", label: "Tips", icono: "✉️" },
  { href: "/chat", label: "Chat", icono: "💬" },
  { href: "/estudio", label: "Estudio", icono: "🎓" },
  { href: "/ajustes", label: "Ajustes", icono: "⚙️" },
];

export default function Nav() {
  const ruta = usePathname();
  return (
    <aside className="w-56 shrink-0 bg-marca-700 text-white flex flex-col">
      <div className="px-5 py-5 border-b border-white/10">
        <div className="font-bold text-lg leading-tight">Estudio</div>
        <div className="text-xs text-white/60 mt-1">Tu plataforma de estudio</div>
      </div>
      <nav className="flex-1 py-3">
        {ITEMS.map((item) => {
          const activo = ruta === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-5 py-2.5 text-sm ${
                activo ? "bg-white/15 font-semibold" : "text-white/80 hover:bg-white/10"
              }`}
            >
              <span>{item.icono}</span> {item.label}
            </Link>
          );
        })}
      </nav>
      <button
        onClick={() => salir()}
        className="px-5 py-3 text-sm text-white/70 hover:bg-white/10 text-left"
      >
        🚪 Salir
      </button>
    </aside>
  );
}
