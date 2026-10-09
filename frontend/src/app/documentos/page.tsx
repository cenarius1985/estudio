"use client";

import { useEffect, useRef, useState } from "react";
import ConNav from "@/components/ConNav";
import { API_URL, api, filtroTema, getTema, getToken } from "@/lib/api";

export default function Documentos() {
  const [docs, setDocs] = useState<any[]>([]);
  const [temas, setTemas] = useState<any[]>([]);
  const [grafo, setGrafo] = useState<any>(null);
  const [mensaje, setMensaje] = useState("");
  const [detalle, setDetalle] = useState<{ ruta: string; chunks: any[] } | null>(null);
  const [url, setUrl] = useState("");
  const inputArchivo = useRef<HTMLInputElement>(null);

  async function cargar() {
    try {
      setDocs(await api(`/documentos${filtroTema()}`));
      setTemas(await api("/temas"));
      setGrafo(await api("/documentos/grafo/resumen"));
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function moverTema(doc: any, temaId: string) {
    try {
      await api(`/documentos/${doc.id}/tema`, { method: "POST", body: JSON.stringify({ tema_id: temaId }) });
      cargar();
    } catch (e: any) {
      setMensaje(e.message);
    }
  }

  async function subir(e: React.ChangeEvent<HTMLInputElement>) {
    const archivos = e.target.files;
    if (!archivos?.length) return;
    setMensaje("Subiendo…");
    const form = new FormData();
    for (const f of Array.from(archivos)) form.append("archivos", f);
    form.append("tema_id", getTema() || "general");
    const res = await fetch(`${API_URL}/documentos/upload`, {
      method: "POST",
      headers: { "x-token": getToken() || "" },
      body: form,
    });
    setMensaje(res.ok ? "Subidos; indexando…" : `Error subiendo: ${await res.text()}`);
    if (inputArchivo.current) inputArchivo.current.value = "";
    setTimeout(cargar, 2000);
  }

  async function accion(id: string, que: "reindexar" | "borrar") {
    try {
      await api(`/documentos/${id}/${que}`, { method: que === "borrar" ? "DELETE" : "POST" });
      setMensaje(que === "reindexar" ? "Reindexado encolado" : "Documento eliminado");
      cargar();
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  async function verChunks(d: any) {
    const chunks = await api(`/documentos/${d.id}/chunks`);
    setDetalle({ ruta: d.ruta, chunks });
  }

  async function agregarUrl(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setMensaje("Agregando URL…");
    try {
      const r = await api("/documentos/url", {
        method: "POST",
        body: JSON.stringify({ url: url.trim(), tema_id: getTema() || "general" }),
      });
      setMensaje(`🔗 URL ${r.mensaje || "agregada"}`);
      setUrl("");
      setTimeout(cargar, 4000);
    } catch (exc: any) {
      setMensaje(exc.message);
    }
  }

  return (
    <ConNav titulo="Documentos">
      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <button className="boton-primario" onClick={() => api("/documentos/escanear", { method: "POST" }).then((r) => setMensaje(`Escaneo encolado (${r.job})`))}>
          🔍 Escanear fuentes
        </button>
        <input ref={inputArchivo} type="file" multiple className="hidden"
          accept=".pdf,.tex,.txt,.md,.csv,.docx,.xlsx,.png,.jpg,.jpeg,.tif,.tiff,.ipynb" onChange={subir} />
        <button className="boton-neutro" onClick={() => inputArchivo.current?.click()}>⬆️ Subir archivos</button>
        <form onSubmit={agregarUrl} className="flex gap-2 flex-1 min-w-[280px]">
          <input className="entrada" value={url} placeholder="🔗 https://pagina.a.estudiar.com"
            onChange={(e) => setUrl(e.target.value)} />
          <button className="boton-neutro" disabled={!url.trim()}>Agregar URL</button>
        </form>
        <button className="boton-neutro" onClick={cargar}>♻️</button>
      </div>
      {mensaje && <div className="tarjeta mb-4 text-sm">{mensaje}</div>}

      <div className="tarjeta overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-500 border-b">
            <tr>
              <th className="py-2">Ruta</th><th>Tema</th><th>Tipo</th><th>Fuente</th><th>Chunks</th><th>Estado</th><th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="py-2 max-w-md truncate" title={d.ruta}>
                  <button className="text-marca-600 hover:underline" onClick={() => verChunks(d)}>{d.ruta}</button>
                </td>
                <td>
                  <select
                    className="text-xs rounded border border-slate-200 px-1 py-0.5"
                    value={d.tema_id || ""}
                    onChange={(e) => moverTema(d, e.target.value)}
                    title="Mover a tema"
                  >
                    <option value="">— sin tema —</option>
                    {temas.map((t) => (
                      <option key={t.id} value={t.id}>{t.nombre}</option>
                    ))}
                  </select>
                </td>
                <td>{d.tipo}</td>
                <td>{d.fuente}</td>
                <td>{d.chunks}</td>
                <td>
                  <span className={
                    d.estado === "listo" ? "chip bg-green-100 text-green-700"
                    : d.estado === "error" ? "chip bg-red-100 text-red-700"
                    : d.estado === "procesando" ? "chip bg-blue-100 text-blue-700"
                    : "chip bg-slate-100 text-slate-600"
                  }>{d.estado}</span>
                  {d.estado === "error" && <div className="text-xs text-red-500 mt-1 max-w-sm truncate" title={d.error}>{d.error}</div>}
                </td>
                <td className="whitespace-nowrap">
                  <button className="boton-neutro !px-2 !py-1 mr-1" onClick={() => accion(d.id, "reindexar")} title="Reindexar">🔁</button>
                  <button className="boton-peligro !px-2 !py-1" onClick={() => confirm(`¿Eliminar ${d.ruta}?`) && accion(d.id, "borrar")} title="Eliminar">🗑️</button>
                </td>
              </tr>
            ))}
            {!docs.length && <tr><td colSpan={6} className="py-6 text-center text-slate-400">Sin documentos aún — escanea las fuentes</td></tr>}
          </tbody>
        </table>
      </div>

      {(grafo?.nodos?.length ?? 0) > 0 && (
        <div className="tarjeta mt-4">
          <h2 className="font-semibold mb-2">Grafo de conceptos (top por conexiones)</h2>
          <div className="flex flex-wrap gap-2">
            {grafo.nodos.slice(0, 30).map((n: any) => (
              <span key={n.id} className="chip bg-marca-50 text-marca-700" title={`${n.grado} conexiones`}>
                {n.nombre} · {n.grado}
              </span>
            ))}
          </div>
        </div>
      )}

      {detalle && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-8" onClick={() => setDetalle(null)}>
          <div className="tarjeta max-w-3xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-3">
              <h2 className="font-semibold text-sm">{detalle.ruta} — {detalle.chunks.length} chunks</h2>
              <button className="boton-neutro !px-2 !py-1" onClick={() => setDetalle(null)}>✕</button>
            </div>
            {detalle.chunks.map((c: any) => (
              <div key={c.id} className="text-xs border-b py-2 last:border-0">
                <span className="chip bg-slate-100 text-slate-500 mr-2">#{c.n} {c.pagina}</span>
                {c.texto}…
              </div>
            ))}
          </div>
        </div>
      )}
    </ConNav>
  );
}
