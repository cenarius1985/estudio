"""Plantilla HTML del tip diario: cabecera, caja con borde, botón y versión
texto-plano, con el nombre del tema de estudio.

El tip guarda su cuerpo HTML/texto en BD; reenviar usa exactamente eso
(0 reprocesamiento).

Fórmulas: el LLM genera LaTeX delimitado ($$display$$ / $inline$) y se
RENDERIZA A IMAGEN en el servidor (`rag.matematica.latex_a_img`, matplotlib
mathtext) embebida como data-URI — Gmail/Outlook no ejecutan JS (KaTeX/
MathJax imposibles) pero sí muestran imágenes data:. El mismo cuerpo_html
sirve para el correo y el panel. Si mathtext no soporta una expresión, la
fórmula degrada a la caja monoespaciada azul con texto.
  - fórmula $$...$$ en su línea → ecuación centrada (imagen)
  - símbolo $...$ inline → imagen alineada al texto
  - línea-fórmula suelta sin $$ → caja centrada con fuente mono (retrocompat)
Tablas markdown (|a|b|) → <table> con estilo inline.
La versión texto-plano convierte el LaTeX a notación Unicode compacta.
"""

from __future__ import annotations

import html as _html
import re

from estudio.rag.matematica import latex_a_img

TITULO = "📚 Tip de estudio"

_MONO = "font-family:'Cascadia Code','Consolas','Courier New',monospace"

# $$fórmula$$ (display, puede ocupar su línea) y $símbolo$ (inline, sin saltos)
_MATH_SPLIT_RE = re.compile(r"(\$\$.+?\$\$|\$[^$\n]+?\$)", re.DOTALL)


def _limpiar_residuo_latex(t: str) -> str:
    """LaTeX → Unicode compacto (texto plano y fallbacks). Nunca falla."""
    t = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", t)
    t = re.sub(r"\\(?:mathrm|text|textbf|textrm)\{([^{}]+)\}", r"\1", t)
    t = re.sub(r"\^\{([^{}]+)\}", r"^(\1)", t)
    t = re.sub(r"_\{([^{}]+)\}", r"_(\1)", t)
    t = t.replace("\\(", " ").replace("\\)", " ")    # delimitadores inline
    t = t.replace("\\[", " ").replace("\\]", " ")    # delimitadores display
    t = t.replace("\\$", "$")                        # \$ escapado
    t = re.sub(r"\$\$?([^$]*)\$\$?", r"\1", t)       # $...$ → contenido
    t = t.replace("$", " ")                          # $ sueltos restantes
    t = t.replace("\\times", "×").replace("\\cdot", "·")
    t = t.replace("\\approx", "≈").replace("\\Rightarrow", "⇒")
    t = t.replace("\\alpha", "α").replace("\\beta", "β")
    t = t.replace("\\Delta", "Δ").replace("\\delta", "δ").replace("\\lambda", "λ")
    t = t.replace("\\gamma", "γ").replace("\\omega", "ω").replace("\\mu", "µ")
    t = t.replace("\\tau", "τ").replace("\\pi", "π").replace("\\rho", "ρ")
    t = t.replace("\\sigma", "σ").replace("\\theta", "θ").replace("\\phi", "φ")
    t = t.replace("\\Omega", "Ω").replace("\\nu", "ν").replace("\\epsilon", "ε")
    t = t.replace("\\int", "∫").replace("\\sum", "Σ").replace("\\sqrt", "√")
    t = t.replace("\\,", " ").replace("\\;", " ").replace("\\ ", " ")
    t = t.replace("\\left", "").replace("\\right", "")
    t = re.sub(r"\\([a-zA-Z]+)", r"\1", t)           # resto de comandos
    t = t.replace("{", "").replace("}", "")          # llaves LaTeX sueltas
    t = t.replace("--", "—")
    return t


def _img_math(latex: str, display: bool) -> str:
    """<img data-URI> de la fórmula; '' si mathtext no la soporta.

    Atributos width/height explícitos (Gmail los respeta) + max-width por
    si la ecuación es más ancha que la tarjeta en pantallas chicas.
    """
    r = latex_a_img(latex)
    if r is None:
        return ""
    alt = _html.escape(_limpiar_residuo_latex(latex))
    img = (
        f'<img src="{r["src"]}" alt="{alt}" width="{r["ancho"]}" '
        f'height="{r["alto"]}" '
        'style="vertical-align:middle;max-width:100%;height:auto">'
    )
    if display:
        return f'<div style="text-align:center;margin:12px 0">{img}</div>'
    return img


