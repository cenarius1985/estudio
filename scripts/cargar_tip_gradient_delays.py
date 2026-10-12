#!/usr/bin/env python3
"""Carga 1 tip: ERRORES DE TRAYECTORIA POR RETRASOS DE GRADIENTE (gradient
delays) — k_real vs k_nom, ramp sampling no lineal, calibración del escáner.

Pedido directo del usuario (texto suyo adaptado al formato de tips: LaTeX
$$..$$/$..$, citas [Fuente N], prosa por párrafos). Estado «generado», SIN
correo, tema Tesis MRI — mismo patrón que cargar_tips_formulas.py.

    docker compose cp scripts/cargar_tip_gradient_delays.py worker-urgente:/tmp/
    docker compose exec -T -e PYTHONPATH=/app worker-urgente \
        python /tmp/cargar_tip_gradient_delays.py [--secos]
"""
import asyncio
import sys
from datetime import date

sys.path.insert(0, "/app")

from sqlalchemy import select  # noqa: E402
from estudio.db import SessionLocal  # noqa: E402
from estudio.mail.plantilla import cuerpo_html_de, cuerpo_texto_de  # noqa: E402
from estudio.models import Tema, Tip  # noqa: E402
from estudio.rag.embeddings import embedir_passages  # noqa: E402

TEMA = "933ee140ea124c5a8aff1afb06c5d257"

MT = "defensa_tesis_doctoral/marco-teorico"

TIPS: list[tuple[str, str, list[dict]]] = [
    (
        "Errores de trayectoria por retrasos de gradiente (gradient delays)",
        r"""Un problema importante de la reconstrucción radial que la matemática de la trayectoria no puede ver por sí sola: la trayectoria de k-space que calculas en PyPulseq puede no coincidir exactamente con la que ejecuta el escáner [Fuente 1]. ¿Por qué ocurre? Los gradientes tienen una respuesta temporal real que puede diferir de la ideal por retrasos en la cadena de gradientes y otras imperfecciones del sistema. Si el gradiente efectivo presenta un retraso temporal $\delta t$, la trayectoria real será
$$\mathbf{k}_{\mathrm{real}}(t) = \frac{\gamma}{2\pi}\int_0^t \mathbf{G}_{\mathrm{real}}(\tau)\,d\tau$$
mientras que la trayectoria nominal, calculada con los gradientes programados, es
$$\mathbf{k}_{\mathrm{nom}}(t) = \frac{\gamma}{2\pi}\int_0^t \mathbf{G}_{\mathrm{nom}}(\tau)\,d\tau$$
La diferencia entre ambas introduce errores de fase y de posicionamiento de las muestras [Fuente 1]. ¿Por qué es especialmente relevante en MRI radial? Cada proyección atraviesa el centro de k-space: si los retrasos afectan de forma diferente a las direcciones de lectura, las proyecciones quedan desalineadas respecto de sus trayectorias previstas. Eso puede producir artefactos de streaking, pérdida de resolución, desenfoque e inconsistencias entre proyecciones. La magnitud del error depende del retraso, de la forma del gradiente, de la dirección de lectura y de la resolución espacial.
Aplicación a la UTE de bajo campo: en la secuencia radial UTE a 0.55 T se usa ramp sampling para comenzar a adquirir mientras aumenta el gradiente de lectura [Fuente 2]. Aquí hay una sutileza importante: durante la rampa, un pequeño error temporal puede traducirse en un error significativo de posición en k-space, especialmente cerca del inicio de la lectura. Además, la relación entre tiempo y posición es no lineal durante una rampa lineal:
$$G(t) = S\,t$$
$$k(t) = \frac{\gamma}{2\pi}\,\frac{S\,t^2}{2}$$
Por eso un retraso temporal no produce necesariamente el mismo error de posición en todos los puntos de la trayectoria. En PyPulseq, la trayectoria calculada a partir de los gradientes programados es una trayectoria nominal: para evaluar los errores reales puede ser necesario medir o calibrar la trayectoria del escáner — no basta con aumentar la precisión numérica de la reconstrucción [Fuente 3]. Certeza: alta para el principio físico; la magnitud y la importancia del retraso en un sistema concreto requieren mediciones o una calibración experimental.
English practice: gradient delays can cause discrepancies between the nominal and actual k-space trajectories. Recuperación activa: intenta explicar por qué un pequeño retraso temporal del gradiente puede generar artefactos en una reconstrucción radial, aunque la trayectoria nominal de PyPulseq sea matemáticamente correcta.""",
        [{"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T13-trayectoria-kspace.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T17-ramp-sampling.md", "pagina": ""},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/anexos/anexo2.tex", "pagina": "tex"}],
    ),
]


def _parrafos(cuerpo: str) -> list[str]:
    return [p.strip() for p in cuerpo.split("\n") if p.strip()]


async def main() -> None:
    secos = "--secos" in sys.argv
    if secos:
        for titulo, cuerpo, citas in TIPS:
            html = cuerpo_html_de(_parrafos(cuerpo), citas)
            imgs, cajas = html.count("<img"), html.count("Cascadia")
            print(f"{'OK ' if cajas == 0 else '⚠️ '}{titulo[:58]:60s} imgs={imgs} cajas={cajas}")
        return

    async with SessionLocal() as db:
        tema = await db.get(Tema, TEMA)
        print(f"tema: {tema.nombre if tema else '??'}")
        hoy = date.today()
        existe = (await db.execute(
            select(Tip).where(Tip.titulo == TIPS[0][0])
        )).scalars().first()
        if existe:
            print("ya existe un tip con ese título — no se inserta nada")
            return
        titulo, cuerpo, citas = TIPS[0]
        emb = embedir_passages([f"{titulo}\n{cuerpo}"])[0]
        parrafos = _parrafos(cuerpo)
        db.add(Tip(
            fecha=hoy,
            titulo=titulo,
            cuerpo_texto=cuerpo_texto_de(parrafos, citas),
            cuerpo_html=cuerpo_html_de(parrafos, citas),
            embedding=emb,
            estado="generado",  # en BD, SIN enviar
            tema_id=TEMA,
        ))
        await db.commit()
        total = (await db.execute(select(Tip))).scalars().all()
        print(f"insertados: 1 | tips del tema en BD: {len([t for t in total if t.tema_id == TEMA])}")


asyncio.run(main())
