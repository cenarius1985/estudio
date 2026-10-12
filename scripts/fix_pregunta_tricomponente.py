#!/usr/bin/env python3
"""Corrige la pregunta n=3 del quiz «Examen Doctoral: UTE, Relaxometría y
Arquitectura de Análisis» (id ab63d54d…).

Problemas de la versión original (generada por LLM): decía «mielina» (pool
de tejido neural, no de hueso cortical), citaba un compilation_log.txt (no
defendible) y su respuesta correcta asumía que «más densidad de TE siempre
mejora». Reemplazo por la versión mejorada a pedido del usuario: el foco
pasa a OPTIMIZAR LA DISTRIBUCIÓN de TEs (tempranos para T2* ultracorto,
tardíos para pools lentos) manteniendo el presupuesto de adquisición.

    docker compose cp scripts/fix_pregunta_tricomponente.py worker-urgente:/tmp/
    docker compose exec -T -e PYTHONPATH=/app worker-urgente \
        python /tmp/fix_pregunta_tricomponente.py
"""
import asyncio
import json
import sys

sys.path.insert(0, "/app")

from sqlalchemy import text  # noqa: E402
from estudio.db import SessionLocal  # noqa: E402

QUIZ = "ab63d54d5b784d24bf6d4ebf2fd4ad10"
N = 3

ENUNCIADO = (
    "En la estimación de un modelo tri-componente de señal UTE — "
    "S(TE) = Σi Ai·e^(−TE/T2i*), con Ai la amplitud de cada componente y "
    "T2i* su constante de relajación efectiva — mediante "
    "differential_evolution, se observa una elevada incertidumbre en los "
    "parámetros T2* y una fuerte correlación entre las amplitudes de las "
    "componentes. ¿Qué modificación de la estrategia de adquisición podría "
    "mejorar la identificabilidad del modelo sin aumentar significativamente "
    "el tiempo total de escaneo, siempre que sea posible mantener el "
    "presupuesto de adquisición?"
)

ALTERNATIVAS = json.dumps([
    "a) Aumentar el número de promedios (NEX), manteniendo sin cambios los "
    "tiempos de eco, para reducir la variabilidad debida al ruido.",
    "b) Reducir el número de tiempos de eco a dos y mantener los seis "
    "parámetros de amplitud y relajación del modelo tri-componente.",
    "c) Optimizar la distribución de los tiempos de eco, dando especial "
    "importancia a los tiempos muy tempranos para captar las componentes de "
    "T2* ultracorto (agua ligada cortical) y cubriendo también los tiempos "
    "posteriores para caracterizar las componentes más lentas (agua poral, "
    "médula).",
    "d) Sustituir el ajuste no lineal por uno lineal, sin modificar la "
    "parametrización del modelo ni las restricciones de los parámetros.",
], ensure_ascii=False)

CORRECTA = 2  # c)

EXPLICACION = (
    "La clave no es simplemente adquirir más puntos, sino seleccionar dónde "
    "muestrear. Si todos los ecos se adquieren demasiado tarde, la componente "
    "de T2* ultracorto ya ha decaído casi por completo y no hay información "
    "que rescatar — de ahí que en UTE las muestras muy tempranas (desde "
    "~30 µs, con ramp sampling) sean decisivas para el agua ligada cortical — "
    "mientras que los ecos tardíos caracterizan las componentes más lentas "
    "(agua poral, médula ósea). Si dos componentes tienen constantes "
    "similares, sus curvas son difíciles de distinguir incluso con muchos "
    "ecos: añadir puntos no garantiza separarlas (es identificabilidad, no "
    "cantidad). differential_evolution puede explorar mejor el espacio de "
    "parámetros que un método local, pero no elimina la falta de información "
    "de los datos ni garantiza el óptimo global: los límites paramétricos, el "
    "ruido, la inicialización y la función objetivo también importan. Y "
    "aumentar el número de TE no implica necesariamente más tiempo de "
    "escaneo: depende de cómo se implementen los ecos y de si se "
    "redistribuye el presupuesto de adquisición existente o se añaden "
    "adquisiciones nuevas. La mejora real debe verificarse mediante "
    "simulaciones con ruido, análisis de sensibilidad o recuperación de "
    "parámetros conocidos."
)

CITA = json.dumps({
    "archivo": "MRI-UTE PROYECTO DE TESIS/codigo/plataforma/api_modelo_tricomponente/src/relajacionTransversalTri.py",
    "pagina": "líneas 44-133",
}, ensure_ascii=False)


async def main() -> None:
    async with SessionLocal() as db:
        vieja = (await db.execute(text(
            "SELECT enunciado FROM preguntas WHERE quiz_id=:q AND n=:n"
        ), {"q": QUIZ, "n": N})).fetchone()
        if not vieja:
            print("ERROR: la pregunta no existe — nada que corregir")
            return
        if "mielina" not in vieja[0]:
            print("La pregunta ya no contiene «mielina» — posible re-ejecución, no se toca")
            return
        await db.execute(text(
            "UPDATE preguntas SET enunciado=:e, alternativas=CAST(:a AS jsonb), "
            "correcta=:c, explicacion=:x, cita=CAST(:ci AS jsonb) "
            "WHERE quiz_id=:q AND n=:n"
        ), {"e": ENUNCIADO, "a": ALTERNATIVAS, "c": CORRECTA, "x": EXPLICACION,
            "ci": CITA, "q": QUIZ, "n": N})
        await db.commit()
        fila = (await db.execute(text(
            "SELECT correcta, left(enunciado,80), cita FROM preguntas "
            "WHERE quiz_id=:q AND n=:n"
        ), {"q": QUIZ, "n": N})).fetchone()
        print(f"OK — pregunta n={N} corregida")
        print(f"  correcta={fila[0]} | enunciado: {fila[1]}…")
        print(f"  cita: {fila[2]}")


asyncio.run(main())
