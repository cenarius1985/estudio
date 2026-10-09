"use client";

import { useEffect, useState } from "react";
import ConNav from "@/components/ConNav";
import { api } from "@/lib/api";

export default function Ajustes() {
  const [datos, setDatos] = useState<any>(null);
  const [mensaje, setMensaje] = useState("");
  const [mostrarTuto, setMostrarTuto] = useState(false);

  // Correo Brevo
  const [smtp, setSmtp] = useState({ smtp_host: "", smtp_puerto: 587, smtp_user: "", smtp_pass: "", smtp_from: "" });
  // Tips
  const [tips, setTips] = useState({ tips_hora: "", tips_to: "", tips_por_dia: 1, tips_umbral_dedupe: 0.9, tips_reintentos: 3, tips_habilitado: true });
  // Fuentes
  const [ruta, setRuta] = useState("");
  const [url, setUrl] = useState("");
  // LLM
  const [llm, setLlm] = useState({ llm_base_url: "", llm_fallback_url: "", llm_model: "" });
  const [llmApiKey, setLlmApiKey] = useState("");
  const [proveedores, setProveedores] = useState<any[]>([]);
  const [proveedor, setProveedor] = useState("local");
  // Seguridad
  const [passNueva, setPassNueva] = useState("");

  async function cargar() {
    const d = await api("/ajustes");
    setDatos(d);
    setSmtp({
      smtp_host: d.smtp.host, smtp_puerto: d.smtp.puerto, smtp_user: d.smtp.usuario,
      smtp_pass: "", smtp_from: d.smtp.from,
    });
    setTips({
      tips_hora: d.tips.hora, tips_to: d.tips.destinos?.join(", ") || "",
      tips_por_dia: d.tips.por_dia || 1,
      tips_umbral_dedupe: d.tips.umbral, tips_reintentos: d.tips.reintentos,
      tips_habilitado: d.tips.habilitado,
    });
    setRuta(d.ruta_fuentes);
    setLlm({ llm_base_url: d.llm.base_url, llm_fallback_url: d.llm.fallback_url, llm_model: d.llm.model });
    try {
      const provs = await api("/ajustes/llm/proveedores");
      setProveedores(provs);
      const match = provs.find((p: any) => p.base_url === d.llm.base_url);
      if (match) setProveedor(match.id);
    } catch { /* catálogo opcional */ }
  }

  function elegirProveedor(id: string) {
    setProveedor(id);
    const p = proveedores.find((x: any) => x.id === id);
    if (!p) return;
    if (p.base_url) setLlm((prev) => ({ ...prev, llm_base_url: p.base_url }));
    if (p.model) setLlm((prev) => ({ ...prev, llm_model: p.model }));
  }

  useEffect(() => {
    cargar().catch((e) => setMensaje(e.message));
  }, []);

  async function guardarSeccion(payload: Record<string, any>, texto: string) {
    try {
      const r = await api("/ajustes", { method: "PUT", body: JSON.stringify(payload) });
      setMensaje(`✅ ${texto} — guardado: ${r.cambios.join(", ") || "sin cambios"}`);
      cargar();
    } catch (exc: any) {
      setMensaje(`❌ ${exc.message}`);
    }
  }

  async function probarSmtp() {
    setMensaje("Probando SMTP…");
    const r = await api("/ajustes/probar-smtp", { method: "POST" });
    setMensaje(`${r.ok ? "✅" : "❌"} ${r.mensaje}`);
  }

  async function agregarUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setMensaje("Agregando e indexando URL…");
    try {
      const r = await api("/documentos/url", { method: "POST", body: JSON.stringify({ url: url.trim() }) });
      setMensaje(`✅ URL ${r.mensaje || "agregada"} — estará citable en el chat en unos segundos`);
      setUrl("");
    } catch (exc: any) {
      setMensaje(`❌ ${exc.message}`);
    }
  }

  return (
    <ConNav titulo="Configuración">
      {mensaje && <div className="tarjeta mb-4 text-sm">{mensaje}</div>}

      <div className="grid lg:grid-cols-2 gap-4 items-start">
        {/* ---------------- Correo Brevo ---------------- */}
        <div className="tarjeta">
          <h2 className="font-semibold mb-1">📬 Correo — Brevo SMTP</h2>
          <p className="text-xs text-slate-500 mb-3">
            Necesario para los tips diarios. Consigue tus claves gratis en{" "}
            <a className="text-marca-600 underline font-semibold" href="https://www.brevo.com/" target="_blank" rel="noreferrer">
              brevo.com
            </a>{" "}
            —{" "}
            <button className="text-marca-600 underline" onClick={() => setMostrarTuto(!mostrarTuto)}>
              {mostrarTuto ? "ocultar tutorial" : "ver tutorial para conseguir las claves"}
            </button>
          </p>

          {mostrarTuto && (
            <ol className="text-xs text-slate-600 bg-marca-50 rounded-lg p-3 mb-3 list-decimal list-inside space-y-1">
              <li>Crea una cuenta gratuita en <a className="underline" href="https://www.brevo.com/" target="_blank" rel="noreferrer">brevo.com</a> (300 correos/día gratis).</li>
              <li>Verifica tu cuenta con el correo que te envían.</li>
              <li>Entra al menú <b>SMTP &amp; API</b> (Perfil → SMTP &amp; API).</li>
              <li>Pulsa <b>「Generate a new SMTP key」</b> y cópiala: es la <b>contraseña</b> (SMTP_PASS).</li>
              <li>El <b>usuario</b> (SMTP_USER) es el que muestra esa misma página.</li>
              <li>Pega ambos valores aquí abajo y pulsa «Probar autenticación». Host: smtp-relay.brevo.com, puerto 587.</li>
            </ol>
          )}

          <div className="grid grid-cols-2 gap-3 text-sm">
            <label className="block">
              Host
              <input className="entrada mt-1" value={smtp.smtp_host} placeholder="smtp-relay.brevo.com"
                onChange={(e) => setSmtp({ ...smtp, smtp_host: e.target.value })} />
            </label>
            <label className="block">
              Puerto
              <input type="number" className="entrada mt-1" value={smtp.smtp_puerto}
                onChange={(e) => setSmtp({ ...smtp, smtp_puerto: Number(e.target.value) })} />
            </label>
            <label className="block">
              Usuario SMTP
              <input className="entrada mt-1" value={smtp.smtp_user} placeholder="usuario Brevo"
                onChange={(e) => setSmtp({ ...smtp, smtp_user: e.target.value })} />
            </label>
            <label className="block">
              Contraseña SMTP {datos?.smtp.password_seteada ? "(✔ ya configurada)" : ""}
              <input type="password" className="entrada mt-1" value={smtp.smtp_pass} placeholder={datos?.smtp.password_seteada ? "•••••••• (dejar vacío para no cambiar)" : "clave SMTP de Brevo"}
                onChange={(e) => setSmtp({ ...smtp, smtp_pass: e.target.value })} />
            </label>
            <label className="block col-span-2">
              Remitente (quién aparece como «de»)
              <input className="entrada mt-1" value={smtp.smtp_from} placeholder="tu@correo.com"
                onChange={(e) => setSmtp({ ...smtp, smtp_from: e.target.value })} />
            </label>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="boton-primario" onClick={() => guardarSeccion(smtp, "Correo Brevo")}>Guardar correo</button>
            <button className="boton-neutro" onClick={probarSmtp}>🧪 Probar autenticación</button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Estado: {datos?.smtp.configurado ? "✅ configurado" : "⚠ sin configurar"} · Los valores del panel tienen prioridad sobre el .env.
          </p>
        </div>

        {/* ---------------- Tips ---------------- */}
        <div className="tarjeta">
          <h2 className="font-semibold mb-3">✉️ Tips diarios</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label className="block">
              Hora del primer envío (HH:MM)
              <input className="entrada mt-1" value={tips.tips_hora} placeholder="07:30"
                onChange={(e) => setTips({ ...tips, tips_hora: e.target.value })} />
            </label>
            <label className="block">
              Tips por día {tips.tips_por_dia > 1 ? "(repartidos hasta las 22:00)" : ""}
              <input type="number" min={1} max={10} className="entrada mt-1" value={tips.tips_por_dia}
                onChange={(e) => setTips({ ...tips, tips_por_dia: Number(e.target.value) })} />
            </label>
            <label className="block col-span-2">
              Destinatarios (separados por coma)
              <input className="entrada mt-1" value={tips.tips_to} placeholder="tu@correo.com"
                onChange={(e) => setTips({ ...tips, tips_to: e.target.value })} />
            </label>
            <label className="block">
              Umbral dedupe (0.5–1)
              <input type="number" step="0.01" className="entrada mt-1" value={tips.tips_umbral_dedupe}
                onChange={(e) => setTips({ ...tips, tips_umbral_dedupe: Number(e.target.value) })} />
            </label>
            <label className="block">
              Reintentos por tema
              <input type="number" className="entrada mt-1" value={tips.tips_reintentos}
                onChange={(e) => setTips({ ...tips, tips_reintentos: Number(e.target.value) })} />
            </label>
            <label className="flex items-center gap-2 col-span-2">
              <input type="checkbox" checked={tips.tips_habilitado} onChange={(e) => setTips({ ...tips, tips_habilitado: e.target.checked })} />
              Tips diarios habilitados (si un tema ya se envió, se reutiliza de la BD sin reprocesar)
            </label>
          </div>
          <button className="boton-primario mt-3" onClick={() => guardarSeccion(tips, "Tips")}>Guardar tips</button>
        </div>

        {/* ---------------- Fuentes + URL ---------------- */}
        <div className="tarjeta">
          <h2 className="font-semibold mb-1">📁 Fuentes de documentos</h2>
          <p className="text-xs text-slate-500 mb-3">
            Carpeta con tu material: pdf, tex, txt, md, csv, docx, xlsx, imágenes con OCR, ipynb y
            <b> código (.py, .jl, Dockerfile, yaml, sh, sql)</b> — las citas de código indican líneas exactas.
            En Docker debe estar montada: ajusta <code>RUTA_TESIS</code> en el <code>.env</code> y ejecuta <code>docker compose up -d</code>.
          </p>
          <label className="block text-sm">
            Carpeta (ruta vista por el contenedor)
            <input className="entrada mt-1" value={ruta} placeholder="/fuentes"
              onChange={(e) => setRuta(e.target.value)} />
          </label>
          <p className="text-xs mt-1">
            {datos?.ruta_fuentes_existe ? "✅ la carpeta existe" : "⚠️ la carpeta NO existe en el contenedor"}
          </p>
          <button className="boton-primario mt-2" onClick={() => guardarSeccion({ ruta_fuentes: ruta }, "Carpeta de fuentes")}>
            Guardar carpeta
          </button>

          <hr className="my-4" />
          <h3 className="font-semibold text-sm mb-2">🔗 Agregar página web como fuente</h3>
          <form onSubmit={agregarUrl} className="flex gap-2">
            <input className="entrada flex-1" value={url} placeholder="https://ejemplo.com/pagina-que-quieras-estudiar"
              onChange={(e) => setUrl(e.target.value)} />
            <button className="boton-primario" disabled={!url.trim()}>Agregar</button>
          </form>
          <p className="text-[11px] text-slate-400 mt-2">
            La página se descarga, se indexa y queda citable en el chat y los tips (mostrando su URL).
          </p>
        </div>

        {/* ---------------- LLM ---------------- */}
        <div className="tarjeta">
          <h2 className="font-semibold mb-1">🤖 LLM</h2>
          <p className="text-xs text-slate-500 mb-3">
            Local (Bonsai/Ollama, gratis y privado) o <b>de pago</b> con tu propia API key —
            más avanzado que Bonsai si lo necesitas.
          </p>
          <div className="space-y-3 text-sm">
            <label className="block">
              Proveedor
              <select className="entrada mt-1" value={proveedor} onChange={(e) => elegirProveedor(e.target.value)}>
                {proveedores.map((p: any) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre}
                  </option>
                ))}
              </select>
            </label>
            {(() => {
              const p = proveedores.find((x: any) => x.id === proveedor);
              if (!p?.requiere_api_key || !p.url_key) return null;
              return (
                <p className="text-xs bg-amber-50 border border-amber-200 rounded-lg p-2">
                  🔑 Consigue tu API key en{" "}
                  <a className="text-marca-600 underline font-semibold" href={p.url_key} target="_blank" rel="noreferrer">
                    {p.url_key.replace(/^https?:\/\//, "")}
                  </a>
                  <br />
                  <span className="text-slate-500">
                    Ojo: con un LLM en la nube, los fragmentos recuperados de tus documentos se envían a ese proveedor para responder.
                  </span>
                </p>
              );
            })()}
            <label className="block">
              Endpoint primario
              <input className="entrada mt-1" value={llm.llm_base_url} placeholder="http://bonsai:8080/v1"
                onChange={(e) => setLlm({ ...llm, llm_base_url: e.target.value })} />
            </label>
            <label className="block">
              API key {datos?.llm?.api_key_seteada ? "(✔ ya configurada — vacío = no cambiar)" : "(solo proveedores de pago)"}
              <input type="password" className="entrada mt-1" value={llmApiKey} placeholder="sk-…"
                onChange={(e) => setLlmApiKey(e.target.value)} />
            </label>
            <label className="block">
              Endpoint de respaldo (opcional, p. ej. Ollama)
              <input className="entrada mt-1" value={llm.llm_fallback_url} placeholder="http://host.docker.internal:11434/v1"
                onChange={(e) => setLlm({ ...llm, llm_fallback_url: e.target.value })} />
            </label>
            <label className="block">
              Modelo
              <input className="entrada mt-1" value={llm.llm_model} placeholder="ternary-bonsai-2-27b"
                onChange={(e) => setLlm({ ...llm, llm_model: e.target.value })} />
            </label>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="boton-primario" onClick={() => guardarSeccion(
              llmApiKey ? { ...llm, llm_api_key: llmApiKey } : llm, "LLM"
            ).then(() => setLlmApiKey(""))}>Guardar LLM</button>
            <button className="boton-neutro" onClick={async () => {
              setMensaje("Consultando (valida también la API key)…");
              const e = await api("/ajustes/estado");
              setMensaje("LLM: " + Object.entries(e.llm).map(([k, v]) => `${k} → ${v}`).join(" · "));
            }}>🩺 Estado</button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Embeddings: multilingual-e5-large (local, CPU — siempre privado)</p>
        </div>

        {/* ---------------- Seguridad ---------------- */}
        <div className="tarjeta">
          <h2 className="font-semibold mb-3">🔐 Contraseña del panel</h2>
          <label className="block text-sm">
            Nueva contraseña (mín. 8; vacío = sin cambio)
            <input type="password" className="entrada mt-1" value={passNueva} placeholder="••••••••"
              onChange={(e) => setPassNueva(e.target.value)} />
          </label>
          <div className="flex gap-2 mt-3">
            <button className="boton-primario" onClick={async () => {
              if (!passNueva) return setMensaje("Escribe la nueva contraseña");
              await guardarSeccion({ admin_password_nueva: passNueva }, "Contraseña");
              setPassNueva("");
            }}>Cambiar</button>
            <button className="boton-neutro" onClick={() => guardarSeccion({ admin_password_restablecer: true }, "Contraseña")}>
              Volver a la del .env
            </button>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Actual: {datos?.password_panel || "…"} · al cambiarla se cierran las sesiones (vuelve a iniciar sesión).
          </p>
        </div>
      </div>
    </ConNav>
  );
}
