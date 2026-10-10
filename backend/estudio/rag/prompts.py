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
    "\n"
    "REGLA CERO (rechazo): responde SIN material SOLO si los fragmentos son "
    "claramente basura administrativa o de proceso: logs de compilación, "
    "listados de archivos, metadatos, tablas de nombres o rutas, código de "
    "infraestructura (endpoints, config, tests), o texto que solo describe el "
    "proceso editorial. En ese caso responde EXACTAMENTE:\n"
    '{{"titulo": "", "cuerpo": "", "sin_material": true}}\n'
    "En cambio, si hay CUALQUIER contenido de física, secuencia, "
    "reconstrucción, relaxometría, física de MR o resultados del estudio "
    "(aunque sea parcial o breve), SÍ genera el tip con eso. Sé permisivo: "
    "prefiere un tip útil y honesto sobre lo que dice el fragmento antes que "
    "rechazarlo.\n"
    "NO escribas avisos, disculpas ni explicaciones: el sistema descarta "
    "esos casos automáticamente.\n"
    "\n"
    "Si SÍ hay material, requisitos:\n"
    "- titulo: 5-9 palabras, técnico, autocontenido y legible. PROHIBIDO "
    "cortar una frase a medias, empezar con signos, o incluir LaTeX crudo.\n"
    "- cuerpo: 150-280 palabras en español, RIGOR DOCTORAL: física y "
    "matemática real del tema, NO divulgación. Incluye SIEMPRE que aplique:\n"
    "  (1) la(s) fórmula(s) clave en NOTACIÓN UNICODE COMPACTA, con cada "
    "símbolo definido. Usa los caracteres directamente: T2*, S(TE) = "
    "S₀·e^(−TE/T2*), k(t) = (γ/2π)·∫G(t)dt, Δf = 3.5 ppm × 42.58 MHz/T × "
    "0.55 T ≈ 82 Hz, S(t) = Σᵢ Sᵢ·e^(−t/T2ᵢ*), √, ≤, ≈, ×, µs, ms, °, ², "
    "³, ω, λ, α. PROHIBIDO LaTeX crudo ($, \\, comandos) Y PROHIBIDO "
    "deletrear símbolos en palabras: escribe 'T2*' (no 'T2 estrella'), "
    "'√' (no 'raíz cuadrada de'), '∫' (no 'integral de'), 'γ' (no 'gamma'), "
    "'Σ' (no 'sumatoria de'). Una fórmula en una sola línea compacta vale "
    "más que tres frases describiéndola;\n"
    "  (2) los valores numéricos con unidades tal como aparecen en los "
    "fragmentos (TE, TR, flip, Δf, resoluciones, tiempos T2*);\n"
    "  (3) el porqué físico (qué fenómeno obliga esa decisión de diseño) y "
    "el trade-off que se acepta;\n"
    "  (4) las condiciones de validez o supuestos del modelo.\n"
    "- Escribe en español correcto y completo (acentos, sin mutilar "
    "palabras). Nada de LaTeX, ni \\, ni $...$, ni comandos.\n"
    "- NO copies tablas de datos crudos ni listados de archivos.\n"
    "- Cada afirmación debe venir de los fragmentos; cita como [Fuente N].\n"
    "- NO inventes nada que no esté en los fragmentos.\n"
    "Responde SOLO JSON válido:\n"
    '{{"titulo": "...", "cuerpo": "...", "sin_material": false}}\n\n'
    "FRAGMENTOS:\n{contexto}"
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
