"""Ciclo de 50 tips SOLO de la secuencia UTE 2D — sin envío por correo.

Los tips se generan y almacenan en la BD (tabla tips, con cuerpo_html
formateado), pero NO se envían: TIPS_TO está vacío en .env ⇒ el worker
marca estado='sin_destinatarios' y omite el SMTP.

Los 6 sub-bloques de la secuencia UTE cubren: diseño del pulso half-pulse
y momento neto nulo, ramp sampling t², VERSE, muestreo radial y trayectoria
k, spoiling, y la implementación/simulación (KomaMRI/PyPulseq).

Uso: ADMIN_PASSWORD=$(grep ADMIN_PASSWORD .env | cut -d= -f2) \
         python scripts/ciclo_50_tips_ute.py [--total 50]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

API = "http://127.0.0.1:8600"

# ── Sub-bloques de la SECUENCIA UTE 2D (fuente: paper §3.1, secuencia-ute,
#    capítulos, UTE-PYTHON/UTE3D) ──────────────────────────────────────────
BLOQUES = [
    ("Half-pulse y momento neto nulo",
     "half pulse excitación medio pulso gradiente bipolar momento neto nulo "
     "kz=0 lóbulo refaseado por qué elimina refase",
     "paper-mri-us,MRI-UTE PROYECTO DE TESIS/capitulos"),
    ("Ramp sampling t²",
     "ramp sampling muestreo cuadrático t^2 rampa gradiente t_rise N_ramp "
     "muestreo durante subida por qué cerca de k=0",
     "paper-mri-us,defensa_tesis_doctoral/presentacion-especiales/secuencia-ute"),
    ("VERSE",
     "VERSE variable rate selective excitation reescalamiento B1 duración "
     "pulso SAR T2 durante excitación condición invariancia",
     "paper-mri-us,MRI-UTE PROYECTO DE TESIS/capitulos"),
    ("Muestreo radial y trayectoria k",
     "muestreo radial ángulos aleatorios radios golden angle trayectoria "
     "k-space densidad centro sobre-muestreo",
     "paper-mri-us,defensa_tesis_doctoral/presentacion-especiales/secuencia-ute"),
    ("Spoiling",
     "spoiling gradientes desfase área 2π voxel espóiler RF cuadrática "
     "117 grados estado estacionario",
     "paper-mri-us,MRI-UTE PROYECTO DE TESIS/capitulos"),
    ("Implementación y simulación",
     "KomaMRI PyPulseq simulación secuencia verificación TE 30 microsegundos "
     "diagrama pulso Python implementación",
     "MRI-UTE PROYECTO DE TESIS/codigo,paper-mri-us"),
]

# el enfoque del tema se acota a la secuencia durante el ciclo
ENFOQUE_UTE = (
    "Nivel doctoral. SOLO la secuencia UTE 2D: diseño del pulso half-pulse "
    "y momento neto nulo (kz=0), ramp sampling cuadrático t_i=t_rise*(i/"
    "(N_ramp-1))^2, VERSE B1'(t)=B1(tau)*|dtau/dt|, muestreo radial y "
    "trayectoria k(t)=(gamma/2pi)*integral G, spoiling (2π por voxel, RF "
    "cuadrática 117°), TE=30µs y su límite físico, simulación KomaMRI/"
    "PyPulseq. Tips: fórmulas con cada símbolo definido, magnitudes con "
    "unidades, porqués físicos, trade-offs y condiciones de validez. "
    "EXCLUYE relajometría, BDAT, reconstrucción CS y resultados."
)


def api(path: str, token: str, method: str = "GET", body: dict | None = None):
    req = urllib.request.Request(
        API + path,
        method=method,
        headers={"X-Token": token, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None,
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=50)
    ap.add_argument("--intervalo", type=int, default=45)
    ap.add_argument("--tema", default="Tesis MRI")
    ap.add_argument("--desde", type=int, default=0)
    args = ap.parse_args()

    pw = os.environ.get("ADMIN_PASSWORD") or input("ADMIN_PASSWORD: ")
    token = api("/auth/login", "", "POST", {"password": pw})["token"]
    temas = api("/temas", token)
    tema = next(t for t in temas if t["nombre"] == args.tema)
    tema_id = tema["id"]
    enfoque_original = tema["enfoque"] or ""
    prio_original = tema["prioridades"] or ""

    base = api("/tips/stats", token)
    inicial = base["total"]
    print(f"Tips actuales en BD: {inicial}. Objetivo: +{args.total} (solo secuencia UTE, sin correo)")

    hechos = 0
    fallos = 0
    try:
        for i in range(args.desde, args.desde + args.total):
            nombre, consulta, prioridades = BLOQUES[i % len(BLOQUES)]
            print(f"\n[{i + 1 - args.desde}/{args.total}] {nombre}", flush=True)

            api(f"/temas/{tema_id}", token, "PUT",
                {"prioridades": prioridades, "enfoque": ENFOQUE_UTE})
            api("/tips/generar", token, "POST", {"forzar": True})

            previo = inicial + hechos
            for _ in range(args.intervalo // 5):
                time.sleep(5)
                actual = api("/tips/stats", token)["total"]
                if actual > previo:
                    hechos += 1
                    ultimo = api("/tips?limite=1", token)[0]
                    print(f"  OK #{actual}: {ultimo['titulo']}", flush=True)
                    break
            else:
                fallos += 1
                print("  sin tip nuevo (dedupe o error)", flush=True)
    finally:
        api(f"/temas/{tema_id}", token, "PUT",
            {"prioridades": prio_original, "enfoque": enfoque_original})
        print("\n(tema restaurado)")

    final = api("/tips/stats", token)
    print(f"\nHecho: {final['total']} tips totales (+{final['total'] - inicial})."
          f" Sin tip nuevo: {fallos}")


if __name__ == "__main__":
    main()
