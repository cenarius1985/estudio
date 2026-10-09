"use client";

import { useEffect, useState } from "react";
import ConNav from "@/components/ConNav";
import { api } from "@/lib/api";

export default function Temas() {
  const [temas, setTemas] = useState<any[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [nuevo, setNuevo] = useState({ nombre: "", descripcion: "", color: "#2c5282", carpetas: "", enfoque: "", tips_activo: true });
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
      setNuevo({ nombre: "", descripcion: "", color: "#2c5282", carpetas: "", enfoque: "", tips_activo: true });
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
          enfoque: editando.enfoque, tips_activo: editando.tips_activo,
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
          <label className="block md:col-span-4">
            Carpetas para auto-clasificar (prefijos de ruta separados por coma)
            <input className="entrada mt-1" value={nuevo.carpetas}
              placeholder="MRI-UTE PROYECTO DE TESIS, RESULTADOS-MRI, paper-mri-us"
              onChange={(e) => setNuevo({ ...nuevo, carpetas: e.target.value })} />
          </label>
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
                <input className="entrada md:col-span-3" value={editando.carpetas} placeholder="carpetas"
                  onChange={(e) => setEditando({ ...editando, carpetas: e.target.value })} />
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
                  <div className="text-xs text-slate-500">
                    {t.documentos} documentos · {t.chunks} chunks
                    {t.carpetas && <> · carpetas: <code>{t.carpetas}</code></>}
                    {t.tips_activo ? " · ✉️ tips activos" : " · tips apagados"}
                  </div>
                  {t.descripcion && <div className="text-xs text-slate-400 mt-0.5">{t.descripcion}</div>}
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