def _caja_formula(texto: str) -> str:
    """Caja azul monoespaciada (fórmulas Unicode o LaTeX no renderizable)."""
    return (
        f'<div style="{_MONO};background:#eef2f7;border:1px solid #d3dce8;'
        "border-radius:6px;padding:10px 14px;margin:10px auto;"
        "font-size:14.5px;color:#1a365d;text-align:center;"
        f'white-space:nowrap;overflow-x:auto">{texto}</div>'
    )


def renderizar_matematica(texto: str) -> str:
    """HTML con fórmulas y tablas renderizadas para clientes de correo.

    Input: texto plano con LaTeX delimitado ($$…$$, $…$), fórmulas Unicode
    sueltas y tablas markdown. El LaTeX se convierte a imagen; el resto se
    escapa y se embellece.
    """
    # ── separar segmentos math ANTES de escapar el HTML ──
    segmentos: list[tuple[str, str]] = []  # ("texto"|"math", contenido)
    for parte in _MATH_SPLIT_RE.split(texto):
        if not parte:
            continue
        if parte.startswith("$$"):
            segmentos.append(("math-display", parte[2:-2]))
        elif parte.startswith("$"):
            segmentos.append(("math-inline", parte[1:-1]))
        else:
            segmentos.append(("texto", parte))

    # ── render: texto → escape+limpieza; math → img (o caja fallback) ──
    trozos: list[str] = []
    for tipo, contenido in segmentos:
        if tipo == "texto":
            for ln in _limpiar_residuo_latex(_html.escape(contenido)).split("\n"):
                if _es_formula(ln):
                    trozos.append(_caja_formula(ln.strip()))
                else:
                    trozos.append(ln)
        elif tipo == "math-display":
            img = _img_math(contenido.strip(), display=True)
            trozos.append(img if img else _caja_formula(
                _html.escape(_limpiar_residuo_latex(contenido.strip()))))
        else:  # inline
            img = _img_math(contenido.strip(), display=False)
            trozos.append(img if img else _html.escape(_limpiar_residuo_latex(contenido)))
    t = "\n".join(trozos)

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
    return "\n".join(salida)


def _es_formula(ln: str) -> bool:
    """Línea que «parece fórmula» Unicode suelta: tiene =, símbolos
    matemáticos y pocas letras (sin verbos españoles largos)."""
    s = ln.strip()
    if len(s) < 6 or len(s) > 160:
        return False
    if "=" not in s:
        return False
    simbolos = sum(s.count(c) for c in "=()+*/·×≈∫Σ√^_")
    letras = sum(c.isalpha() for c in s)
    return simbolos >= 2 and letras / max(len(s), 1) < 0.6


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
    out = []
    for p in parrafos:
        r = renderizar_matematica(p)
        # párrafo que ES una ecuación display: el <div> centrado va suelto
        # (un div dentro de <p> es HTML inválido; Gmail es laxo pero mejor
        # no arriesgar)
        if r.startswith('<div style="text-align:center') and "<p" not in r:
            out.append(r)
        else:
            out.append(f'<p style="margin:0 0 12px">{r}</p>')
    cuerpo = "\n".join(out)
    if citas:
        items = "".join(
            f'<li style="margin:2px 0">{c["archivo"]}'
            + (f' — pág. {c["pagina"]}' if c.get("pagina") else "")
            + "</li>"
            for c in citas
        )
        cuerpo += (
            '<div style="margin-top:14px;font-size:13px;color:#556">'
            "<b style='color:#2c3e50'>Fuentes (tus documentos):</b>"
            f"<ul style='margin:6px 0 0 18px;padding:0'>{items}</ul></div>"
        )
    return cuerpo


def cuerpo_texto_de(parrafos: list[str], citas: list[dict]) -> str:
    """Versión texto-plano: el LaTeX se compacta a Unicode legible."""
    plano = [_limpiar_residuo_latex(p) for p in parrafos]
    out = "\n\n".join(plano)
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
