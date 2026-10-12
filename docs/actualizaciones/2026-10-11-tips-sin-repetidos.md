---
proyecto: ESTUDIO
documento: Actualización — Tips sin repetidos (cuota, dedupe y siembra)
fecha: 2026-10-11
estado: ✅
tags: [actualización, tips, dedupe, brevo, cron]
---

# Actualización 2026-10-11 — Tips sin repetidos

## Incidente

El usuario recibía el mismo tip por correo una y otra vez (hasta 10 veces el
mismo título; 36 y 42 tips los días 09/10-oct). Tres causas combinadas:

1. `tips_por_dia` había quedado en **6** en Ajustes (se esperaban 2).
2. El camino «duplicado» de `_tip_de_tema` **reenviaba el tip original**
   (reutilización sin reproceso): con el tema «Tesis MRI» semánticamente
   agotado tras el ciclo de siembra, TODOS los cupos caían en duplicado y
   reenviaban contenido ya visto (el 11-oct los 5 correos fueron reenvíos).
3. `scripts/ciclo_50_tips_ute.py` (siembra, ~80 generaciones forzadas el
   09/10-oct) asumía «sin correo porque TIPS_TO vacío en .env», pero los
   destinos ya viven en la tabla `settings` (pisan el .env) → cada tip
   forzado se envió de verdad.

## Qué cambió

- **Duplicado ⇒ silencio**: si todos los reintentos duplican (o ninguna
  semilla tiene material técnico), NO se crea la copia ni se envía correo;
  el tema queda marcado **agotado por hoy** en Redis (`tip:agotado:{tema}:{fecha}`,
  TTL 24 h) y el cron deja de reintentar cada 15 min. Respuesta del job:
  `sin_contenido_nuevo`.
- **Reintentos con semillas distintas**: `chunk_menos_cobierto(n=reintentos)`
  de una vez (antes se re-muestreaba y podía repetir semilla). Con consulta
  de siembra fija no se reintenta (la semilla no cambia).
- **`forzar` = siembra sin correo**: `generar_tip_diario(forzar=True)` guarda
  con estado `generado` y salta el SMTP (salvo `enviar=True` explícito).
  `POST /tips/generar` acepta `enviar` opcional (default: `not forzar`).
- **Cron sin acumulación**: `chequear_tip_diario` encola con
  `_job_id=tip_diario_{fecha}` (arq reemplaza pendientes) y salta temas
  marcados agotados.
- **Reparto de cupos equiespaciado DENTRO de [tips_hora, 22:00)**: con 2/día
  y 07:30 ⇒ 07:30 y ~14:45 (antes el último cupo caía justo a las 22:00).
- Panel Tips: fuera el checkbox «forzar»; el botón Generar respeta cuota.
- Limpieza BD: 33 copias (`duplicado_de`) borradas — backup previo en
  `_backups/tips_2026-10-11_pre_limpieza_duplicados.json` (fuera de git);
  `tips_por_dia` → 2.

## Verificación

- Smoke test post-fix: job disparó 8 semillas, 7 descartadas por
  `sin_material`, la 8ª generó un tip NUEVO («Modelo tricomponente de señal
  ósea con verosimilitud Rice»), dedupe < 0.92, 1 solo envío. Cuota 1/2.
- Reenvío manual (`✉️ Reenviar` del panel) sigue usando el contenido
  almacenado sin reprocesar — es explícito y puntual, no automático.
