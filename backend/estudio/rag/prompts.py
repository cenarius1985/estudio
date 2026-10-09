"""Prompts con citas estrictas: el LLM SOLO puede usar los fragmentos dados."""

from __future__ import annotations

from estudio.rag.retrieval import Fragmento

MAX_FRAG = 1800  # chars por fragmento en el contexto

SISTEMA_CHAT = (
    "Eres un tutor de doctorado experto en resonancia magnética (MRI, UTE, "
    "elastografía por ultrasonido). Respondes en español, con rigor técnico y "
    "brevedad.\n"
    "REGLAS DE FIDELIDAD (innegociables):\n"
    "1. Responde ÚNICAMENTE con la información contenida en los FRAGMENTOS.\n"
    "2. Tras cada afirmación cita su fuente con [Fuente N].\n"
    "3. Si los fragmentos no contienen la respuesta (o no la contienen "
    "completa), responde exactamente: «No encontré eso en tus documentos» y "
    "explica en una línea qué sí hay relacionado, si aplica.\n"
    "4. NO uses conocimiento previo, NO inventes números, páginas ni citas.\n"
    "5. Puedes sintetizar entre fragmentos, marcando cada dato con su fuente."
)


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
    "Vas a crear un TIP DE ESTUDIO diario para el autor de una tesis doctoral "
    "sobre MRI (secuencias UTE y elastografía por ultrasonido), a partir de "
    "FRAGMENTOS REALES de su tesis.\n"
    "Requisitos:\n"
    "- titulo: máximo 8 palabras, específico y atractivo.\n"
    "- cuerpo: 120-220 palabras en español, tono directo de estudio, UNA idea "
    "clave bien explicada, con una cifra o detalle concreto cuando exista.\n"
    "- Cada afirmación debe venir de los fragmentos; cita como [Fuente N].\n"
    "- NO inventes nada que no esté en los fragmentos.\n"
    "Responde SOLO JSON válido:\n"
    '{{"titulo": "...", "cuerpo": "..."}}\n\nFRAGMENTOS:\n{contexto}'
)

PROMPT_DECK = (
    "Crea {n} flashcards de estudio a partir de los FRAGMENTOS de la tesis. "
    "Cada tarjeta: frente = pregunta o concepto corto; reverso = respuesta "
    "correcta y autocontenida (máx 60 palabras). Responde SOLO JSON válido:\n"
    '{{"titulo": "...", "tarjetas": [{{"frente": "...", "reverso": "...", '
    '"fuente": <número de Fuente>}}]}}\n\nFRAGMENTOS:\n{contexto}'
)

PROMPT_QUIZ = (
    "Crea {n} preguntas de opción múltiple de examen doctoral sobre los "
    "FRAGMENTOS de la tesis. 4 alternativas, una correcta, distractores "
    "plausibles pero claramente falsos según los fragmentos. Incluye "
    "explicación breve con [Fuente N]. Responde SOLO JSON válido:\n"
    '{{"titulo": "...", "preguntas": [{{"enunciado": "...", "alternativas": '
    '["a","b","c","d"], "correcta": <índice 0-3>, "explicacion": "...", '
    '"fuente": <número de Fuente>}}]}}\n\nFRAGMENTOS:\n{contexto}'
)

PROMPT_GRAFO = (
    "Del siguiente texto de una tesis de MRI, extrae tripletas de conocimiento "
    "(concepto, relación, concepto). Máximo 8 tripletas, solo conceptos "
    "técnicos relevantes (secuencias, tejidos, magnitudes, técnicas). "
    "Relación en minúsculas (p. ej. \"mide\", \"afecta a\", \"se usa en\"). "
    "Responde SOLO JSON válido:\n"
    '{{"tripletas": [{{"a": "...", "rel": "...", "b": "..."}}]}}\n\nTEXTO:\n{texto}'
)
