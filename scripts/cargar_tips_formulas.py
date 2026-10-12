#!/usr/bin/env python3
"""Carga masiva de 20 tips de FÓRMULAS ESENCIALES (formulario de defensa).

Serie «Formulario · 01..20»: cada tip es UNA fórmula clave de la tesis con
sus símbolos explicados y su papel en la defensa (física UTE 0.55 T,
muestreo k-space, reconstrucción CS, relaxometría tri-componente y
métricas). Redactados a mano a partir del marco teórico indexado
(T01–T56), el paper y los guiones de defensa. Se insertan con estado
«generado», SIN enviar correos (mismo patrón que cargar_tips_cs.py).

    docker compose cp scripts/cargar_tips_formulas.py worker-urgente:/tmp/
    docker compose exec -T -e PYTHONPATH=/app worker-urgente \
        python /tmp/cargar_tips_formulas.py [--secos]

--secos: renderiza cuerpo_html de cada tip y reporta imágenes/cajas de
fallback SIN escribir en BD (validación de mathtext).
"""
import asyncio
import sys
from datetime import date

sys.path.insert(0, "/app")

from sqlalchemy import select  # noqa: E402
from estudio.db import SessionLocal  # noqa: E402
from estudio.mail.plantilla import cuerpo_html_de, cuerpo_texto_de  # noqa: E402
from estudio.models import Tema, Tip  # noqa: E402
from estudio.rag.embeddings import embedir_passages  # noqa: E402

TEMA = "933ee140ea124c5a8aff1afb06c5d257"

MT = "defensa_tesis_doctoral/marco-teorico"
GUION_CS = "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"

