"use client";

import { useEffect, useState } from "react";
import ConNav from "@/components/ConNav";
import { api } from "@/lib/api";

export default function Ajustes() {
  const [datos, setDatos] = useState<any>(null);
  const [form, setForm] = useState({ tips_hora: "", tips_to: "", tips_umbral_dedupe: 0.9, tips_reintentos: 3, tips_habilitado: true });
  const [mensaje, setMensaje] = useState("");

  async function cargar() {
    const d = await api("/ajustes");
    setDatos(d);
    setForm({
      tips_hora: d.tips_hora,
      tips_to: d.tips_to,
      tips_umbral_dedupe: d.tips_umbral_dedupe,
      tips_reintentos: d.tips_reintentos,
      tips_habilitado: d.tips_habilitado,
    });
  }

  useEffect(() => {
    cargar().catch((e) => setMensaje(e.message));
  }, []);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/ajustes", { method: "PUT", body: JSON.stringify(form) });
      setMensaje("✅ Ajustes guardados (aplican en el próximo chequeo del worker, cada 15 min)");
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  async function probarSmtp() {
    setMensaje("Probando SMTP…");
    const r = await api("/ajustes/probar-smtp", { method: "POST" });
    setMensaje(`${r.ok ? "✅" : "❌"} ${r.mensaje}`);
  }

  const llmEntradas = datos ? Object.entries(datos.llm).filter(([k]) => k !== "modelo") : [];

  return (
    <ConNav titulo="Ajustes">
      {mensaje && <div className="tarjeta mb-4 text-sm">{mensaje}</div>}

      <form onSubmit={guardar} className="tarjeta mb-4">
        <h2 className="font-semibold mb-4">Tip diario</h2>
        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <label className="block">
            Hora de envío (HH:MM, hora Chile)
            <input className="entrada mt-1" value={form.tips_hora} onChange={(e) => setForm({ ...form, tips_hora: e.target.value })} placeholder="07:30" />
          </label>
          <label className="block">
            Destinatarios (coma-separated)
            <input className="entrada mt-1" value={form.tips_to} onChange={(e) => setForm({ ...form, tips_to: e.target.value })} placeholder="tu@correo.com" />
          </label>
          <label className="block">
            Umbral de dedupe (0–1; similitud coseno)
            <input type="number" step="0.01" min="0.5" max="1" className="entrada mt-1" value={form.tips_umbral_dedupe} onChange={(e) => setForm({ ...form, tips_umbral_dedupe: Number(e.target.value) })} />
          </label>
          <label className="block">
            Reintentos con otro tema antes de reutilizar
            <input type="number" min="1" max="10" className="entrada mt-1" value={form.tips_reintentos} onChange={(e) => setForm({ ...form, tips_reintentos: Number(e.target.value) })} />
          </label>
          <label className="flex items-center gap-2 md:col-span-2">
            <input type="checkbox" checked={form.tips_habilitado} onChange={(e) => setForm({ ...form, tips_habilitado: e.target.checked })} />
            Tips diarios habilitados
          </label>
        </div>
        <button className="boton-primario mt-4">Guardar</button>
      </form>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="tarjeta">
          <h2 className="font-semibold mb-3">Correo (Brevo SMTP)</h2>
          {datos && (
            <ul className="text-sm space-y-1 text-slate-600">
              <li>Host: {datos.smtp.host || "—"}:{datos.smtp.puerto}</li>
              <li>Usuario: {datos.smtp.usuario || "—"}</li>
              <li>From: {datos.smtp.from || "—"}</li>
              <li>Estado: <span className={datos.smtp.configurado ? "text-green-600 font-semibold" : "text-red-600"}>{datos.smtp.configurado ? "configurado" : "FALTA configurar (.env)"}</span></li>
            </ul>
          )}
          <button className="boton-neutro mt-3" onClick={probarSmtp}>
            🧪 Probar autenticación (sin enviar)
          </button>
        </div>

        <div className="tarjeta">
          <h2 className="font-semibold mb-3">LLM (Bonsai)</h2>
          {datos && (
            <ul className="text-sm space-y-1 text-slate-600">
              <li>Modelo: {datos.llm.modelo}</li>
              <li>Primario: {datos.llm.base_url}</li>
              <li>Fallback: {datos.llm.fallback_url || "— (configura LLM_FALLBACK_URL si usas ollama)"}</li>
              <li>Embeddings: {datos.embed_model}</li>
            </ul>
          )}
          <button
            className="boton-neutro mt-3"
            onClick={async () => {
              const e = await api("/ajustes/estado");
              setMensaje("LLM: " + Object.entries(e.llm).map(([k, v]) => `${k} → ${v}`).join(" · "));
            }}
          >
            🩺 Ver estado ahora
          </button>
          {llmEntradas.length === 0 && null}
        </div>
      </div>
    </ConNav>
  );
}
