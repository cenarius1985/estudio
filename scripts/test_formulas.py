# -*- coding: utf-8 -*-
"""Prueba del pipeline de fórmulas LaTeX→PNG (se copia y ejecuta DENTRO del
contenedor worker-urgente; el heredoc por docker exec colapsa backslashes)."""
from estudio.mail.plantilla import cuerpo_html_de, cuerpo_texto_de
from estudio.rag.matematica import latex_a_img

# cuerpo simulado como lo generaría el LLM (párrafos ya separados por \n+)
parrafos = [
    "La trayectoria radial de la secuencia UTE se define como",
    "$$k(t) = \\frac{\\gamma}{2\\pi}\\int_0^t G(\\tau)\\,d\\tau$$",
    "donde $\\gamma$ es la razón giromagnética y $T_2^*$ el decaimiento "
    "transversal efectivo del pool de agua ligada [Fuente 3]. La señal "
    "tri-componente resulta",
    "$$S(t) = \\sum_{i} f_i\\,e^{-t/T_{2,i}^*}$$",
    "con fracciones $f_i$ normalizadas ($\\sum_i f_i = 1$) [Fuente 5]. "
    "Fórmula no soportada de prueba: $$\\begin{align}x=1\\end{align}$$",
]
citas = [{"archivo": "anexo1_fisica_ute.pdf", "pagina": "12"}]

html = cuerpo_html_de(parrafos, citas)
texto = cuerpo_texto_de(parrafos, citas)

print("== HTML ==")
print("imgs:", html.count("<img"), "(esperado 6: 2 display + γ, T2*, f_i, Σf=1 + 1 para el entorno alineado si cayera a img — el align debe CAER a caja)")
print("divs centrados:", html.count('text-align:center'))
print("cajas mono (fallback + unicode):", html.count("Cascadia"))
print("div dentro de p:", "<p" in html.split("<div")[0] and "<div" in html and "<p" in html[html.find("<div"):html.find("</div>")] if "<div" in html else "n/a")
for linea in html.split("\n"):
    print(" ", linea[:150])
print()
print("== TEXTO PLANO ==")
print(texto)
