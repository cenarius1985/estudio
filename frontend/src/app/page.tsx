"use client";

import { useEffect, useState } from "react";
import ConNav from "@/components/ConNav";
import { api } from "@/lib/api";

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [tipsStats, setTipsStats] = useState<any>(null);
  const [salud, setSalud] = useState<any>(null);
  const [mensaje, setMensaje] = useState("");

  async function cargar() {
    try {
      const [s, t, sal] = await Promise.all([
        api("/stats"),
        api("/tips/stats"),
        api("/salud"),
      ]);
      setStats(s);
      setTipsStats(t);
      setSalud(sal);
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function escanear() {
    setMensaje("Escaneo encolado…");
    try {
      const r = await api("/documentos/escanear", { method: "POST" });
      setMensaje(`Escaneo encolado (${r.job}). Vuelve a cargar en unos minutos.`);
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  const totalDocs = Object.values(stats?.documentos?.por_estado || {}).reduce((a: number, b: any) => a + b, 0);
  const llmOk = salud?.llm && Object.entries(salud.llm).some(([k, v]) => k !== "modelo" && v === "ok");

  return (
    <ConNav titulo="Panel de estudio">
      <div className="flex gap-3 mb-6">
        <button className="boton-primario" onClick={escanear}>🔍 Escanear fuentes</button>
        <button className="boton-neutro" onClick={cargar}>♻️ Actualizar</button>
      </div>
      {mensaje && <div className="tarjeta mb-6 text-sm">{mensaje}</div>}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="tarjeta">
          <div className="text-3xl font-bold text-navy-700">{totalDocs}</div>
          <div className="text-sm text-gray-600">documentos indexados</div>
        </div>
        <div className="tarjeta">
          <div className="text-3xl font-bold text-navy-700">{stats?.chunks ?? "—"}</div>
          <div className="text-sm text-gray-600">fragmentos (chunks)</div>
        </div>
        <div className="tarjeta">
          <div className="text-3xl font-bold text-navy-700">{stats?.envios_ok ?? "—"}</div>
          <div className="text-sm text-gray-600">tips enviados por correo</div>
        </div>
        <div className="tarjeta">
          <div className="text-3xl font-bold text-navy-700">{stats?.flashcards ?? "—"}</div>
          <div className="text-sm text-gray-600">flashcards</div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="tarjeta">
          <h2 className="font-semibold mb-2">Estado del sistema</h2>
          <ul className="text-sm space-y-1">
            <li>API: <span className={salud?.api === "ok" ? "text-green-600 font-semibold" : "text-red-600"}>{salud?.api ?? "…"}</span></li>
            <li>Base de datos: <span className={salud?.db === "ok" ? "text-green-600 font-semibold" : "text-red-600"}>{salud?.db ?? "…"}</span></li>
            <li>LLM ({salud?.llm?.modelo ?? "—"}):{" "}
              <span className={llmOk ? "text-green-600 font-semibold" : "text-amber-600"}>
                {llmOk ? "disponible" : "no disponible (usa fallback o activa perfil gpu)"}
              </span>
            </li>
          </ul>
        </div>
        <div className="tarjeta">
          <h2 className="font-semibold mb-2">Ingesta</h2>
          <ul className="text-sm space-y-1">
            {Object.entries(stats?.documentos?.por_estado || {}).map(([estado, n]: any) => (
              <li key={estado}>
                <span className={
                  estado === "listo" ? "chip bg-green-100 text-green-700"
                  : estado === "error" ? "chip bg-red-100 text-red-700"
                  : estado === "procesando" ? "chip bg-blue-100 text-blue-700"
                  : "chip bg-lightPrimary text-gray-600"
                }>{estado}</span> {n} documento(s)
              </li>
            ))}
            {Object.entries(stats?.documentos?.por_tipo || {}).map(([tipo, n]: any) => (
              <li key={tipo} className="text-gray-600">{tipo}: {n}</li>
            ))}
          </ul>
        </div>
        <div className="tarjeta">
          <h2 className="font-semibold mb-2">Tips</h2>
          <p className="text-sm">Total generados: {tipsStats?.total ?? "—"}</p>
          <p className="text-sm">Cobertura de temas: {tipsStats?.cobertura_chunks?.pct ?? 0}% ({tipsStats?.cobertura_chunks?.cubiertos ?? 0}/{tipsStats?.cobertura_chunks?.total ?? 0} chunks)</p>
          <p className="text-sm text-gray-600 mt-1">
            Último enviado: {tipsStats?.ultimo_enviado ? `${tipsStats.ultimo_enviado.fecha} — ${tipsStats.ultimo_enviado.titulo}` : "ninguno aún"}
          </p>
        </div>
        <div className="tarjeta md:col-span-2">
          <h2 className="font-semibold mb-3">Temas de estudio</h2>
          <div className="flex flex-wrap gap-2">
            {(stats?.temas || []).map((t: any) => (
              <span key={t.id} className="chip text-xs px-3 py-1"
                    style={{ background: t.color + "22", color: t.color }}>
                ● {t.nombre}: {t.documentos} docs
              </span>
            ))}
            {!stats?.temas?.length && <span className="text-sm text-gray-500">Sin temas aún (crea uno en Temas)</span>}
          </div>
        </div>
        <div className="tarjeta">
          <h2 className="font-semibold mb-2">Grafo de conceptos</h2>
          <p className="text-sm">{stats?.grafo?.nodos ?? "—"} nodos · {stats?.grafo?.aristas ?? "—"} relaciones</p>
          <p className="text-xs text-gray-600 mt-1">Los conceptos de tus documentos conectan fragmentos entre fuentes (ver Documentos → grafo).</p>
        </div>
      </div>
    </ConNav>
  );
}
