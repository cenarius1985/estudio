---
proyecto: ESTUDIO-DOCTORADO
documento: Runbook de operación
fecha: 2026-10-09
estado: 🔍 en revisión
tags: [runbook, docker, operación]
---

# Runbook — Plataforma Estudio Doctorado (tesis MRI-UTE)

> Sincronizar al vault con `python scripts/sincronizar_vault.py` cuando la
> unidad G: esté montada.

## Objetivo

Operación diaria de la plataforma: levantarla, indexar material, verificar el
tip diario, el chat y el estudio; diagnóstico de fallas.

## Alcance

Instalación, operación diaria, verificaciones y rollback. No cubre el
desarrollo de nuevas funciones (ver PRD `01-prd-plataforma-estudio.md`).

## Contenido

### 1. Instalación inicial

```bash
cd E:\GitHub\MRI\estudio-doctorado
python coordinador.py            # genera .env (copiando Brevo de reportesDiariosGes), detecta GPU y levanta todo
```

- Panel: http://localhost:8601 — login con `ADMIN_PASSWORD` (ver `.env`).
- API docs: http://localhost:8600/docs
- Sin GPU: `python coordinador.py --sin-gpu` y configurar `LLM_FALLBACK_URL`
  en `.env` (p. ej. `http://host.docker.internal:4686/v1` para ollama).

### 2. Operación diaria

| Acción | Cómo |
|---|---|
| Indexar material nuevo de la tesis | Panel → Documentos → **Escanear fuentes** (incremental por hash SHA256) |
| Subir un archivo suelto | Panel → Documentos → **Subir archivos** (pdf, tex, txt, md, csv, docx, xlsx, png, jpg, tif, ipynb) |
| Tip del día | Automático a la hora de Ajustes (cron del worker cada 15 min); manual con **Generar y enviar ahora** |
| Reenviar un tip ya hecho | Panel → Tips → **Reenviar** (usa el HTML almacenado, NO reprocesa) |
| Preguntar a la tesis | Panel → Chat (responde solo con citas; si no hay respaldo lo dice) |
| Estudiar | Panel → Estudio: decks con repetición espaciada, quiz y simulacro |
| Cambiar hora/destinatario/umbral | Panel → Ajustes (aplica en ≤15 min) |

### 3. Verificaciones

```bash
python scripts/probar_correo.py      # auth SMTP sin enviar (✅ ya verificado 2026-10-09)
curl http://localhost:8600/salud     # API + DB + estado LLM
docker compose ps                    # servicios arriba
docker compose logs -f worker        # ingesta / tips
```

Panel → Ajustes → **Probar autenticación** y **Ver estado LLM**.

### 4. Diagnóstico de fallas

| Síntoma | Causa probable | Acción |
|---|---|---|
| Chat responde «no hay LLM» | Bonsai apagado o GPU ocupada (whispertext, OCR…) | `docker compose --profile gpu up -d bonsai` o usar fallback; la GPU de 8 GB solo corre un modelo a la vez |
| Tip no llega | SMTP/destinatario en `.env` o worker caído | `probar_correo.py`; Ajustes → destinos; `logs worker` |
| Documentos en `error` | Archivo dañado o sin texto | Panel → Documentos → ver tooltip del error; reintentar 🔁 |
| Ingesta lenta | OCR de PDFs escaneados | Normal (Tesseract por página); esperar; worker serializa jobs |
| GGUF truncado | Descarga interrumpida (<3 GB) | Borrar el archivo en `BONSAI_MODELS_DIR`; el entrypoint re-descarga |
| Bonsai no cabe en VRAM | Otra app usando la GPU | Bajar `BONSAI_NGL` en `.env` o liberar la GPU |

### 5. Respaldos y rollback

- BD completa: `docker compose exec db pg_dump -U estudio estudio > respaldo.sql`
- Todo el estado vive en volúmenes docker (`pgdata`, `modelos`, `cargas`).
- Actualizar código: `git pull && docker compose --profile gpu up -d --build`.

### 6. Seguridad

- Puertos publicados solo en 127.0.0.1 (panel/API/DB/redis/bonsai).
- `.env` fuera de git (credenciales Brevo reales del MINSAL).
- Login por contraseña única (`ADMIN_PASSWORD`), token 30 días.

## Ejemplos

- Forzar segundo tip el mismo día: Tips → marcar **forzar** → Generar.
- Ver cobertura de temas: Tips → encabezado («cobertura X%» = chunks ya usados).

## Checklist de verificación

- [ ] `python coordinador.py` deja 6 servicios en `healthy/up`.
- [ ] Escaneo inicial indexa la tesis completa sin errores.
- [ ] Chat cita archivo y página reales; pregunta trampa → «No encontré eso…».
- [ ] Tip de prueba llega al correo y el re-envío no regenera.
- [ ] `scripts/sincronizar_vault.py` copia PRD y runbook a G: cuando esté montada.
