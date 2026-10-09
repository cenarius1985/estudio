#!/usr/bin/env python3
"""Coordinador de Estudio — instalador todo-en-uno (open source).

1. Verifica Docker.
2. Detecta GPU NVIDIA → decide el perfil `gpu` (LLM Bonsai local).
3. Genera el .env con credenciales ALEATORIAS (BD, panel).
   - El correo Brevo y demás se configuran después desde el panel
     (Ajustes → Configuración, con tutorial); o copiándolos al .env.
   - Si existe el .env de reportesDiariosGes (MINSAL) en el PC, ofrece
     copiar el SMTP silenciosamente (solo en esa máquina).
4. Verifica el GGUF de Bonsai (si está truncado lo borra → re-descarga).
5. docker compose up -d --build.
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
FUENTES = RAIZ / "fuentes"
SMTP_ORIGEN = Path("E:/GitHub/Ministerio/reportesDiariosGes/.env")

# El 27B PTQ1_0 completo pesa ~5.7 GB; menos de 3 GB = truncado.
GGUF_MIN_BYTES = 3_000_000_000


def correr(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


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


def generar_env() -> None:
    if ENV.exists():
        print("✓ .env ya existe (no se toca)")
        return

    print("→ Generando .env con credenciales aleatorias…")
    lineas = ENV_EJEMPLO.read_text(encoding="utf-8").splitlines()

    reemplazos = {
        "POSTGRES_PASSWORD": secrets.token_urlsafe(18),
        "ADMIN_PASSWORD": secrets.token_urlsafe(9),
    }

    # Conveniencia en el PC del autor: SMTP Brevo ya verificado de MINSAL.
    origen = leer_env(SMTP_ORIGEN) if SMTP_ORIGEN.exists() else {}
    smtp = {k: origen.get(k, "") for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM")}
    if smtp["SMTP_USER"] and smtp["SMTP_PASS"]:
        reemplazos.update({k: v for k, v in smtp.items() if v})
        reemplazos["TIPS_TO"] = smtp["SMTP_FROM"]
        print("✓ SMTP Brevo copiado desde reportesDiariosGes (solo en este PC)")
    else:
        print("· Sin SMTP en el .env: configúralo en el panel (Ajustes → Correo Brevo, "
              "tutorial incluido) o edítalo a mano en el .env")

    salida = []
    for linea in lineas:
        if "=" in linea and not linea.strip().startswith("#"):
            k = linea.split("=", 1)[0].strip()
            if k in reemplazos:
                salida.append(f"{k}={reemplazos[k]}")
                continue
        salida.append(linea)
    ENV.write_text("\n".join(salida) + "\n", encoding="utf-8")
    print("✓ .env creado. La contraseña del panel está en ADMIN_PASSWORD dentro del .env")


def preparar_fuentes() -> None:
    env = leer_env(ENV)
    ruta = env.get("RUTA_TESIS", "./fuentes")
    carpeta = Path(ruta) if Path(ruta).is_absolute() else (RAIZ / ruta)
    if not carpeta.exists():
        if ruta == "./fuentes":
            carpeta.mkdir(exist_ok=True)
            print(f"✓ Carpeta de fuentes creada: {carpeta} (deja ahí tus documentos)")
        else:
            print(f"⚠ RUTA_TESIS={ruta} no existe; créala o corrígela en el .env")


def verificar_gguf(env: dict[str, str], gpu: bool) -> None:
    if not gpu:
        return
    gguf = env.get("BONSAI_GGUF", "Ternary-Bonsai-2-27B-PTQ1_0.gguf")
    dir_models = Path(env.get("BONSAI_MODELS_DIR", "./bonsai/models"))
    if not dir_models.is_absolute():
        dir_models = RAIZ / dir_models
    ruta = dir_models / gguf
    dir_models.mkdir(parents=True, exist_ok=True)
    if ruta.exists() and ruta.stat().st_size < GGUF_MIN_BYTES:
        print(f"⚠ GGUF truncado ({ruta.stat().st_size / 1e9:.2f} GB < 3 GB) — se elimina para re-descarga")
        ruta.unlink(missing_ok=True)
    elif ruta.exists():
        print(f"✓ GGUF presente ({ruta.stat().st_size / 1e9:.2f} GB)")
    else:
        print("· El GGUF (~5.7 GB) se descargará solo la primera vez que levante bonsai")


def main() -> int:
    parser = argparse.ArgumentParser(description="Instalador de Estudio")
    parser.add_argument("--sin-gpu", action="store_true", help="sin perfil gpu (usa LLM_FALLBACK_URL, p. ej. Ollama)")
    parser.add_argument("--solo-env", action="store_true", help="solo generar el .env y salir")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    args = parser.parse_args()

    print("== Estudio · coordinador de instalación ==\n")

    if not args.solo_env:
        if correr(["docker", "info"]).returncode != 0:
            print("❌ Docker no está corriendo. Ábrelo (Docker Desktop) y reintenta.")
            return 1
        print("✓ Docker activo")

    gpu = (not args.sin_gpu) and hay_gpu()
    if gpu:
        print("✓ GPU NVIDIA detectada → perfil gpu (LLM Bonsai 27B local en VRAM)")
    else:
        print("· Sin GPU → sin perfil gpu. Configura un LLM en el panel (Ajustes → LLM), "
              "p. ej. Ollama: http://host.docker.internal:11434/v1")

    generar_env()
    if args.solo_env:
        return 0

    preparar_fuentes()
    verificar_gguf(leer_env(ENV), gpu)

    print("\n→ Construyendo y levantando (la primera vez tarda varios minutos)…")
    perfil = ["--profile", "gpu"] if gpu else []
    r = subprocess.run(["docker", "compose", *perfil, "up", "-d", "--build"], cwd=RAIZ)
    if r.returncode != 0:
        print("❌ Falló docker compose up — revisa el log de arriba")
        return 1

    env = leer_env(ENV)
    api_puerto = env.get("API_PORT", "8600")
    front_puerto = env.get("FRONTEND_PORT", "8601")
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

    panel = f"http://localhost:{front_puerto}"
    print(f"""
✅ Estudio listo
   Panel       : {panel}   (login: ADMIN_PASSWORD del .env)
   API docs    : http://localhost:{api_puerto}/docs
   Siguientes pasos:
     1) Ajustes → Correo Brevo (tutorial con link a https://www.brevo.com)
     2) Ajustes → Fuentes (carpeta y URLs) o Ajustes → Tips (destinatarios)
     3) Documentos → «Escanear fuentes» para indexar tu material
   Test SMTP   : python scripts/probar_correo.py
""")
    if not args.no_abrir:
        webbrowser.open(panel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
