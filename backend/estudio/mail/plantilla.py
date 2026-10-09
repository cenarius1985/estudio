"""Plantilla HTML del tip diario — adaptada de plantillaReporte
(reportesDiariosGes/Backend/correo.js): cabecera, caja con borde, botón y
versión texto-plano. Marca propia del doctorado, sin branding MINSAL.

El tip guarda su cuerpo HTML/texto en BD; reenviar usa exactamente eso
(0 reprocesamiento).
"""

from __future__ import annotations

TITULO = "📚 Tip de estudio"


def cuerpo_html_de(parrafos: list[str], citas: list[dict]) -> str:
    """Bloque interno (párrafos + fuentes) — lo que se almacena en tips.cuerpo_html."""
    out = "\n".join(f'<p style="margin:0 0 12px">{p}</p>' for p in parrafos)
    if citas:
        items = "".join(
            f'<li style="margin:2px 0">{c["archivo"]}'
            + (f' — pág. {c["pagina"]}' if c.get("pagina") else "")
            + "</li>"
            for c in citas
        )
        out += (
            '<div style="margin-top:14px;font-size:13px;color:#556">'
            "<b style='color:#2c3e50'>Fuentes (tus documentos):</b>"
            f"<ul style='margin:6px 0 0 18px;padding:0'>{items}</ul></div>"
        )
    return out


def cuerpo_texto_de(parrafos: list[str], citas: list[dict]) -> str:
    out = "\n\n".join(parrafos)
    if citas:
        out += "\n\nFuentes: " + "; ".join(
            c["archivo"] + (f" pág. {c['pagina']}" if c.get("pagina") else "") for c in citas
        )
    return out


def plantilla_tip(titulo: str, cuerpo_html: str, cuerpo_texto: str, link: str) -> dict:
    """→ {asunto, texto, html}."""
    return {
        "asunto": f"{TITULO} · {titulo}",
        "texto": f"{titulo}\n\n{cuerpo_texto}\n\nPlataforma de estudio: {link}\n",
        "html": f"""
<div style="background:#f4f4f4;padding:24px 0;font-family:'Segoe UI',Tahoma,Arial,sans-serif">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,.08)">
    <div style="background:linear-gradient(135deg,#1a365d,#2c5282);color:#fff;padding:22px 24px;text-align:center">
      <h1 style="margin:0;font-size:20px">Estudio</h1>
      <div style="opacity:.85;font-size:13px;margin-top:4px">Tu plataforma de estudio · tip diario</div>
    </div>
    <div style="padding:26px 24px;color:#333;line-height:1.6">
      <div style="background:#f8f9fa;border-left:5px solid #2c5282;border-radius:6px;padding:16px 18px;margin:0 0 20px">
        <div style="font-size:17px;font-weight:700;color:#2c3e50">{titulo}</div>
        <div style="font-size:14.5px;color:#333;margin-top:10px">{cuerpo_html}</div>
      </div>
      <p style="margin:0 0 8px">
        <a href="{link}" style="background:#28a745;color:#fff;padding:11px 22px;border-radius:6px;text-decoration:none;font-weight:700;font-size:14px;display:inline-block">&#128218; Abrir la plataforma</a>
      </p>
      <p style="color:#8a94a6;font-size:12px;margin:10px 0 0">Si el botón no funciona:<br>
        <span style="word-break:break-all">{link}</span></p>
    </div>
    <div style="background:#eee;color:#777;text-align:center;font-size:12px;padding:14px">
      Mensaje automático de tu plataforma de estudio · no responder.
    </div>
  </div>
</div>""",
    }
