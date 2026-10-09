---
proyecto: ESTUDIO
documento: Actualización — open source, configuración completa y URLs
fecha: 2026-10-09
estado: ✅
tags: [actualización, open-source, configuración, urls]
---

# Actualización 2026-10-09 — Estudio se vuelve open source

## Qué cambió

1. **Rebranding**: «Estudio Doctorado · Tesis MRI-UTE» → **«Estudio — tu
   plataforma de estudio»** (plantilla de correo, panel, API, README). El
   proyecto deja de ser personal y se publica como open source (MIT).
2. **Configuración completa desde el panel** (`Ajustes → Configuración`):
   - Correo Brevo (host, puerto, usuario, contraseña write-only, remitente)
     con **tutorial para conseguir las claves** y link a brevo.com.
   - Tips: hora, destinatarios, umbral dedupe, reintentos, habilitado.
   - **Carpeta de fuentes** (seteable) y **agregar URLs** como material.
   - LLM: endpoint primario, respaldo y modelo.
   - **Contraseña del panel** cambiable (hash sha256; restablecer → .env).
3. **Credenciales BD → .env**: lo seteado en el panel (tabla `settings`) pisa
   al `.env`; si falta en el panel se usa el `.env`; si falta en ambos queda
   vacío y se configura después. Nuevo módulo `estudio/credenciales.py`.
4. **URLs como fuente**: `POST /documentos/url` → job `ingestar_url`
   (cola urgentes) descarga la página, extrae texto HTML→bloques (stdlib) y
   la indexa; las citas muestran la URL. Verificado: artículo corto (1 chunk)
   y largo (122 bloques / 38 KB).
5. **Open source**: `coordinador.py` genera `.env` con credenciales
   aleatorias (en el PC del autor además copia el SMTP de reportesDiariosGes),
   detecta GPU, build+up, abre el navegador. Compose con carpeta portable
   `./fuentes` por defecto; `LICENSE` MIT; README completo (instalación,
   arquitectura, tutorial Brevo, uso, variables).

## Por qué

- Publicar la plataforma para cualquier estudiante, no solo la tesis propia:
  sin edición de archivos, todo configurable desde el panel.
- Los usuarios nuevos no tienen `.env` con credenciales: la BD las guarda.

## Cómo se verificó

- Precedencia: `smtp_host` inválido en BD → probar-smtp FALLA; al limpiar
  (vacío) → vuelve al `.env` y autentica OK. ✅
- Contraseña: cambio → login nuevo OK, token viejo 401, restablecer → login
  del `.env` OK. ✅
- URLs: Wikipedia corta y larga indexadas vía cola urgentes (11 s y ~40 s). ✅
- Escaneo con carpeta resuelta BD→.env (RUTA_TESIS del host montada). ✅

## Incidente corregido durante la actualización

El refactor de `ruta_absoluta` omitió la fuente `montada` → 1476 documentos
pasaron a `error` ("no es un archivo local") en minutos. Corregido
(ruta resuelta desde ajustes), re-escaneo automático los re-encoló; la cola
drenó a ~30 docs/min. Lección: refactor de funciones-camino-crítico exige
prueba inmediata de los TRES orígenes (montada/upload/url).

## Pendiente

- Sincronizar este directorio al vault G: cuando la unidad esté montada
  (`python scripts/sincronizar_vault.py`).
- Publicar el repo (GitHub privado→público tras purga de secretos; el .env
  real NO está versionado).
