"use client";

import { useEffect, useRef, useState } from "react";
import ConNav from "@/components/ConNav";
import { api, chatSSE } from "@/lib/api";

interface Msg {
  rol: string;
  contenido: string;
  fuentes?: any[];
}

export default function Chat() {
  const [conversaciones, setConversaciones] = useState<any[]>([]);
  const [conversacionId, setConversacionId] = useState<string | null>(null);
  const [mensajes, setMensajes] = useState<Msg[]>([]);
  const [pregunta, setPregunta] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const finRef = useRef<HTMLDivElement>(null);

  async function cargarConversaciones() {
    setConversaciones(await api("/conversaciones"));
  }

  useEffect(() => {
    cargarConversaciones();
  }, []);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes]);

  async function abrir(id: string | null) {
    setConversacionId(id);
    setError("");
    if (!id) {
      setMensajes([]);
      return;
    }
    const m = await api(`/conversaciones/${id}/mensajes`);
    setMensajes(m);
  }

  async function preguntar(e: React.FormEvent) {
    e.preventDefault();
    if (!pregunta.trim() || ocupado) return;
    const q = pregunta;
    setPregunta("");
    setOcupado(true);
    setError("");
    setMensajes((m) => [...m, { rol: "user", contenido: q }, { rol: "assistant", contenido: "", fuentes: [] }]);

    try {
      let convId = conversacionId;
      await chatSSE({ conversacion_id: convId, pregunta: q }, (evento, dato) => {
        if (evento === "inicio") {
          convId = dato.conversacion_id;
          setConversacionId(dato.conversacion_id);
        } else if (evento === "fuentes") {
          setMensajes((m) => {
            const copia = [...m];
            copia[copia.length - 1] = { ...copia[copia.length - 1], fuentes: dato };
            return copia;
          });
        } else if (evento === "delta") {
          setMensajes((m) => {
            const copia = [...m];
            const ult = copia[copia.length - 1];
            copia[copia.length - 1] = { ...ult, contenido: ult.contenido + dato.t };
            return copia;
          });
        } else if (evento === "error") {
          setError(dato.mensaje || String(dato));
        }
      });
      cargarConversaciones();
    } catch (exc: any) {
      setError(exc.message);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <ConNav titulo="Pregunta a tu tesis">
      <div className="flex gap-6 h-[calc(100vh-12rem)]">
        <div className="w-56 shrink-0">
          <button className="boton-primario w-full justify-center mb-3" onClick={() => abrir(null)}>➕ Nueva</button>
          <div className="space-y-1 overflow-y-auto max-h-full">
            {conversaciones.map((c) => (
              <button
                key={c.id}
                onClick={() => abrir(c.id)}
                className={`w-full text-left text-xs px-3 py-2 rounded-lg truncate ${c.id === conversacionId ? "bg-marca-600 text-white" : "bg-white hover:bg-slate-50 border border-slate-200"}`}
                title={c.titulo}
              >
                {c.titulo}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {mensajes.map((m, i) => (
              <div key={i} className={m.rol === "user" ? "text-right" : ""}>
                <div
                  className={`inline-block max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap text-left ${
                    m.rol === "user" ? "bg-marca-600 text-white" : "bg-white border border-slate-200"
                  }`}
                >
                  {m.contenido || (ocupado ? "…" : "")}
                </div>
                {(m.fuentes?.length ?? 0) > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1 justify-end">
                    {(m.fuentes || []).map((f: any, j: number) => (
                      <span key={j} className="chip bg-marca-50 text-marca-700 text-[10px]" title={f.origen === "grafo" ? "vía grafo de conceptos" : "recuperación híbrida"}>
                        📄 {f.archivo}{f.pagina ? ` · ${f.pagina}` : ""}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div ref={finRef} />
          </div>

          {error && <div className="text-red-600 text-xs mb-2">{error}</div>}

          <form onSubmit={preguntar} className="flex gap-2 mt-3">
            <input
              className="entrada flex-1"
              placeholder="Pregunta sobre tu tesis (responde solo con citas a tus documentos)…"
              value={pregunta}
              onChange={(e) => setPregunta(e.target.value)}
              disabled={ocupado}
            />
            <button className="boton-primario" disabled={ocupado || !pregunta.trim()}>
              {ocupado ? "…" : "Enviar"}
            </button>
          </form>
        </div>
      </div>
    </ConNav>
  );
}
