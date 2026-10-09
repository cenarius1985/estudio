---
proyecto: ESTUDIO
documento: PRD — Temas de estudio (multi-tema)
fecha: 2026-10-09
estado: 🔍 en revisión
tags: [prd, temas, multi-tema]
---

# PRD — Temas de estudio: varios temas en una misma instalación

## Objetivo

Que una instalación de Estudio sirva para VARIOS temas de estudio (p. ej.
«Tesis MRI», «Oposiciones», «Inglés»), cada uno con sus documentos, chat,
tips diarios, flashcards y quizzes — sin perder nada de lo ya indexado.

## Alcance

### Dentro
- Tabla `temas` (nombre, descripción, color, `carpetas` de auto-clasificación,
  `tips_activo`).
- `tema_id` en documents, tips, conversaciones, decks y quizzes.
- Migración idempotente: lo existente pasa al tema «General» y se
  auto-clasifica por prefijos de carpeta al escanear.
- Tips: un tip diario por tema con `tips_activo` (idempotencia y dedupe por
  tema; asunto/cabecera con el nombre del tema).
- Chat y estudio (decks/quizzes) filtrados por tema activo; «Todos» permite
  búsqueda cruzada.
- Panel: página Temas (CRUD, color, carpetas, re-escaneo) + selector de tema
  activo global + mover documento de tema.

### Fuera
- Multiusuario; permisos por tema; tips con destinos distintos por tema.

## Reglas de negocio

1. **Sin pérdida**: los chunks/embeddings nunca se tocan; solo se asigna
   `tema_id` en los documents existentes.
2. **Auto-clasificación**: si la ruta relativa de un archivo empieza con uno
   de los prefijos (`carpetas`, separadas por coma) del tema, va a ese tema;
   si no coincide con ninguno, al tema «General».
3. **Eliminar tema**: solo si no tiene documentos, o indicando `mover_a`
   (sus documentos pasan a otro tema; tips/decks del tema se borran).
4. **Tip diario**: para cada tema con `tips_activo` se genera/envía un tip;
   la cobertura de temas (chunks usados) y el dedupe coseno son POR tema.

## Casos de prueba

1. Migración: todos los documents existentes quedan clasificados (0 con
   tema vacío); chunks totales idénticos antes/después.
2. Crear tema «Tesis MRI» con carpetas reales → re-escanear → sus ~2100
   docs asignados; «General» queda con el resto.
3. Tips: generar → un tip por tema activo, cada email con su tema; el mismo
   día no regenera.
4. Chat dentro de un tema no cita documentos de otros temas; «Todos» sí cruza.
5. Deck generado con tema activo usa solo chunks de ese tema.

## Checklist de verificación

- [ ] Migración sin pérdida (caso 1) ✅ 2026-10-09
- [ ] Auto-clasificación por carpetas (caso 2) ✅ 2026-10-09
- [ ] Tips por tema + idempotencia (caso 3) ✅ 2026-10-09
- [ ] Chat/estudio por tema (casos 4-5) ✅ 2026-10-09
