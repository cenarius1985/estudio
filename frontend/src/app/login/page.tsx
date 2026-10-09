"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
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
    <main className="min-h-screen flex items-center justify-center bg-marca-700">
      <form onSubmit={entrar} className="tarjeta w-96">
        <h1 className="text-xl font-bold text-marca-700">Estudio Doctorado</h1>
        <p className="text-sm text-slate-500 mt-1 mb-5">Tesis MRI-UTE · panel de estudio</p>
        <input
          type="password"
          className="entrada"
          placeholder="Contraseña de administrador"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
        <button className="boton-primario mt-4 w-full justify-center" disabled={cargando}>
          {cargando ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
    </main>
  );
}
