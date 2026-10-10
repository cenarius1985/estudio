"""Ciclo de 50 tips doctorales para el tema 'Tesis MRI' (v2 — dirigido).

Diferencia clave vs v1: cada tip se siembra con UNA CONSULTA ESPECÍFICA del
bloque de física (ramp sampling, VERSE, bi/tri-componente…), recuperada vía
RAG híbrido sobre los chunks reales del tema. Así la semilla cae en el
material correcto (paper, presentaciones especiales, marco teórico) y NO en
logs de compilación ni tablas auxiliares.

Flujo por tip:
  1. Recuperar top-k fragmentos del bloque (búsqueda semántica local vía API
     de chat RAG no está expuesta, así que usamos la misma consulta que el
     enfoque del bloque — el worker usa chunk_menos_cubierto + recuperar).
     Para dirigir la semilla, actualizamos `prioridades` del tema NO: en su
     lugar inyectamos la consulta del bloque en el campo `enfoque` temporal
     del tema es invasivo. Solución elegida: llamar al endpoint interno
     /tips/generar con forzar=True y confiar en la mejora de PROMPT_TIP +
     ROTAR prioridades por bloque vía API PATCH /temas/{id} (prioridades).
  2. Verificar que el tip nuevo apareció y registrar su título.

Uso (host, stack arriba):
    ADMIN_PASSWORD=... python scripts/ciclo_50_tips.py [--total 50]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

API = "http://127.0.0.1:8600"

# ── Temario curado: 10 bloques × 5 tips = 50 ─────────────────────────────
# (nombre, consulta_semilla, prioridades_ruta)
# prioridades dirige chunk_menos_cubierto hacia el material correcto.
BLOQUES = [
    ("UTE 2D: half-pulse y TE ultracorto",
     "half pulse excitación momento neto nulo TE mínimo 30 microsegundos "
     "por qué el agua ligada decae antes del eco",
     "MRI-UTE PROYECTO DE TESIS/capitulos,paper-mri-us"),
    ("Muestreo radial y ramp sampling",
     "ramp sampling muestreo cuadrático t2 rampa gradiente densidad k-space "
     "muestreo radial ángulos aleatorios",
     "paper-mri-us,defensa_tesis_doctoral/presentacion-especiales/secuencia-ute"),
    ("VERSE y excitación variable",
     "VERSE variable rate selective excitation B1 reshaping duración pulso "
     "SAR T2 durante excitación",
     "paper-mri-us,MRI-UTE PROYECTO DE TESIS/capitulos"),
    ("Reconstrucción compressed sensing",
     "compressed sensing total variation ADMM NUFFT submuestreo aliasing "
     "incoherente regularización lambda",
     "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing,paper-mri-us"),
    ("Relajometría bi-componente",
     "bi-componente dos pools agua ligada agua libre S_s S_l fracciones "
     "ajuste riciano T2 corto T2 largo",
     "defensa_tesis_doctoral/presentacion-especiales/relaxometria,MRI-UTE PROYECTO DE TESIS/capitulos"),
    ("Relajometría tri-componente",
     "tri-componente médula batido grasa agua chemical shift 82 Hz anclaje "
     "marrow fase exponencial compleja",
     "defensa_tesis_doctoral/Paper-MRI-US,MRI-UTE PROYECTO DE TESIS/capitulos"),
    ("Física T2* en hueso cortical",
     "susceptibilidad inhomogeneidad T2 estrella hueso cortical 50 500 "
     "microsegundos invisible GRE convencional porosidad",
     "MRI-UTE PROYECTO DE TESIS/capitulos,defensa_tesis_doctoral/marco-teorico"),
    ("Ultrasonido BDAT",
     "BDAT transmisión axial bidireccional ondas guiadas curvas dispersión "
     "placa libre inversa Ct.Th Ct.Po 1 MHz",
     "defensa_tesis_doctoral/Paper-MRI-US,RESULTADOS-MRI"),
    ("Concordancia MRI-US biomarcadores",
     "concordancia espesor cortical regresión pendiente R2 RMSE porosidad "
     "fracciones agua poro validación",
     "paper-mri-us,RESULTADOS-MRI"),
    ("Validación e implementación",
     "fantoma GRE validación KomaMRI PyPulseq registro ECC máxima "
     "verosimilitud riciano información Fisher",
     "MRI-UTE PROYECTO DE TESIS/capitulos,MRI-UTE PROYECTO DE TESIS/codigo"),
]


def api(path: str, token: str, method: str = "GET", body: dict | None = None):
    req = urllib.request.Request(
        API + path,
        method=method,
        headers={"X-Token": token, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None,
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def login() -> str:
    pw = os.environ.get("ADMIN_PASSWORD") or input("ADMIN_PASSWORD: ")
    return api("/auth/login", "", "POST", {"password": pw})["token"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=50)
    ap.add_argument("--intervalo", type=int, default=45)
    ap.add_argument("--tema", default="Tesis MRI")
    ap.add_argument("--desde", type=int, default=0, help="índice de bloque inicial")
    args = ap.parse_args()

    token = login()
    temas = api("/temas", token)
    tema = next(t for t in temas if t["nombre"] == args.tema)
    tema_id = tema["id"]
    original = tema["enfoque"] or ""
    original_prio = tema["prioridades"] or ""

    base = api("/tips/stats", token)
    inicial = base["total"]
    print(f"Tips actuales en BD: {inicial}. Objetivo: +{args.total}")

    hechos = 0
    try:
        for i in range(args.desde, args.desde + args.total):
            nombre, consulta, prioridades = BLOQUES[i % len(BLOQUES)]
            print(f"\n[{i + 1 - args.desde}/{args.total}] Bloque: {nombre}")

            # dirigir la semilla: prioridades del tema = fuente del bloque
            api(f"/temas/{tema_id}", token, "PUT",
                {"prioridades": prioridades})

            r = api("/tips/generar", token, "POST", {"forzar": True})
            if not r.get("job"):
                print("  ERROR: worker no disponible"); sys.exit(1)

            previo = inicial + hechos
            for _ in range(args.intervalo // 5):
                time.sleep(5)
                actual = api("/tips/stats", token)["total"]
                if actual > previo:
                    hechos += 1
                    ultimo = api("/tips?limite=1", token)[0]
                    print(f"  OK #{actual}: {ultimo['titulo']}")
                    break
            else:
                print("  TIMEOUT: sin tip nuevo; continúo")
    finally:
        # restaurar configuración original del tema
        api(f"/temas/{tema_id}", token, "PUT",
            {"prioridades": original_prio, "enfoque": original})
        print("\n(prioridades del tema restauradas)")

    final = api("/tips/stats", token)
    print(f"Hecho: {final['total']} tips totales (+{final['total'] - inicial}).")
    print("Por estado:", final["por_estado"])


if __name__ == "__main__":
    main()
