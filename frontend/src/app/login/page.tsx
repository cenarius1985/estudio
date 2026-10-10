"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { MdOutlineLock } from "react-icons/md";
import { API_URL, setToken } from "@/lib/api";

export default function Login() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setCargando(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) throw new Error("Contraseña incorrecta");
      const datos = await res.json();
      setToken(datos.token);
      router.push("/");
    } catch (exc: any) {
      setError(exc.message || "Error de conexión con la API");
    } finally {
      setCargando(false);
    }
  }

  return (
    /* Auth layout de Horizon: panel blanco (flex-1) + franja gradiente brand a la derecha */
    <div className="flex min-h-screen w-full !bg-white">
      <main className="flex min-h-screen flex-1 flex-col justify-center px-6 pb-16 pt-10 md:px-16 lg:px-20">
        <div className="mx-auto flex w-full max-w-[480px] flex-col">
          <div className="mb-12 flex w-fit items-center hover:cursor-pointer">
            <div className="mt-1 h-2.5 font-poppins text-[28px] font-bold uppercase text-navy-700">
              Estudio <span className="font-medium">MRI</span>
            </div>
          </div>
          <h1 className="mb-3 font-poppins text-4xl font-bold text-navy-700">Iniciar sesión</h1>
          <p className="mb-8 text-lg text-gray-600">
            Escribe la contraseña de administrador para entrar a tu plataforma de estudio.
          </p>

          <form onSubmit={entrar} className="flex max-w-[420px] flex-col gap-4">
            <div>
              <label className="mb-2 block ml-[10px] text-sm font-medium text-navy-700">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type="password"
                  className="entrada"
                  style={{ paddingLeft: "44px" }}
                  placeholder="Contraseña de administrador"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoFocus
                />
                <MdOutlineLock className="pointer-events-none absolute top-1/2 left-4 h-5 w-5 -translate-y-1/2 text-gray-500" />
              </div>
            </div>
            {error && <p className="text-sm font-medium text-red-500">{error}</p>}
            <button className="boton-primario mt-2 w-full justify-center py-3 text-base" disabled={cargando}>
              {cargando ? "Ingresando…" : "Ingresar"}
            </button>
          </form>

          <p className="mt-16 w-fit font-poppins text-xs text-gray-600">
            © 2026 Estudio MRI · Tesis UTE 0.55 T
          </p>
        </div>
      </main>

      {/* Franja decorativa gradiente del auth de Horizon (hermana flex: nunca solapa) */}
      <div
        className="hidden w-[42%] shrink-0 md:block lg:w-[46%]"
        style={{ background: "linear-gradient(135deg, #868CFF 0%, #4318FF 100%)" }}
      >
        <div className="flex h-full min-h-screen w-full flex-col items-center justify-end pb-16">
          <div className="flex flex-col items-center px-8 text-center">
            <p className="font-poppins text-4xl font-bold text-white drop-shadow-xl">Tesis MRI-UTE</p>
            <p className="mt-3 max-w-md text-lg font-medium text-white drop-shadow-xl">
              UTE 2D half pulse · Reconstrucción radial con CS · Relaxometría T2* tri-componente ·
              US-BDAT a 0.55 T
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
