# 📚 Estudio — tu plataforma de estudio con IA local

**Estudio** indexa TODO tu material de estudio (PDF, LaTeX, Word, Excel, TXT,
CSV, Markdown, imágenes con OCR, notebooks Jupyter y páginas web), te envía un
**tip diario por correo**, responde tus **preguntas con respuestas 100%
respaldadas por tus documentos** (con citas — si no está en tu material, lo
dice, no inventa) y te deja estudiar con **flashcards con repetición espaciada,
cuestionarios y simulacros de examen**.

Todo corre **local** con Docker: tus documentos no salen de tu máquina y el LLM
puede ser 100% propio (Bonsai, Ollama, LM Studio o cualquier API compatible
con OpenAI).

## ¿Para qué sirve?

| Quiero… | Estudio te da |
|---|---|
| Repasar sin leer todo de nuevo | Un tip diario por correo con citas a tus documentos, sin repetir temas ya enviados |
| Preguntar a mis apuntes | Chat que responde SOLO con lo que hay en tus documentos, citando archivo y página |
| Preparar un examen | Flashcards (SM-2), quizzes y simulacros cronometrados generados desde tu material |
| Tener todo centralizado | Búsqueda semántica + grafo de conceptos sobre PDFs, Word, Excel, LaTeX, imágenes, notebooks y URLs |

## Arquitectura

```
                    ┌──────────────────────────────────────────────┐
   tu carpeta  ──▶  │ worker (ARQ): OCR + extractores + embeddings │
   de documentos    │ + grafo de conceptos + tips diarios          │
   (bind mount ro)  └───────────────┬──────────────────────────────┘
   URLs (web)  ──────────────────────┤
   uploads    ───────────────────────┤
                                     ▼
                    ┌──────────────────────────┐   ┌───────────────┐
                    │ db: PostgreSQL 16 +      │◀─ │ redis (colas) │
                    │ pgvector (vectorial)     │   │ "urgentes" +  │
                    │ + BM25 (búsqueda texto)  │   │ ingesta       │
                    │ + grafo (nodos/aristas)  │   └───────────────┘
                    └────────────▲─────────────┘
                                 │
                    ┌────────────┴─────────────┐    ┌──────────────────────┐
   navegador ─────▶ │ api (FastAPI, :8600)     │◀──▶│ bonsai (perfil gpu)  │
                    │ REST + SSE (chat)        │    │ LLM 27B en tu GPU    │
                    └────────────▲─────────────┘    │ (o cualquier LLM     │
                                 │                  │  OpenAI-compatible)  │
                    ┌────────────┴─────────────┐    └──────────────────────┘
                    │ frontend (Next.js :8601) │
                    │ panel + chat + estudio   │
                    └──────────────────────────┘
                                 │  tips diarios
                                 ▼
                    ┌──────────────────────────┐
                    │ Brevo SMTP (relay correo)│
                    └──────────────────────────┘
```

**Por qué no alucina**: el LLM solo ve fragmentos recuperados de TUS documentos
(búsqueda híbrida: similitud vectorial + BM25 fusionadas con RRF, más expansión
por grafo de conceptos) y tiene prohibido responder sin citar. Si el contexto
no basta, responde exactamente «No encontré eso en tus documentos».

| Servicio | Tecnología | Puerto |
|---|---|---|
| db | PostgreSQL 16 + pgvector (BD vectorial + full-text + grafo) | 5433 |
| redis | Colas de jobs (ingesta / urgentes) | 6380 |
| api | FastAPI (REST + SSE) | 8600 |
| worker / worker-urgente | ARQ (OCR, embeddings, tips, decks) | — |
| frontend | Next.js 14 (panel) | 8601 |
| bonsai (opcional, perfil `gpu`) | llama-server + Ternary-Bonsai-2-27B | 8602 |

## Instalación

Requisitos: Docker (con WSL2 en Windows) y Python 3.10+.

```bash
git clone <este-repo> && cd estudio
python coordinador.py
```

El coordinador decide la instalación según tu arquitectura:

| Detecta | Instala |
|---|---|
| GPU NVIDIA + Docker con runtime NVIDIA + ≥7 GB VRAM | Perfil `gpu`: LLM Bonsai 27B local en tu GPU (si la VRAM está ocupada, avisa y reintenta) |
| GPU con <7 GB VRAM, o Docker sin runtime NVIDIA | Sin LLM local + guía para habilitarlo (WSL2 / nvidia-container-toolkit) |
| Sin GPU, con Ollama / LM Studio / llama.cpp corriendo | Los detecta y conecta automáticamente (`LLM_BASE_URL`) |
| Sin GPU y sin LLM local | Sin LLM: se configura después en el panel (Ajustes → LLM) |

Además:
1. Crea el `.env` con **credenciales aleatorias** (BD y contraseña del panel).
2. Construye y levanta todos los contenedores.
3. Abre el panel en el navegador (la contraseña está en `ADMIN_PASSWORD`
   dentro del `.env`).

