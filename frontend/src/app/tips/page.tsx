"use client";

import { useEffect, useState } from "react";
import ConNav from "@/components/ConNav";
import { api } from "@/lib/api";

export default function Tips() {
  const [tips, setTips] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [mensaje, setMensaje] = useState("");
  const [detalle, setDetalle] = useState<any>(null);
  const [forzar, setForzar] = useState(false);

  async function cargar() {
    try {
      setTips(await api("/tips"));
      setStats(await api("/tips/stats"));
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function generar() {
    setMensaje("Generación encolada… el worker crea el tip y lo envía");
    try {
      const r = await api("/tips/generar", { method: "POST", body: JSON.stringify({ forzar }) });
      setMensaje(`Encolado (${r.job}). Forzar=${forzar}`);
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  async function reenviar(id: string) {
    setMensaje("Reenvío encolado (usa el contenido almacenado, sin reprocesar)");
    try {
      await api(`/tips/${id}/reenviar`, { method: "POST" });
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  async function abrir(id: string) {
    setDetalle(await api(`/tips/${id}`));
  }

  return (
    <ConNav titulo="Tips diarios">
      <div className="flex flex-wrap gap-3 items-center mb-4">
        <button className="boton-primario" onClick={generar}>⚡ Generar y enviar ahora</button>
        <label className="text-sm flex items-center gap-2">
          <input type="checkbox" checked={forzar} onChange={(e) => setForzar(e.target.checked)} />
          forzar (regenera aunque hoy ya se envió)
        </label>
        <button className="boton-neutro" onClick={cargar}>♻️</button>
        {stats && (
          <span className="text-sm text-slate-500 ml-auto">
            {stats.total} tips · {stats.envios_ok} envíos OK · cobertura {stats.cobertura_chunks?.pct}%
          </span>
        )}
      </div>
      {mensaje && <div className="tarjeta mb-4 text-sm">{mensaje}</div>}

      <div className="tarjeta">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-500 border-b">
            <tr><th className="py-2">Fecha</th><th>Título</th><th>Estado</th><th>Envíos</th><th></th></tr>
          </thead>
          <tbody>
            {tips.map((t) => (
              <tr key={t.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="py-2 whitespace-nowrap">{t.fecha}</td>
                <td>
                  <button className="text-marca-600 hover:underline" onClick={() => abrir(t.id)}>{t.titulo}</button>
                  {t.duplicado_de && <span className="chip bg-amber-100 text-amber-700 ml-2" title={`Reutiliza el tip del ${t.duplicado_de}`}>duplicado reutilizado</span>}
                </td>
                <td>
                  <span className={
                    t.estado === "enviado" ? "chip bg-green-100 text-green-700"
                    : t.estado === "error" ? "chip bg-red-100 text-red-700"
                    : t.estado === "duplicado" ? "chip bg-amber-100 text-amber-700"
                    : "chip bg-slate-100 text-slate-600"
                  }>{t.estado}</span>
                </td>
                <td>{t.envios?.filter((e: any) => e.estado === "ok").length ?? 0}/{t.envios?.length ?? 0}</td>
                <td className="whitespace-nowrap">
                  <button className="boton-neutro !px-2 !py-1" onClick={() => reenviar(t.id)} title="Reenviar sin reprocesar">✉️ Reenviar</button>
                </td>
              </tr>
            ))}
            {!tips.length && <tr><td colSpan={5} className="py-6 text-center text-slate-400">Aún no hay tips — genera el primero</td></tr>}
          </tbody>
        </table>
      </div>

      {detalle && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-8" onClick={() => setDetalle(null)}>
          <div className="bg-white rounded-xl max-w-2xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center p-4 border-b sticky top-0 bg-white">
              <h2 className="font-semibold">{detalle.titulo} · {detalle.fecha}</h2>
              <div className="flex gap-2">
                <button className="boton-neutro !px-2 !py-1" onClick={() => reenviar(detalle.id)}>✉️ Reenviar</button>
                <button className="boton-neutro !px-2 !py-1" onClick={() => setDetalle(null)}>✕</button>
              </div>
            </div>
            <div className="p-5" dangerouslySetInnerHTML={{ __html: detalle.cuerpo_html }} />
            {detalle.envios?.length > 0 && (
              <div className="px-5 pb-5 text-xs text-slate-500">
                Envíos: {detalle.envios.map((e: any) => `${e.email} (${e.estado})`).join(", ")}
              </div>
            )}
          </div>
        </div>
      )}
    </ConNav>
  );
}
