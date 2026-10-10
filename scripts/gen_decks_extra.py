#!/usr/bin/env python3
"""3 decks adicionales para completar 20."""
import asyncio, sys
from datetime import date
sys.path.insert(0, "/app")
from estudio.db import SessionLocal
from estudio.models import Deck, Flashcard

TEMA = "933ee140ea124c5a8aff1afb06c5d257"
CT = "MRI-UTE PROYECTO DE TESIS"
DF = "defensa_tesis_doctoral"
PM = "paper-mri-us"

DECKS_EXTRA = [
("Introduccion y Motivacion", [
 ("Limite DXA", "DM2/obesidad/glucocorticoides fracturan sin caida DMO: >50% T-score>-2.5", CT+"/narracion/texto/cap2.txt"),
 ("Fragilidad=fractura", "No el score densitometrico sino la fractura por bajo trauma", CT+"/narracion/texto/cap2.txt"),
 ("Calidad osea", "Densidad+microarquitectura+matriz+mineralizacion+geometria", CT+"/narracion/texto/cap2.txt"),
 ("Osteoporosis T-score", "<=-2.5 pero es UNA causa de fragilidad entre varias", CT+"/narracion/texto/cap2.txt"),
 ("Sin radiacion UTE+BDAT", "Permite estudios longitudinales y en jovenes", CT+"/docs/qa/abstract_p3.png"),
 ("Tibia=80% resistencia", "Deterioro cortical precede perdida DMO", CT+"/narracion/texto/cap2.txt"),
 ("Abstract tesis", "UTE 0.55T cuantifica agua cortical, half pulse VERSE ramp sampling, CS, tricomponente Rician, US-BDAT", CT+"/docs/qa/abstract_p3.png"),
 ("Objetivo general", "Medir agua cortical con UTE 0.55T, cuantificar como biomarcadores, validar vs BDAT", CT+"/narracion/texto/cap4.txt"),
 ("Diseno multimodal emparejado", "UTE tibia media izq + BDAT mismo sitio: sitio-a-sito", CT+"/narracion/texto/cap4.txt"),
 ("3 etapas de validacion", "Simulacion/fantoma -> ex vivo -> in vivo cohorte N=20", CT+"/narracion/texto/cap4.txt"),
]),
("Cronograma y Gestion", [
 ("24 meses, mes 19", "Marzo 2025-febrero 2027. Mes 19 a sep 2026", CT+"/narracion/texto/cap6.txt"),
 ("Fases completadas", "Secuencias, reconstruccion, plataforma: todas completadas", CT+"/narracion/texto/cap6.txt"),
 ("Plataforma adelantada", "Ejecutada en paralelo con fase experimental", CT+"/narracion/texto/cap6.txt"),
 ("Campana cierra sep 2026", "Actividad mas demorosa del proyecto", CT+"/narracion/texto/cap6.txt"),
 ("Etica UV+PUC", "ID 210125006, cohorte N=20", CT+"/narracion/texto/cap7.txt"),
 ("15 pares BDAT", "Adquiridos a sep 2026 de N=20", CT+"/narracion/texto/cap7.txt"),
 ("Contenido del cap 7", "Fantomas + ex vivo + primeros in vivo del paper", CT+"/narracion/texto/cap7.txt"),
 ("Orden validacion", "Fantoma referencia -> corte animal -> in vivo protocolo final", CT+"/narracion/texto/cap7.txt"),
 ("Presentacion iHealth", "ISMRM 2026: fuente de resultados preliminares", CT+"/narracion/texto/cap7.txt"),
 ("Contribucion original", "First in vivo tri-component T2* at 0.55T", DF+"/Paper-MRI-US/narracion/texto/discussion.txt"),
]),
("Formulas Clave para Memorizar", [
 ("y=Ex+n (M<<N)", "Submuestreado: nucleo no trivial, infinitas soluciones", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("E=D^0.5*NUFFT*C", "Operador directo: densidad, Fourier no uniforme, sensibilidades", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("argmin||Ex-y||^2/2+lambda*TV", "lambda=1e-4. Fidelidad+regularizacion. ADMM 50 iter", CT+"/main.pdf"),
 ("TV(x)=suma||grad x||_1", "Norma l1 del gradiente: borde barato, ruido caro", DF+"/marco-teorico/bloque-F-reconstruccion/T29-problema-inverso.md"),
 ("Nyquist radial: pi*Nx", "Numero minimo radios sin aliasing 2D. Nx=500", DF+"/marco-teorico/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md"),
 ("S(TE) tricomponente", "S0*|f_bw*e+f_pw*e+f_bm*e*e^(j2pi*82*TE)|, suma f=1", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("Df=3.5ppm*42.577*0.55=82Hz", "Chemical shift agua-grasa. Minimos 6.1ms, in-phase 12.2ms", DF+"/codigo/plataforma/api_modelo_tricomponente/src/priors.py"),
 ("TE=30us", "Fin RF a primera muestra ADC: half pulse VERSE + ramp sampling", CT+"/anexos/anexo2.tex"),
 ("PI=f_pw=S_pw/(S_bw+S_pw)", "Indice porosidad: agua poro sobre cortical, proxy fragilidad", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("kmax=2pi*G*t_eff", "Meseta+mitad rampas. Verificado pi*Nx/FOV. Gmax=18mT/m", DF+"/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf"),
]),
]


async def main():
    async with SessionLocal() as db:
        hoy = date.today()
        nd = 0
        for titulo, tarjetas in DECKS_EXTRA:
            deck = Deck(titulo=titulo, tema_id=TEMA, estado="listo")
            db.add(deck)
            await db.flush()
            for frente, reverso, archivo in tarjetas:
                db.add(Flashcard(
                    deck_id=deck.id, frente=frente, reverso=reverso,
                    cita={"archivo": archivo, "pagina": ""},
                    proxima_repaso=hoy,
                ))
            nd += len(tarjetas)
            print(f"  OK {titulo} ({len(tarjetas)})")
        await db.commit()
        print(f"Extra: {nd} tarjetas en {len(DECKS_EXTRA)} decks")

asyncio.run(main())
