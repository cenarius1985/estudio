#!/usr/bin/env python3
"""Coordinador de Estudio Doctorado — instalador todo-en-uno (patrón whispertext).

Qué hace:
1. Verifica Docker y docker compose.
2. Detecta GPU NVIDIA (nvidia-smi) → decide si activar el perfil `gpu` (Bonsai).
3. Genera el .env si falta: claves aleatorias + copia de las credenciales SMTP
   de Brevo desde reportesDiariosGes (nunca las imprime).
4. Verifica el GGUF de Bonsai (si está truncado lo borra para que el
   entrypoint lo re-descargue completo).
5. docker compose up -d --build (con o sin perfil gpu).
6. Espera la API y abre el panel en el navegador.

Uso:  python coordinador.py [--sin-gpu] [--solo-env] [--no-abrir]
"""

from __future__ import annotations

import argparse
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV = RAIZ / ".env"
ENV_EJEMPLO = RAIZ / ".env.example"
SMTP_ORIGEN = Path("E:/GitHub/Ministerio/reportesDiariosGes/.env")

# El 27B PTQ1_0 completo pesa ~5.7 GB; si hay menos de 3 GB está truncado.
GGUF_MIN_BYTES = 3_000_000_000


def correr(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("  $", " ".join(str(c) for c in cmd[:6]), "…" if len(cmd) > 6 else "")
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def hay_gpu() -> bool:
    return shutil.which("nvidia-smi") is not None and correr(["nvidia-smi"]).returncode == 0


def leer_env(ruta: Path) -> dict[str, str]:
    vals: dict[str, str] = {}
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def generar_env(gpu: bool) -> None:
    if ENV.exists():
        print("✓ .env ya existe (no se toca)")
        return

    print("→ Generando .env con claves aleatorias…")
    lineas = ENV_EJEMPLO.read_text(encoding="utf-8").splitlines()

    # Credenciales SMTP de Brevo desde reportesDiariosGes (sin imprimirlas)
    origen = leer_env(SMTP_ORIGEN)
    smtp = {k: origen.get(k, "") for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM")}
    if smtp["SMTP_USER"] and smtp["SMTP_PASS"]:
        print("✓ Credenciales Brevo copiadas desde reportesDiariosGes")
    else:
        print("⚠ No se pudieron copiar las credenciales Brevo: complétalas a mano en .env")

    reemplazos = {
        "POSTGRES_PASSWORD": secrets.token_urlsafe(18),
        "ADMIN_PASSWORD": secrets.token_urlsafe(9),
    }
    for k, v in smtp.items():
        if v:
            reemplazos[k] = v
    # Destinatario por defecto: el mismo remitente Brevo
    if smtp.get("SMTP_FROM"):
        reemplazos["TIPS_TO"] = smtp["SMTP_FROM"]

    salida = []
    for linea in lineas:
        if "=" in linea and not linea.strip().startswith("#"):
            k = linea.split("=", 1)[0].strip()
            if k in reemplazos:
                salida.append(f"{k}={reemplazos[k]}")
                continue
        salida.append(linea)
    ENV.write_text("\n".join(salida) + "\n", encoding="utf-8")
    print(f"✓ .env creado. Contraseña del panel: revísala con  findstr ADMIN_PASSWORD .env")


def verificar_gguf(env: dict[str, str], gpu: bool) -> None:
    if not gpu:
        return
    gguf = env.get("BONSAI_GGUF", "Ternary-Bonsai-2-27B-PTQ1_0.gguf")
    dir_models = Path(env.get("BONSAI_MODELS_DIR", "E:/GitHub/whispertext/backend/bonsai/models"))
    ruta = dir_models / gguf
    if ruta.exists() and ruta.stat().st_size < GGUF_MIN_BYTES:
        print(f"⚠ GGUF truncado ({ruta.stat().st_size / 1e9:.2f} GB < 3 GB) — se elimina para re-descarga")
        ruta.unlink(missing_ok=True)
    elif ruta.exists():
        print(f"✓ GGUF presente ({ruta.stat().st_size / 1e9:.2f} GB)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Instalador de Estudio Doctorado")
    parser.add_argument("--sin-gpu", action="store_true", help="no activar el perfil gpu (Bonsai en CPU no; usa fallback LLM)")
    parser.add_argument("--solo-env", action="store_true", help="solo generar el .env y salir")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    args = parser.parse_args()

    print("== Estudio Doctorado · coordinador ==\n")

    # 1) Docker (no necesario si solo se genera el .env)
    if not args.solo_env:
        if correr(["docker", "info"]).returncode != 0:
            print("❌ Docker no está corriendo. Ábrelo (Docker Desktop) y reintenta.")
            return 1
        print("✓ Docker activo")

    # 2) GPU
    gpu = (not args.sin_gpu) and hay_gpu()
    print(f"{'✓ GPU NVIDIA detectada → perfil gpu (Bonsai 27B en VRAM)' if gpu else '· Sin GPU → sin perfil gpu (configura LLM_FALLBACK_URL, p. ej. ollama)'}")

    # 3) .env
    generar_env(gpu)
    env = leer_env(ENV)

    if args.solo_env:
        return 0

    # 4) GGUF
    verificar_gguf(env, gpu)

    # 5) build + up
    print("\n→ Construyendo y levantando (esto tarda la primera vez)…")
    perfil = ["--profile", "gpu"] if gpu else []
    r = subprocess.run(["docker", "compose", *perfil, "up", "-d", "--build"], cwd=RAIZ)
    if r.returncode != 0:
        print("❌ Falló docker compose up — revisa el log de arriba")
        return 1

    # 6) esperar API
    api_puerto = env.get("API_PORT", "8600")
    url = f"http://localhost:{api_puerto}/salud"
    print(f"\n→ Esperando la API en {url}…")
    for _ in range(60):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    print("✓ API arriba")
                    break
        except Exception:
            time.sleep(3)
    else:
        print("⚠ La API tardó en responder; revisa:  docker compose logs api")

    front_puerto = env.get("FRONTEND_PORT", "8601")
    panel = f"http://localhost:{front_puerto}"
    print(f"""
✅ Plataforma lista
   Panel  : {panel}   (login: ADMIN_PASSWORD del .env)
   API    : http://localhost:{api_puerto}/docs
   Fuentes: se indexan con «Escanear fuentes» en Documentos, o:
            curl -X POST http://localhost:{api_puerto}/documentos/escanear
   Test SMTP: python scripts/probar_correo.py
""")
    if not args.no_abrir:
        webbrowser.open(panel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
