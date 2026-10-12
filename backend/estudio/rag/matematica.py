"""LaTeX → PNG embebido (data URI) para las fórmulas de los tips.

Gmail/Outlook no ejecutan JavaScript (KaTeX/MathJax en vivo imposibles) pero
SÍ muestran imágenes ``data:`` embebidas: matplotlib mathtext renderiza cada
fórmula en el servidor y el mismo ``cuerpo_html`` sirve para el correo y el
panel. mathtext cubre el subconjunto de una línea que usan las fórmulas de
la tesis (\\int, \\sum, \\frac, griegas, sub/superíndices); si una expresión
no la soporta, devolvemos None y el llamador degrada a texto.

Import diferido de matplotlib: el worker-urgente no paga su RAM salvo cuando
el tip trae fórmulas.
"""

from __future__ import annotations

import base64
import io
import re
from functools import lru_cache

COLOR = "#1a365d"  # azul del correo (caja del tip / fórmulas)
DPI = 200          # el CSS usa px/2 → nítido en pantallas retina

_ENTORNO_RE = re.compile(r"\\(?:begin|end)\{")
_COMANDO_TEXT_RE = re.compile(r"\\(?:text|textbf|textrm)\{")


def _sanear(latex: str) -> str | None:
    """Adapta el LaTeX del LLM a lo que mathtext soporta.

    None si hay entornos multi-línea (align/cases/…) — no renderizables.
    """
    if _ENTORNO_RE.search(latex):
        return None
    return _COMANDO_TEXT_RE.sub(r"\\mathrm{", latex)


@lru_cache(maxsize=256)  # T2*, S(TE)… se repiten entre tips y reenvíos
def _render(latex: str, color: str) -> tuple[bytes, int, int]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    fig = plt.figure(figsize=(0.01, 0.01))
    try:
        fig.text(0, 0, f"${latex}$", fontsize=15, color=color)
        buf = io.BytesIO()
        fig.savefig(
            buf, dpi=DPI, format="png", transparent=True,
            bbox_inches="tight", pad_inches=0.06,
        )
        png = buf.getvalue()
    finally:
        plt.close(fig)
    with Image.open(io.BytesIO(png)) as im:
        ancho, alto = im.size
    return png, ancho, alto


def latex_a_img(latex: str, color: str = COLOR) -> dict | None:
    """→ {src: data-URI, ancho, alto, bytes} en píxeles CSS (mitad del render).

    None si la expresión no es renderizable → el llamador muestra texto.
    """
    lx = (latex or "").strip().strip("$").strip()
    if not lx or "$" in lx:
        return None
    saneado = _sanear(lx)
    if saneado is None:
        return None
    try:
        png, ancho, alto = _render(saneado, color)
    except Exception:  # mathteth rechaza sintaxis que no conoce
        return None
    b64 = base64.b64encode(png).decode()
    return {
        "src": f"data:image/png;base64,{b64}",
        "ancho": max(10, round(ancho / 2)),
        "alto": max(10, round(alto / 2)),
        "bytes": len(png),
    }
