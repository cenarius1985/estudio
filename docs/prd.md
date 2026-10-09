---
proyecto: ESTUDIO-DOCTORADO
documento: PRD plataforma de estudio
fecha: 2026-10-09
estado: 🔍 en revisión
tags: [prd, doctorado, mri, rag, docker]
---

# PRD — Plataforma de estudio "Estudio Doctorado" (tesis MRI-UTE)


## Objetivo

Plataforma personal dockerizada que indexa todo el material de la tesis doctoral
MRI-UTE (PDF, LaTeX, Word, Excel, TXT/MD/CSV, imágenes con OCR, notebooks) y:

1. Envía un **tip diario por correo** (Brevo SMTP) con contenido fiel a la tesis.
2. Permite **hacer preguntas en la web** con respuestas 100% respaldadas por los
   documentos (citas archivo/página; si no hay respaldo, lo declara).
3. Ofrece **flashcards, cuestionarios y simulacro** (estilo Astra AI) con
   repetición espaciada.
4. Administra todo desde un **panel web**: documentos, historial de tips
   anti-duplicados, chat, ajustes y estadísticas.

## Usuario objetivo

El propio autor de la tesis (usuario único). Sin multiusuario; acceso protegido
por contraseña simple de administrador.

## Alcance

### Dentro
- Ingesta multiformato con OCR (Tesseract spa+eng) de las carpetas de
  `E:\GitHub\MRI\Proyecto-Tesis`: tesis LaTeX/PDF, papers EN/ES, defensa,
  `RESULTADOS-MRI` (documentos, tablas, figuras, notebooks).
- Base de datos vectorial: PostgreSQL 16 + pgvector (embeddings multilingües
  fastembed `intfloat/multilingual-e5-large`).
- Recuperación híbrida: pgvector (coseno) + BM25 (tsvector) fusionadas con RRF
  + grafo de conocimiento ligero (entidades de dominio MRI y sus co-ocurrencias,
  extraídas por diccionario + LLM opcional).
- LLM local **Bonsai** (Ternary-Bonsai-2-27B, patrón del proyecto whispertext
  rama `gpu`) con fallback a cualquier endpoint OpenAI-compatible.
- Tips diarios: cron idempotente, dedupe por similitud coseno contra el
  historial, reenvío desde BD sin reprocesar, log de envíos.
- Correo por relay SMTP de Brevo (cuenta propia del usuario).
- Panel Next.js + chat SSE con citas estrictas.

### Fuera
- Datos crudos `Tensorflowmri` (54 GB) y binarios pesados.
- Multiusuario / roles / registro.
- Entrenamiento de modelos; solo inferencia.

## Contenido

### Arquitectura (docker-compose, puertos sin conflicto con 8300/8400/8500/4686)

| Servicio | Tecnología | Puerto | Rol |
|---|---|---|---|
| db | pgvector/pgvector:pg16 | 5433 | Relacional + vectorial + FTS + grafo |
| redis | redis:7 | 6380 | Cola ARQ + agendamiento |
| api | FastAPI (Python 3.11) | 8600 | REST + SSE |
| worker | ARQ | — | Ingesta, embeddings, grafo, cron tips, SMTP |
| frontend | Next.js 14 + Tailwind | 8601 | Panel + chat + estudio |
| bonsai (perfil gpu) | llama-server PrismML + GGUF 27B | interno | LLM local |

Instalador: `coordinador.py` (detecta GPU, genera `.env`, verifica GGUF,
levanta compose). Fallback LLM: `LLM_FALLBACK_URL` (p. ej. ollama :4686).

### Reglas de negocio clave

- **Fidelidad de respuesta**: el LLM solo puede responder citando fragmentos
  recuperados `[Fuente N]`; sin respaldo → "No encontré eso en tus documentos".
- **Tip diario idempotente**: si hoy ya se generó/envió, no se reprocesa.
- **Dedupe de tips**: similitud coseno del tip nuevo vs historial ≥ umbral
  (default 0.90) → se marca duplicado y se reutiliza/reenvía el tip almacenado
  (0 reprocesamiento); hasta 3 reintentos con otro tema.
- **Ingesta incremental**: hash SHA256 por archivo; solo se reindexa lo cambiado.
- **Reenvío histórico**: el panel reenvía el HTML almacenado, sin regenerar.

### Esquema de datos (resumen)

`documents`, `chunks(vector + tsv)`, `nodos`, `aristas`, `tips(vector)`,
`tips_envios`, `tips_chunks`, `decks`, `flashcards` (SM-2 lite), `quizzes`,
`preguntas`, `intentos`, `conversaciones`, `mensajes`, `settings`.

## Ejemplos

- "¿Qué secuencias UTE se compararon en el capítulo 3?" → respuesta con
  [Fuente: main.pdf, pág. 45].
- Tip diario: "T2* y su efecto en la señal UTE…" con citas al capítulo 4.
- Forzar un segundo envío el mismo día → detecta duplicado, no reprocesa.

## Casos de prueba

1. Ingesta de `main.pdf` (tesis), un `.xlsx` de RESULTADOS-MRI, una figura
   `.png` (OCR) y un `.tex` → chunks con embeddings y FTS.
2. Pregunta con respuesta en la tesis → cita correcta archivo+página.
3. Pregunta trampa → "No encontré eso en tus documentos".
4. Tip de prueba → llega por Brevo; segundo intento el mismo día → idempotente.
5. Tip con tema similar a uno histórico → duplicado detectado y reutilizado.
6. `coordinador.py` con y sin GPU → plataforma operativa (fallback LLM).

## Checklist de verificación

- [ ] `python coordinador.py` levanta todos los servicios (perfil según GPU).
- [ ] Test SMTP autentica sin enviar (`scripts/probar_correo.py`).
- [ ] Ingesta inicial completa sin errores (documentos `estado=listo`).
- [ ] Chat responde con citas y rechaza lo que no está en los documentos.
- [ ] Tip diario llega al correo con plantilla HTML correcta.
- [ ] Dedupe e idempotencia verificados (casos 4 y 5).
- [ ] Flashcards/quiz/simulacro generados y repaso SM-2 persiste.
- [ ] Runbook (`02-runbook-estudio-doctorado.md`) aprobado.