# (titulo, cuerpo con LaTeX $$..$$/$..$ y citas [Fuente N], citas)
TIPS: list[tuple[str, str, list[dict]]] = [
    (
        "Formulario · 01 · Larmor: ω₀ = γ·B₀",
        r"""La fórmula más citada de toda la defensa: los espines precesan alrededor del campo $B_0$ a una frecuencia proporcional al campo, con la razón giromagnética $\gamma$ del protón como constante de proporcionalidad [Fuente 1]. Es el ancla de todo el sistema: la RF debe excitar exactamente aquí, las bobinas se sintonizan a esta frecuencia y el off-resonance se mide como desviación respecto a ella.
$$\omega_0 = \gamma\,B_0$$
En frecuencia cíclica: $f_0 = \gamma B_0/2\pi$ con $\gamma/2\pi = 42.58\;\mathrm{MHz/T}$ para el protón. A $B_0 = 0.55\;\mathrm{T}$ (el campo bajo de esta tesis) resulta $f_0 \approx 23.4\;\mathrm{MHz}$ [Fuente 2].
Por qué importa en bajo campo: Larmor fija la escala de todo lo demás — el chemical shift agua-grasa es proporcional a $f_0$ (3.5 ppm → ~82 Hz a 0.55 T, frente a los cientos de Hz de alto campo), el SAR cambia con la frecuencia y el diseño de bobinas cambia de banda. Si el comité pregunta «¿qué cambia físicamente a 0.55 T?», la respuesta entera se cuelga de esta igualdad.""",
        [{"archivo": f"{MT}/bloque-B-fisica-resonancia-magnetica/T05-spin-larmor.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-B-fisica-resonancia-magnetica/T10-bajo-campo.md", "pagina": ""}],
    ),
    (
        "Formulario · 02 · La señal FID y el decaimiento T2*",
        r"""Tras la excitación, el magnetización transversal precesa y decae; la señal inducida en la bobina es la FID (free induction decay). Su forma funcional es el ladrillo de toda la tesis: cada pool de agua ósea es un término así [Fuente 1].
$$S(t) = S_0\;e^{-t/T_2^*}\;e^{\,i\,\omega_0 t}$$
Cada símbolo: $S_0$ es la amplitud inicial (densidad de protones por la excitación), $T_2^*$ el decaimiento transversal efectivo — incluye las inhomogeneidades de campo además del $T_2$ intrínseco — y $e^{i\omega_0 t}$ la rotación de fase a Larmor [Fuente 1]. El módulo decae como $e^{-t/T_2^*}$: la UTE lee esta curva casi desde $t = 0$ [Fuente 2].
Por qué es LA señal de la tesis: el hueso cortical tiene $T_2^*$ cortísimo (agua ligada), así que la FID muere en sub-milisegundos — la UTE existe para alcanzarla, y la relaxometría tri-componente no es más que ajustar sumas de estas exponenciales.""",
        [{"archivo": f"{MT}/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T11-te-ultra-corto.md", "pagina": ""}],
    ),
    (
        "Formulario · 03 · Relajación de Bloch: recuperación T1 y decaimiento T2",
        r"""Las ecuaciones de Bloch describen la evolución del magnetización; sus soluciones entre pulsos dan el contraste. Durante el TR el magnetización longitudinal se recupera hacia $M_0$ con constante $T_1$; hacia el eco, el transversal decae con $T_2$ [Fuente 1].
$$M_z(TR) = M_0\left(1 - e^{-TR/T_1}\right), \;\;\; M_{xy}(TE) = M_0\;e^{-TE/T_2}$$
Lección de contraste en dos igualdades: TR corto (comparable a $T_1$) satura y pondera en T₁; TE largo pondera en T₂. La UTE rompe la segunda: con TE de decenas de µs el factor $e^{-TE/T_2^*}$ apenas muerde y tejidos de $T_2^*$ ultracorto — invisibles en spin-eco — emiten señal medible [Fuente 1] [Fuente 2].
Para la defensa: explicar UTE es elegir $TE \ll T_2^*$ en esta fórmula; explicar saturación es la fracción de $M_z$ disponible en cada TR. Los dos fenómenos que el comité puede leer directamente de aquí.""",
        [{"archivo": f"{MT}/bloque-B-fisica-resonancia-magnetica/T07-relajacion-T1.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-B-fisica-resonancia-magnetica/T08-relajacion-T2.md", "pagina": ""}],
    ),
    (
        "Formulario · 04 · Señal de gradiente-eco en estado estacionario",
        r"""La UTE es un gradiente-eco con lectura radial: excitaciones repetidas con TR corto llevan el magnetización a un estado estacionario donde la señal por excitación queda determinada por α, TR, $T_1$ y TE [Fuente 1].
$$S \propto \sin\alpha\;\frac{1-e^{-TR/T_1}}{1-\cos\alpha\;e^{-TR/T_1}}\;e^{-TE/T_2^*}$$
Los tres factores, de izquierda a derecha: cuánta magnetización transversal crea el pulso ($\sin\alpha$), cuánta longitudinal hay disponible tras la saturación (la fracción de T₁, cuyo denominador se encoge cuando $\cos\alpha\,e^{-TR/T_1}$ se acerca a 1), y cuánta sobrevive hasta el eco ($e^{-TE/T_2^*}$) [Fuente 1].
Por qué memorizarla: de ella salen a la vez el ángulo de Ernst (maximizar el segundo factor) y el argumento UTE (minimizar el tercero). Una sola expresión conecta los tres parámetros de secuencia que la tesis manipula: α, TR y TE [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T11-te-ultra-corto.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T18-te-minimo.md", "pagina": ""}],
    ),
    (
        "Formulario · 05 · Ángulo de Ernst",
        r"""Dado un TR fijo, existe un ángulo de excitación que maximiza la señal en estado estacionario: el ángulo de Ernst. Se obtiene derivando la señal de gradiente-eco respecto de α e igualando a cero [Fuente 1].
$$\cos\alpha_E = e^{-TR/T_1}$$
Lectura rápida: TR mucho mayor que $T_1$ lleva $\alpha_E$ hacia 90° (no hay saturación, se usa todo el magnetización); TR mucho menor que $T_1$ da ángulos pequeños (pulso suave para no quemar una señal que apenas se ha recuperado). Ejemplo numérico: con TR = 10 ms y $T_1$ = 250 ms, $\alpha_E = \arccos(e^{-0.04}) \approx 16°$ [Fuente 1].
En la tesis, la UTE repite excitaciones radiales con TR corto y por eso trabaja con ángulos bajos: el Ernst dice cuánto pedirle a cada disparo. Es la respuesta estándar a «¿por qué no usas 90°, si da más señal por excitación?» [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T18-te-minimo.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-B-fisica-resonancia-magnetica/T07-relajacion-T1.md", "pagina": ""}],
    ),
    (
        "Formulario · 06 · Atenuación al eco: por qué TE ≪ T2*",
        r"""Cuánta señal sobrevive hasta leer el eco: nada más que el factor exponencial de la FID evaluado en TE. Esta igualdad, evaluada con los $T_2^*$ del hueso, es la justificación cuantitativa completa de la secuencia UTE [Fuente 1].
$$\frac{S(TE)}{S_0} = e^{-TE/T_2^*}$$
Números ilustrativos: agua ligada cortical con $T_2^*$ del orden de $0.4\;\mathrm{ms}$; con TE = 50 µs se conserva $e^{-0.125} \approx 88\%$ de la señal; con un TE clínico de 5 ms queda $e^{-12.5} \approx 4\times10^{-6}$ — el hueso literalmente desaparece de la imagen [Fuente 1]. La UTE, con TE de decenas de µs, es la única ventana donde ese pool es visible.
Argumento de defensa en una línea: cada microsegundo de TE cobra $e^{-TE/T_2^*}$ sobre el pool corto; minimizar TE no es refinamiento, es la diferencia entre señal y silencio [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T11-te-ultra-corto.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md", "pagina": ""}],
    ),
    (
        "Formulario · 07 · Trayectoria k(t): el gradiente como integral",
        r"""El gradiente no «codifica posiciones» directamente: hace que los espines adquieran fase acumulada, y esa fase se interpreta como posición en el espacio k. La trayectoria es la integral temporal del gradiente [Fuente 1].
$$\mathbf{k}(t) = \frac{\gamma}{2\pi}\int_0^t \mathbf{G}(\tau)\,d\tau$$
De aquí salen las dos decisiones de muestreo de la tesis: center-out radial (la lectura parte de $k = 0$ y sale hacia $k_{max}$ — el eco se forma al inicio de la lectura, TE ultracorto) y ramp sampling (se muestrea durante la rampa: como k es la integral, la rampa produce un barrido cuadrático en k, más lento cerca del centro) [Fuente 1] [Fuente 2].
Para la defensa: cualquier pregunta «¿dónde está el eco?» o «¿por qué muestrear en rampa?» se resuelve mirando esta integral — el tiempo de eco es el instante en que la trayectoria cruza el centro del espacio k.""",
        [{"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T13-trayectoria-kspace.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T17-ramp-sampling.md", "pagina": ""}],
    ),
    (
        "Formulario · 08 · FOV y resolución: Δk y k_max",
        r"""Dos igualdades gobiernan cualquier muestreo, cartesiano o radial: el espaciado entre muestras k fija el campo de vista, y la extensión máxima del k-space fija la resolución [Fuente 1].
$$FOV = \frac{1}{\Delta k}, \;\;\; \Delta x = \frac{1}{2\,k_{max}}$$
Lectura de defensa: un espaciado $\Delta k$ demasiado grande (pocas líneas o pocos radios) produce plegamiento de estructuras mayores que el FOV; un $k_{max}$ insuficiente produce borrosidad — pérdida de detalle fino, por ejemplo el borde cortical [Fuente 1]. En radial esto desemboca en el criterio de Nyquist de radios: del orden de $\pi\,N_x$ radios para una matriz de $N_x$ [Fuente 2].
Con la matriz de la tesis ($N_x = 500$) estas dos igualdades fijan el presupuesto de adquisición: cuántos radios compra Nyquist y cuántos regala el submuestreo CS — el puente entre la física de la secuencia y la reconstrucción.""",
        [{"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T16-gradiente-trapezoidal.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md", "pagina": ""}],
    ),
    (
        "Formulario · 09 · Off-resonance: φ = γ·ΔB₀·t (y los 82 Hz)",
        r"""Toda desviación de campo $\Delta B_0$ — inhomogeneidad o chemical shift — desplaza la frecuencia de precesión y acumula fase linealmente con el tiempo [Fuente 1].
$$\phi(t) = \gamma\,\Delta B_0\,t \;\;\Rightarrow\;\; \Delta f = \frac{\gamma}{2\pi}\,\Delta B_0$$
El caso emblemático: agua y grasa difieren en 3.5 ppm; a $B_0 = 0.55\;\mathrm{T}$ con $f_0 \approx 23.4\;\mathrm{MHz}$ resulta $\Delta f \approx 3.5\times10^{-6}\times 23.4\;\mathrm{MHz} \approx 82\;\mathrm{Hz}$ — el desplazamiento agua-grasa de la tesis [Fuente 2]. En ecos largos esa fase separa y cancela señal (bandas de fase opuesta); la médula ósea, llena de grasa, la sufre de primera mano.
Por qué está en el formulario: la separación agua-grasa de la plataforma (UTE-hmrGC) estima $\Delta B_0$ exactamente desde esta relación, y el modelo tri-componente incluye la médula con su frecuencia propia — 82 Hz no es una curiosidad, es un parámetro del modelo [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-E-supresion-grasa/T24-chemical-shift.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-E-supresion-grasa/T27-modelo-espectral-grasa.md", "pagina": ""}],
    ),
    (
        "Formulario · 10 · Imagen = inversa de Fourier del k-space",
        r"""La relación imagen-espacio k es una pareja de Fourier. La dirección que importa a la reconstrucción: la imagen es la integral del k-space pesada por la fase de cada posición [Fuente 1].
$$x(\mathbf{r}) = \int s(\mathbf{k})\;e^{\,i\,2\pi\,\mathbf{k}\cdot\mathbf{r}}\;d\mathbf{k}$$
El operador de medición E de la tesis ES esta integral discretizada: con trayectoria cartesiana uniforme es una FFT; con trayectoria radial (puntos k no uniformes sobre radios) exige la NUFFT — y por eso la reconstrucción CS cuesta una NUFFT directa y una adjunta por iteración [Fuente 2].
Idea de defensa: submuestrear el k-space no es «tomar menos fotos», es integrar sobre menos puntos — y la regularización (TV) decide cómo rellenar lo no medido. Esta integral es el eslabón entre la física de adquisición y el problema inverso.""",
        [{"archivo": f"{MT}/bloque-C-fisica-secuencia-ute/T12-relacion-fourier.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-F-reconstruccion/T30-operador-adquisicion.md", "pagina": ""}],
    ),
    (
        "Formulario · 11 · Ecuaciones normales con Tikhonov",
        r"""El problema de mínimos cuadrados $\Vert\mathbf{E}\mathbf{x}-\mathbf{y}\Vert^2$ tiene solución analítica cerrando el gradiente: las ecuaciones normales. Con regularización de Tikhonov para estabilizar el operador mal condicionado [Fuente 1].
$$\hat{x} = \left(\mathbf{E}^H\mathbf{E} + \lambda\,\mathbf{I}\right)^{-1}\mathbf{E}^H\,\mathbf{y}$$
Cada pieza: $\mathbf{E}^H$ es el adjunto (retroproyección), $\mathbf{E}^H\mathbf{E}$ la curvatura del problema — su mal condicionamiento al submuestrear es el corazón del asunto — y $\lambda\mathbf{I}$ empuja soluciones pequeñas para que la inversa no amplifique ruido [Fuente 1]. Es la reconstrucción clásica tipo SENSE.
Por qué la tesis NO la usa: el prior L₂ penaliza energía, no estructura — devuelve imágenes borrosas que reparten el aliasing en vez de eliminarlo. Saber escribirla de memoria es saber explicar qué se gana al cambiar L₂ por ℓ₁/TV: la esparsidad [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-F-reconstruccion/T29-problema-inverso.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-F-reconstruccion/T33-metodos-reconstruccion.md", "pagina": ""}],
    ),
    (
        "Formulario · 12 · Umbral suave: el proximal de la ℓ1",
        r"""El operador proximal de la norma ℓ₁ es el umbral suave (soft-thresholding): el único paso donde la regularización esparsa «actúa» dentro de FISTA y ADMM [Fuente 1].
$$\mathrm{prox}(v;\lambda) = \mathrm{sign}(v)\,\max\left(|v| - \lambda,\;0\right)$$
Lectura: los valores por debajo de λ en módulo se anulan exactamente (esparsidad real, no solo encoger) y los que superan λ se reducen en λ. Compárese con el proximal de L₂, que solo encoge ($v/(1+\lambda)$) sin nunca anular: esa diferencia operatoria es, matemáticamente, la diferencia entre Tikhonov y Compressed Sensing [Fuente 1].
Para la defensa: si preguntan «¿dónde entra exactamente la ℓ₁ en el algoritmo?», la respuesta es este operador aplicado a los coeficientes o gradientes en cada iteración del solver; todo lo demás (gradientes, FFT) es el término de datos [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-F-reconstruccion/T32-variacion-total.md", "pagina": ""}],
    ),
    (
        "Formulario · 13 · FISTA y el momentum de Nesterov",
        r"""FISTA resuelve problemas «término suave + ℓ₁» igual que el gradiente proximal, pero con memoria: extrapola hacia la dirección del paso anterior (momentum de Nesterov), lo que acelera la convergencia de $O(1/k)$ a $O(1/k^2)$ [Fuente 1].
$$y_{k+1} = x_k + \frac{t_k - 1}{t_{k+1}}\,\left(x_k - x_{k-1}\right), \;\;\; t_{k+1} = \frac{1 + \sqrt{1 + 4\,t_k^2}}{2}$$
La receta por iteración: gradiente del término de datos en $y_k$ (una NUFFT y una adjunta), paso proximal (umbral suave) hacia $x_{k+1}$, y este momentum que mira hacia atrás antes de saltar; la sucesión $t_k$ crece como $k/2$ y controla cuánto momentum [Fuente 1].
Contexto tesis: la familia proximal (FISTA, ADMM) existe porque la ℓ₁ no es diferenciable; la tesis resuelve TV con ADMM y el guion justifica L-BFGS con suavizado de Huber — pero si el comité pide «un método con garantía $O(1/k^2)$», es este [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-F-reconstruccion/T33-metodos-reconstruccion.md", "pagina": ""},
         {"archivo": GUION_CS, "pagina": "8"}],
    ),
    (
        "Formulario · 14 · Gradiente del término de datos: E^H(Ex − y)",
        r"""Todo solver de la reconstrucción (FISTA, ADMM, L-BFGS) necesita, en cada iteración, el gradiente del término de fidelidad. Es una sola línea que esconde el costo computacional completo [Fuente 1].
$$\nabla f(\mathbf{x}) = \mathbf{E}^H\,\left(\mathbf{E}\mathbf{x} - \mathbf{y}\right)$$
Se lee de adentro hacia afuera: proyectar la imagen actual al k-space ($\mathbf{E}$: NUFFT con sensibilidades y densidad), restar los datos medidos, y retroproyectar el residuo al espacio imagen ($\mathbf{E}^H$: la adjunta). Dos aplicaciones de operador por evaluación — por eso cada iteración cuesta «una NUFFT directa y una adjunta» [Fuente 1].
El corolario que el comité espera: $\mathbf{E}^H\mathbf{E}$ es la curvatura del problema; el submuestreo incoherente la hace mal condicionada y de ahí que, sin regularizador, la iteración amplifique aliasing en vez de eliminarlo [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-F-reconstruccion/T30-operador-adquisicion.md", "pagina": ""},
         {"archivo": GUION_CS, "pagina": "6"}],
    ),
    (
        "Formulario · 15 · Variación Total isotrópica",
        r"""La definición exacta del regularizador de la tesis: la TV isotrópica discreta suma la magnitud del gradiente de la imagen en cada vóxel [Fuente 1].
$$TV(\mathbf{x}) = \sum_{i,j}\sqrt{\left(x_{i+1,j} - x_{i,j}\right)^2 + \left(x_{i,j+1} - x_{i,j}\right)^2}$$
Es una ℓ₁ sobre la magnitud del gradiente, rotacionalmente invariante (de ahí «isótropa»; la variante anisotrópica suma valores absolutos por componentes). Penaliza las variaciones grandes vóxel a vóxel: regiones homogéneas y bordes finos son baratos, el ruido y el aliasing difuso son caros [Fuente 1].
Por qué encaja en cortical: hueso cortical = región suave limitada por bordes nítidos (periostio, endostio) — exactamente la señal de baja TV. El λ del funcional pondera fidelidad frente a este prior ($\lambda = 10^{-4}$ calibrado en la tesis) [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-F-reconstruccion/T32-variacion-total.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""}],
    ),
    (
        "Formulario · 16 · Modelo tri-componente y fracciones",
        r"""El biomarcador de la tesis en dos igualdades: la señal ósea como suma de tres exponenciales (agua ligada, agua de poro, médula) y la normalización que define las fracciones [Fuente 1].
$$S(t) = S_{bw}\,e^{-t/T_{2,bw}^*} + S_{pw}\,e^{-t/T_{2,pw}^*} + S_{bm}\,e^{-t/T_{2,bm}^*}$$
con fracciones normalizadas [Fuente 2]:
$$f_i = \frac{S_i}{S_{bw} + S_{pw} + S_{bm}}$$
Las $f_i$ (fracciones de agua ligada y de poro) son las que se correlacionan con la porosidad por BDAT/US y sostienen la interpretación biomecánica; los $T_{2,i}^*$ reportan la cinética de cada pool. Nota de defensa: la médula entra con fase propia por el chemical shift (82 Hz a 0.55 T), por eso el ajuste fino opera sobre la señal compleja con verosimilitud Riciana [Fuente 1].""",
        [{"archivo": f"{MT}/bloque-G-ruido-modelos/T39-modelo-tricomponente.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-I-procesamiento-metricas/T48-sistema-fracciones.md", "pagina": ""}],
    ),
    (
        "Formulario · 17 · Linealización ln S(t): pendiente −R2*",
        r"""Para una exponencial única, el logaritmo convierte el ajuste no lineal en una recta: pendiente $-R_2^*$ y ordenada $\ln S_0$ [Fuente 1].
$$\ln S(t) = \ln S_0 - R_2^*\,t, \;\;\; R_2^* = \frac{1}{T_2^*}$$
La trampa: la S medida es magnitud de datos complejos con ruido (distribución Rice), no señal pura. A SNR alto el logaritmo es casi insesgado; a SNR bajo — en las colas de la exponencial, donde la señal muere — el $\ln$ amplifica el sesgo positivo del ruido, la pendiente se aplana y $T_2^*$ queda sobreestimado. Por eso la tesis ajusta por MLE Riciano y no por log-lineal [Fuente 2].
Uso legítimo: inspección rápida en escala semilogarítmica — cada exponencial es un tramo recto, así que la curva revela cuántos pools hay (mono/bi/tri). La decisión del modelo sale de aquí; la estimación fina, del MLE.""",
        [{"archivo": f"{MT}/bloque-G-ruido-modelos/T37-modelo-monoexponencial.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-H-optimizacion/T41-lsq-rician.md", "pagina": ""}],
    ),
    (
        "Formulario · 18 · RMSE y PSNR",
        r"""Las métricas píxel a píxel contra la referencia (la reconstrucción completa): el error cuadrático medio y su versión en decibeles [Fuente 1].
$$RMSE = \sqrt{\frac{1}{N}\sum_{i}\left(x_i - \hat{x}_i\right)^2}, \;\;\; PSNR = 20\,\log_{10}\left(\frac{x_{max}}{RMSE}\right)$$
Aquí $x_i$ es la referencia, $\hat{x}_i$ la reconstrucción evaluada y N el número de vóxeles del ROI. El PSNR expresa el error como relación señal máxima-ruido en decibeles: subir 6 dB equivale a reducir el error a la mitad. Es sencillo y universal, pero global: no distingue un error distribuido de un borde destruido [Fuente 1].
Por eso la tesis lo acompaña de SSIM (estructura) y de métricas por ROI: el argumento al comité es que CS no solo iguala el RMSE frente a Nyquist completo, sino que las diferencias pareadas son significativas [Fuente 1].""",
        [{"archivo": f"{MT}/bloque-I-procesamiento-metricas/T50-metricas-ajuste.md", "pagina": ""}],
    ),
    (
        "Formulario · 19 · SSIM: luminancia, contraste y estructura",
        r"""La métrica de calidad estructural de la tesis: compara medias (luminancia), varianzas (contraste) y covarianza (estructura) entre referencia y reconstrucción, en ventanas locales [Fuente 1].
$$SSIM(x,y) = \frac{\left(2\,\mu_x\,\mu_y + C_1\right)\left(2\,\sigma_{xy} + C_2\right)}{\left(\mu_x^2 + \mu_y^2 + C_1\right)\left(\sigma_x^2 + \sigma_y^2 + C_2\right)}$$
Con $\mu$ medias locales, $\sigma^2$ varianzas locales, $\sigma_{xy}$ covarianza local y $C_1, C_2$ constantes pequeñas que estabilizan la división en regiones planas. Vale 1 solo si las imágenes coinciden; es sensible a la borrosidad y a la distorsión estructural que el RMSE perdona [Fuente 1].
Argumento de defensa: el par RMSE (energía) + SSIM (estructura) cubre las dos clases de error que importan en cortical — aliasing difuso y bordes borrados. Si CS empata RMSE pero gana SSIM, la estructura cortical se conservó; y como toda métrica, se mide tras alinear las series [Fuente 2].""",
        [{"archivo": f"{MT}/bloque-I-procesamiento-metricas/T50-metricas-ajuste.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-I-procesamiento-metricas/T46-registro-ecc.md", "pagina": ""}],
    ),
    (
        "Formulario · 20 · SNR y CNR",
        r"""El par de métricas de medición: cuánta señal hay sobre el ruido del sistema, y cuánto se distinguen dos tejidos entre sí [Fuente 1].
$$SNR = \frac{\mu_{ROI}}{\sigma_{fondo}}, \;\;\; CNR = \frac{\left|\mu_A - \mu_B\right|}{\sqrt{\sigma_A^2 + \sigma_B^2}}$$
Con $\mu_{ROI}$ la media de señal en el tejido y $\sigma_{fondo}$ la desviación estándar del aire — con un matiz Riciano: el fondo mide una distribución Rayleigh, así que la σ gaussiana subyacente se obtiene corrigiendo por el factor $\sqrt{2/(4-\pi)} \approx 1.53$ cuando se quiere el ruido «verdadero» [Fuente 2]. El CNR responde «¿se ve la cortical contra la médula?» — lo que el diagnóstico realmente necesita.
En la tesis: el SNR condiciona hasta dónde submuestrear con CS (menos promediado es menos SNR) y el CNR cortical/médula acompaña al SSIM en los resultados in vivo. En bajo campo (0.55 T) el presupuesto de SNR es el argumento físico para no exigir factores CS agresivos.""",
        [{"archivo": f"{MT}/bloque-I-procesamiento-metricas/T49-snr.md", "pagina": ""},
         {"archivo": f"{MT}/bloque-G-ruido-modelos/T35-distribucion-rice.md", "pagina": ""}],
    ),
]


def _parrafos(cuerpo: str) -> list[str]:
    return [p.strip() for p in cuerpo.split("\n") if p.strip()]


async def main() -> None:
    secos = "--secos" in sys.argv
    if secos:
        total_imgs, total_cajas = 0, 0
        for titulo, cuerpo, citas in TIPS:
            html = cuerpo_html_de(_parrafos(cuerpo), citas)
            imgs, cajas = html.count("<img"), html.count("Cascadia")
            total_imgs += imgs
            total_cajas += cajas
            marca = "OK " if cajas == 0 else "⚠️ "
            print(f"{marca}{titulo[:58]:60s} imgs={imgs:2d} cajas={cajas}")
        print(f"\nTOTAL: {len(TIPS)} tips | imgs={total_imgs} | cajas fallback={total_cajas}")
        if total_cajas:
            print("HAY CAJAS DE FALLBACK: alguna fórmula no la soporta mathtext — corregir antes de insertar.")
        return

    async with SessionLocal() as db:
        tema = await db.get(Tema, TEMA)
        print(f"tema: {tema.nombre if tema else '??'}")
        hoy = date.today()
        textos = [f"{t}\n{c}" for t, c, _ in TIPS]
        embs = embedir_passages(textos)
        n = 0
        for (titulo, cuerpo, citas), emb in zip(TIPS, embs):
            parrafos = _parrafos(cuerpo)
            db.add(Tip(
                fecha=hoy,
                titulo=titulo,
                cuerpo_texto=cuerpo_texto_de(parrafos, citas),
                cuerpo_html=cuerpo_html_de(parrafos, citas),
                embedding=emb,
                estado="generado",  # en BD, SIN enviar
                tema_id=TEMA,
            ))
            n += 1
        await db.commit()
        total = (await db.execute(select(Tip))).scalars().all()
        print(f"insertados: {n} | tips del tema en BD: {len([t for t in total if t.tema_id == TEMA])}")


asyncio.run(main())
