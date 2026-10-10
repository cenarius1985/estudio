"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  MdHome,
  MdOutlineFolder,
  MdOutlineMail,
  MdOutlineChat,
  MdOutlineSchool,
  MdOutlineLabel,
  MdOutlineSettings,
  MdOutlineLogout,
} from "react-icons/md";
import { api, getTema, setTema, salir } from "@/lib/api";

/** Navegación lateral — portada del Sidebar de Horizon UI. */
const ITEMS = [
  { href: "/", label: "Panel", Icono: MdHome },
  { href: "/documentos", label: "Documentos", Icono: MdOutlineFolder },
  { href: "/tips", label: "Tips", Icono: MdOutlineMail },
  { href: "/chat", label: "Chat", Icono: MdOutlineChat },
  { href: "/estudio", label: "Estudio", Icono: MdOutlineSchool },
  { href: "/temas", label: "Temas", Icono: MdOutlineLabel },
  { href: "/ajustes", label: "Ajustes", Icono: MdOutlineSettings },
];

export default function Nav({ abierto = true, onCerrar }: { abierto?: boolean; onCerrar?: () => void }) {
  const ruta = usePathname();
  const [temas, setTemas] = useState<any[]>([]);
  const [activo, setActivo] = useState("");

  useEffect(() => {
    setActivo(getTema());
    api("/temas").then(setTemas).catch(() => {});
  }, []);

  return (
    <div
      className={`duration-175 linear fixed !z-50 flex min-h-full w-[290px] flex-col bg-white pb-10 shadow-2xl shadow-white/5 transition-all lg:!z-50 xl:!z-0 ${
        abierto ? "translate-x-0" : "-translate-x-96 xl:translate-x-0"
      }`}
    >
      <span className="absolute top-4 right-4 block cursor-pointer text-navy-700 xl:hidden" onClick={onCerrar}>
        ✕
      </span>

      {/* BRAND — tipografía Poppins del logo Horizon */}
      <div className="mx-[42px] mt-[36px] flex items-center">
        <div className="mt-1 h-2.5 font-poppins text-[26px] font-bold uppercase text-navy-700">
          Estudio <span className="font-medium">MRI</span>
        </div>
      </div>
      <div className="mt-[30px] mb-7 h-px bg-gray-300" />

      {/* Tema activo */}
      <div className="mx-6 mb-5">
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-600">
          Tema activo
        </label>
        <select
          className="entrada"
          value={activo}
          onChange={(e) => setTema(e.target.value)}
        >
          <option value="">Todos</option>
          {temas.map((t) => (
            <option key={t.id} value={t.id}>
              {t.nombre}
            </option>
          ))}
        </select>
      </div>

      {/* Links — activo en brand-500 con barra indicadora derecha */}
      <ul className="mb-auto pt-1">
        {ITEMS.map(({ href, label, Icono }) => {
          const activoItem = ruta === href;
          return (
            <Link key={href} href={href} onClick={onCerrar}>
              <div className="relative mb-1 flex cursor-pointer hover:bg-lightPrimary/60">
                <li className="my-[3px] flex cursor-pointer items-center px-8 py-2">
                  <span
                    className={`text-2xl ${
                      activoItem ? "font-bold text-brand-500" : "font-medium text-gray-600"
                    }`}
                  >
                    <Icono />
                  </span>
                  <p
                    className={`leading-1 ml-4 text-[15px] ${
                      activoItem ? "font-bold text-navy-700" : "font-medium text-gray-600"
                    }`}
                  >
                    {label}
                  </p>
                </li>
                {activoItem && (
                  <div className="absolute top-px right-0 h-9 w-1 rounded-lg bg-brand-500" />
                )}
              </div>
            </Link>
          );
        })}
      </ul>

      {/* Card inferior estilo SidebarCard de Horizon */}
      <div className="flex justify-center px-6">
        <div className="rounded-[20px] bg-lightPrimary p-4 text-center">
          <p className="font-poppins text-sm font-bold text-navy-700">Tesis MRI-UTE</p>
          <p className="mt-1 text-xs text-gray-600">UTE 2D · CS radial · Relaxometría T2*</p>
        </div>
      </div>

      <button
        onClick={() => salir()}
        className="mx-8 mt-6 flex items-center gap-3 text-sm font-medium text-gray-600 hover:text-red-500"
      >
        <MdOutlineLogout className="text-xl" /> Cerrar sesión
      </button>
    </div>
  );
}
