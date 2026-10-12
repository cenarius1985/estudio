# -*- coding: utf-8 -*-
"""Migra los tips existentes de notación Unicode compacta a LaTeX renderizado.

CORRE DENTRO DEL CONTENEDOR worker-urgente (necesita estudio.* y la BD):
  docker compose cp scripts/tips_a_latex.py worker-urgente:/tmp/
  docker compose exec -T -e PYTHONPATH=/app worker-urgente \
      python /tmp/tips_a_latex.py [--limite N] [--secos]

Por cada tip con fórmulas: GLM reescribe SOLO la notación matemática a
LaTeX ($$display$$ / $inline$), se regeneran cuerpo_html (ecuaciones →
imágenes PNG data-URI) y cuerpo_texto (Unicode), y se recalcula el
embedding para que el dedupe siga midiendo contra el contenido real.
Backup previo: lo hace el HOST con psycopg2 antes de correr esto.

--secos: solo muestra qué migraría (sin escribir en BD).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import Counter

from sqlalchemy import text

from estudio.credenciales import config_llm
from estudio.db import SessionLocal
from estudio.llm import chat, extraer_json
from estudio.mail.plantilla import cuerpo_html_de, cuerpo_texto_de
from estudio.rag.embeddings import embedir_passages, vector_a_pg

# símbolos que delatan fórmulas en notación Unicode compacta o LaTeX residual
INDICIOS = ("∫", "Σ", "√", "e^(", "·10^", "T2*", "^(−", "^", "µs",
            "γ", "Δ", "ω₀", "λ", "≈", "×", "²", "³", "S₀", "B₁", "T₁",
            "π", ">=", "·N", "\\ell", "\\nabla", "\\delta", "ceil", "log(")

PROMPT_MIGRACION = """REESCRIBE la notación matemática de un texto técnico de tesis.

REGLAS ABSOLUTAS (su incumplimiento invalida el resultado):
1. NO cambies NINGUNA palabra: mismas frases, mismo orden, misma puntuación.
2. Mantén INTACTAS todas las citas [Fuente N] exactamente donde están.
3. SOLO convierte la notación Unicode compacta a LaTeX delimitado:
   - fórmula o igualdad completa → $$...$$ EN SU PROPIA LÍNEA (rompe el
     párrafo con un salto de línea antes y después si hace falta);
   - símbolo corto suelto en el texto → $...$ inline (p. ej. $T_2^*$, $\\gamma$);
   - subíndices con guion bajo: T2_bw → $T_{2,\\mathrm{bw}}$; superíndices con ^;
   - integrales $\\int_0^t$, sumatorias $\\sum_i$, fracciones $\\frac{{a}}{{b}}$,
     griegas $\\gamma$ $\\Delta$ $\\omega$, unidades $\\,\\mathrm{{ms}}$.
4. LaTeX de UNA línea: sin \\begin, sin \\text (usa \\mathrm), sin alineaciones.
5. Si un número o unidad NO es fórmula (p. ej. "30 µs", "0.55 T", "1278"),
   déjalo como texto normal.
6. No agregues ni quites fórmulas: las que están, esas van.

Responde SOLO JSON válido: {{"cuerpo": "<el mismo texto con el LaTeX>"}}

