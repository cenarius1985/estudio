"""Plantilla HTML del tip diario: cabecera, caja con borde, botón y versión
texto-plano, con el nombre del tema de estudio.

El tip guarda su cuerpo HTML/texto en BD; reenviar usa exactamente eso
(0 reprocesamiento).

Fórmulas: el LLM genera texto plano (p. ej. S(t)=S_bw*exp(-TE/T2_bw*)).
`renderizar_matematica` lo convierte a HTML legible en clientes de correo
(sin LaTeX, sin MathJax — no funciona en Gmail/Outlook):
  - subíndices: T2_bw  → T<sub>2,bw</sub>
  - superíndices: T2*^2, exp(-TE/T2) se muestran tal cual con fuente mono
  - líneas de fórmula aisladas → caja centrada con fuente monoespaciada
Tablas markdown (|a|b|) → <table> con estilo inline.
"""

from __future__ import annotations

import html as _html
import re

TITULO = "📚 Tip de estudio"

_MONO = "font-family:'Cascadia Code','Consolas','Courier New',monospace"


def renderizar_matematica(texto: str) -> str:
    """HTML con fórmulas y tablas renderizadas para clientes de correo.

    Input: texto plano que puede contener fórmulas, LaTeX residual y tablas
    markdown. Escape de HTML primero, luego transformaciones seguras.
    """
    t = _html.escape(texto)

    # ── LaTeX residual que el LLM a veces emite ──
    t = t.replace("\\(", " ").replace("\\)", " ")    # delimitadores inline
    t = t.replace("\\[", " ").replace("\\]", " ")    # delimitadores display
    t = t.replace("\\$", "$")                        # \$ escapado
    t = re.sub(r"\$\$?([^$]+)\$\$?", r"\1", t)       # $...$ → contenido
    t = t.replace("$", " ")                          # $ sueltos restantes
    t = t.replace("\\times", "×").replace("\\cdot", "·")
    t = t.replace("\\approx", "≈").replace("\\Rightarrow", "⇒")
    t = t.replace("\\alpha", "α").replace("\\beta", "β")
    t = t.replace("\\Delta", "Δ").replace("\\delta", "δ").replace("\\lambda", "λ")
    t = t.replace("\\,", " ").replace("\\;", " ").replace("\\ ", " ")
    t = t.replace("\\mathrm", "").replace("\\text", "").replace("\\textbf", "")
    t = t.replace("\\left", "").replace("\\right", "")
    t = t.replace("\\sum", "Σ").replace("\\sqrt", "√")
    t = t.replace("\\textbf", "").replace("\\text", "").replace("\\mathrm", "")
    t = re.sub(r"\\([a-zA-Z]+)", r"\1", t)           # resto de comandos
    t = t.replace("{", "").replace("}", "")          # llaves LaTeX sueltas
    t = t.replace("--", "—")

    # ── Tablas markdown → HTML ──
    lineas = t.split("\n")
    salida: list[str] = []
    filas_tabla: list[list[str]] = []
    for ln in lineas:
        s = ln.strip()
        if s.startswith("|") and s.endswith("|"):
            celdas = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", c) for c in celdas):  # separador
                continue
            filas_tabla.append(celdas)
            continue
        if filas_tabla:
            salida.append(_tabla_html(filas_tabla))
            filas_tabla = []
        salida.append(ln)
    if filas_tabla:
        salida.append(_tabla_html(filas_tabla))
    t = "\n".join(salida)

    # ── Fórmulas aisladas → caja monoespaciada ──
    # línea que "parece fórmula": contiene = y símbolos matemáticos, sin
    # verbos españoles largos
    def _es_formula(ln: str) -> bool:
        s = ln.strip()
        if len(s) < 6 or len(s) > 160:
            return False
        if "=" not in s:
            return False
        simbolos = sum(s.count(c) for c in "=()+*/·×≈∫Σ√^_")
        letras = sum(c.isalpha() for c in s)
        return simbolos >= 2 and letras / max(len(s), 1) < 0.6

    partes = []
    for ln in t.split("\n"):
        if _es_formula(ln):
            partes.append(
                f'<div style="{_MONO};background:#eef2f7;border:1px solid #d3dce8;'
                'border-radius:6px;padding:10px 14px;margin:10px auto;'
                'font-size:14.5px;color:#1a365d;text-align:center;'
                f'white-space:nowrap;overflow-x:auto">{ln.strip()}</div>'
            )
        else:
            partes.append(ln)
    return "\n".join(partes)


