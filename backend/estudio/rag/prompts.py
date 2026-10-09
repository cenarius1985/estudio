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
    "- cuerpo: 120-220 palabras en español AL NIVEL EXIGIDO: conceptos "
    "técnicos, fórmulas (en texto plano, p. ej. S(t)=S0·exp(-t/T2*)), "
    "magnitudes, trade-offs y porqués — NO consejos genéricos de estudio ni "
    "divulgación.\n"
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
    "Las preguntas deben exigir COMPRENSIÓN, no memorización: derivaciones "
    "cualitativas, por qué se elige una técnica sobre otra, qué pasa si se "
    "cambia un parámetro, interpretación de magnitudes y trade-offs. "
    "4 alternativas, una correcta, distractores plausibles pero falsos según "
    "los fragmentos. La explicación debe razonar la respuesta con [Fuente N]. "
    "Responde SOLO JSON válido:\n"
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
