"""Prompts con citas estrictas: el LLM SOLO puede usar los fragmentos dados.

Cada tema define su ENFOQUE (nivel/temario) que se inyecta en todos los
prompts: un tema de doctorado exige rigor matemático y físico; un tema de
idiomas, vocabulario. Sin enfoque, se usa un nivel técnico general.
"""

from __future__ import annotations

from estudio.rag.retrieval import Fragmento

MAX_FRAG = 1800  # chars por fragmento en el contexto

_SIN_ENFOQUE = (
    "nivel técnico-estudioso: conceptos precisos, cifras y definiciones tal "
    "como aparecen en los fragmentos"
)

SISTEMA_CHAT = (
    "Eres un tutor experto en el material del usuario. Respondes en español, "
    "con rigor técnico y brevedad.\n"
    "REGLAS DE FIDELIDAD (innegociables):\n"
    "1. Responde ÚNICAMENTE con la información contenida en los FRAGMENTOS.\n"
    "2. Tras cada afirmación cita su fuente con [Fuente N].\n"
    "3. Si los fragmentos no contienen la respuesta (o no la contienen "
    "completa), responde exactamente: «No encontré eso en tus documentos» y "
    "explica en una línea qué sí hay relacionado, si aplica.\n"
    "4. NO uses conocimiento previo, NO inventes números, páginas ni citas.\n"
    "5. Puedes sintetizar entre fragmentos, marcando cada dato con su fuente."
)


def perfil_enfoque(enfoque: str | None) -> str:
    return (enfoque or "").strip() or _SIN_ENFOQUE


def construir_contexto(fragmentos: list[Fragmento], max_frag: int = MAX_FRAG) -> str:
    partes = []
    for i, f in enumerate(fragmentos, start=1):
        ref = f" ({f.pagina})" if f.pagina else ""
        partes.append(
            f"[Fuente {i}] {f.archivo}{ref}\n{f.texto[:max_frag]}"
            + ("…" if len(f.texto) > max_frag else "")
        )
    return "\n\n".join(partes)


PROMPT_TIP = (
    "Vas a crear un TIP DE ESTUDIO TÉCNICO diario a partir de FRAGMENTOS "
    "REALES del material del estudiante.\n"
    "NIVEL Y ENFOQUE DE ESTE TEMA: {enfoque}.\n"
    "Requisitos:\n"
    "- titulo: máximo 8 palabras, técnico y específico.\n"
    "- cuerpo: 150-280 palabras en español, RIGOR DOCTORAL: física y "
    "matemática real del tema, NO divulgación. Incluye SIEMPRE que aplique:\n"
    "  (1) la(s) fórmula(s) clave en texto plano con cada símbolo definido "
    "(p. ej. S(t)=S_bw*exp(-TE/T2_bw*) + S_pw*exp(-TE/T2_pw*), donde S_i es "
    "la amplitud del pool i y T2_i* su tiempo de relajación transversal "
    "efectivo);\n"
    "  (2) los valores numéricos con unidades tal como aparecen en los "
    "fragmentos (TE, TR, flip, Δf, resoluciones, tiempos T2*);\n"
    "  (3) el porqué físico (qué fenómeno obliga esa decisión de diseño) y "
    "el trade-off que se acepta;\n"
    "  (4) las condiciones de validez o supuestos del modelo.\n"
    "- Cada afirmación debe venir de los fragmentos; cita como [Fuente N].\n"
    "- NO inventes nada que no esté en los fragmentos.\n"
    "Responde SOLO JSON válido:\n"
    '{{"titulo": "...", "cuerpo": "..."}}\n\nFRAGMENTOS:\n{contexto}'
)

PROMPT_DECK = (
    "Crea {n} flashcards de ESTUDIO TÉCNICO a partir de los FRAGMENTOS, al "
    "nivel que exige este tema.\n"
    "NIVEL Y ENFOQUE: {enfoque}.\n"
    "Cada tarjeta: frente = pregunta, definición, fórmula o magnitud "
    "específica; reverso = respuesta correcta y autocontenida (máx 60 "
    "palabras, con la fórmula o cifra exacta cuando aplique). Nada de "
    "trivialidades. Responde SOLO JSON válido:\n"
    '{{"titulo": "...", "tarjetas": [{{"frente": "...", "reverso": "...", '
    '"fuente": <número de Fuente>}}]}}\n\nFRAGMENTOS:\n{contexto}'
)

PROMPT_QUIZ = (
    "Crea {n} preguntas de opción múltiple de EXAMEN DOCTORAL (estilo defensa "
    "de tesis o calificación oral) sobre los FRAGMENTOS.\n"
    "NIVEL Y ENFOQUE: {enfoque}.\n"
    "Las preguntas deben exigir COMPRENSIÓN PROFUNDA, no memorización:\n"
    "- derivaciones cualitativas (¿qué le ocurre a la señal si X cambia?);\n"
    "- por qué se elige una técnica sobre otra (UTE vs GRE, CS vs SENSE, "
    "bi- vs tri-componente, ramp sampling vs uniforme);\n"
    "- interpretación numérica: magnitudes reales con unidades (TE en µs, "
    "T2* en ms, Δf en Hz, resoluciones en mm) y qué implican;\n"
    "- fórmulas en los enunciados o alternativas cuando aplique (texto "
    "plano, p. ej. k(t) = (γ/2π)·∫G(τ)dτ) y qué pasa si se viola un "
    "supuesto (momento neto nulo, spoiling, anclaje de médula).\n"
    "4 alternativas, una correcta, distractores plausibles pero falsos según "
    "los fragmentos (errores conceptuales típicos, no obvios). "
    "La explicación debe razonar la respuesta física paso a paso con "
    "[Fuente N]. Responde SOLO JSON válido:\n"
    '{{"titulo": "...", "preguntas": [{{"enunciado": "...", "alternativas": '
    '["a","b","c","d"], "correcta": <índice 0-3>, "explicacion": "...", '
    '"fuente": <número de Fuente>}}]}}\n\nFRAGMENTOS:\n{contexto}'
)

PROMPT_GRAFO = (
    "Del siguiente texto, extrae tripletas de conocimiento "
    "(concepto, relación, concepto). Máximo 8 tripletas, solo conceptos "
    "técnicos relevantes (secuencias, tejidos, magnitudes, técnicas). "
    "Relación en minúsculas (p. ej. \"mide\", \"afecta a\", \"se usa en\"). "
    "Responde SOLO JSON válido:\n"
    '{{"tripletas": [{{"a": "...", "rel": "...", "b": "..."}}]}}\n\nTEXTO:\n{texto}'
)
