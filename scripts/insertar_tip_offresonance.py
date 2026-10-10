import asyncio, uuid, sys
from datetime import date
sys.path.insert(0, "/app")

from estudio.mail.plantilla import renderizar_matematica
from estudio.db import SessionLocal
from estudio.models import Tema, Tip

TITULO = ("Off-resonance: por qué una trayectoria radial correcta "
          "no garantiza una imagen correcta")

CUERPO = """Hoy repasamos la corrección de off-resonance en reconstrucción radial, un aspecto importante cuando quieres obtener imágenes fiables del hueso cortical mediante UTE.

1. ¿Qué es el off-resonance?
Si el campo magnético local difiere ligeramente del valor esperado, los protones experimentan una frecuencia de resonancia diferente. Podemos expresar esa desviación como Delta f(r), en Hz.
Durante la adquisición, esta diferencia produce una fase adicional:

phi(r,t) = 2*pi * Delta f(r) * t

Por eso, la señal recibida no depende únicamente de la trayectoria de k-space, sino también de la evolución de fase de los protones.
Un modelo simplificado de la señal es:

s(t) = integral rho(r) * e^(-i2*pi*[k(t)·r + Delta f(r)*t]) dr

El signo de la fase depende de la convención utilizada, pero el concepto físico es el mismo.
La idea clave: si reconstruyes suponiendo que Delta f = 0 cuando realmente no lo es, puedes introducir errores de fase, desenfoque y distorsiones en la imagen.

2. ¿Cómo afecta a tu UTE radial a 0.55 T?
Hay dos cuestiones que conviene distinguir:
TE ultracorto: reduce el tiempo transcurrido entre la excitación y la primera muestra, algo esencial para detectar componentes con T2* muy corto.
Off-resonance durante la lectura: sigue acumulando fase mientras recoges las muestras posteriores.
Por tanto, un TE de aproximadamente 20 µs no elimina los efectos de las inhomogeneidades de campo durante toda la adquisición.
Además, a 0.55 T el desplazamiento químico entre agua y grasa, expresado en Hz, es menor que a 3 T. Sin embargo, eso no garantiza que los errores por inhomogeneidad de B0 sean despreciables.

3. ¿Cómo se puede corregir?
Una posibilidad es estimar un mapa de desviación de frecuencia, Delta f(r), y utilizarlo durante la reconstrucción.
Por ejemplo, los métodos de reconstrucción con corrección de off-resonance pueden incorporar la fase espacial y temporal en el modelo de señal, en lugar de asumir una evolución de fase ideal.
En tu flujo con PyPulseq y reconstrucción no cartesiana, conviene distinguir:
Trayectoria: ¿dónde se encuentra cada muestra en k-space?
Off-resonance: ¿qué fase adicional acumula cada posición durante la lectura?
Sensibilidad de bobina: ¿cómo varía la señal recibida espacialmente?
Son efectos diferentes y no deberían confundirse al investigar artefactos.

Dependencia del contexto: la importancia de la corrección depende de la duración de la lectura, la distribución de Delta f(r), la resolución y el método de reconstrucción. No puedo determinar cuánto afecta a tus imágenes concretas sin conocer esos parámetros o analizar los datos.

English practice: "Ultrashort echo time reduces signal loss before acquisition, but it does not eliminate off-resonance effects during readout."

Pregunta de recuperación activa: si corriges perfectamente la trayectoria radial, pero ignoras una desviación espacial de frecuencia Delta f(r), ¿por qué todavía puedes obtener una imagen con desenfoque?"""

async def run():
    import sqlalchemy
    async with SessionLocal() as db:
        tema = (await db.execute(
            sqlalchemy.select(Tema).where(Tema.nombre == "Tesis MRI")
        )).scalars().first()
        parrafos = [p.strip() for p in CUERPO.split("\n\n") if p.strip()]
        tip = Tip(
            id=uuid.uuid4().hex[:32],
            fecha=date.today(),
            titulo=TITULO,
            cuerpo_texto=CUERPO,
            cuerpo_html="<br>".join(
                renderizar_matematica(p).replace("\n", "<br>") for p in parrafos
            ),
            estado="generado",
            tema_id=tema.id if tema else None,
        )
        db.add(tip)
        await db.commit()
        print(f"Tip insertado: {tip.id} — {tip.titulo}")

asyncio.run(run())
