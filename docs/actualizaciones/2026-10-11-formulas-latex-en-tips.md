---
proyecto: ESTUDIO
documento: Actualización — Fórmulas de tips como ecuaciones renderizadas (LaTeX → PNG)
fecha: 2026-10-11
estado: ✅
tags: [actualización, tips, latex, fórmulas, matplotlib, correo]
---

# Actualización 2026-10-11 — Fórmulas LaTeX renderizadas en tips

## Problema

Las fórmulas de los tips llegaban como "notación Unicode compacta" en una
línea (`k(t) = (γ/2π)·∫G(t)dt`) — ilegibles: una integral debe verse como
una integral. Gmail no ejecuta JavaScript (KaTeX/MathJax en vivo
imposibles), pero sí muestra imágenes `data:` embebidas.

## Qué cambió

- **NUEVO `backend/estudio/rag/matematica.py`**: `latex_a_img()` renderiza
  LaTeX a PNG con matplotlib mathtext (backend Agg, dpi 200, fondo
  transparente, texto #1a365d) y devuelve data-URI + dimensiones CSS
  (px/2, nítido en retina). `lru_cache` por fórmula (T2*, S(TE)… se
  repiten). Sanitiza `\text{}`→`\mathrm{}` y rechaza entornos
  multi-línea; import diferido (el worker no paga la RAM de matplotlib si
  el tip no trae fórmulas). `matplotlib==3.10.9` añadido a requirements.
- **`PROMPT_TIP`**: de "PROHIBIDO LaTeX / Unicode compacto" a **LaTeX
  real**: cada fórmula clave en su propia línea entre `$$...$$` (ejemplos
  del dominio: k(t)=γ/2π∫G dτ, S(TE)=S₀e^(−TE/T2*), Δf=82 Hz con
  decimales `{,}`), símbolos cortos inline `$T_2^*$`. Título sigue SIN
  LaTeX (asunto del correo y listado).
- **`plantilla.py`**: `renderizar_matematica` extrae `$$`/`$` ANTES del
  escape → display = `<div>` centrado con `<img>` (fuera de `<p>`, HTML
  válido), inline = img con `vertical-align:middle`; fallback a la caja
  monoespaciada si mathtext no soporta la expresión. `cuerpo_texto_de`
  convierte LaTeX → Unicode (fracciones `(a)/(b)`, griegas τ π ρ σ…) para
  la versión texto-plano del correo.
- **`_cuerpo_valido`**: valida con los segmentos `$…$` extraídos (un
  `= {` o `\frac{}` legítimo dentro de una ecuación ya no rechaza el tip).
- **Migración `scripts/tips_a_latex.py`**: GLM reescribe SOLO la notación
  de los tips existentes (valida citas [Fuente N] idénticas y longitud
  ±30%), regenera cuerpo_html + cuerpo_texto y **recalcula el embedding**
  (dedupe sigue midiendo bien). Idempotente (salta tips con `<img`).
  Resultado: **45/52 tips con ecuaciones (318 imágenes)**; 1 manual (VERSE,
  GLM no lo convertía); "Parámetros radiales" sin migrar correctamente
  (no tiene fórmulas). Backups en `_backups/tips_2026-10-11_pre_latex.json`.

## Verificación

- 6 fórmulas de la tesis → PNG OK (4-9 KB c/u); entorno align → fallback
  caja (degradación con gracia).
- Panel: modal del tip "Diseño UTE 2D" muestra integrales grandes,
  fracciones en dos pisos y subíndices correctos (inspección visual).
- Correo real reenviado al Gmail con las 10 ecuaciones del tip.

## Limitaciones conocidas

- Outlook desktop no muestra `data:` URIs (tu destino es Gmail; plan B si
  algún día hace falta: adjuntos CID vía Brevo).
- mathtext no soporta entornos multi-línea (align/cases): el prompt los
  prohíbe y el fallback los muestra como texto.
- Quizzes y decks siguen con fórmulas Unicode (texto plano en el panel);
  extender render a ellos sería trabajo aparte.
