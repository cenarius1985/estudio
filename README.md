# Estudio Doctorado — plataforma de estudio de la tesis MRI-UTE

Plataforma personal dockerizada que indexa todo el material de la tesis
(PDF, LaTeX, Word, Excel, TXT/MD/CSV, imágenes con OCR, notebooks), envía un
**tip diario por correo (Brevo)**, responde **preguntas en la web con citas
estrictas** a los documentos (sin inventar), y genera **flashcards,
cuestionarios y simulacros** estilo Astra AI con repetición espaciada.

## Arquitectura

| Servicio | Tecnología | Puerto |
|---|---|---|
| db | PostgreSQL 16 + pgvector (BD vectorial + FTS + grafo) | 5433 |
| redis | Cola ARQ | 6380 |
| api | FastAPI | 8600 |
| worker | ARQ (ingesta, embeddings, tips diarios, SMTP) | — |
| frontend | Next.js 14 (panel) | 8601 |
| bonsai | LLM local Ternary-Bonsai-2-27B (perfil `gpu`) | 8602 |

## Puesta en marcha

```bash
python coordinador.py            # detecta GPU, genera .env, descarga modelos y levanta todo
```

Manual (sin coordinador):

```bash
cp .env.example .env             # completar SMTP_* (Brevo) y TIPS_TO
docker compose up -d --build     # añadir --profile gpu si hay GPU NVIDIA
```

- Panel: http://localhost:8601 (login con `ADMIN_PASSWORD`)
- API docs: http://localhost:8600/docs
- Test SMTP sin enviar correo: `python scripts/probar_correo.py`

## Decisiones clave

- **Respuestas fieles**: recuperación híbrida (pgvector + BM25/RRF + grafo de
  conceptos) y generación con citas obligatorias `[Fuente N]`; si el contexto
  no basta, responde "No encontré eso en tus documentos".
- **Tips sin duplicados**: cada tip se guarda con su embedding; si uno nuevo
  supera el umbral de similitud (default 0.90) se reutiliza el almacenado sin
  reprocesar. Reenviar un tip histórico usa el HTML guardado.
- **Ingesta incremental**: hash SHA256 por archivo (solo se reindexa lo que cambió).
- **LLM**: Bonsai 27B local (patrón [whispertext](../whispertext) rama `gpu`)
  con `LLM_FALLBACK_URL` opcional (p. ej. ollama).

## Documentación

- `docs/vault/01-prd-plataforma-estudio.md` — PRD (sincronizar al vault DATACEF
  con `python scripts/sincronizar_vault.py` cuando la unidad G: esté montada).
- `docs/vault/02-runbook-estudio-doctorado.md` — operación diaria.
