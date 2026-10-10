#!/usr/bin/env python3
"""Genera 20 decks × 10 tarjetas de nivel doctoral."""
import asyncio, sys
from datetime import date
sys.path.insert(0, "/app")
from estudio.db import SessionLocal
from estudio.models import Deck, Flashcard, Tema

TEMA = "933ee140ea124c5a8aff1afb06c5d257"
CT = "MRI-UTE PROYECTO DE TESIS"
DF = "defensa_tesis_doctoral"
PM = "paper-mri-us"

DECKS = [
("Half Pulse y Excitacion UTE", [
 ("Que es un half pulse", "Cada mitad de un par de pulsos con gradiente invertido que suman el perfil planar", CT+"/narracion/texto/anexo1.txt"),
 ("Por que DOS half pulses", "Cada half deja fase residual; dos con polaridad invertida completan el perfil", CT+"/narracion/texto/anexo1.txt"),
 ("Que es VERSE", "Variable-Rate Selective Excitation: remapea RF sobre la rampa del gradiente", CT+"/codigo/plataforma/api_generacion_ute/src/crearPulsoSeleccionCorte.py"),
 ("Parametros del pulso", "Flip 30, TBW=2, dur 0.5ms, corte 10mm, Gz=BW/(gamma*dz)", DF+"/presentacion-especiales/secuencia-ute/scripts/gen_guion.py"),
 ("Por que kz=0 al terminar", "Sin fase residual de corte: ADC abre inmediatamente, TE=30us", CT+"/narracion/texto/anexo1.txt"),
 ("Que es spoiling RF 117", "Progresion aritmetica de fase que destruye coherencia entre TRs", CT+"/main.pdf"),
 ("Que es dummy scan", "Excitacion sin datos: estabiliza estado estacionario", CT+"/narracion/texto/anexo2.txt"),
 ("Que es SAR", "Calentamiento por RF, limitado en ventanas de 10s y 6min", DF+"/presentacion-especiales/secuencia-ute/scripts/gen_guion.py"),
 ("Gmax=18mT/m a 0.55T", "Amplitud maxima del gradiente, maximiza kmax en menor tiempo", DF+"/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf"),
 ("Momento gradiente nulo", "Area de gradiente produce kz=0: sin momento residual", CT+"/docs/qa/abstract_p3.png"),
]),
("Trayectoria Radial y k-space", [
 ("Por que radial para UTE", "k=0 al inicio (TE corto), sin refocusing, robusta movimiento, sobremuestrea centro, angulos aleatorios=CS", DF+"/marco-teorico/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("Proyeccion gradiente phi", "Gx=G*cos(phi), Gy=G*sin(phi): cambiar radio=cambiar dos amplitudes", DF+"/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf"),
 ("Que es ramp sampling", "ADC abre mientras sube el gradiente: k(t) no lineal, NUFFT recibe tiempos exactos", CT+"/capitulos/capitulo4.tex"),
 ("Nyquist radial", "pi*Nx radios para sin aliasing 2D radial", DF+"/marco-teorico/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md"),
 ("Nx=500", "Incorpora sobremuestreo radial. Nyquist pi*500=1571 (~785 TRs) * factor CS", DF+"/marco-teorico/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md"),
 ("kmax=2pi*G*t_eff", "Meseta+mitad rampas. Verificado contra pi*Nx/FOV", DF+"/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf"),
 ("Cuantizacion raster ADC", "t_k_q=round(t_k/dt_ADC)*dt_ADC: NUFFT usa trayectoria exacta", CT+"/capitulos/capitulo9.tex"),
 ("UTE vs ZTE", "UTE: pulso truncado+radial. ZTE: gradiente encendido (TE~0) pero menos flexible CS", CT+"/narracion/texto/cap3.txt"),
 ("Ventaja radial vs cartesiano", "Robusta al movimiento, sobremuestreo central, incoherencia CS", DF+"/marco-teorico/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("Visualizacion trayectoria", "Cientos de radios aleatorios densos al centro, coloreados por tiempo", CT+"/docs/qa/cap2_cs_trayectoria_p30.png"),
]),
("CS: Fundamentos", [
 ("Dos condiciones CS", "1) Esparsidad 2) Incoherencia: aliasing como ruido", DF+"/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md"),
 ("y=Ex+n", "M<<N: nucleo no trivial, infinitas soluciones, CS elige", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Funcional CS", "argmin (1/2)||Ex-y||^2+lambda*TV(x), lambda=1e-4", CT+"/main.pdf"),
 ("Variacion Total", "TV=suma||grad x||_1: borde barato, ruido caro, preserva cortical", DF+"/marco-teorico/bloque-F-reconstruccion/T29-problema-inverso.md"),
 ("TV vs wavelets", "TV promueve suavidad por partes: estructura cortical. Wavelet=generico", DF+"/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md"),
 ("RIP", "E preserva normas de senales esparsas: informacion sin distorsion", DF+"/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md"),
 ("Tabla aceleracion", "2x=50% excelente, 5x=20% aceptable, >6x artefactos", DF+"/marco-teorico/bloque-F-reconstruccion/T31-compressed-sensing.md"),
 ("Incoherencia", "Radial aleatorio=incoherente. Cartesiano uniforme=ghosting irrecuperable", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("CS como MAP", "Funcional=-logL-logp: minimizar=maximizar P(x|y)", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("CS vs SENSE", "CS submuestrea k-space (paga computo). SENSE usa bobinas (paga g-factor)", DF+"/marco-teorico/bloque-F-reconstruccion/T33-metodos-reconstruccion.md"),
]),
("Operador E y Solver", [
 ("E=D^0.5*NUFFT*C", "Raiz densidad, Fourier no uniforme, sensibilidades", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("NUFFT", "Fourier para posiciones no uniformes del k-space radial", DF+"/Paper-MRI-US/diseno_images/03_metodo_cs/fig4_cs_reconstruction.pdf"),
 ("Densidad D (Pipe-Menon)", "Radios cruzan centro: 1/|k|. D reequilibra, D^0.5 blanquea residuo", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("ADMM 50 iter", "Maneja TV no-diferenciable con operador proximal", CT+"/main.pdf"),
 ("Huber en TV", "Reemplaza cuspide l1 en origen por cuadratico: habilita L-BFGS", DF+"/presentacion-especiales/compressed-sensing/scripts/gen_guion.py"),
 ("Normalizacion por eco", "TV grado 1, datos grado 2: sin normalizar sesga curva decaimiento", DF+"/Paper-MRI-US/Content/3_Methods.tex"),
 ("Elegir lambda", "L-curve, discrepancia, visual. lambda=1e-4 calibrado fantoma", DF+"/marco-teorico/bloque-F-reconstruccion/T32-variacion-total.md"),
 ("SENSE descartado", "Solo cartesiano regular. Radial aleatorio exige CS", DF+"/marco-teorico/bloque-F-reconstruccion/T33-metodos-reconstruccion.md"),
 ("Regridding", "Interpolar a cartesiana+IFFT: no iterativo, aliasing intacto", CT+"/docs/template-parcial-final-2026-09-19.pdf"),
 ("Framework TF-MRI", "NUFFT, sensibilidades, proximales componibles", CT+"/docs/template-parcial-final-2026-09-19.pdf"),
]),
("Modelo Tricomponente", [
 ("Modelo S(TE) tri-comp", "S0*|f_bw*e+ f_pw*e + f_bm*e*e^(j2pi*Df*TE)|, suma f=1", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("e^(j2pi*82Hz*TE)", "Grasa oscila cada 12.2ms: exponencial compleja captura desfase", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("Stick-breaking", "Garantiza f_bw+f_pw+f_bm=1 exactamente por construccion", PM+"/Content/3_Methods.tex"),
 ("Ancla two-decay", "Dixon en ROI medula: congela T2*f si califica (R2>=0.5, sin topes)", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("5 libres con ancla", "S0, f_bw, f_pw, T2*bw, T2*pw. AICc k=5", PM+"/main.pdf"),
 ("Poda AICc", "Si 3 pools no justifican, poda el debil. f_short<5%=degenera a mono", DF+"/presentacion-especiales/relaxometria/README.md"),
 ("Rango [0.03,120]ms", "bw y pw en banda compartida: etiquetado canonico (mas rapido=bw)", PM+"/main.pdf"),
 ("Differential evolution", "Optimizador global genetico: paisaje multimodal", DF+"/presentacion-especiales/relaxometria/README.md"),
 ("Frontera BW/PW 1500us", "El prior MAS influyente: separa pools en etiquetado", DF+"/codigo/plataforma/api_modelo_tricomponente/src/priors.py"),
 ("Por que ancla medula", "T2*bm largo+oscila+SNR bajo=no identificable. Ancla lo congela", DF+"/marco-teorico/bloque-G-ruido-modelos/T40-prior-medula.md"),
]),
("Ruido Rician", [
 ("Distribucion Rice", "p(M)=M/sigma2*exp(-(M2+nu2)/2sigma2)*I0(M*nu/sigma2)", DF+"/marco-teorico/bloque-G-ruido-modelos/README.md"),
 ("E[M]>=nu siempre", "Sesgo magnitud: maximo a SNR->0 (piso Rayleigh sigma*sqrt(pi/2))", DF+"/marco-teorico/bloque-G-ruido-modelos/README.md"),
 ("Sigma desde fondo", "STD_ruido promediado sobre TEs. Fallback: 0.5*STD_tejido", DF+"/marco-teorico/bloque-I-procesamiento-metricas/T47-extraccion-roi.md"),
 ("LS vs MLE", "LS rapido pero asume gaussiano. MLE exacto, insesgado a bajo SNR", DF+"/presentacion-especiales/relaxometria/main.pdf"),
 ("Chi no central", "Multi-canal RSS: 2N gdl, piso ~sqrt(2N)*sigma", CT+"/codigo/plataforma/api_mapas_t2/src/utils_relajacion.py"),
 ("Despejar sigma y N", "Media fondo=piso(dep N), STD=sigma: datos lo dicen", CT+"/codigo/plataforma/api_mapas_t2/src/utils_relajacion.py"),
 ("Inicializacion secuencial", "Mono a TEs altos=inicializa larga. Mono al residuo=inicializa corta", DF+"/marco-teorico/bloque-G-ruido-modelos/T38-modelo-biexponencial.md"),
 ("f_short<5%", "Bi-exp degenera a mono: componente corta despreciable", DF+"/marco-teorico/bloque-G-ruido-modelos/T38-modelo-biexponencial.md"),
 ("Sesgo critico 0.55T", "M0~B0 menor, senal cae al piso: ignorar sesga T2* arriba", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("I0 y I1", "Bessel modificadas 1a especie ordenes 0,1: en PDF y E[M] Rice", DF+"/marco-teorico/bloque-G-ruido-modelos/README.md"),
]),
("Anatomia Hueso Cortical", [
 ("3 pools agua", "BW(colageno,50-500us), PW(Havers,1-50ms), BM(grasa,30-80ms+CS)", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("BW anatomicamente", "Interfase colageno I-hidroxiapatita, escalas nm", DF+"/marco-teorico/bloque-A-marco-clinico-anatomico/T04-tres-pools-protones.md"),
 ("PW anatomicamente", "Havers(~50um)+lacunocaniculares(10um,100nm)", DF+"/marco-teorico/bloque-A-marco-clinico-anatomico/T04-tres-pools-protones.md"),
 ("Que es osteon", "Unidad cilindrica ~200um con laminillas alrededor de Havers", DF+"/marco-teorico/bloque-A-marco-clinico-anatomico/T04-tres-pools-protones.md"),
 ("Composicion cortical", "70% mineral, 30% colageno. Agua 15-20% con senal RM", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("Porosidad cortical", "Fraccion volumen con canales+lagunas: determina resistencia", DF+"/marco-teorico/bloque-A-marco-clinico-anatomico/T04-tres-pools-protones.md"),
 ("Por que tibia media", "Cortical gruesa, accesible, estandar QUS, medula para ancla", CT+"/narracion/texto/cap5.txt"),
 ("Cortical=80% resistencia", "Su deterioro precede a perdida DMO detectable", CT+"/narracion/texto/cap2.txt"),
 ("Otros tejidos UTE", "Tendones/ligamentos(colageno denso), pulmon(interfase)", CT+"/narracion/texto/cap3.txt"),
 ("Separacion ~100x", "BW~0.4ms, PW~4ms, BM~40ms: 0.55T se separan mas", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
]),
("Chemical Shift", [
 ("Df=82Hz a 0.55T", "3.5ppm*42.577MHz/T*0.55T=81.96Hz", DF+"/codigo/plataforma/api_modelo_tricomponente/src/priors.py"),
 ("Minimos 6.1ms", "Oposicion: 1/(2*82Hz). Recuperacion 12.2ms: 1/82Hz", CT+"/docs/template-parcial-final-2026-09-19.pdf"),
 ("IR-UTE", "Inversion Recovery: 180 invierte grasa, adquiere UTE en cruce nulo", DF+"/Paper-MRI-US/Others/capitulo7/capitulo7c.tex"),
 ("Pulsos IR probados", "Hard y Silver-Hoult: ninguno efectivo a 0.55T", CT+"/narracion/texto/cap8.txt"),
 ("Por que dificil 0.55T", "Df=82Hz menor: menos margen espectral. B1-inhom mayor", CT+"/narracion/texto/cap8.txt"),
 ("UTE-hmrGC", "Graph Cut multirresolucion: PDFF, R2*, B0. Valida f_bm", CT+"/anexos/anexo5.tex"),
 ("1a linea defensa", "Evitar TE=6.1ms (oposicion de fase)", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("2a linea (elegante)", "Modelar desfase: exp(j2pi*Df*TE). No suprimir, incorporar", DF+"/presentacion-especiales/chemical-shift/scripts/gen_guion.py"),
 ("PDFF", "Proton Density Fat Fraction: mapa % grasa (hmrGC)", CT+"/anexos/anexo5.tex"),
 ("In-phase 12.2ms util", "Agua+grasa alineadas: senal medula maxima, mejor ancla", CT+"/docs/template-parcial-final-2026-09-19.pdf"),
]),
("Fragilidad Osea", [
 ("Que es fragilidad", "Perdida capacidad resistir cargas: fractura bajo trauma", CT+"/narracion/texto/cap2.txt"),
 ("Disociacion densidad-riesgo", "DM2,obesidad,gluco: fracturan sin caida DMO. >50% T-score>-2.5", DF+"/Paper-MRI-US/narracion/texto/intro.txt"),
 ("PI=f_pw", "S_pw/(S_bw+S_pw): proxy fragilidad, adimensional", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("PI1 vs PI2", "PI1=dual-eco(screening). PI2=model-based(f_pw completo)", CT+"/docs/planificacion-parcial-final.md"),
 ("f_bm calidad ROI", "Alto=contaminacion medula, resultado menos confiable", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("f_bw alto=matriz densa", "Hueso joven/sano. f_pw alto=poroso/fragil", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("T-score<=-2.5", "Umbral osteoporosis. Pero calidad va mas alla de densidad", CT+"/narracion/texto/cap2.txt"),
 ("RM+US vs DXA", "Sin radiacion, miden composicion+porosidad no solo densidad", CT+"/docs/qa/abstract_p3.png"),
 ("Contribucion original", "1ra tri-comp in vivo 0.55T con modelo medular y US sin radiacion", DF+"/Paper-MRI-US/narracion/texto/discussion.txt"),
 ("Cadena conceptual", "Fractura/DXA->calidad->pools->UTE->CS->tri-comp->PI. BDAT converge", CT+"/capitulos/capitulo2.tex"),
]),
("US-BDAT", [
 ("BDAT", "Bidirectional Axial Transmission: ultrasonido ambas direcciones", CT+"/narracion/texto/anexo6.txt"),
 ("Corteza=guia ondas", "Espesor~lambda(200-500kHz): modos guiados dependen espesor+elasticidad", CT+"/narracion/texto/anexo6.txt"),
 ("Espesor/porosidad BDAT", "Curvas dispersion->ajuste modelo guia ondas->espesor+porosidad", CT+"/narracion/texto/anexo6.txt"),
 ("UTE solo tibia, BDAT tibia+radio", "Comparacion sitio-a-sito en tibia", DF+"/Paper-MRI-US/narracion/texto/methods.txt"),
 ("Ventaja emparejado", "Propio sitio=su control: sin variabilidad inter-sujeto", DF+"/Paper-MRI-US/narracion/texto/methods.txt"),
 ("15 pares a la fecha", "Sep 2026, N=20 cierra", CT+"/narracion/texto/cap7.txt"),
 ("Modelos A y B", "Regresion UTE(f,PI) vs BDAT(velocidad,atenuacion)", CT+"/docs/planificacion-parcial-final.md"),
 ("BDAT sin radiacion", "Ondas mecanicas, no rayos X. Mediciones repetidas", CT+"/narracion/texto/anexo6.txt"),
 ("Transductor tangencial", "Cara medial tibia 50% longitud", DF+"/Paper-MRI-US/Others/pag8_final.png"),
 ("BDAT vs DXA", "Mide elasticidad+geometria cortical. Sin radiacion. Portable", CT+"/narracion/texto/anexo6.txt"),
]),
("Validacion y Resultados", [
 ("Fantoma: 2.2% y 0.8%", "UTE reproduce GRE con desviaciones minimas", CT+"/docs/template-parcial-final-2026-09-19.pdf"),
 ("Orden: fantoma->exvivo->invivo", "Cada nivel valida el anterior", CT+"/narracion/texto/cap7.txt"),
 ("N=20, 20-80 anos", "Etica UV+PUC ID 210125006", DF+"/Paper-MRI-US/Content/3_Methods/3.4_In_Vivo_Feasibility.tex"),
 ("Exclusion: IMC>35", "Posicionamiento bobina, implantes RM, claustrofobia", DF+"/Paper-MRI-US/Content/3_Methods/3.4_In_Vivo_Feasibility.tex"),
 ("simulador_t2.py", "Tablas sinteticas con fondo SIMULADO: ejercita ruta completa", CT+"/codigo/plataforma/api_modelo_tricomponente/src/simulador_t2.py"),
 ("ECC: 10^4it, tol 10^-12", "Registro rigido rot+trasl contra TE mas corto", DF+"/Paper-MRI-US/diseno_images/04_metodo_tricomponente/fig5_tricomponente_relaxometry.pdf"),
 ("Frontera BW/PW=1500us", "Prior MAS influyente del modelo", DF+"/codigo/plataforma/api_modelo_tricomponente/src/priors.py"),
 ("MAGNETOM Free.Max", "0.55T Siemens cuerpo completo, bobina flexible", CT+"/capitulos/capitulo4.tex"),
 ("KomaMRI", "Simulador Julia Bloch: valida timing antes del scanner", CT+"/capitulos/capitulo5.tex"),
 ("Mes 19 de 24", "Marzo 2025-febrero 2027. Campana cierra sep 2026", CT+"/narracion/texto/cap6.txt"),
]),
("Plataforma e Implementacion", [
 ("Pypulseq", "Open-source Python, compila a .seq Siemens", CT+"/narracion/texto/anexo2.txt"),
 ("RelajacionTransversal", "Clase en relajacionTransversalTri.py: mono Rician + tri-comp CS", CT+"/codigo/plataforma/api_modelo_tricomponente/src/relajacionTransversalTri.py"),
 ("15 servicios docker", "Scanner->rawdata->CS->PNG->tricomponente->PostgreSQL->frontend", CT+"/anexos/anexo7.tex"),
 ("api_reconstruccion_radial", "Pipeline CS radial + cartesiano + libre", CT+"/codigo/plataforma/README.md"),
 ("ejecutarSecuenciaRadial.py", "random_sampling, seed=42, cs_factor=1.0", CT+"/codigo/plataforma/api_generacion_ute/src/ejecutarSecuenciaRadial.py"),
 ("priors.py", "Frontera BW/PW(1500us), Df(82Hz), rangos T2*", DF+"/codigo/plataforma/api_modelo_tricomponente/src/priors.py"),
 ("validateUTEImplementation", "Banco validacion: timing, trayectoria, spoiling", CT+"/narracion/texto/anexo2.txt"),
 ("Trazabilidad formulas", "docs/trazabilidad: 21 ecuaciones mapeadas a origen", CT+"/docs/trazabilidad-formulas.md"),
 ("Collage UTE", "Visualizacion multi-eco canonica desde plataforma", CT+"/codigo/plataforma/README.md"),
 ("Flujo completo", "Scanner->rawdata-api->CS->PNG->api_mapas_t2+tri->PostgreSQL->Next.js", PM+"/docs/02-arquitectura-ecosistema.md"),
]),
("Preguntas de Defensa", [
 ("P1: Por que UTE bajo campo", "T2* ultracorto, convencional llega tarde, SNR limitado a 0.55T", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("P2: Que es Rician", "Magnitud con ruido gaussiano: E[M]>=nu, sesgo maximo bajo SNR", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("P6: Df=82Hz", "3.5ppm*42.577MHz/T*0.55T. Fasor rota: rizado. Modelar fase", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("P7: Prior medula", "T2*bm largo+oscila+SNR bajo=no identificable. Ancla congela", DF+"/marco-teorico/bloque-G-ruido-modelos/T40-prior-medula.md"),
 ("10 iter L-BFGS", "Ganancia en primeras iter. Residual~ruido: mas=ajustar ruido", DF+"/presentacion-especiales/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Abstract 1 frase", "UTE 0.55T cuantifica agua cortical CS+Rician, validado vs BDAT", CT+"/docs/qa/abstract_p3.png"),
 ("Bajo campo=ventaja", "Menor susceptibilidad->T2* alargados->pools mas separados", DF+"/marco-teorico/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("Plataforma=contribucion", "Reproducible punta a punta: 15 servicios dockerizados", CT+"/anexos/anexo7.tex"),
 ("1ra tri-comp 0.55T", "First in vivo tri-component T2* quantification at 0.55T", DF+"/Paper-MRI-US/narracion/texto/discussion.txt"),
 ("Cadena conceptual", "Fractura->calidad->pools->UTE->CS->tri->PI. BDAT->concordancia", CT+"/capitulos/capitulo2.tex"),
]),
("Bajo Campo 0.55T", [
 ("0.55T=eleccion metodologica", "Menor susceptibilidad, pools separados, costo, acceso, sin helio", DF+"/Paper-MRI-US/narracion/texto/discussion.txt"),
 ("Ventaja implantes", "Menos artefactos susceptibilidad cerca de metal", DF+"/articulos/1-s2.0-S1120179726000086-main.pdf"),
 ("Compensar SNR menor", "Bobina cercana, CS, Rician, 12 TEs logisticos", DF+"/Paper-MRI-US/narracion/texto/discussion.txt"),
 ("Trade-off SNR/separacion", "Menor SNR pero mayor separacion: facilita cuantificacion", DF+"/marco-teorico/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("MAGNETOM Free.Max", "0.55T, cuerpo completo, helio reducido, ruido menor", CT+"/capitulos/capitulo4.tex"),
 ("Mayor campo=T2* mas corto", "T2*~1/(gamma*dB0): misma inhomogeneidad produce mas desfase", DF+"/marco-teorico/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("Larmor 0.55T=23.4MHz", "42.577*0.55. Df=3.5ppm*23.4=82Hz", DF+"/codigo/plataforma/api_modelo_tricomponente/src/priors.py"),
 ("Bobina extremidad", "Mayor sensibilidad local: compensa menor M0", CT+"/capitulos/capitulo4.tex"),
 ("Gmax=18mT/m", "Maximo gradiente a 0.55T. Maximiza kmax", DF+"/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf"),
 ("Desventajas 0.55T", "Menor SNR, senal al piso rapido. Compensado CS+Rician", DF+"/Paper-MRI-US/narracion/texto/discussion.txt"),
]),
("ECC y Preprocesamiento", [
 ("ECC", "Enhanced Correlation Coefficient: registro rigido entre ecos", DF+"/Paper-MRI-US/diseno_images/04_metodo_tricomponente/fig5_tricomponente_relaxometry.pdf"),
 ("1er eco referencia", "Mayor SNR y detalle estructural", DF+"/Paper-MRI-US/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("ECC 10^4it tol 10^-12", "Euclidean 2D rot+trasl. Adaptado hmrGC", DF+"/Paper-MRI-US/diseno_images/04_metodo_tricomponente/fig5_tricomponente_relaxometry.pdf"),
 ("Imagenes alineadas", "Subcarpeta /magnitude_alineadas/", DF+"/marco-teorico/bloque-J-plataforma-dockerizada/T54-api-tricomponente.md"),
 ("ROI coordenadas originales", "API revierte escala canvas antes de procesar", DF+"/marco-teorico/bloque-J-plataforma-dockerizada/T54-api-tricomponente.md"),
 ("Interpretacion clinica", "interpretar_resultados_clinicos: diagnostico automatico", CT+"/codigo/plataforma/api_modelo_tricomponente/src/utils_relajacion.py"),
 ("Modo Mapa T2", "ROI por percentil T2: subregiones por umbral", CT+"/codigo/plataforma/api_reconstruccion_radial/src/coordinador.py"),
 ("Normalizacion eco CS", "K-space unidad: evita sesgo TV/datos al decaer senal", DF+"/Paper-MRI-US/Content/3_Methods.tex"),
 ("process_batch", "Procesa .dat/.npy con normalizacion global lote", CT+"/codigo/plataforma/api_reconstruccion_radial/src/coordinador.py"),
 ("16-bit PNG cv2", "cv2.imread directo. API valida (cx,cy,r)", DF+"/marco-teorico/bloque-J-plataforma-dockerizada/T54-api-tricomponente.md"),
]),
("Biormarcadores y Fracciones", [
 ("2 denominadores", "f_bw,f_pw/agua cortical=composicion. f_bm/total=calidad ROI", DF+"/marco-teorico/bloque-I-procesamiento-metricas/T48-sistema-fracciones.md"),
 ("PI=f_pw", "S_pw/(S_bw+S_pw): proxy fragilidad adimensional", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("PI1 dual-eco", "Razon 2 ecos: screening rapido", CT+"/docs/planificacion-parcial-final.md"),
 ("PI2 model-based", "f_pw tricomponente con error estandar", CT+"/docs/planificacion-parcial-final.md"),
 ("f_bw alto=matriz densa", "Hueso sano/joven", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("f_pw alto=poroso", "Fragilidad, osteoporosis", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("Formula tri-comp", "S0*|f_bw*e+f_pw*e+f_bm*e*e^(j2pi*82*TE)|, suma f=1", DF+"/presentacion-especiales/relaxometria/guion_relaxometria.pdf"),
 ("S0 total (tutora)", "Fracciones reparten S0 en TE=0, no amplitudes independientes", DF+"/presentacion-especiales/relaxometria/README.md"),
 ("Validacion: 2.2%/0.8%", "Fantoma vs GRE. N=20, 15 pares BDAT", CT+"/narracion/texto/cap7.txt"),
 ("Concordancia emparejada", "Sitio tibial UTE+BDAT misma sesion", DF+"/Paper-MRI-US/narracion/texto/methods.txt"),
]),
("Estado del Arte", [
 ("Pauly 1989", "Referencia half pulse (Stanford)", CT+"/docs/trazabilidad-formulas.md"),
 ("Conolly 1988", "VERSE: Variable-Rate Selective Excitation", CT+"/docs/trazabilidad-formulas.md"),
 ("Du2012Ultrashort", "DOI 10.1002/mrm.23047: UTE en hueso", CT+"/docs/informe-bib-tesis.md"),
 ("Seifert 2015", "BW 1.5T=401us, PW=4110us: tabla referencia", DF+"/marco-teorico/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("Grupos UTE hueso", "Robson, Du, Chang, Seifert: campo alto 1.5-3T", CT+"/capitulos/capitulo1.tex"),
 ("312 referencias", "Mayoría DOI verificado en .bib", CT+"/docs/doi-check-tesis-full.md"),
 ("Open-source RM", "Pypulseq, KomaMRI.jl, TF-MRI, twixtools", CT+"/docs/template-parcial-final-2026-09-19.pdf"),
 ("fieldmapping-hmrGC", "Stelter 2022: Graph Cut multirresolucion agua-grasa", CT+"/anexos/anexo5.tex"),
 ("Pregunta clave", "Biomarcadores calidad osea con UTE a 0.55T accesible", DF+"/Paper-MRI-US/narracion/texto/discussion.txt"),
 ("Interdisciplinaria", "Fisica RM+matematica+software+anatomia+clinica", CT+"/narracion/texto/cap4.txt"),
]),
]


async def main():
    async with SessionLocal() as db:
        tema = await db.get(Tema, TEMA)
        hoy = date.today()
        print("Generando decks...")
        nd = 0
        for titulo, tarjetas in DECKS:
            deck = Deck(titulo=titulo, tema_id=TEMA, estado="listo")
            db.add(deck)
            await db.flush()
            for frente, reverso, archivo in tarjetas:
                db.add(Flashcard(
                    deck_id=deck.id, frente=frente, reverso=reverso,
                    cita={"archivo": archivo, "pagina": ""},
                    proxima_repaso=hoy,
                ))
            nd += len(tarjetas)
            print(f"  OK {titulo} ({len(tarjetas)})")
        await db.commit()
        print(f"Total: {nd} tarjetas en {len(DECKS)} decks")

asyncio.run(main())
