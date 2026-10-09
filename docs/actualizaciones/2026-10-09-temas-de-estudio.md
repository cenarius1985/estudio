---
proyecto: ESTUDIO
documento: Actualización — Temas de estudio (multi-tema)
fecha: 2026-10-09
estado: ✅
tags: [actualización, temas, multi-tema, migración]
---

# Actualización 2026-10-09 — Temas de estudio

## Qué cambió

- Nueva tabla `temas` (nombre, descripción, color, `carpetas` de
  auto-clasificación, `tips_activo`) y `tema_id` en documents, tips,
  conversaciones, decks y quizzes (PRD `03-prd-temas-de-estudio.md`).
- **Migración sin pérdida** (idempotente en `crear_esquema`): todo lo
  pre-existente pasa al tema «General»; los chunks/embeddings no se tocan.
- Escaneo con **auto-clasificación por prefijos de carpeta** por tema;
  endpoint `POST /temas/{id}/reclasificar`; mover documento a mano.
- Tips: **un tip diario por tema activo** (idempotencia, cobertura y dedupe
  coseno POR tema); asunto/cabecera del email con el nombre del tema.
- Chat y estudio filtrados por tema activo (selector global en el panel;
  «Todos» = búsqueda cruzada). Stats del dashboard por tema.
- `crear_esquema` reforzado: DDL por sentencia con `lock_timeout` y reintentos
  (los ALTER no-ops necesitan lock exclusivo y la ingesta puede tener `chunks`
  caliente → antes la API se quedaba colgada arrancando).

## Incidentes corregidos durante la implementación

1. INSERT del tema «general» sin la columna NOT NULL `carpetas` → NotNull.
2. API colgada en arranque: ALTERs esperando lock exclusivo de `chunks` tras
   la ingesta continua del worker (sesiones en `Lock` en pg_stat_activity).
3. Bonsai killed por el host (exit 137, presión de RAM con ingesta+embeddings
   simultáneos): reiniciado; el fallback extractivo mantuvo los tips.
   Lección: en la misma máquina, ingesta masiva y LLM compiten por RAM.

## Verificación (checklist del PRD completo)

- Migración: 4137 chunks intactos, 0 documents sin tema. ✅
- Tema «Tesis MRI» creado con carpetas reales → 1445 docs / 3807 chunks;
  «General» 680 docs con tips apagados. ✅
- Tips: solo «Tesis MRI» generó y envió al Gmail personal (asunto con tema);
  «General» omitido por tips_activo=false. ✅
- Chat con tema: citas solo de archivos de la tesis; con LLM recuperado. ✅
- Deck dentro del tema: «MRI-UTE en bajo campo + US-BDAT» (5 tarjetas). ✅
