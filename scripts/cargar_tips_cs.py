#!/usr/bin/env python3
"""Carga masiva de tips de RECONSTRUCCIÓN CON COMPRESSED SENSING en la BD.

Los 50 tips fueron redactados a partir del material real indexado de la tesis
(guiones de defensa, marco teórico, capítulos, anexos y código) — cada uno cita
sus fuentes. Se insertan con estado «generado», SIN enviar correos.

    docker compose exec worker python /mnt/cargar_tips_cs.py   (montar scripts/)
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

# (titulo, cuerpo con [Fuente N], citas) — N según orden de la lista de citas
TIPS: list[tuple[str, str, list[dict]]] = [
    (
        "Compressed Sensing: recuperar más allá de Nyquist",
        "Compressed Sensing (Candès–Tao–Donoho, ~2004–2006) demuestra que una señal esparsa puede recuperarse a partir de muchas menos muestras de las que Nyquist exige, usando optimización no-lineal con un regularizador apropiado [Fuente 1]. Su relevancia clínica en esta tesis es directa: la UTE radial a 0.55 T gana tiempo de adquisición submuestreando radios, y CS reconstruye sin aliasing visible. Las dos condiciones habilitantes son la esparsidad de la imagen en algún dominio (RIP, propiedad de isometría restringida) y la incoherencia del muestreo [Fuente 1]. La imagen ósea cortical es ideal: pieza suave por tramos (gradiente disperso), lo que satisface el prior de Variación Total.",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""}],
    ),
    (
        "y = Ex + n: el problema inverso submuestreado",
        "El modelo de medición es y = Ex + η: los datos y son el operador E aplicado a la imagen x, más ruido η [Fuente 1]. Lo decisivo es la relación de tamaños: se miden M muestras para reconstruir N píxeles con M ≪ N. Entonces E deja de ser invertible y tiene núcleo no trivial: hay vectores no nulos que E envía a cero, de modo que Ex = y tiene infinitas soluciones [Fuente 1]. Todo Compressed Sensing consiste, literalmente, en decidir cuál de esas infinitas imágenes conservar: la regularización aporta el criterio de elección. Con E bien condicionado (cartesiano completo) la solución es trivial x̂ = F⁻¹(y); submuestreado, E^H E diverge en número de condición y la inversa amplifica el ruido [Fuente 2].",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "2"},
         {"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T29-problema-inverso.md", "pagina": ""}],
    ),
    (
        "Nyquist radial: π·Nx radios sin aliasing",
        "Para evitar aliasing en muestreo radial 2D se necesitan al menos π·Nx radios (o π·Nx/2 TRs si se adquieren 2 spokes por TR) [Fuente 1]. La derivación: en el borde del k-space, el espaciado angular debe garantizar que el arco entre radios consecutivos sea ≤ 1/FOV; si se viola, aparecen artefactos en estrella que arruinan la imagen [Fuente 1]. Con Δk = 1/L y k_max = N/(2L), cualquier región con extensión > L produce aliasing si no se filtra antes de digitalizar [Fuente 1]. En la tesis Nx = 500, y el número de radios se define partiendo de este criterio y multiplicando por el factor de submuestreo CS [Fuente 1].",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md", "pagina": ""}],
    ),
    (
        "Incoherencia: el error debe parecer ruido, no anatomía",
        "Submuestrear siempre genera error; no hay forma de evitarlo. Lo que decide si ese error es eliminable no es su magnitud sino su aspecto: si se parece a estructura anatómica, es irrecuperable (ningún algoritmo distingue réplica de anatomía real); si se parece a ruido difuso, la minimización ℓ1 lo separa sin dificultad [Fuente 1]. En cartesiano uniforme, saltarse líneas regulares produce réplicas periódicas (ghosting clásico): una réplica desplazada es indistinguible de anatomía [Fuente 1]. En radial con ángulos aleatorios el aliasing es incoherente — ruido distribuido —, exactamente el régimen donde CS recupera una imagen nítida [Fuente 2].",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "4"},
         {"archivo": "paper-mri-us/diseno_images/03_metodo_cs/fig4_cs_reconstruction.pdf", "pagina": "1"}],
    ),
    (
        "Ángulos aleatorios con semilla fija: incoherencia reproducible",
        "Para el submuestreo CS, los ángulos de adquisición se sortean uniformes en [0, 2π) con semilla fija, de modo que la distribución es incoherente pero la secuencia es reproducible bit a bit [Fuente 1]. En el código, ejecutarSecuenciaRadial expone random_sampling=True, random_seed=42 y cs_undersampling_factor=1.0: si el factor vale 1, el módulo fuerza el barrido secuencial uniforme de Nyquist completo; si es menor, sortea ángulos [Fuente 2]. Con factor unitario los ángulos son secuenciales uniformes φi = Δθ·(i−1) con Δθ = 2π/Nr [Fuente 3]. La reproducibilidad no es un detalle cosmético: permite re-adquirir o simular exactamente el mismo patrón k-space en validación.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/anexos/anexo2.tex", "pagina": "tex"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/codigo/plataforma/api_generacion_ute/src/ejecutarSecuenciaRadial.py", "pagina": "líneas 26-187"},
         {"archivo": "defensa_tesis_doctoral/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf", "pagina": "8"}],
    ),
    (
        "El operador directo E = D^½·NUFFT·C",
        "El operador de medición se factoriza en tres bloques, leídos de derecha a izquierda: E = D^½ · F_NUFFT · C — raíz de la compensación de densidad, por la Fourier no uniforme, por las sensibilidades de bobina [Fuente 1]. Igual de importante es su adjunto E^H = C^H · NUFFT^H · D^½, la retroproyección: el algoritmo alterna E y E^H para evaluar el gradiente del término de datos en cada iteración, una NUFFT directa y una adjunta por iteración [Fuente 1]. La curvatura del problema — el operador E^H E — es lo que gobierna su condicionamiento [Fuente 2]. Las trayectorias k(t) de los radios entran a la reconstrucción precisamente a través de la NUFFT [Fuente 3].",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "6"},
         {"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/scripts/gen_guion.py", "pagina": "líneas 181-330"},
         {"archivo": "defensa_tesis_doctoral/Paper-MRI-US/diseno_images/03_metodo_cs/fig4_cs_reconstruction.pdf", "pagina": "1"}],
    ),
    (
        "Compensación de densidad: Pipe–Menon y el blanqueado D^½",
        "Todos los radios cruzan el centro del espacio k, sobremuestreándolo: la densidad de muestreo radial va como 1/|k| [Fuente 1]. Sin corregir, el centro domina y emborrona la imagen. D son pesos diagonales calculados con el método iterativo de Pipe–Menon (w ← w/(Gw)), que reequilibra el muestreo [Fuente 1]. El factor D(k) pondera la contribución de cada punto para compensar las diferencias de densidad del muestreo radial [Fuente 2]. El uso de su raíz D^½ en E tiene una razón estadística: blanquea el residuo para que el término ℓ2 del funcional sea estadísticamente correcto — homocedástico — y el λ tenga un significado uniforme [Fuente 1].",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "13"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "24"}],
    ),
    (
        "El funcional CS: fidelidad a los datos + Variación Total",
        "La reconstrucción hace dos cosas a la vez: la imagen debe ser consistente con los datos medidos, y debe estar formada por regiones suaves con bordes limpios [Fuente 1]. Formalmente: x̂ = argmin_x (1/2)·‖E·x − y‖²₂ + λ·TV(x), con λ = 10⁻⁴ en esta tesis [Fuente 2]. El primer término es fidelidad a los datos; el segundo, el regularizador λ·TV(x) = λ·‖∇x‖₁, es un prior de esparsidad del gradiente que impone estructura suave por tramos [Fuente 3]. Su efecto: restringir la variedad de soluciones al aliasing incoherente, suprimiendo los streaks sin borrar los bordes corticales [Fuente 3].",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/cap2_cs_trayectoria_p30.png", "pagina": "OCR"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "24"},
         {"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/scripts/gen_guion.py", "pagina": "líneas 181-330"}],
    ),
    (
        "Por qué TV y no ℓ1 sobre wavelets en esta tesis",
        "El marco general de CS permite cualquier dominio de esparsidad Ψ: R(x) = ‖Ψx‖₁ con Ψ wavelet, gradiente, etc. [Fuente 1]. En la tesis se usa Variación Total en lugar de ℓ1 en wavelets [Fuente 1]. TV(x) promueve imágenes suaves por partes preservando bordes — exactamente la estructura del hueso cortical: región homogénea con un borde fino y nítido contra la médula [Fuente 1]. La TV es norma de tipo ℓ1 sobre los gradientes de la imagen: TV(x) = Σ √((Δx_ri)² + (Δy_ri)²), suma de los cambios de vóxel a vóxel penalizando los grandes [Fuente 2]. Los wavelets habrían aportado esparsidad genérica; TV aporta el prior anatómico correcto.",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/eq_tv_p24.png", "pagina": "OCR"}],
    ),
    (
        "Tikhonov vs ℓ1: por qué L2 no basta para CS",
        "Los regularizadores clásicos Tikhonov L2 promueven imágenes «pequeñas» en norma y son diferenciables — optimización suave con solución analítica x̂ = (E^H·E + λI)⁻¹·E^H·y; es lo usado en SENSE [Fuente 1]. Pero L2 no promueve esparsidad: penaliza grandes valores sin favorecer soluciones escasas, y en submuestreo agresivo devuelve imágenes borrosas que reparten el aliasing [Fuente 1]. La esparsidad — R(x) = ‖Ψx‖₁ — promueve representaciones escasas en el dominio Ψ y es la base de Compressed Sensing; al no ser diferenciable, requiere algoritmos proximales como FISTA o ADMM [Fuente 1]. La elección del prior define el régimen: suave y analítico, o esparso e iterativo.",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T29-problema-inverso.md", "pagina": ""}],
    ),
    (
        "ADMM: el solver de la tesis y sus 50 iteraciones",
        "Como la Variación Total es una norma de tipo ℓ1 sobre los gradientes de la imagen y no es diferenciable en el origen, el problema se resuelve con el método de multiplicadores alternos direccionales (ADMM): un solver iterativo que repite pequeñas correcciones, cincuenta veces, hasta que la imagen cumple las dos condiciones — consistencia con los datos y suavidad por tramos — tratando el término no suave por separado [Fuente 1]. ADMM descompone el funcional en subproblemas simples: uno cuadrático en x (resoluble en Fourier), uno de umbralamiento suave en la variable auxiliar del gradiente, y una actualización de multiplicadores — por eso converge de forma robusta en problemas no suaves.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "24"}],
    ),
    (
        "El suavizado de Huber para el gradiente de TV",
        "TV no es suave, y en la práctica numérica se maneja con su subgradiente o con el suavizado de Huber [Fuente 1]. Huber reemplaza la cúspide de la ℓ1 en el origen por un tramo cuadrático: es idéntica a ℓ1 para valores grandes pero diferenciable en cero, lo que habilita métodos de gradiente tipo L-BFGS sin oscilaciones numéricas cerca del mínimo [Fuente 1]. El trade-off: un parámetro de transición que controla dónde empieza el tramo cuadrático — pequeño respecto a la escala de los gradientes de la imagen para no alterar el prior, suficiente para estabilizar el descenso. Es la vía que usa el guion de la defensa para justificar un solver de tipo L-BFGS sobre el funcional TV [Fuente 1].",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/scripts/gen_guion.py", "pagina": "líneas 181-330"}],
    ),
    (
        "Por qué solo 10 iteraciones de L-BFGS: pregunta de defensa",
        "Pregunta anticipada de la defensa: ¿por qué solo diez iteraciones de L-BFGS? Respuesta del guion: porque para este nivel de submuestreo — factor CS en el rango soportado — la mayor parte de la ganancia de calidad ocurre en las primeras iteraciones, y el residual que queda es comparable al ruido del dato [Fuente 1]. Iterar más no reduce error recuperable sino que empieza a ajustar ruido (sobre-ajuste del término de datos). La justificación empírica: las curvas de métrica vs iteración se aplanan alrededor de esa cuenta, y la cola de cómputo extra no compra señal. Es un argumento de parada temprana defendido con el nivel de ruido esperado del dato — la discrepancia entre residuo y ruido como criterio de corte [Fuente 1].",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "11+12"}],
    ),
    (
        "Elegir λ: L-curve, discrepancia y validación",
        "El peso λ del regularizador fija el balance fidelidad-suavidad: λ pequeño (→0) predomina la fidelidad y la imagen queda ruidosa con aliasing; λ correcto da el balance óptimo; λ grande (→∞) predomina TV y la imagen queda sobre-suavizada, perdiendo detalles [Fuente 1]. En la práctica se ajusta empíricamente por tres vías: L-curve — graficar ‖E·x−y‖ vs TV(x) y buscar la «rodilla»; discrepancia — elegir λ tal que el residuo coincida con el ruido esperado; y validación cruzada — probar varios λ y elegir el mejor visualmente [Fuente 1]. En la tesis el valor de producción es λ = 10⁻⁴, calibrado sobre fantoma y validado en las campañas de medición [Fuente 2].",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T32-variacion-total.md", "pagina": ""},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "24"}],
    ),
    (
        "Tabla de aceleración CS: cuánto submuestrear",
        "Con CS, la adquisición típicamente se acelera: 1× = 100% de Nyquist; 2× = 50% de muestras con calidad excelente; 3× = 33% muy buena; 4× = 25% buena; 5× = 20% aceptable con buena regularización; por encima de 6× (<17%) aparecen artefactos visibles [Fuente 1]. El protocolo de la tesis soporta cs_undersampling_factor ∈ [0.2, 1.0], es decir de 5× a 1× [Fuente 1]. La decisión operativa no es «máxima aceleración» sino la mejor relación entre tiempo ganado y fidelidad del biomarcador posterior: el ajuste tri-componente downstream exige SNR suficiente en los ecos tardíos, lo que pone un piso práctico al factor.",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""}],
    ),
    (
        "La reconstrucción como estimador MAP",
        "En qué sentido la reconstrucción es un estimador MAP: el funcional (1/2)·‖E·x−y‖²₂ + λ·TV(x) es exactamente −log verosimilitud (ruido gaussiano) menos −log prior (Laplaciano sobre el gradiente) [Fuente 1]. Minimizarlo equivale a maximizar la probabilidad a posteriori: la imagen más probable dado el dato y el prior [Fuente 1]. Esta lectura probabilística justifica cada término: el modelo de ruido η complejo gaussiano circular de varianza σ² viene del dato crudo; el prior Laplaciano del gradiente codifica la creencia de imágenes suaves por tramos. Por eso la regularización no es un «truco numérico»: es inferencia bayesiana con las hipótesis físicas explícitas.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "13"}],
    ),
    (
        "RIP: la propiedad de isometría restringida",
        "La garantía teórica de CS es la RIP (Restricted Isometry Property): el operador de medición debe preservar aproximadamente las normas de todas las señales esparsas — formaliza que las pocas muestras tomadas contienen la información de la señal esparsa sin distorsión direccional [Fuente 1]. Junto a la incoherencia mutua µ(E) entre el patrón de muestreo y la base de esparsidad, RIP da las cotas de recuperación: con suficiente incoherencia y esparsidad k, la solución ℓ1 coincide con la señal real con alta probabilidad (Candès–Tao) [Fuente 1]. En la tesis no se verifica RIP numéricamente — es intratable — pero la trayectoria radial con ángulos cuasi-aleatorios es el diseño que la teoría recomienda satisfacer en la práctica [Fuente 2].",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""},
         {"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "11+12"}],
    ),
    (
        "Trayectoria radial centro-fuera: cinco razones físicas",
        "La trayectoria radial 2D centro-fuera es estratégicamente óptima para UTE por cinco razones: 1) empieza en k = 0, compatible con TE ultra-corto (la adquisición arranca apenas se enciende el gradiente); 2) no requiere refocusing — ahorra ~1 ms frente al cartesiano; 3) robustez al movimiento (cada radio es independiente y cruza el centro); 4) sobremuestrea el centro del k-space, donde vive el contraste; 5) con ángulos aleatorios entrega de regalo la incoherencia que CS necesita [Fuente 1]. Los radios parten del centro justo mientras la señal de T2* corto todavía vive — esa es la razón de ser de la lectura radial en hueso cortical [Fuente 2].",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md", "pagina": ""},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/ord_cap2_cs_24.png", "pagina": "OCR"}],
    ),
    (
        "Proyectar el gradiente: Gx = G·cosφ, Gy = G·sinφ",
        "La observación económica de la trayectoria radial: no hace falta un gradiente distinto por cada radio; basta repartir el mismo trapezoide de lectura entre los dos ejes según el ángulo, proyectándolo sobre x como Gx = G·cosφ y sobre y como Gy = G·sinφ [Fuente 1]. Cambiar de radio es cambiar dos amplitudes, no rediseñar la secuencia. La ejecución radial recorre los Nr ángulos rotando el gradiente de lectura en las componentes cosφ (eje x) y sinφ (eje y) [Fuente 2]. Esta proyección es la que materializa la trayectoria centro-fuera y la que el módulo ejecutarSecuenciaRadial implementa junto al muestreo en rampa y el spoiling [Fuente 2].",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf", "pagina": "8"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "88"}],
    ),
    (
        "kmax = 2π·G·t_eff y su verificación contra π·Nx/FOV",
        "El k_max (máxima frecuencia espacial adquirida) se calcula a partir del gradiente de lectura como k_max = 2π·G·t_eff, donde t_eff es el tiempo efectivo: la meseta más la mitad de las rampas [Fuente 1]. Usar la amplitud máxima G_max = 18 mT/m maximiza el k_max en el menor tiempo [Fuente 1]. Ese valor se contrasta con el límite teórico que impone la geometría: k_max_teórico = π/Δx = π·Nx/FOV [Fuente 1]. Si el k_max calculado excede el teórico, se avisa y se reajusta la amplitud — sobrepasarlo significaría resolución inconsistente con el FOV; quedarse corto, perder resolución. Así la resolución queda acotada por diseño, no por accidente.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf", "pagina": "18"}],
    ),
    (
        "El puente secuencia→reconstrucción: del .seq al k-space",
        "El puente entre la secuencia y la reconstrucción parte de los datos crudos del espacio k normalizados (escala y fase) [Fuente 1]: capítulo 9 compromete reconstrucción por compressed sensing sobre toolboxes de código abierto, partiendo de datos del espacio k normalizados [Fuente 1]. En el paper, los datos k-space crudos se reconstruyen con el framework TensorFlow-MRI mediante Compressed Sensing iterativo [Fuente 2]. La normalización previa no es menor: alinear escala/offset del dato crudo evita que el término de fidelidad ℓ2 tenga pesos heterogéneos que sesguen el solver — complementa el blanqueado D^½ del operador E.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo9.tex", "pagina": "tex"},
         {"archivo": "defensa_tesis_doctoral/Paper-MRI-US/Others/pag8_final.png", "pagina": "OCR"}],
    ),
    (
        "Regridding: el camino clásico no cartesiano",
        "El proceso clásico de reconstrucción para secuencias UTE con muestreo radial consta de tres etapas: (a) adquisición en k-space radial con trayectorias que parten del centro, capturando señales de T2 corto; (b) regridding, donde los datos no cartesianos se interpolan a una grilla cartesiana uniforme mediante kernels de interpolación; (c) reconstrucción final mediante la transformada inversa de Fourier 2D [Fuente 1]. Es la alternativa directa a la NUFFT del pipeline CS. La diferencia operativa: regridding + IFFT es una sola pasada no iterativa y barata, pero no incorpora regularización — el aliasing del submuestreo pasa intacto; por eso en la tesis se reservó para referencia y el camino de producción fue CS iterativo con TV.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/docs/template-parcial-final-2026-09-19.pdf", "pagina": "31"}],
    ),
    (
        "SENSE y sus límites frente al radial aleatorio",
        "SENSE resuelve el aliasing cartesiano desenredando píxeles plegados con los mapas de sensibilidad: x̂(r_n) = (C^H·C + λI)⁻¹·C^H·y_aliased(r), con λ pequeño para no amplificar ruido [Fuente 1]. En TensorFlow-MRI: tfmri.recon.sense(kspace, sensitivities, reduction_factor, regularizer=L2Norm) [Fuente 1]. Sus limitaciones lo excluyen del diseño de esta tesis: solo funciona con submuestreo cartesiano regular de factor entero R; requiere sensibilidades C_i bien estimadas (si no, artefactos en bordes); y sufre el g-factor — amplificación de ruido donde las antenas son redundantes [Fuente 1]. El radial con ángulos aleatorios no produce plegamiento desenredable por SENSE: exige el enfoque CS.",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T33-metodos-reconstruccion.md", "pagina": ""}],
    ),
    (
        "IR-UTE con CS: supresión de grasa acelerada",
        "En respuesta a los artefactos de chemical shift observados en estudios previos, se implementó el 14 de agosto de 2025 un protocolo experimental de supresión de grasa basado en Inversion Recovery UTE (IR-UTE) combinado con aceleración por Compressed Sensing [Fuente 1]. El objetivo: evaluar la viabilidad de supresión selectiva de la señal grasa para mejorar la especificidad del contraste en hueso cortical [Fuente 1]. El patrón de muestreo k-space para IR-UTE con CS muestra la distribución radial acelerada con factor de submuestreo del 60% [Fuente 1]. Es CS aplicado a un problema clínico concreto: ganar tiempo en el tren de inversión sin sacrificar la definición del borde cortical que el ajuste posterior necesita.",
        [{"archivo": "defensa_tesis_doctoral/Paper-MRI-US/Others/capitulo7/capitulo7c.tex", "pagina": "tex"}],
    ),
    (
        "El argumental completo de la defensa CS (para memorizar)",
        "La cadena argumental completa del cierre de la presentación de CS: la adquisición UTE radial con ángulos cuasi-aleatorios genera un aliasing incoherente que satisface la RIP; el operador directo E modela con precisión la formación de la señal combinando sensibilidades, NUFFT y compensación de densidad; el problema inverso mal condicionado se plantea como estimador MAP que busca la imagen consistente con los datos y esparsa en el gradiente; la Variación Total limpia el ruido sin difuminar los bordes gracias a la penalización ℓ1; y las métricas objetivas confirman, con significancia por pares, que CS gana [Fuente 1]. Cinco eslabones — cada uno defendible por separado, y esta es la versión un párrafo para el cierre oral.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "11+12"}],
    ),
    (
        "CS en el mapa conceptual: un eslabón de la cadena",
        "En el mapa conceptual de la tesis, la reconstrucción CS es un eslabón intermedio de una cadena completa: de la fractura por fragilidad y el límite de la DXA nace la calidad ósea, con la tibia media como blanco anatómico; los dos pools de agua conectan la estructura del hueso con la medición; la cadena de la resonancia — secuencia UTE a 0.55 T, reconstrucción por compressed sensing y modelo de tres compartimentos — entrega los biomarcadores de porosidad, mientras el ultrasonido BDAT recorre su ruta independiente; ambas rutas convergen en la concordancia emparejada por sitio [Fuente 1]. CS no es un fin: es lo que hace viable clínicamente la cadena (tiempo de adquisición razonable) sin romper la cuantificación posterior.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo2.tex", "pagina": "tex"}],
    ),
    (
        "TE = 30 µs: la restricción que condiciona todo el pipeline",
        "La secuencia UTE radial 2D se diseñó en torno a una sola restricción: capturar la señal cortical antes de que decaiga. Dos elementos la materializan: una excitación de medio pulso truncado, remapeada sobre su gradiente de corte (VERSE) de modo que la excitación termina en k_z = 0 sin fase de corte por refocalizar, y una lectura radial del centro hacia afuera muestreada durante la rampa del gradiente, que abre el ADC inmediatamente después del fin de la RF y define el eco más corto en TE = 30 µs [Fuente 1]. El TE mínimo se verifica desde el fin del pulso RF hasta la primera muestra del ADC [Fuente 2]. Esa exigencia temporal es la que fija radial + ramp sampling, y de ahí el problema no cartesiano que CS resuelve.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo4.tex", "pagina": "tex"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/anexos/anexo2.tex", "pagina": "tex"}],
    ),
    (
        "Spoiling coherente con el radio: 20% + RF 117°",
        "Cada lectura radial cierra con un spoiler de gradiente en el plano de lectura, rotado en la misma dirección del radio, con amplitud del 20% del máximo del sistema y duración acotada por el tiempo disponible del TR; y entre disparos aplica spoiling de RF con el incremento clásico de 117° — la progresión aritmética de fase — asignada a la fase del pulso de RF y del ADC para que la magnetización residual no se re-adicione coherente entre adquisiciones [Fuente 1]. Sin spoiling, la señal residual de TRs anteriores contaminaría los radios con historia previa y el modelo lineal y = E·x dejaría de describir el dato — la fidelidad del término ‖E·x−y‖ dependería de un error sistemático, no de ruido.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "88"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/anexo1b_p82.png", "pagina": "OCR"}],
    ),
    (
        "Cuantización al raster del ADC antes de reconstruir",
        "Antes de la reconstrucción, todos los tiempos de la secuencia se cuantizan al raster del ADC: t_k^(q) = round(t_k/Δt_ADC)·Δt_ADC, con corrección sobre los ticks para asegurar t_k^(q) > t_(k−1)^(q) [Fuente 1]. Si la ventana de ADC requerida difiere de T_r + T_f, se aplica un factor de escala s = T_ADC/(T_r+T_f) a todos los tiempos para igualar la duración efectiva [Fuente 1]. El dwell de captura se fija uniforme en Δt_ADC y el número de muestras N_cap lo determina el último tick válido: T_ADC = N_cap·Δt_ADC [Fuente 1]. Esta disciplina temporal garantiza que la trayectoria k(t) que la NUFFT usa en E coincida con la realmente ejecutada por el escáner.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo9.tex", "pagina": "tex"}],
    ),
    (
        "Nx = 500: el sobremuestreo radial dentro del radio",
        "En la tesis se usa Nx = 500 muestras por radio, número que incorpora el sobremuestreo radial característico de la trayectoria [Fuente 1]. El conteo de radios parte del criterio de Nyquist radial Nr·Nx/2 (dos radios por TR) y se multiplica por el factor de submuestreo de compressed sensing, que define la aceleración [Fuente 2]. El sobremuestreo a lo largo del radio no es redundancia inocente: da margen para la corrección de densidad, mejora el condicionamiento del operador E cerca del centro y soporta la interpolación NUFFT con menor error de kernel. Pregunta de comité: ¿por qué no menos muestras por radio? Porque la resolución efectiva la fija k_max, y muestrear más denso el radio baja el error de gridding/NUFFT sin tocar el FOV.",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md", "pagina": ""},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/anexos/anexo2.tex", "pagina": "tex"}],
    ),
    (
        "Radios por TR: el par de medios pulsos",
        "La ejecución radial alterna dos excitaciones por TR con la polaridad del gradiente de corte invertida — el par de medios pulsos que completa el perfil de corte — y recorre los Nr ángulos de lectura [Fuente 1]. De ahí que el criterio de Nyquist radial se exprese en TRs como π·Nx/2: dos spokes por TR [Fuente 2]. El medio pulso con polaridad alternada resuelve el dilema de la excitación plana con TE ultracorto: un pulso 2D selectivo corto es físicamente imposible, dos medios pulsos simétricos suman el perfil y cada uno deja el TE en 30 µs. La contraparte para reconstrucción: ambos halves deben sumarse coherente en k-space, lo que exige fidelidad de fase — de nuevo, el modelo E debe describir exactamente lo ejecutado.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "88"},
         {"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md", "pagina": ""}],
    ),
    (
        "Métricas objetivas con significancia por pares",
        "El cierre del argumental CS se apoya en métricas objetivas que confirman, con significancia por pares, que CS gana frente a la alternativa no regularizada [Fuente 1]. La comparación por pares es la elección estadística correcta cuando cada sitio anatómico se mide con ambos métodos: el propio sitio es su control, y la prueba pareada (diferencias por sujeto/sitio) elimina la variabilidad inter-sujeto que ahogaría el efecto. El andamiaje métrico de la tesis incluye SSIM (Wang 2004) para similitud estructural y SNR según Dietrich 2007 [Fuente 2]. Para el comité: la afirmación «CS gana» no es visual — es una diferencia pareada significativa sobre métricas definidas a priori.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "11+12"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/fusion-log.md", "pagina": ""}],
    ),
    (
        "La trayectoria real: cientos de radios densos en el centro",
        "La figura 2.8 de la tesis muestra la trayectoria real en el espacio k de una adquisición radial del protocolo: cientos de radios con ángulos aleatorios, densos en el centro, coloreados por tiempo de muestreo [Fuente 1]. El submuestreo con ángulos aleatorios produce aliasing incoherente, el régimen del compressed sensing [Fuente 1]. Dos detalles defendibles de esa figura: la densidad central natural de lo radial (que D compensa, no que haya que evitar) y la coloración por tiempo — visualiza que todos los radios arrancan en t≈TE del centro hacia afuera, coherente con la lectura en rampa centro-fuera que captura la señal T2* corta antes de su decaimiento [Fuente 1].",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/cap2_cs_trayectoria_p30.png", "pagina": "OCR"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/main.pdf", "pagina": "22+23"}],
    ),
    (
        "Corrección de densidad visualizada: antes y después de D(k)",
        "La corrección de densidad en la adquisición radial se visualiza en dos paneles: a la izquierda, la distribución original de los puntos de muestreo, con mayor densidad en el centro del espacio k; a la derecha, el efecto del factor de corrección D(k), que pondera la contribución de cada punto para compensar las diferencias de densidad del muestreo radial [Fuente 1]. Sin esta corrección, la sobre-representación central pesa desproporcionadamente en cualquier suma directa (retroproyección simple) y emborrona la imagen con un sesgo de bajas frecuencias [Fuente 2]. Es la contraparte visual de la pregunta P6 de la defensa: para qué sirve D — y por qué su raíz D^½ entra en E para blanquear el residuo ℓ2.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/ord_cap2_cs_25.png", "pagina": "OCR"},
         {"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "13"}],
    ),
    (
        "El condicionamiento de E^H·E gobierna la convergencia",
        "Cada evaluación del gradiente del término de datos cuesta una NUFFT directa y una adjunta por iteración; la curvatura del problema — el operador E^H·E — es lo que gobierna su condicionamiento [Fuente 1]. Interpretación para el comité: el número de condición de E^H·E determina cuántas iteraciones necesita un método de gradiente (o cuasi-Newton como L-BFGS) para converger. El submuestreo CS agrava el condicionamiento — menos filas de E, más direcciones nulas — y es exactamente donde el regularizador TV actúa como curvatura artificial en las direcciones faltantes: curva el paisaje en el núcleo de E y hace único el mínimo. Regularizar y acelerar la convergencia son aquí la misma cosa.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/scripts/gen_guion.py", "pagina": "líneas 181-330"}],
    ),
    (
        "TV limpia streaks sin borrar el borde cortical",
        "El efecto concreto del regularizador TV sobre la imagen reconstruida: restringe la variedad de soluciones al aliasing incoherente, suprimiendo los streaks sin borrar los bordes [Fuente 1]. El mecanismo fino: TV penaliza la norma ℓ1 del gradiente — variación total a lo largo de cada dirección, con las diferencias finitas Δx_ri y Δy_ri — de modo que un borde nítido (un solo salto grande) es barato, mientras que el ruido y los streaks (muchos saltos pequeños distribuidos) son caros [Fuente 2]. Esa asimetría es la que preserva el borde cortical — un único frente de transición — y elimina la textura incoherente del submuestreo. Es la respuesta a «¿por qué no difumina?» porque difuminar costaría muchos gradientes medianos.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/scripts/gen_guion.py", "pagina": "líneas 181-330"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/eq_tv_p24.png", "pagina": "OCR"}],
    ),
    (
        "Ruido gaussiano circular: la hipótesis del término ℓ2",
        "El modelo de ruido de la reconstrucción es η complejo gaussiano circular de varianza σ² [Fuente 1]. Esta hipótesis justifica matemáticamente el término de fidelidad (1/2)·‖E·x−y‖²₂: el negativo del logaritmo de una verosimilitud gaussiana es exactamente una norma ℓ2 al cuadrado — de ahí que el funcional sea un estimador MAP [Fuente 1]. La palabra «circular» importa: partes real e imaginaria independientes con igual varianza, lo que hace isotrópico el ruido en el plano complejo. Nota de coherencia con el resto de la tesis: este modelo es válido para el dato crudo k-space; las imágenes de magnitud ya reconstruidas siguen ruido Rician (anexo 4), una distinción que el comité suele sondear.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "6"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/anexos/anexo4.tex", "pagina": "tex"}],
    ),
    (
        "Pypulseq y KomaMRI: la secuencia validada antes del escáner",
        "La secuencia UTE 2D se implementó con el framework Pypulseq para el resonador de 0.55 T, y hoy se genera desde el servicio de secuencias de la plataforma (módulo api_generacion_ute/src): configuración del sistema y del ADC, gradientes de lectura y spoiler, ejecución radial, guardado y un banco de validación (validateUTEImplementation, testUTEValidation, análisis de trayectoria y de spoiling); los parámetros viven centralizados con sus rangos admitidos (parametros.py), de modo que un mismo núcleo científico sirve a la simulación y al escáner [Fuente 1]. La secuencia generada se verifica por simulación — sincronización de eventos RF, gradientes y ADC en KomaMRI — antes de su ejecución en el resonador [Fuente 2]. Para CS esto es crítico: E debe modelar la trayectoria ejecutada, y la ejecución se garantiza in silico primero.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/narracion/texto/anexo2.txt", "pagina": ""},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/anexo1_p82.png", "pagina": "OCR"}],
    ),
    (
        "El problema inverso mal condicionado: por qué regularizar",
        "La reconstrucción en IRM es un problema inverso lineal: dados los datos y en k-space, recuperar la imagen x que satisface y = E·x + n [Fuente 1]. Si E es bien condicionado (cartesiano completo), la solución es trivial: x̂ = E⁻¹·y = F⁻¹(y). Si E está submuestreado (CS radial), el problema es mal condicionado: E^H·E tiene número de condición divergente y aplicar la inversa amplifica el ruido [Fuente 1]. La salida es regularizar añadiendo un término de prior: x̂ = argmin ‖E·x−y‖²₂ + λ·R(x), con R = Tikhonov L2 (suave) o ℓ1/TV (esparso) [Fuente 1]. La regularización no es opcional en CS: sin ella, el submuestreo hace indeseable la solución de mínimos cuadrados puros.",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T29-problema-inverso.md", "pagina": ""}],
    ),
    (
        "Alternativas de reconstrucción: el anexo 13 como mapa",
        "El panorama de alternativas clásicas de reconstrucción no cartesiana se resume en el anexo 13 de la tesis: el anexo 3 presenta las principales técnicas y sus formulaciones generales, y la sección final desarrolla con detalle las reconstrucciones que la plataforma dockerizada ejecuta en producción [Fuente 1]. El precio de la trayectoria radial: los datos ya no viven en una grilla cartesiana y la transformada de Fourier inversa ya no se aplica de forma directa [Fuente 2]. De ese mapa — regridding, SENSE, GRAPPA, RSS, CS — la elección de la tesis fue una sola: compressed sensing, desarrollado completo en el capítulo 2 [Fuente 2]. Justificación de la exclusividad: es el único que incorpora el prior de esparsidad explotando además la incoherencia natural del radial aleatorio.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/anexos/anexo3.tex", "pagina": "tex"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/ord_cap2_cs_24.png", "pagina": "OCR"}],
    ),
    (
        "TensorFlow-MRI: CS iterativo en producción",
        "La reconstrucción avanzada implementada incorpora algoritmos especializados disponibles en la biblioteca TensorFlow-MRI [Fuente 1]. En el paper: los datos k-space crudos se reconstruyeron con el framework TensorFlow-MRI mediante Compressed Sensing iterativo, partiendo del k-space normalizado [Fuente 2]. La elección de framework es defendible en términos de reproducibilidad y GPU: TF-MRI expone la NUFFT, operadores de sensibilidad y optimizadores proximales como bloques componibles, y el mismo pipeline corre en simulación y en la campaña in vivo. El módulo api_reconstruccion_radial de la plataforma ejecuta el pipeline radial (CS) junto al cartesiano y el libre [Fuente 3].",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/docs/template-parcial-final-2026-09-19.pdf", "pagina": "31"},
         {"archivo": "defensa_tesis_doctoral/Paper-MRI-US/Others/pag8_final.png", "pagina": "OCR"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/codigo/plataforma/README.md", "pagina": ""}],
    ),
    (
        "Validación integral de la secuencia antes de confiar en E",
        "La implementación incluye un sistema completo de validación que verifica múltiples aspectos críticos de la secuencia UTE, importado de validateUTEImplementation: runCompleteUTEValidation, printValidationSummary y generateOptimizationRecommendations, con parámetros reales (samplingTimes, rampSamples…) [Fuente 1]. Los chequeos del capítulo 5: verificar la correcta ejecución temporal de los eventos (timing de RF, gradientes, ADC); evaluar la fidelidad de la trayectoria en el espacio-k generada; estimar la respuesta de la señal para diferentes T1, T2* y densidad protónica en fantomas numéricos; y realizar ajustes iterativos de parámetros antes de la implementación experimental [Fuente 2]. El argumento para CS: la confianza del término ‖E·x−y‖ descansa en que la E del software coincide con la secuencia física — la validación es lo que compra esa igualdad.",
        [{"archivo": "paper-mri-us/Others/anexo1.tex", "pagina": "tex"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo5.tex", "pagina": "tex"}],
    ),
    (
        "Muestreo en rampa: la lectura que abre con el gradiente",
        "La lectura radial del centro hacia afuera se muestrea durante la rampa del gradiente: el ADC abre inmediatamente después del fin de la RF, definiendo el eco más corto TE = 30 µs [Fuente 1]. El abstract lo resume: excitación de medio pulso con remapeo VERSE y momento de gradiente nulo, ramp sampling [Fuente 2]. Para la reconstrucción, el muestreo en rampa tiene una consecuencia directa: la trayectoria k(t) no es lineal en t durante la subida del gradiente — los primeros puntos avanzan más lento — y la NUFFT debe recibir los tiempos exactos k(t) cuantizados al raster del ADC, no un espaciado uniforme supuesto. Ignorar la rampa en E desalinearía sistemáticamente el centro del k-space, justo donde vive el contraste.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo4.tex", "pagina": "tex"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/abstract_p3.png", "pagina": "OCR"}],
    ),
    (
        "Doce ecos y el tren multi-eco después de CS",
        "El tren multi-eco barre doce tiempos de eco entre 0.03 y 25 ms, evitando deliberadamente ciertos ecos conflictivos [Fuente 1]. La cadena completa — secuencia UTE 0.55 T, reconstrucción CS, modelo de tres compartimentos — entrega los biomarcadores de porosidad [Fuente 2]. La implicación para CS: cada uno de los 12 ecos se reconstruye y el ajuste tri-exponencial posterior opera sobre esa serie. La coherencia entre ecos importa más que el brillo individual: el regularizador y λ son los mismos para todo el tren, de modo que el sesgo de suavizado — si lo hay — es sistemático e igual en todos los TE, y el ajuste de T2* lo absorbe como efecto común en lugar de introducir pseudo-dependencias temporales.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo4.tex", "pagina": "tex"},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo2.tex", "pagina": "tex"}],
    ),
    (
        "UTE-hmrGC: separación agua-grasa aguas abajo de CS",
        "La implementación UTE-hmrGC de separación agua–grasa opera sobre adquisiciones UTE multi-eco, generando water-only/fat-only junto a mapas de PDFF, R2* y f(B0); se construye sobre la librería fieldmapping-hmrGC (hierarchical multi-resolution Graph Cut) y corre como etapa del servicio de mapas T2 de la plataforma (módulo api_mapas_t2, servicio wf_separation_service) [Fuente 1]. Su relación con la reconstrucción: recibe las imágenes multi-eco ya reconstruidas por CS; la calidad del mapa B0 y del PDFF hereda directamente la fidelidad del k-space recuperado. Un submuestreo mal regularizado no solo se ve: sesga la separación espectral. De nuevo la tesis de diseño: cada etapa aguas abajo exige disciplina en la anterior.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/anexos/anexo5.tex", "pagina": "tex"}],
    ),
    (
        "El guion como fuente: cómo se defiende el CS oralmente",
        "El guion de la presentación especial de compressed sensing estructura la defensa en diapositivas con preguntas anticipadas: el problema (menos datos que Nyquist), la condición de esparsidad, la condición de incoherencia, el operador E, el problema regularizado, y el cierre con la cadena argumental y las preguntas P6 (compensación de densidad) y P7 (estimador MAP) resueltas de memoria [Fuente 1]. El propio guion se genera con gen_guion.py, cuyo código fuente contiene las formulaciones en LaTeX que luego se proyectan [Fuente 2]. Tip de método: estudiar CS en el orden del guion — problema, condiciones, operador, funcional, solver, resultados — es exactamente el orden en que el comité encadena sus preguntas.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "2"},
         {"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/scripts/gen_guion.py", "pagina": "líneas 91-180"}],
    ),
    (
        "Submuestrear el k-space vs acelerar por paralelismo",
        "Distinción que el comité sondea: hay dos familias de aceleración en RM. La paralela (SENSE, GRAPPA) explota múltiples bobinas como codificación espacial simultánea — exige factor entero, cartesiano regular y paga con g-factor de ruido [Fuente 1]. La de compressed sensing submuestrea el k-space mismo — en esta tesis, menos radios con ángulos aleatorios — y paga con trabajo computacional en la reconstrucción, no con hardware [Fuente 2]. Son complementarias en la literatura, pero la tesis usa solo CS: el radial con ángulos aleatorios no produce el plegamiento regular que SENSE desenreda, y a 0.55 T con bobina flexible el SNR no regala margen para amplificaciones de g-factor [Fuente 1].",
        [{"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T33-metodos-reconstruccion.md", "pagina": ""},
         {"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""}],
    ),
    (
        "Anatomía que justifica el prior: por qué TV encaja en cortical",
        "El blanco anatómico es la tibia media y el hueso cortical: una capa relativamente delgada de tejido con dos reservorios de agua — bound water unida a la matriz de colágeno y pore water en poros — cuya partición refleja porosidad y espesor cortical, medibles sin radiación ionizante [Fuente 1]. La estructura es la que hace TV el prior correcto para CS: la cortical es una región homogénea limitada por bordes nítidos (periostio, endostio) contra señal de fondo distinta — suave por tramos en el sentido exacto de la Variación Total [Fuente 2]. Un prior wavelet genérico trataría el borde cortical como cualquier otra textura; TV lo protege porque el borde es un frente de gradiente único y barato bajo ℓ1.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/docs/qa/abstract_p3.png", "pagina": "OCR"},
         {"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T32-variacion-total.md", "pagina": ""}],
    ),
    (
        "Del k-space a biomarcadores: por qué CS sostiene la cuantificación",
        "La cadena de la resonancia — secuencia UTE a 0.55 T, reconstrucción por CS, modelo de tres compartimentos — entrega los biomarcadores de porosidad [Fuente 1]. El riesgo metodológico que CS debe acotar: el ajuste tri-componente S(t) = S_bw·e^(−t/T2,bw*) + S_pw·e^(−t/T2,pw*) + S_bm·e^(−t/T2,bm*) es sensible al nivel de ruido y a sesgos espaciales de la imagen [Fuente 2]. Un regularizador demasiado fuerte reduce amplitudes relativas (sesgo en las fracciones f); uno demasiado débil deja aliasing que correlaciona los residuos del ajuste. Por eso λ = 10⁻⁴ se calibró con fantoma y se validó con las métricas pareadas: el objetivo de la reconstrucción no es una linda imagen, es un biomarcador confiable aguas abajo.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/capitulos/capitulo2.tex", "pagina": "tex"},
         {"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-G-ruido-modelos/T37-modelo-monoexponencial.md", "pagina": ""}],
    ),
    (
        "Código citable: dónde vive la reconstrucción en la plataforma",
        "El módulo api_reconstruccion_radial/ contiene el pipeline de reconstrucción radial (CS) junto al cartesiano y al libre; el servicio collage_ute_service.py genera el collage UTE canónico desde la plataforma [Fuente 1]. El snapshot de código está respaldado versionado junto a la tesis en codigo/plataforma, tomado del repo PROYECTO-INFORMATICO-MRI-US-DOCKERIZADO (rama mri-us-bdat-test) [Fuente 1]. Y la semilla CS vive aguas arriba: ejecutarSecuenciaRadial.py expone random_sampling, random_seed y cs_undersampling_factor como parámetros de primera clase [Fuente 2]. Para la defensa: saber citar archivo y función — reconstrucción en api_reconstruccion_radial, muestreo CS en api_generacion_ute/src — demuestra que el flujo es reproducible de punta a punta.",
        [{"archivo": "MRI-UTE PROYECTO DE TESIS/codigo/plataforma/README.md", "pagina": ""},
         {"archivo": "MRI-UTE PROYECTO DE TESIS/codigo/plataforma/api_generacion_ute/src/ejecutarSecuenciaRadial.py", "pagina": "líneas 26-187"}],
    ),
    (
        "Pregunta capciosa: ¿CS inventa información?",
        "No. CS no crea información ausente: elige, entre las infinitas imágenes consistentes con el dato submuestreado, la más plausible bajo un prior explícito [Fuente 1]. Cuando Ex = y tiene núcleo no trivial, toda solución del núcleo es indistinguible para el dato; el regularizador TV rompe el empate con criterio anatómico, no con información nueva [Fuente 1]. La garantía formal (RIP/incoherencia) acota cuándo esa elección coincide con la señal real [Fuente 2]. La respuesta honesta al comité: CS intercambia supuesto — esparsidad del gradiente — por muestras; si el supuesto falla (texto fino, trabéculas múltiples), el error aparece como pérdida de detalle, no como estructura falsa, y las métricas pareadas cuantifican ese costo.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "2"},
         {"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md", "pagina": ""}],
    ),
    (
        "Cierre de defensa: los cinco eslabones en una frase",
        "Síntesis memorable para el cierre oral, palabra por palabra del guion: la adquisición UTE radial con ángulos cuasi-aleatorios genera un aliasing incoherente que satisface la RIP; el operador directo E modela con precisión la formación de la señal combinando sensibilidades, NUFFT y compensación de densidad; el problema inverso mal condicionado se plantea como estimador MAP que busca la imagen consistente con los datos y esparsa en el gradiente; la Variación Total limpia el ruido sin difuminar los bordes gracias a la penalización ℓ1; y las métricas objetivas confirman, con significancia por pares, que CS gana [Fuente 1]. Si el comité pide una sola frase: «submuestreo incoherente + prior correcto = aceleración sin perder el biomarcador».",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "11+12"}],
    ),
    (
        "Nyquist cuantificado: cuántos radios para 256×256",
        "Del guion de defensa: ¿cuántos datos exigiría Nyquist? Para una matriz de 256×256, un muestreo radial completo necesita del orden de π·N radios — para N = 256, del orden de 800 radios [Fuente 1]. Con el criterio π·Nx de la tesis y Nx = 500, el conteo completo parte de ~785 TRs (π·500/2 con dos spokes por TR) y el factor CS lo multiplica: al 20% (5×) quedan ~157 radios sorteados [Fuente 2]. La escala importa para el argumento clínico: la diferencia entre ~785 y ~157 adquisiciones es la diferencia entre un protocolo inviable y uno utilizable en la campaña in vivo — la viabilidad temporal de la tesis la sostiene CS.",
        [{"archivo": "defensa_tesis_doctoral/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf", "pagina": "2"},
         {"archivo": "defensa_tesis_doctoral/marco-teorico/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md", "pagina": ""}],
    ),
]


async def main() -> None:
    async with SessionLocal() as db:
        tema = await db.get(Tema, TEMA)
        print(f"tema: {tema.nombre if tema else '??'}")
        hoy = date.today()
        textos = [f"{t}\n{c}" for t, c, _ in TIPS]
        embs = embedir_passages(textos)
        n = 0
        for (titulo, cuerpo, citas), emb in zip(TIPS, embs):
            parrafos = [p.strip() for p in cuerpo.split("\n") if p.strip()]
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
