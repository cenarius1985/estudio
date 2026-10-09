"use client";

import { useEffect, useState } from "react";
import ConNav from "@/components/ConNav";
import { api, filtroTema, getTema } from "@/lib/api";

const CALIDADES = [
  { q: 1, label: "Otra vez", clase: "bg-red-500 hover:bg-red-600" },
  { q: 3, label: "Difícil", clase: "bg-amber-500 hover:bg-amber-600" },
  { q: 4, label: "Bien", clase: "bg-green-500 hover:bg-green-600" },
  { q: 5, label: "Fácil", clase: "bg-marca-600 hover:bg-marca-700" },
];

export default function Estudio() {
  const [decks, setDecks] = useState<any[]>([]);
  const [quizzes, setQuizzes] = useState<any[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [repaso, setRepaso] = useState<{ deck: any; tarjetas: any[]; idx: number; visible: boolean } | null>(null);
  const [quiz, setQuiz] = useState<{ quiz: any; respuestas: Record<number, number>; resultado: any } | null>(null);

  async function cargar() {
    setDecks(await api(`/estudio/decks${filtroTema()}`));
    setQuizzes(await api(`/estudio/quizzes${filtroTema()}`));
  }

  useEffect(() => {
    cargar().catch((e) => setMensaje(e.message));
  }, []);

  async function crearDeck() {
    setMensaje("Generando deck…");
    try {
      const r = await api("/estudio/decks", {
        method: "POST",
        body: JSON.stringify({ n: 12, tema_id: getTema() || "general" }),
      });
      setMensaje(`Deck ${r.deck_id} en generación`);
      setTimeout(cargar, 4000);
    } catch (e: any) {
      setMensaje(e.message);
    }
  }

  async function repasarDeck(deck: any) {
    const d = await api(`/estudio/decks/${deck.id}?solo_pendientes=true`);
    if (!d.tarjetas.length) {
      setMensaje(`«${deck.titulo}» no tiene tarjetas pendientes hoy 🎉`);
      return;
    }
    setRepaso({ deck: d, tarjetas: d.tarjetas, idx: 0, visible: false });
  }

  async function puntuar(q: number) {
    if (!repaso) return;
    const tarjeta = repaso.tarjetas[repaso.idx];
    await api(`/estudio/flashcards/${tarjeta.id}/repasar`, {
      method: "POST",
      body: JSON.stringify({ calidad: q }),
    });
    const idx = repaso.idx + 1;
    if (idx >= repaso.tarjetas.length) {
      setMensaje(`Repaso completo: ${repaso.tarjetas.length} tarjetas ✅`);
      setRepaso(null);
      cargar();
    } else {
      setRepaso({ ...repaso, idx, visible: false });
    }
  }

  async function crearQuiz(tipo: string) {
    setMensaje(`Generando ${tipo}…`);
    try {
      const r = await api("/estudio/quizzes", {
        method: "POST",
        body: JSON.stringify({
          n: tipo === "simulacro" ? 20 : 10, tipo,
          duracion_min: tipo === "simulacro" ? 30 : 0,
          tema_id: getTema() || "general",
        }),
      });
      setMensaje(`${tipo} ${r.quiz_id} en generación`);
      setTimeout(cargar, 5000);
    } catch (e: any) {
      setMensaje(e.message);
    }
  }

  async function abrirQuiz(q: any) {
    const detalle = await api(`/estudio/quizzes/${q.id}`);
    if (detalle.estado !== "listo") {
      setMensaje(detalle.error || "Aún generándose…");
      return;
    }
    setQuiz({ quiz: detalle, respuestas: {}, resultado: null });
  }

  async function entregarQuiz() {
    if (!quiz) return;
    const respuestas = Object.entries(quiz.respuestas).map(([pid, elegida]) => ({
      pregunta_id: Number(pid),
      elegida,
    }));
    const resultado = await api(`/estudio/quizzes/${quiz.quiz.id}/intentos`, {
      method: "POST",
      body: JSON.stringify({ respuestas }),
    });
    setQuiz({ ...quiz, resultado });
    cargar();
  }

  return (
    <ConNav titulo="Estudio (flashcards · quiz · simulacro)">
      <div className="flex flex-wrap gap-3 mb-4">
        <button className="boton-primario" onClick={crearDeck}>🃏 Generar deck de flashcards</button>
        <button className="boton-neutro" onClick={() => crearQuiz("quiz")}>📝 Generar quiz</button>
        <button className="boton-neutro" onClick={() => crearQuiz("simulacro")}>⏱️ Generar simulacro</button>
        <button className="boton-neutro" onClick={cargar}>♻️</button>
      </div>
      {mensaje && <div className="tarjeta mb-4 text-sm">{mensaje}</div>}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="tarjeta">
          <h2 className="font-semibold mb-3">Decks</h2>
          {decks.map((d) => (
            <div key={d.id} className="flex items-center gap-2 py-2 border-b last:border-0 text-sm">
              <div className="flex-1">
                <div className="font-medium">{d.titulo}</div>
                <div className="text-xs text-slate-500">
                  {d.tarjetas} tarjetas · {d.pendientes_hoy} pendientes hoy ·{" "}
                  <span className={d.estado === "listo" ? "text-green-600" : d.estado === "error" ? "text-red-600" : "text-blue-600"}>{d.estado}</span>
                  {d.error && <span title={d.error}> ⚠️</span>}
                </div>
              </div>
              <button className="boton-primario !px-3 !py-1" onClick={() => repasarDeck(d)} disabled={d.estado !== "listo"}>
                Repasar
              </button>
            </div>
          ))}
          {!decks.length && <p className="text-sm text-slate-400">Sin decks todavía.</p>}
        </div>

        <div className="tarjeta">
          <h2 className="font-semibold mb-3">Quizzes y simulacros</h2>
          {quizzes.map((q) => (
            <div key={q.id} className="flex items-center gap-2 py-2 border-b last:border-0 text-sm">
              <div className="flex-1">
                <div className="font-medium">{q.tipo === "simulacro" ? "⏱️" : "📝"} {q.titulo}</div>
                <div className="text-xs text-slate-500">
                  {q.preguntas} preguntas ·{" "}
                  <span className={q.estado === "listo" ? "text-green-600" : q.estado === "error" ? "text-red-600" : "text-blue-600"}>{q.estado}</span>
                </div>
              </div>
              <button className="boton-neutro !px-3 !py-1" onClick={() => abrirQuiz(q)} disabled={q.estado !== "listo"}>
                Rendir
              </button>
            </div>
          ))}
          {!quizzes.length && <p className="text-sm text-slate-400">Sin quizzes todavía.</p>}
        </div>
      </div>

      {/* ---------- repaso de flashcards ---------- */}
      {repaso && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-8">
          <div className="tarjeta max-w-xl w-full text-center">
            <div className="text-xs text-slate-400 mb-3">
              {repaso.idx + 1} / {repaso.tarjetas.length}
            </div>
            <div className="text-lg font-medium min-h-24 flex items-center justify-center">
              {repaso.tarjetas[repaso.idx].frente}
            </div>
            {repaso.visible ? (
              <>
                <div className="mt-4 p-4 bg-green-50 rounded-lg text-sm">{repaso.tarjetas[repaso.idx].reverso}</div>
                <div className="text-xs text-slate-400 mt-2">
                  📄 {repaso.tarjetas[repaso.idx].cita?.archivo} {repaso.tarjetas[repaso.idx].cita?.pagina ? `· ${repaso.tarjetas[repaso.idx].cita.pagina}` : ""}
                </div>
                <div className="flex justify-center gap-2 mt-5">
                  {CALIDADES.map((c) => (
                    <button key={c.q} className={`boton text-white ${c.clase}`} onClick={() => puntuar(c.q)}>
                      {c.label}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <button className="boton-primario mt-6" onClick={() => setRepaso({ ...repaso, visible: true })}>
                Ver respuesta
              </button>
            )}
            <button className="boton-neutro mt-4 !px-3 !py-1 text-xs" onClick={() => setRepaso(null)}>
              Cerrar repaso
            </button>
          </div>
        </div>
      )}

      {/* ---------- runner de quiz ---------- */}
      {quiz && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-6">
          <div className="tarjeta max-w-2xl w-full max-h-[85vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-semibold">{quiz.quiz.titulo}</h2>
              <button className="boton-neutro !px-2 !py-1" onClick={() => setQuiz(null)}>✕</button>
            </div>
            {quiz.quiz.preguntas.map((p: any, i: number) => {
              const correcta = quiz.resultado ? p.correcta : null;
              const elegida = quiz.respuestas[p.id];
              return (
                <div key={p.id} className="mb-5">
                  <div className="text-sm font-medium mb-2">
                    {i + 1}. {p.enunciado}
                  </div>
                  <div className="space-y-1">
                    {p.alternativas.map((alt: string, j: number) => {
                      let clase = "border border-slate-200 hover:border-marca-600";
                      if (quiz.resultado && j === correcta) clase = "border-green-500 bg-green-50";
                      else if (quiz.resultado && j === elegida && j !== correcta) clase = "border-red-500 bg-red-50";
                      else if (j === elegida) clase = "border-marca-600 bg-marca-50";
                      return (
                        <button
                          key={j}
                          disabled={!!quiz.resultado}
                          className={`block w-full text-left text-sm px-3 py-2 rounded-lg ${clase}`}
                          onClick={() => setQuiz({ ...quiz, respuestas: { ...quiz.respuestas, [p.id]: j } })}
                        >
                          {String.fromCharCode(65 + j)}) {alt}
                        </button>
                      );
                    })}
                  </div>
                  {quiz.resultado && p.explicacion && (
                    <div className="text-xs text-slate-500 mt-1">
                      💡 {p.explicacion} — 📄 {p.cita?.archivo} {p.cita?.pagina ? `· ${p.cita.pagina}` : ""}
                    </div>
                  )}
                </div>
              );
            })}
            {quiz.resultado ? (
              <div className="text-center">
                <div className="text-3xl font-bold text-marca-700">{quiz.resultado.puntaje}%</div>
                <div className="text-sm text-slate-500">
                  {quiz.resultado.aciertos}/{quiz.resultado.total} correctas
                </div>
              </div>
            ) : (
              <button className="boton-primario w-full justify-center" onClick={entregarQuiz}>
                Entregar ({Object.keys(quiz.respuestas).length}/{quiz.quiz.preguntas.length})
              </button>
            )}
          </div>
        </div>
      )}
    </ConNav>
  );
}
