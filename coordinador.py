#!/usr/bin/env python3
"""Coordinador de Estudio — instalador todo-en-uno (open source).

Decide la instalación según la ARQUITECTURA detectada:

  GPU NVIDIA + Docker con runtime nvidia + VRAM ≥ 7 GB
      → perfil `gpu`: LLM Bonsai 27B local en tu GPU.
  GPU con VRAM insuficiente, o Docker sin runtime NVIDIA
      → sin perfil gpu + guía para arreglarlo; usa un LLM externo.
  Sin GPU
      → detecta Ollama / LM Studio / llama.cpp local y lo conecta
        (LLM_BASE_URL=host.docker.internal); si no hay nada, se
        configura después desde el panel (Ajustes → LLM).

Además: genera el .env con credenciales ALEATORIAS, verifica el GGUF,
construye y levanta los contenedores y abre el panel.

Uso:  python coordinador.py [--sin-gpu] [--gpu-forzado] [--solo-env] [--no-abrir]
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

# El 27B PTQ1_0 completo pesa ~5.7 GB (modelo + contexto ≈ 6.5-7 GB de VRAM).
GGUF_MIN_BYTES = 3_000_000_000
VRAM_MIN_MB = 7000        # mínimo para Bonsai 27B completo (-ngl 99)
VRAM_AVISO_MB = 5500      # por debajo de esto: la GPU está ocupada → aviso


def correr(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def info_gpu() -> dict | None:
    """GPU NVIDIA del host: nombre, VRAM total y libre (MiB), o None."""
    if not shutil.which("nvidia-smi"):
        return None
    r = correr(["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits"])
    if r.returncode != 0:
        return None
    try:
        nombre, total, libre = [x.strip() for x in r.stdout.splitlines()[0].split(",")]
        return {"nombre": nombre, "total_mb": int(total), "libre_mb": int(libre)}
    except (ValueError, IndexError):
        return None


def docker_con_gpu() -> bool:
    """¿Docker puede usar la GPU? (runtime nvidia; en Windows: backend WSL2)."""
    r = correr(["docker", "info", "--format", "{{json .Runtimes}}"])
    if r.returncode == 0 and "nvidia" in r.stdout.lower():
        return True
    r2 = correr(["docker", "info"])
    return r2.returncode == 0 and "nvidia" in (r2.stdout + r2.stderr).lower()


LLMS_LOCALES = ((11434, "Ollama"), (1234, "LM Studio"), (8080, "llama.cpp"))


def detectar_llm_local() -> tuple[str, int] | None:
    """Endpoint OpenAI-compatible ya corriendo en el host (para instalar sin GPU)."""
    for puerto, nombre in LLMS_LOCALES:
        try:
            with urllib.request.urlopen(f"http://localhost:{puerto}/v1/models", timeout=2) as resp:
                if resp.status == 200:
                    return nombre, puerto
        except Exception:  # noqa: BLE001
            continue
    return None


def decidir_arquitectura(sin_gpu: bool, gpu_forzado: bool) -> dict:
    """Matriz de decisión: {usar_gpu, motivo, gpu, llm_local}."""
    gpu = info_gpu()
    resultado = {"usar_gpu": False, "motivo": "", "gpu": gpu, "llm_local": detectar_llm_local()}

    if sin_gpu:
        resultado["motivo"] = "--sin-gpu"
        return resultado
    if gpu is None:
        resultado["motivo"] = "sin GPU NVIDIA detectada"
        return resultado
    if not docker_con_gpu():
        resultado["motivo"] = (
            f"GPU {gpu['nombre']} presente pero Docker NO tiene runtime NVIDIA "
            "(en Windows: Docker Desktop → Settings → General → «Use the WSL 2 based engine», "
            "actualiza el driver NVIDIA; en Linux: nvidia-container-toolkit)"
        )
        return resultado
    if gpu["total_mb"] < VRAM_MIN_MB and not gpu_forzado:
        resultado["motivo"] = (
            f"GPU {gpu['nombre']} con {gpu['total_mb']} MiB de VRAM: insuficiente para el "
            f"LLM local de 27B (se recomienda ≥ {VRAM_MIN_MB} MiB). Se instalará sin él"
        )
        return resultado
    resultado["usar_gpu"] = True
    if gpu["libre_mb"] < VRAM_AVISO_MB:
        resultado["motivo"] = (
            f"AVISO: la GPU está ocupada ahora ({gpu['libre_mb']} MiB libres de "
            f"{gpu['total_mb']}). El LLM local reintentará arrancar hasta que se libere"
        )
    return resultado


def leer_env(ruta: Path) -> dict[str, str]:
    vals: dict[str, str] = {}
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals


def generar_env(decision: dict) -> None:
    if ENV.exists():
        print("✓ .env ya existe (no se toca)")
        return

    print("→ Generando .env con credenciales aleatorias…")
    lineas = ENV_EJEMPLO.read_text(encoding="utf-8").splitlines()

    reemplazos = {
        "POSTGRES_PASSWORD": secrets.token_urlsafe(18),
        "ADMIN_PASSWORD": secrets.token_urlsafe(9),
    }

    # LLM según arquitectura detectada
    if decision["usar_gpu"]:
        pass  # default del ejemplo: http://bonsai:8080/v1
    elif decision["llm_local"]:
        nombre, puerto = decision["llm_local"]
        reemplazos["LLM_BASE_URL"] = f"http://host.docker.internal:{puerto}/v1"
        print(f"✓ LLM local detectado: {nombre} (puerto {puerto}) → LLM_BASE_URL")
    else:
        reemplazos["LLM_BASE_URL"] = ""

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
    parser.add_argument("--sin-gpu", action="store_true",
                        help="forzar instalación sin perfil gpu (LLM externo/detectado)")
    parser.add_argument("--gpu-forzado", action="store_true",
                        help="usar perfil gpu aunque la VRAM parezca insuficiente")
    parser.add_argument("--solo-env", action="store_true", help="solo generar el .env y salir")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    args = parser.parse_args()

    print("== Estudio · coordinador de instalación ==\n")

    if not args.solo_env:
        if correr(["docker", "info"]).returncode != 0:
            print("❌ Docker no está corriendo. Ábrelo (Docker Desktop) y reintenta.")
            return 1
        print("✓ Docker activo")

    decision = decidir_arquitectura(args.sin_gpu, args.gpu_forzado)
    gpu = decision["gpu"]
    if decision["usar_gpu"]:
        print(f"✓ GPU: {gpu['nombre']} ({gpu['total_mb']} MiB VRAM) + runtime NVIDIA en Docker"
              f" → perfil gpu (LLM Bonsai 27B local)")
    else:
        print(f"· Sin perfil gpu — {decision['motivo'] or 'según flags'}")
        if decision["llm_local"]:
            nombre, puerto = decision["llm_local"]
            print(f"  ↳ Se conectará a tu {nombre} local (puerto {puerto})")
        else:
            print("  ↳ Configura un LLM en el panel (Ajustes → LLM): Ollama, LM Studio… "
                  "p. ej. http://host.docker.internal:11434/v1")
    if decision["usar_gpu"] and decision["motivo"].startswith("AVISO"):
        print(f"  ⚠ {decision['motivo']}")

    generar_env(decision)
    if args.solo_env:
        return 0

    preparar_fuentes()
    verificar_gguf(leer_env(ENV), decision["usar_gpu"])

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
