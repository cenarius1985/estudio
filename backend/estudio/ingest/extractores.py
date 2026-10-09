"""Extractores por formato. Todos devuelven list[Bloque(texto, pagina)].

Formatos: PDF (texto nativo + OCR de páginas escaneadas), LaTeX, TXT/MD, CSV,
Word .docx, Excel .xlsx, imágenes (OCR Tesseract spa+eng) y notebooks .ipynb.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import nbformat
import pytesseract
from docx import Document as Docx
from openpyxl import load_workbook
from PIL import Image

OCR_LANGS = "spa+eng"
FILAS_POR_BLOQUE = 60


class IngestaError(Exception):
    pass


@dataclass
class Bloque:
    texto: str
    pagina: str = ""


EXTENSIONES: dict[str, str] = {
    ".pdf": "pdf",
    ".tex": "latex",
    ".txt": "txt",
    ".md": "txt",
    ".csv": "csv",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".png": "imagen",
    ".jpg": "imagen",
    ".jpeg": "imagen",
    ".tif": "imagen",
    ".tiff": "imagen",
    ".ipynb": "notebook",
}


def tipo_de(ruta: Path) -> str | None:
    return EXTENSIONES.get(ruta.suffix.lower())


def _leer_texto(ruta: Path) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return ruta.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise IngestaError(f"No se pudo decodificar {ruta.name}")


# ---------------------------------------------------------------- PDF


def extraer_pdf(ruta: Path) -> list[Bloque]:
    bloques: list[Bloque] = []
    with fitz.open(ruta) as doc:
        for i, page in enumerate(doc, start=1):
            texto = page.get_text("text").strip()
            if len(texto) < 20:  # página escaneada → OCR
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                texto = pytesseract.image_to_string(img, lang=OCR_LANGS).strip()
            if texto:
                bloques.append(Bloque(texto, str(i)))
    if not bloques:
        raise IngestaError("PDF sin texto extraíble (ni con OCR)")
    return bloques


# ---------------------------------------------------------------- LaTeX

# Comandos cuyo argumento se conserva como texto (títulos, captions)
_KEEP_ARG = {"section", "subsection", "subsubsection", "chapter", "caption", "textbf", "textit", "emph"}
_DROP = (
    r"\\(documentclass|usepackage|inputenc|fontenc|babel|geometry|setlength|"
    r"newcommand|renewcommand|providecommand|definecolor|hypersetup|graphicspath|"
    r"addbibresource|bibliographystyle|includegraphics|label|ref|eqref|cite|"
    r"pagestyle|thispagestyle|fancyhead|fancyfoot|headrulewidth|footrulewidth|"
    r"vspace|hspace|noindent|indent|small|footnotesize|large|Large|centering|"
    r"printbibliography|maketitle|tableofcontents|listoffigures|listoftables|"
    r"newpage|clearpage|footnote|thanks|onehalfspacing|singlespacing|setcounter|"
    r"algorithm|algorithmic|State|Return|Require|Ensure|numberwithin|"
    r"DeclareMathOperator|operatorname|graphicspath|url|href)"
)


def extraer_latex(ruta: Path) -> list[Bloque]:
    src = _leer_texto(ruta)
    src = re.sub(r"(?<!\\)%.*", "", src)  # comentarios
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", src, re.DOTALL)
    if m:
        src = m.group(1)
    # \section{X} / \caption{X} → encabezado markdown
    src = re.sub(
        r"\\(chapter|section|subsection|subsubsection)\*?\{([^{}]*)\}",
        lambda m: f"\n\n## {m.group(2).strip()}\n",
        src,
    )
    src = re.sub(r"\\(caption|textbf|textit|emph)\{([^{}]*)\}", r"\2", src)
    src = re.sub(_DROP + r"\*?(\[[^\]]*\])?", " ", src)
    src = re.sub(r"\\(begin|end)\{[a-zA-Z*]+\}", "\n", src)  # entornos
    src = re.sub(r"\\item\s*", "\n- ", src)
    src = src.replace("\\\\", "\n").replace("\\~", " ").replace("\\%", "%")
    src = src.replace("&", " | ").replace("~", " ")
    src = re.sub(r"\\[a-zA-Z]+\*?", " ", src)  # comandos restantes (math degradado)
    src = src.replace("{", "").replace("}", "")
    src = re.sub(r"[ \t]+", " ", src)
    src = re.sub(r"\n{3,}", "\n\n", src)
    bloques = [Bloque(p.strip(), "tex") for p in src.split("\n\n") if len(p.strip()) > 15]
    if not bloques:
        raise IngestaError("LaTeX sin contenido extraíble")
    return bloques


# ---------------------------------------------------------------- TXT / CSV


def _tabla_markdown(filas: list[list[str]]) -> str:
    if not filas:
        return ""
    ancho = max(len(f) for f in filas)
    filas = [f + [""] * (ancho - len(f)) for f in filas]
    out = ["| " + " | ".join(filas[0]) + " |", "|" + "---|" * ancho]
    out += ["| " + " | ".join(f) + " |" for f in filas[1:]]
    return "\n".join(out)


def extraer_txt(ruta: Path) -> list[Bloque]:
    texto = _leer_texto(ruta)
    partes = [p.strip() for p in re.split(r"\n\s*\n", texto) if len(p.strip()) > 5]
    return [Bloque(p, "") for p in partes] or [Bloque(texto)]


def extraer_csv(ruta: Path) -> list[Bloque]:
    texto = _leer_texto(ruta)
    lector = list(csv.reader(io.StringIO(texto)))
    if not lector:
        raise IngestaError("CSV vacío")
    cabecera = lector[0]
    bloques = []
    for i in range(1, len(lector), FILAS_POR_BLOQUE):
        lote = [cabecera] + lector[i : i + FILAS_POR_BLOQUE]
        bloques.append(Bloque(_tabla_markdown(lote), f"filas {i}-{i + len(lote) - 1}"))
    return bloques


# ---------------------------------------------------------------- Word / Excel


def extraer_docx(ruta: Path) -> list[Bloque]:
    doc = Docx(str(ruta))
    bloques = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if len(t) > 5:
            estilo = (p.style.name or "").lower()
            pref = "## " if "heading" in estilo or "título" in estilo else ""
            bloques.append(Bloque(pref + t, "docx"))
    for tabla in doc.tables:
        filas = [[c.text.strip() for c in fila.cells] for fila in tabla.rows]
        if filas:
            bloques.append(Bloque(_tabla_markdown(filas), "tabla"))
    if not bloques:
        raise IngestaError("DOCX sin texto")
    return bloques


def extraer_xlsx(ruta: Path) -> list[Bloque]:
    wb = load_workbook(str(ruta), read_only=True, data_only=True)
    bloques = []
    for hoja in wb.worksheets:
        filas = []
        for fila in hoja.iter_rows(values_only=True):
            celdas = ["" if c is None else str(c) for c in fila]
            if any(c.strip() for c in celdas):
                filas.append(celdas)
        if not filas:
            continue
        for i in range(0, len(filas), FILAS_POR_BLOQUE):
            lote = filas[i : i + FILAS_POR_BLOQUE]
            bloques.append(Bloque(_tabla_markdown(lote), f"hoja {hoja.title} filas {i + 1}-{i + len(lote)}"))
    wb.close()
    if not bloques:
        raise IngestaError("XLSX sin celdas con contenido")
    return bloques


# ---------------------------------------------------------------- imagen / notebook


def extraer_imagen(ruta: Path) -> list[Bloque]:
    img = Image.open(ruta)
    if max(img.size) > 3000:
        escala = 3000 / max(img.size)
        img = img.resize((int(img.width * escala), int(img.height * escala)))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    texto = pytesseract.image_to_string(img, lang=OCR_LANGS).strip()
    if len(texto) < 10:
        raise IngestaError("Imagen sin texto OCR relevante")
    return [Bloque(texto, "OCR")]


def extraer_notebook(ruta: Path) -> list[Bloque]:
    nb = nbformat.read(str(ruta), as_version=4)
    bloques = []
    for i, celda in enumerate(nb.cells, start=1):
        if celda.cell_type == "markdown":
            t = celda.source.strip()
            if t:
                bloques.append(Bloque(t, f"celda {i}"))
        elif celda.cell_type == "code":
            partes = [f"```python\n{celda.source.strip()}\n```"]
            for sal in celda.get("outputs", []):
                if sal.get("output_type") == "stream":
                    partes.append("```\n" + sal.get("text", "")[:500] + "\n```")
                elif sal.get("output_type") in ("execute_result", "display_data"):
                    dato = sal.get("data", {})
                    if "text/plain" in dato:
                        partes.append("```\n" + "".join(dato["text/plain"])[:500] + "\n```")
            bloques.append(Bloque("\n\n".join(partes), f"celda {i}"))
    if not bloques:
        raise IngestaError("Notebook sin celdas")
    return bloques


_EXTRACTORES = {
    "pdf": extraer_pdf,
    "latex": extraer_latex,
    "txt": extraer_txt,
    "csv": extraer_csv,
    "docx": extraer_docx,
    "xlsx": extraer_xlsx,
    "imagen": extraer_imagen,
    "notebook": extraer_notebook,
}


def extraer(ruta: Path, tipo: str) -> list[Bloque]:
    fn = _EXTRACTORES.get(tipo)
    if fn is None:
        raise IngestaError(f"Tipo no soportado: {tipo}")
    return fn(ruta)
