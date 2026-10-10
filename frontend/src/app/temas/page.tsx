"use client";

import { useEffect, useState } from "react";
import ConNav from "@/components/ConNav";
import { api } from "@/lib/api";

/** Selector de carpetas: chips + explorador visual del montaje de fuentes. */
function SelectorCarpetas({ valor, onChange }: { valor: string; onChange: (v: string) => void }) {
  const [explorando, setExplorando] = useState(false);
  const [rutaActual, setRutaActual] = useState("");
  const [hijos, setHijos] = useState<any[]>([]);
  const [manual, setManual] = useState("");
  const chips = valor.split(",").map((c) => c.trim()).filter(Boolean);

  async function abrir(ruta: string) {
    setRutaActual(ruta);
    const r = await api(`/temas/carpetas?ruta=${encodeURIComponent(ruta)}`);
    setHijos(r.carpetas);
    setExplorando(true);
  }

  function agregar(carpeta: string) {
    if (!chips.includes(carpeta)) onChange([...chips, carpeta].join(","));
  }

  function quitar(carpeta: string) {
    onChange(chips.filter((c) => c !== carpeta).join(","));
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5 mb-2 min-h-8">
        {chips.map((c) => (
          <span key={c} className="chip bg-lightPrimary text-navy-700 flex items-center gap-1">
            📁 {c}
            <button type="button" className="text-brand-500 hover:text-red-600 font-bold"
                    onClick={() => quitar(c)}>✕</button>
          </span>
        ))}
        {!chips.length && <span className="text-xs text-gray-500">Sin carpetas — todo irá a «General»</span>}
      </div>
      <div className="flex gap-2">
        <button type="button" className="boton-neutro !py-1 text-xs" onClick={() => abrir("")}>
          📁 Explorar y añadir carpetas
        </button>
        <input className="entrada flex-1 !py-1 text-xs" value={manual}
               placeholder="…o escribe un prefijo y Enter (si está fuera del montaje)"
               onChange={(e) => setManual(e.target.value)}
               onKeyDown={(e) => {
                 if (e.key === "Enter" && manual.trim()) { agregar(manual.trim()); setManual(""); }
               }} />
      </div>
      <p className="text-[11px] text-gray-500 mt-1">
        El explorador muestra lo montado en <code>RUTA_TESIS</code>; para carpetas de otro punto del disco,
        amplía esa variable en el <code>.env</code> y haz <code>docker compose up -d</code>.
      </p>

      {explorando && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-6 z-50"
             onClick={() => setExplorando(false)}>
          <div className="tarjeta max-w-lg w-full max-h-[75vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold text-sm">Explorador de carpetas</h3>
              <div className="flex gap-2">
                {rutaActual && (
                  <button className="boton-primario !px-2 !py-1 text-xs"
                          onClick={() => agregar(rutaActual)}>✚ Añadir «{rutaActual.split("/").pop()}»</button>
                )}
                <button className="boton-neutro !px-2 !py-1 text-xs" onClick={() => setExplorando(false)}>✕</button>
              </div>
            </div>
            <div className="text-xs text-gray-600 mb-2 flex flex-wrap gap-1 items-center">
              <button className="hover:underline" onClick={() => abrir("")}>fuentes/</button>
              {rutaActual.split("/").filter(Boolean).map((seg, i, arr) => (
                <span key={i}>
                  <button className="hover:underline"
                          onClick={() => abrir(arr.slice(0, i + 1).join("/"))}>{seg}/</button>
                </span>
              ))}
            </div>
            {hijos.length === 0 && <p className="text-sm text-gray-500 py-4 text-center">Sin subcarpetas aquí</p>}
            {hijos.map((h) => (
              <div key={h.ruta} className="flex items-center gap-2 border-b last:border-0 py-1.5 text-sm">
                <button className="flex-1 text-left hover:text-brand-500 truncate"
                        onClick={() => abrir(h.ruta)} title={`Entrar en ${h.ruta}`}>
                  📂 {h.nombre}
                  <span className="text-xs text-gray-500 ml-2">{h.documentos} docs</span>
                </button>
                <button className="boton-neutro !px-2 !py-0.5 text-xs"
                        onClick={() => agregar(h.ruta)} title="Añadir como carpeta del tema">✚</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Temas() {
  const [temas, setTemas] = useState<any[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [nuevo, setNuevo] = useState({ nombre: "", descripcion: "", color: "#2c5282", carpetas: "", prioridades: "", enfoque: "", tips_activo: true });
  const [editando, setEditando] = useState<any>(null);

  async function cargar() {
    try {
      setTemas(await api("/temas"));
    } catch (e: any) {
      setMensaje(e.message);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function crear(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await api("/temas", { method: "POST", body: JSON.stringify(nuevo) });
      setMensaje(`✅ Tema creado${r.nota ? " — " + r.nota : ""}`);
      setNuevo({ nombre: "", descripcion: "", color: "#2c5282", carpetas: "", prioridades: "", enfoque: "", tips_activo: true });
      cargar();
    } catch (e: any) {
      setMensaje(`❌ ${e.message}`);
    }
  }

  async function guardarEdicion() {
    if (!editando) return;
    try {
      await api(`/temas/${editando.id}`, {
        method: "PUT",
        body: JSON.stringify({
          nombre: editando.nombre, descripcion: editando.descripcion,
          color: editando.color, carpetas: editando.carpetas,
          prioridades: editando.prioridades, enfoque: editando.enfoque,
          tips_activo: editando.tips_activo,
        }),
      });
      setEditando(null);
      setMensaje("✅ Tema actualizado");
      cargar();
    } catch (e: any) {
      setMensaje(`❌ ${e.message}`);
    }
  }

  async function reclasificar(id: string) {
    setMensaje("Reclasificando…");
    try {
      const r = await api(`/temas/${id}/reclasificar`, { method: "POST" });
      setMensaje(`✅ ${r.movidos} documento(s) movidos a este tema`);
      cargar();
    } catch (e: any) {
      setMensaje(`❌ ${e.message}`);
    }
  }

  async function borrar(t: any) {
    if (!confirm(`¿Eliminar el tema «${t.nombre}»?`)) return;
    try {
      await api(`/temas/${t.id}`, { method: "DELETE" });
      setMensaje("✅ Tema eliminado");
      cargar();
    } catch (e: any) {
      const destino = temas.find((x) => x.id !== t.id);
      if (destino && confirm(`${e.message}\n\n¿Mover sus ${t.documentos} documento(s) a «${destino.nombre}» y eliminar?`)) {
        await api(`/temas/${t.id}?mover_a=${destino.id}`, { method: "DELETE" });
        setMensaje("✅ Tema eliminado y documentos reasignados");
        cargar();
      } else if (!destino) {
        setMensaje(`❌ ${e.message}`);
      }
    }
  }

  return (
    <ConNav titulo="Temas de estudio">
      {mensaje && <div className="tarjeta mb-4 text-sm">{mensaje}</div>}

      <form onSubmit={crear} className="tarjeta mb-6">
        <h2 className="font-semibold mb-3">Nuevo tema</h2>
        <div className="grid md:grid-cols-4 gap-3 text-sm">
          <label className="block">
            Nombre *
            <input className="entrada mt-1" value={nuevo.nombre} placeholder="Oposiciones, Inglés…"
              onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} required />
          </label>
          <label className="block">
            Descripción
            <input className="entrada mt-1" value={nuevo.descripcion}
              onChange={(e) => setNuevo({ ...nuevo, descripcion: e.target.value })} />
          </label>
          <label className="block">
            Color
            <input type="color" className="entrada mt-1 h-9" value={nuevo.color}
              onChange={(e) => setNuevo({ ...nuevo, color: e.target.value })} />
          </label>
          <label className="flex items-center gap-2 pt-6">
            <input type="checkbox" checked={nuevo.tips_activo}
              onChange={(e) => setNuevo({ ...nuevo, tips_activo: e.target.checked })} />
            Tips diarios
          </label>
          <div className="md:col-span-4">
            <label className="block text-sm">Carpetas para auto-clasificar (elige del explorador)</label>
            <div className="mt-1">
              <SelectorCarpetas valor={nuevo.carpetas}
                                onChange={(v) => setNuevo({ ...nuevo, carpetas: v })} />
            </div>
          </div>
          <div className="md:col-span-4">
            <label className="block text-sm">PRIORIDAD — el core del tema (tips y preguntas siembran aquí primero)</label>
            <div className="mt-1">
              <SelectorCarpetas valor={nuevo.prioridades}
                                onChange={(v) => setNuevo({ ...nuevo, prioridades: v })} />
            </div>
          </div>
          <label className="block md:col-span-4">
            Enfoque / nivel (se inyecta en tips, preguntas, flashcards y chat)
            <textarea className="entrada mt-1" rows={2} value={nuevo.enfoque}
              placeholder="Nivel doctoral. Enfoque: física de RM, secuencias UTE (half pulse, ramp sampling, VERSE), relaxometría bi/tri-componente, compressed sensing…"
              onChange={(e) => setNuevo({ ...nuevo, enfoque: e.target.value })} />
          </label>
        </div>
        <button className="boton-primario mt-3">➕ Crear tema</button>
      </form>

      <div className="space-y-3">
        {temas.map((t) => (
          <div key={t.id} className="tarjeta">
            {editando?.id === t.id ? (
              <div className="grid md:grid-cols-4 gap-3 text-sm">
                <input className="entrada" value={editando.nombre}
                  onChange={(e) => setEditando({ ...editando, nombre: e.target.value })} />
                <input className="entrada md:col-span-2" value={editando.descripcion}
                  onChange={(e) => setEditando({ ...editando, descripcion: e.target.value })} />
                <input type="color" className="entrada h-9" value={editando.color}
                  onChange={(e) => setEditando({ ...editando, color: e.target.value })} />
                <div className="md:col-span-4">
                  <SelectorCarpetas valor={editando.carpetas || ""}
                                    onChange={(v) => setEditando({ ...editando, carpetas: v })} />
                  <div className="mt-3">
                    <label className="text-xs text-gray-600">PRIORIDAD (core del tema)</label>
                    <SelectorCarpetas valor={editando.prioridades || ""}
                                      onChange={(v) => setEditando({ ...editando, prioridades: v })} />
                  </div>
                </div>
                <textarea className="entrada md:col-span-4" rows={2} value={editando.enfoque || ""}
                  placeholder="Enfoque / nivel (tips, preguntas, flashcards y chat)"
                  onChange={(e) => setEditando({ ...editando, enfoque: e.target.value })} />
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={editando.tips_activo}
                    onChange={(e) => setEditando({ ...editando, tips_activo: e.target.checked })} />
                  Tips
                </label>
                <div className="flex gap-2 md:col-span-4">
                  <button className="boton-primario" onClick={guardarEdicion}>Guardar</button>
                  <button className="boton-neutro" onClick={() => setEditando(null)}>Cancelar</button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3 flex-wrap">
                <span className="w-4 h-4 rounded-full shrink-0" style={{ background: t.color }} />
                <div className="flex-1 min-w-48">
                  <div className="font-semibold text-sm">{t.nombre}</div>
                  <div className="text-xs text-gray-600">
                    {t.documentos} documentos · {t.chunks} chunks
                    {t.carpetas && <> · carpetas: <code>{t.carpetas}</code></>}
                    {t.tips_activo ? " · ✉️ tips activos" : " · tips apagados"}
                  </div>
                  {t.descripcion && <div className="text-xs text-gray-500 mt-0.5">{t.descripcion}</div>}
                </div>
                <button className="boton-neutro !px-3 !py-1 text-xs" onClick={() => setEditando(t)}>✏️ Editar</button>
                {t.carpetas && (
                  <button className="boton-neutro !px-3 !py-1 text-xs" onClick={() => reclasificar(t.id)}>
                    🔄 Reclasificar
                  </button>
                )}
                <button className="boton-peligro !px-3 !py-1 text-xs" onClick={() => borrar(t)}>🗑️</button>
              </div>
            )}
          </div>
        ))}
      </div>
    </ConNav>
  );
}
