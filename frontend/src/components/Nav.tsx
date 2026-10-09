"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getTema, setTema, salir } from "@/lib/api";

const ITEMS = [
  { href: "/", label: "Panel", icono: "📊" },
  { href: "/documentos", label: "Documentos", icono: "📁" },
  { href: "/tips", label: "Tips", icono: "✉️" },
  { href: "/chat", label: "Chat", icono: "💬" },
  { href: "/estudio", label: "Estudio", icono: "🎓" },
  { href: "/temas", label: "Temas", icono: "🏷️" },
  { href: "/ajustes", label: "Ajustes", icono: "⚙️" },
];

export default function Nav() {
  const ruta = usePathname();
  const [temas, setTemas] = useState<any[]>([]);
  const [activo, setActivo] = useState("");

  useEffect(() => {
    setActivo(getTema());
    api("/temas").then(setTemas).catch(() => {});
  }, []);

  return (
    <aside className="w-56 shrink-0 bg-marca-700 text-white flex flex-col">
      <div className="px-5 py-5 border-b border-white/10">
        <div className="font-bold text-lg leading-tight">Estudio</div>
        <div className="text-xs text-white/60 mt-1">Tu plataforma de estudio</div>
      </div>

      <div className="px-4 py-3 border-b border-white/10">
        <label className="text-[11px] uppercase tracking-wide text-white/50">Tema activo</label>
        <select
          className="w-full mt-1 rounded-lg bg-white/10 text-white text-sm px-2 py-1.5 border border-white/20 focus:outline-none"
          value={activo}
          onChange={(e) => setTema(e.target.value)}
        >
          <option value="" className="text-slate-800">Todos</option>
          {temas.map((t) => (
            <option key={t.id} value={t.id} className="text-slate-800">
              {t.nombre}
            </option>
          ))}
        </select>
      </div>

      <nav className="flex-1 py-3">
        {ITEMS.map((item) => {
          const activoItem = ruta === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-5 py-2.5 text-sm ${
                activoItem ? "bg-white/15 font-semibold" : "text-white/80 hover:bg-white/10"
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