TEXTO:
"""


def _citas(v: list) -> list[dict]:
    out, vistos = [], set()
    for archivo, pagina in v:
        k = (archivo, pagina)
        if k in vistos:
            continue
        vistos.add(k)
        out.append({"archivo": archivo, "pagina": pagina or ""})
    return out[:5]


def _citas_de_texto(cuerpo: str) -> Counter:
    return Counter(re.findall(r"\[Fuente \d+\]", cuerpo))


async def migrar(db, tip, cfg_llm, secos: bool) -> dict:
    row = (await db.execute(text(
        "SELECT t.titulo, t.cuerpo_texto FROM tips t WHERE t.id = :i"
    ), {"i": tip})).fetchone()
    titulo, viejo = row
    r = await chat(
        [{"role": "user", "content": PROMPT_MIGRACION + viejo}],
        temperature=0.1, max_tokens=3000, json_mode=True, cfg=cfg_llm,
    )
    datos = extraer_json(r)
    nuevo = str((datos or {}).get("cuerpo") or "").strip()
    if not nuevo or "$" not in nuevo:
        return {"id": tip, "ok": False, "motivo": "sin LaTeX en la respuesta"}
    # fidelidad: mismas citas, longitud razonable (sin math)
    if _citas_de_texto(nuevo) != _citas_de_texto(viejo):
        return {"id": tip, "ok": False, "motivo": "citas [Fuente N] cambiadas"}
    sin_math_v = re.sub(r"\$\$.+?\$\$|\$[^$\n]+\$", " ", viejo, flags=re.DOTALL)
    sin_math_n = re.sub(r"\$\$.+?\$\$|\$[^$\n]+\$", " ", nuevo, flags=re.DOTALL)
    ratio = len(sin_math_n) / max(len(sin_math_v), 1)
    if not 0.6 <= ratio <= 1.3:
        return {"id": tip, "ok": False, "motivo": f"longitud {ratio:.2f} fuera de rango"}

    citas_raw = (await db.execute(text(
        "SELECT dd.ruta, c.pagina FROM tips_chunks tc "
        "JOIN chunks c ON c.id = tc.chunk_id "
        "JOIN documents dd ON dd.id = c.document_id "
        "WHERE tc.tip_id = :i ORDER BY tc.es_semilla DESC"
    ), {"i": tip})).fetchall()
    citas = _citas(citas_raw)

    parrafos = [p.strip() for p in re.split(r"\n+", nuevo) if p.strip()]
    html = cuerpo_html_de(parrafos, citas)
    plano = cuerpo_texto_de(parrafos, citas)
    emb = embedir_passages([f"{titulo}\n{nuevo}"])[0]

    res = {"id": tip, "ok": True, "titulo": titulo,
           "imgs": html.count("<img"), "cajas": html.count("Cascadia"),
           "len_viejo": len(viejo), "len_nuevo": len(nuevo)}
    if not secos:
        await db.execute(text(
            "UPDATE tips SET cuerpo_texto = :ct, cuerpo_html = :ch, "
            "embedding = CAST(:emb AS vector) WHERE id = :i"
        ), {"ct": plano, "ch": html, "emb": vector_a_pg(emb), "i": tip})
    return res


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--ids", default="", help="procesar solo estos ids (coma)")
    ap.add_argument("--secos", action="store_true")
    a = ap.parse_args()

    async with SessionLocal() as db:
        cfg_llm = await config_llm(db)
        filas = (await db.execute(text(
            "SELECT id, titulo, cuerpo_texto, cuerpo_html FROM tips "
            "ORDER BY fecha, creado_en"
        ))).fetchall()
        objetivos = [
            (i, t, c) for (i, t, c, ch) in filas
            if "<img" not in (ch or "")            # idempotente: ya migrado
            and any(s in c for s in INDICIOS)
            and (not a.ids or i in a.ids.split(","))
        ]
        if a.limite:
            objetivos = objetivos[:a.limite]
        print(f"{len(objetivos)} de {len(filas)} tips con fórmulas "
              f"({'SECO' if a.secos else 'ESCRIBIENDO'})")
        ok = fallos = 0
        for i, (tid, titulo, _) in enumerate(objetivos, 1):
            try:
                r = await migrar(db, tid, cfg_llm, a.secos)
            except Exception as exc:  # noqa: BLE001
                r = {"id": tid, "ok": False, "motivo": str(exc)[:120]}
            marca = "OK " if r.get("ok") else "FALLA"
            extra = (f" imgs={r['imgs']} cajas={r['cajas']} "
                     f"{r['len_viejo']}→{r['len_nuevo']}") if r.get("ok") \
                else f" — {r.get('motivo')}"
            print(f"[{i}/{len(objetivos)}] {marca} {titulo[:55]}{extra}",
                  flush=True)
            ok += r.get("ok", False)
            fallos += not r.get("ok", False)
            if r.get("ok") and not a.secos:
                await db.commit()
        print(f"\nListo: {ok} migrados, {fallos} fallidos"
              + (" (modo seco: nada escrito)" if a.secos else ""))


if __name__ == "__main__":
    asyncio.run(main())