def _tabla_html(filas: list[list[str]]) -> str:
    """Tabla markdown → <table> con estilo inline amigable con correo."""
    cuerpo = ""
    for i, celdas in enumerate(filas):
        tag = "th" if i == 0 else "td"
        bg = "background:#eef2f7;color:#1a365d" if i == 0 else ""
        tds = "".join(
            f'<{tag} style="border:1px solid #d3dce8;padding:6px 10px;'
            f'font-size:13px;text-align:left;{bg}">{c}</{tag}>'
            for c in celdas
        )
        cuerpo += f"<tr>{tds}</tr>"
    return (
        f'<table style="border-collapse:collapse;margin:12px auto;'
        f'font-size:13px">{cuerpo}</table>'
    )


def cuerpo_html_de(parrafos: list[str], citas: list[dict]) -> str:
    """Bloque interno (párrafos + fuentes) — lo que se almacena en tips.cuerpo_html."""
    renderizados = [renderizar_matematica(p) for p in parrafos]
    out = "\n".join(f'<p style="margin:0 0 12px">{p}</p>' for p in renderizados)
    if citas:
        items = "".join(
            f'<li style="margin:2px 0">{c["archivo"]}'
            + (f' — pág. {c["pagina"]}' if c.get("pagina") else "")
            + "</li>"
            for c in citas
        )
        out += (
            '<div style="margin-top:14px;font-size:13px;color:#556">'
            "<b style='color:#2c3e50'>Fuentes (tus documentos):</b>"
            f"<ul style='margin:6px 0 0 18px;padding:0'>{items}</ul></div>"
        )
    return out


def cuerpo_texto_de(parrafos: list[str], citas: list[dict]) -> str:
    out = "\n\n".join(parrafos)
    if citas:
        out += "\n\nFuentes: " + "; ".join(
            c["archivo"] + (f" pág. {c['pagina']}" if c.get("pagina") else "") for c in citas
        )
    return out


def plantilla_tip(titulo: str, cuerpo_html: str, cuerpo_texto: str, link: str, tema: str | None = None) -> dict:
    """→ {asunto, texto, html}. tema: nombre del tema de estudio (opcional)."""
    sub = f"{tema} · tip diario" if tema else "tip diario"
    asunto = f"{TITULO} · {tema} · {titulo}" if tema else f"{TITULO} · {titulo}"
    return {
        "asunto": asunto,
        "texto": f"{titulo}\n\n{cuerpo_texto}\n\nPlataforma de estudio: {link}\n",
        "html": f"""
<div style="background:#f4f4f4;padding:24px 0;font-family:'Segoe UI',Tahoma,Arial,sans-serif">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,.08)">
    <div style="background:linear-gradient(135deg,#1a365d,#2c5282);color:#fff;padding:22px 24px;text-align:center">
      <h1 style="margin:0;font-size:20px">Estudio</h1>
      <div style="opacity:.85;font-size:13px;margin-top:4px">Tu plataforma de estudio · {sub}</div>
    </div>
    <div style="padding:26px 24px;color:#333;line-height:1.6">
      <div style="background:#f8f9fa;border-left:5px solid #2c5282;border-radius:6px;padding:16px 18px;margin:0 0 20px">
        <div style="font-size:17px;font-weight:700;color:#2c3e50">{titulo}</div>
        <div style="font-size:14.5px;color:#333;margin-top:10px">{cuerpo_html}</div>
      </div>
      <p style="margin:0 0 8px">
        <a href="{link}" style="background:#28a745;color:#fff;padding:11px 22px;border-radius:6px;text-decoration:none;font-weight:700;font-size:14px;display:inline-block">&#128218; Abrir la plataforma</a>
      </p>
      <p style="color:#8a94a6;font-size:12px;margin:10px 0 0">Si el botón no funciona:<br>
        <span style="word-break:break-all">{link}</span></p>
    </div>
    <div style="background:#eee;color:#777;text-align:center;font-size:12px;padding:14px">
      Mensaje automático de tu plataforma de estudio · no responder.
    </div>
  </div>
</div>""",
    }