Flags: `--sin-gpu` (forzar sin LLM local) · `--gpu-forzado` (usarlo aunque la
VRAM parezca insuficiente) · `--solo-env` (solo generar el .env) · `--no-abrir`.

### Instalación manual

```bash
cp .env.example .env        # edita POSTGRES_PASSWORD y ADMIN_PASSWORD
mkdir fuentes               # deja ahí tus documentos (o apunta RUTA_TESIS)
docker compose up -d --build          # añade --profile gpu si tienes NVIDIA
```

### Configuración (todo desde el panel)

Entra a **Ajustes → Configuración**. Todo lo que configures ahí se guarda en
la base de datos y **tiene prioridad sobre el `.env`** — si el `.env` no trae
un valor, se toma de la BD. No necesitas editar archivos:

- **Correo Brevo** (para los tips diarios) con tutorial y link a
  <https://www.brevo.com/>.
- **Tips**: hora de envío, destinatarios, umbral anti-duplicados.
- **Fuentes**: carpeta de documentos y **agregar URLs** como material.
- **LLM**: endpoint primario, respaldo y modelo.
- **Seguridad**: cambiar la contraseña del panel.

### Tutorial: conseguir las claves de Brevo (2 minutos, gratis)

1. Crea una cuenta en <https://www.brevo.com/> (plan gratuito: 300 correos/día).
2. Verifica tu cuenta con el correo que te envían.
3. Menú **Perfil → SMTP & API**.
4. Pulsa **「Generate a new SMTP key」** y copia la clave → es la *contraseña*.
5. El *usuario* aparece en esa misma página.
6. Pega ambos en **Ajustes → Correo Brevo** (host `smtp-relay.brevo.com`,
   puerto `587`) y pulsa «Probar autenticación» (verifica sin enviar nada).

### Usar un LLM de pago (más avanzado que Bonsai)

En **Ajustes → LLM** eliges el proveedor y pegas tu API key (se guarda en tu
base de datos, nunca se muestra de nuevo y puedes borrarla dejando el campo
vacío). Todos usan el mismo cliente OpenAI-compatible, así que funcionan sin
código extra:

| Proveedor | Dónde conseguir la API key |
|---|---|
| OpenAI | platform.openai.com/api-keys |
| DeepSeek | platform.deepseek.com/api_keys |
| Moonshot · Kimi | platform.moonshot.ai/console/api-keys |
| Google Gemini | aistudio.google.com/app/apikey |
| Anthropic Claude | console.anthropic.com/settings/keys |
| Groq | console.groq.com/keys |
| OpenRouter (miles de modelos) | openrouter.ai/settings/keys |
| Personalizado | cualquier endpoint OpenAI-compatible |

El botón **Estado** valida el endpoint Y la key (401 ⇒ «API key rechazada»).
Puedes mantener Bonsai/Ollama como **respaldo** para no quedarte sin LLM.

> Privacidad: con un LLM en la nube, los fragmentos recuperados de tus
> documentos se envían al proveedor para generar cada respuesta. Los
> embeddings y la base de datos siempre quedan en tu máquina.

## Uso diario

1. **Documentos** → «Escanear fuentes» (ingesta incremental: solo reindexa lo
   que cambió, por hash SHA256), sube archivos sueltos o agrega URLs.
2. **Chat** → pregunta lo que quieras; cada afirmación llega con
   `[Fuente N]` clicable al archivo y página.
3. **Tips** → historia de tips enviados, «Generar y enviar ahora», reenviar
   cualquiera **sin reprocesar** (usa el HTML almacenado).
4. **Estudio** → genera decks de flashcards (repetición espaciada SM-2),
   quizzes y simulacros cronometrados.
5. **Panel** → estado de sistema, cobertura de temas, grafo de conceptos.

## Variables del .env (opcionales — el panel manda)

| Variable | Default | Para qué |
|---|---|---|
| `ADMIN_PASSWORD` | aleatoria | Contraseña inicial del panel |
| `RUTA_TESIS` | `./fuentes` | Carpeta HOST con tus documentos (montada en `/fuentes`) |
| `SMTP_*` / `TIPS_TO` | vacío | Relay Brevo y destinatarios (o configúralo en el panel) |
| `LLM_BASE_URL` / `LLM_FALLBACK_URL` / `LLM_MODEL` | bonsai | Cualquier API OpenAI-compatible |
| `BONSAI_MODELS_DIR` | `./bonsai/models` | Dónde se guarda el GGUF (~5.7 GB) |
| `EXCLUDE_DIRS` | `.git,node_modules,…` | Carpetas que el escaneo ignora |
| `GRAFO_LLM` | `0` | Extraer tripletas del grafo con LLM (lento) |

## Desarrollo

```bash
docker compose logs -f worker        # ingesta / tips
docker compose exec db psql -U estudio -d estudio
python scripts/probar_correo.py      # auth SMTP sin enviar
python scripts/sincronizar_vault.py  # docs/vault → Obsidian (si usas el vault)
```

Documentación extendida en `docs/vault/` (PRD y runbook).

## Licencia

MIT — ver [LICENSE](LICENSE).
