"use client";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8600";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export function setToken(t: string) {
  localStorage.setItem("token", t);
}

export function salir() {
  localStorage.removeItem("token");
  window.location.href = "/login";
}

// ---- Tema activo global ("" = Todos) ----
export function getTema(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("tema") || "";
}

export function setTema(temaId: string) {
  localStorage.setItem("tema", temaId);
  window.location.reload(); // todas las páginas refrescan con el nuevo tema
}

export function filtroTema(params: Record<string, string> = {}): string {
  const t = getTema();
  if (!t) return "";
  const sp = new URLSearchParams({ ...params, tema_id: t });
  return `?${sp.toString()}`;
}

export async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "x-token": token } : {}),
      ...(opts.headers || {}),
    },
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error("No autorizado");
  }
  if (!res.ok) {
    const detalle = await res.text();
    throw new Error(`${res.status}: ${detalle.slice(0, 300)}`);
  }
  return res.json();
}

/** Lee el stream SSE de POST /chat y emite eventos parseados. */
export async function chatSSE(
  body: { conversacion_id?: string | null; pregunta: string; tema_id?: string | null },
  onEvento: (nombre: string, dato: any) => void
) {
  const token = getToken();
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { "x-token": token } : {}) },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`chat ${res.status}`);
  const lector = res.body.getReader();
  const dec = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await lector.read();
    if (done) break;
    buffer += dec.decode(value, { stream: true });
    const bloques = buffer.split("\n\n");
    buffer = bloques.pop() || "";
    for (const bloque of bloques) {
      let evento = "mensaje";
      const datos: string[] = [];
      for (const linea of bloque.split("\n")) {
        if (linea.startsWith("event:")) evento = linea.slice(6).trim();
        else if (linea.startsWith("data:")) datos.push(linea.slice(5).trim());
      }
      if (datos.length) {
        try {
          onEvento(evento, JSON.parse(datos.join("\n")));
        } catch {
          onEvento(evento, datos.join("\n"));
        }
      }
    }
  }
}
