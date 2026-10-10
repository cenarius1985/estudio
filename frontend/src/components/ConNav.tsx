"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FiAlignJustify } from "react-icons/fi";
import Nav from "./Nav";
import { getToken } from "@/lib/api";

/** Guard de sesión + layout admin de Horizon UI (sidebar + navbar sticky). */
export default function ConNav({ children, titulo }: { children: React.ReactNode; titulo: string }) {
  const router = useRouter();
  const [listo, setListo] = useState(false);
  const [menuAbierto, setMenuAbierto] = useState(false);

  useEffect(() => {
    if (!getToken()) router.push("/login");
    else setListo(true);
  }, [router]);

  if (!listo) return null;
  return (
    <div className="flex h-full w-full">
      <Nav abierto={menuAbierto} onCerrar={() => setMenuAbierto(false)} />

      <div className="h-full w-full bg-lightPrimary font-dm xl:ml-[290px]">
        {/* Navbar Horizon: breadcrumb + título grande + hamburger móvil */}
        <nav className="sticky top-3 z-40 mx-4 mb-6 flex flex-row flex-wrap items-center justify-between rounded-xl bg-white/70 p-2 shadow-3xl backdrop-blur-xl">
          <div className="ml-[6px]">
            <div className="h-6 pt-1">
              <span className="text-sm font-normal text-navy-700">Pages</span>
              <span className="mx-1 text-sm text-navy-700"> / </span>
              <span className="text-sm font-normal capitalize text-navy-700">{titulo}</span>
            </div>
            <p className="shrink font-poppins text-[33px] font-bold capitalize leading-tight text-navy-700">
              {titulo}
            </p>
          </div>
          <span
            className="flex cursor-pointer px-4 text-2xl text-gray-600 xl:hidden"
            onClick={() => setMenuAbierto(true)}
          >
            <FiAlignJustify className="h-5 w-5" />
          </span>
        </nav>

        <main className="mx-auto min-h-screen p-4 pb-16 xl:max-w-[1120px] 2xl:max-w-[1280px]">
          {children}
        </main>
      </div>
    </div>
  );
}
