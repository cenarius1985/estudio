#!/usr/bin/env python3
"""20 decks NUEVOS (10 tarjetas c/u) enfocados en proyectos de tesis, paper
MRI-US y las matemáticas de UTE y CS. Inserta directo en BD (estado listo).
Formato: (titulo, [(frente, reverso, archivo), ...]) — igual que gen_decks.py.
"""
import asyncio, sys
from datetime import date
sys.path.insert(0, "/app")
from sqlalchemy import select
from estudio.db import SessionLocal
from estudio.models import Deck, Flashcard, Tema

TEMA = "933ee140ea124c5a8aff1afb06c5d257"

C = "MRI-UTE PROYECTO DE TESIS"
D = "defensa_tesis_doctoral"
P = "paper-mri-us"
MT = D + "/marco-teorico"
PS = D + "/presentacion-especiales"
COD = D + "/codigo/plataforma"

DECKS = [
("Paper MRI-US: Cifras Clave del Abstract", [
 ("¿Qué campo magnético usa el estudio del paper?", "0.55 T (MAGNETOM Free.Max, Siemens) — cuerpo completo de bajo campo", P + "/Content/1_Abstract.tex"),
 ("¿Qué secuencia implementa el paper para hueso cortical?", "UTE 2D radial con half-pulse, ramp sampling y TE = 30 µs", P + "/Content/1_Abstract.tex"),
 ("¿Cuántos sujetos y qué sitio anatómico?", "N = 20, diáfisis tibial al 50% del largo (corteza más gruesa y uniforme)", P + "/Content/1_Abstract.tex"),
 ("¿Qué validación con fantoma reporta el abstract?", "Concordancia 2.2% (bound water) y 0.8% (pore water) frente a GRE multi-eco", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Qué modalidad complementaria se compara?", "US-BDAT: ondas guiadas ultrasónicas bidireccionales en la misma tibia, diseño emparejado", P + "/Content/3_Methods/3.5_Multimodal_Analysis_US_BDAT.tex"),
 ("¿Cuántos TEs y en qué rango?", "12 TEs logarítmicamente espaciados entre 0.03 y 25 ms", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Qué aporte resume el abstract en una línea?", "La cadena UTE+CS+relajometría tri-componente es viable a 0.55 T con pipeline reproducible", P + "/Content/1_Abstract.tex"),
 ("¿Qué ID ética respalda el estudio?", "UV + PUC, ID 210125006 (N=20)", C + "/capitulos/capitulo4.tex"),
 ("¿Qué resolución espacial logra la UTE 2D?", "≈ 0.9 mm (kmax acotado por G=18 mT/m y t_eff corto)", C + "/narracion/texto/anexo1.txt"),
 ("¿Qué factor de submuestreo CS maneja el pipeline?", "cs_undersampling_factor ∈ [0.2, 1.0]", COD + "/api_generacion_ute/src/ajustarParametros.py"),
]),
("Paper MRI-US: Methods al Detalle", [
 ("¿Por qué TEs logarítmicos y no lineales?", "Los T2* de los pools difieren ~100×: el muestreo log iguala la información por década temporal (µs→BW, ms→PW/BM)", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Qué hace el paso 1 (ancla) del pipeline?", "Ajuste two-decay water-fat en médula con Δf=82 Hz para fijar/congelar T2*_bm", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Qué hace el paso 2?", "Ajuste tri-componente de la corteza con T2*_bm congelado del ancla (evita degeneración de parámetros)", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Qué optimizador ajusta el modelo?", "differential_evolution (global, evita mínimos locales del multimodal) con ECC: 10⁴ iter, tol 10⁻¹²", COD + "/api_modelo_tricomponente/src/relajacionTransversalTri.py"),
 ("¿Qué compuertas de calidad se aplican?", "Fracciones libres (sin topes) + R² ≥ 0.50; los fallos se registran y excluyen pre-declaradamente", COD + "/api_modelo_tricomponente/src/relajacionTransversalTri.py"),
 ("¿Qué decide la poda AICc?", "Bi vs tri-componente por ROI: si el 3er pool no reduce AICc, se reporta el modelo simple", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Por qué normalización por eco antes del ajuste?", "Iguala la contribución informativa de cada TE: sin ella los ecos tempranos dominan el χ² y la cola (f_bm) pesa casi nada", COD + "/api_modelo_tricomponente/src/relajacionTransversalTri.py"),
 ("¿Cómo se comparan RM y US-BDAT estadísticamente?", "Correlación Pearson/Spearman + Bland-Altman (sesgo y límites de acuerdo) + repetibilidad entre sesiones", P + "/Content/3_Methods/3.5_Multimodal_Analysis_US_BDAT.tex"),
 ("¿Qué rol tiene el fantoma de dos pools?", "Demostrar EXACTITUD (verdad conocida por construcción): in-vivo solo puede demostrarse precisión/repetibilidad", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Por qué la tibia al 50%?", "Corteza más gruesa y homogénea + estándar de la literatura UTE (comparabilidad con Seifert y otros)", P + "/Content/3_Methods.tex"),
]),
("Paper MRI-US: Results y Lectura Clínica", [
 ("f_bw ALTA en corteza significa…", "Más agua ligada a colágeno-hidroxiapatita: matriz mejor conservada (calidad ósea)", C + "/narracion/texto/cap3.txt"),
 ("f_pw ALTA en corteza significa…", "Más agua en poros (Havers/lacunocaniculares): porosidad y fragilidad", C + "/narracion/texto/cap3.txt"),
 ("DXA normal + f_pw elevada en DM2 ejemplifica…", "La disociación densidad-riesgo: la hiperglucemia deteriora microarquitectura sin bajar densidad areal", C + "/narracion/texto/cap3.txt"),
 ("¿Por qué la médula casi no aporta al mapa f_bw?", "Su T2* (decenas de ms, pool BM) es físicamente distinto del BW (~0.4 ms): la separación es física, no por umbral", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Qué mide el CV entre sesiones y para qué sirve?", "SD/media de réplicas = ruido técnico relativo: define la mínima diferencia detectable longitudinal", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Limitación honesta nº1 del estudio", "N=20 mono-sitio: factibilidad, no generalización clínica", D + "/Paper-MRI-US/Content/6_Conclusion.tex"),
 ("Limitación honesta nº2", "Sin referencia histológica/mecánica directa (compartida por toda la literatura UTE in-vivo)", D + "/Paper-MRI-US/Content/6_Conclusion.tex"),
 ("¿Qué propone el paper como siguiente paso?", "Estudios longitudinales en cohortes clínicas (DM2/osteoporosis) dimensionadas con las variabilidades estimadas", D + "/Paper-MRI-US/Content/6_Conclusion.tex"),
 ("¿Por qué IR-UTE quedó como estudio secundario?", "La inversión (TR extra + SAR) suprime el pool largo a costo alto; el ancla two-decay separa médula sin ese costo", C + "/capitulos/capitulo4.tex"),
 ("La frase-elevador de la tesis", "La calidad del hueso cortical es cuantificable a 0.55 T con cadena reproducible UTE+CS+tri-componente validada por fantoma y US-BDAT", P + "/Content/1_Abstract.tex"),
]),
("Matemáticas de k-space Radial (Fórmulas)", [
 ("Trayectoria k(t)", "k(t) = (γ/2π)·∫₀ᵗ G(τ)dτ  [ciclos/m; γ en rad/s/T]", MT + "/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("¿Por qué el 2π en k(t)?", "k en ciclos/m: γ=2π·42.577 rad/s/T ⇒ dividir por 2π pasa de radianes a ciclos (error clásico: FOV escalado 2π)", MT + "/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("Resolución Δx vs kmax", "Δx = 1/(2·kmax) — kmax=556 m⁻¹ ⇒ Δx≈0.9 mm", MT + "/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("Δk y FOV", "Δk = 1/FOV (sin aliasing); FOV=180 mm, Nx=500 ⇒ Δx=FOV/Nx=0.36 mm", MT + "/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("Muestreo en rampa cuadrático", "tᵢ = t_rise·(i/(N_ramp−1))² — concentra muestras cerca de k=0 compensando k∝t²", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
 ("Proyección del gradiente por radio φ", "Gx = G·cosφ, Gy = G·sinφ — |dk/dt| igual en todos los radios (resolución isotrópica)", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
 ("Crecimiento de k en la meseta del gradiente", "Lineal: k(t) = k_rampa + (γ/2π)·G·(t−t_rampa)", MT + "/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("Nyquist radial 2D", "N_r ≥ π·Nx radios (sin aliasing); violación ⇒ artefactos en estrella", MT + "/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md"),
 ("Conteo del pipeline con Nx=500, cs=1", "N_r = ceil(π·Nx/2)·2 = 1572 radios ⇒ 786 TRs a 2 radios/TR", COD + "/api_generacion_ute/src/ajustarParametros.py"),
 ("kmax en términos del discretizado", "kmax = π·Nx/FOV = π·500/0.18m ≈ 8729 rad/m ⇔ 1389 ciclos/m… (equivalente: G·t_eff·γ/2π)", MT + "/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
]),
("Matemáticas del Operador E (CS)", [
 ("Problema directo CS", "y = E·x + n (muestras submuestreadas = operador × imagen + ruido)", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Descomposición de E", "E = D^½ · NUFFT · C (densidad, NUFFT, mapas de bobina)", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("¿Qué hace C?", "Aplica los mapas de sensibilidad de bobina (estimados del centro k sobremuestreado)", P + "/Content/3_Methods.tex"),
 ("¿Qué hace D^½ (Pipe–Menon)?", "Repondera por densidad de muestreo: el centro radial sobremuestreado no debe dominar el data-fidelity", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Funcional minimizado", "(1/2)·||E·x − y||² + λ·TV(x), con λ = 10⁻⁴", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("¿Qué controla λ?", "Trade-off fidelidad-datos vs regularidad: λ alto = sobresuavizado; λ bajo = aliasing residual", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Por qué TV para hueso", "La corteza es casi constante por tramos: ∇x disperso — CS funciona en el dominio del gradiente", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("De ℓ₀ a ℓ₁", "min ||∇x||₀ es NP-duro; ||∇x||₁ es el relajamiento convexo con unicidad bajo RIP", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Qué garantiza RIP", "E preserva normas de vectores ∇-dispersos ⇒ la solución ℓ₁ es estable y única cerca de la ℓ₀", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Por qué E^H·y no basta", "Es la gridding con aliasing incoherente (M<<N): el punto de partida que ADMM refina imponiendo dispersión", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
]),
("Solvers: ADMM y L-BFGS en el Pipeline", [
 ("¿Por qué ADMM para TV?", "||∇x||₁ no es diferenciable en 0: ADMM separa fidelidad (cuadrática) y TV (proximal = soft-thresholding)", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Iteraciones del solver principal", "ADMM: 50 iteraciones", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Variante L-BFGS", "10 iteraciones con TV suavizado por Huber (quasi-Newton exige gradiente continuo)", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("¿Qué es el soft-thresholding?", "El proximal de |u|: shrink(u,λ) = sign(u)·max(|u|−λ, 0) — el paso cerrado del TV en ADMM", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Con cs_factor=0.2 el sistema y=Ex queda…", "M << N: núcleo no trivial, infinitas soluciones — la TV pasa de 'mejora' a 'necesaria'", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("¿Qué aporta el ángulo aleatorio de radios a CS?", "Incoherencia: aliasing distribuido como ruido (no estrellones) — condición de recuperación", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("¿Qué imposibilita 'inventar' señal?", "Fidelidad ||Ex−y||² obliga a explicar lo medido + TV castiga estructura nueva: calibrado por fantoma", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("La NUFFT del pipeline es propia porque…", "Debe soportar la geometría exacta de rampa (tiempos al raster) y adjunto E^H consistente para el solver", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Reconstrucción 'cuantitativa' significa…", "E/E^H consistentes y λ calibrado: los valores alimentan el ajuste T2* sin sesgo sistemático del solver", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Criterio de Nyquist en código", "N_r_final = ceil(π·Nx/2 · cs_undersampling_factor)·2 — el ·2 garantiza par (2 radios/TR)", COD + "/api_generacion_ute/src/ajustarParametros.py"),
]),
("Pulsos RF: Sinc, TBW y Apodización", [
 ("Parámetros del pulso de selección de corte", "Flip 30°, TBW=2, duración 0.5 ms, corte 10 mm (sinc apodizado)", PS + "/secuencia-ute/scripts/gen_guion.py"),
 ("¿Qué es TBW?", "Time-bandwidth product = Δf·T: fija el trade-off selectividad vs duración", PS + "/secuencia-ute/scripts/gen_guion.py"),
 ("¿Por qué apodizar el sinc?", "La ventana (Hann) suprime lóbulos laterales (Gibbs) a costa de ensanchar la transición", PS + "/secuencia-ute/scripts/gen_guion.py"),
 ("Relación gradiente-ancho de banda del corte", "G_z = BW/(γ·Δz): el gradiente traduce ancho de banda en grosor de corte", PS + "/secuencia-ute/scripts/gen_guion.py"),
 ("¿Por qué half pulse y no pulso completo?", "El pulso selectivo completo duraría ms (mata TE=30 µs); dos medios pulsos con G invertido completan el perfil", C + "/narracion/texto/anexo1.txt"),
 ("¿Qué excita cada half pulse?", "La mitad del plano con fase residual en k_z; la pareja con polaridad invertida suma el perfil completo", C + "/narracion/texto/anexo1.txt"),
 ("Costo del half pulse", "2 excitaciones por corte (el TR lo absorbe)", C + "/narracion/texto/anexo1.txt"),
 ("¿Por qué el TE mínimo es ~30 µs y no 0?", "Dead-time de conmutación T/R + llegada al primer punto k cuantizado: límite de electrónica, no de código", C + "/anexos/anexo2.tex"),
 ("¿Desde dónde se mide el TE?", "Del FIN del pulso RF a la PRIMERA muestra del ADC (verificable en el .seq)", C + "/anexos/anexo2.tex"),
 ("Flip 30° (no 90°) porque…", "Secuencia GRE spoiled con repetición: Ernst-like para SNR por unidad de tiempo en adquisición multi-TE", C + "/capitulos/capitulo4.tex"),
]),
("SAR: Fórmulas y Números", [
 ("Fórmula general del SAR", "SAR = σ·|E|²/(2ρ) — disipación óhmica del campo inducido en tejido conductor", C + "/main.pdf"),
 ("SAR de la UTE 2D en tibia (cilindro a=5 cm)", "SAR = σ·ω₀²·a²/(16·ρ·TR)·∫|B₁(t)|²dt", C + "/main.pdf"),
 ("¿De dónde sale el factor a²/16?", "E inducido crece con r (Faraday: E=ω₀B₁r/2); integrar σE² sobre el cilindro da a² con constante 1/16", C + "/main.pdf"),
 ("SAR ∝ B₀² porque…", "|E| ∝ ω₀|B₁| y ω₀=γB₀: potencia cuadrática en el campo", C + "/main.pdf"),
 ("3 T vs 0.55 T en SAR", "(3/0.55)² ≈ 30× más deposición a 3 T para el mismo pulso — el argumento físico del bajo campo", C + "/main.pdf"),
 ("¿De dónde NO viene el SAR?", "Ni de B₀ estático ni de gradientes: solo del RF que induce E en tejido conductor", C + "/main.pdf"),
 ("Implicación regulatoria", "A 0.55 T queda margen SAR para pulsos VERSE y repeticiones rápidas (ventanas 10 s / 6 min)", C + "/main.pdf"),
 ("Si el banco pide el SAR a 3 T", "Reportar la fórmula con parámetros del .seq y redisear (VERSE más largo, flip menor): escala ~30×", C + "/main.pdf"),
 ("¿Qué mide la integral ∫|B₁|²dt?", "La energía del RF efectivamente depositada por TR: pulso real del .seq, no el nominal", C + "/main.pdf"),
 ("Relación con ω₀", "ω₀ = γ·B₀ = 2π·42.577·0.55 ≈ 147 rad/s·10⁶ (23.4 MHz) — entra al cuadrado en SAR", C + "/main.pdf"),
]),
("VERSE: Condición y Derivación", [
 ("Condición VERSE", "B₁'(t) = B₁(τ(t))·|dτ/dt| — reparametrización temporal que conserva el flip angle", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("¿Qué preserva VERSE exactamente?", "La integral de B₁ en el tiempo reparametrizado (= ángulo de giro y perfil de excitación)", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("Forma integral de VERSE (por qué)", "Evaluar en forma integrada evita mal condicionamiento donde G_z≈0 en las rampas", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("Beneficio temporal de VERSE", "Absorbe el tiempo muerto de bajada del gradiente DENTRO de la excitación: RF y gradiente terminan juntos", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("¿Qué garantiza el momento neto nulo junto a VERSE?", "∫₀ᵗ¹ G_z dt = 0 ⇒ k_z(t₁)=0: la excitación termina en el centro de k sin refaseo", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
 ("La trayectoria k-space con VERSE+spoiler arranca…", "En kmax y termina en el origen (omitiendo el rephaser convencional)", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("¿La invariancia VERSE depende de qué par?", "Del par (B₁, G_z) vía el ángulo de inclinación acumulado — el perfil M⊥(z) queda invariante", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("Implementación en la tesis", "La lógica de remuestreo VERSE-like replica el esquema de MATLAB en Python (crearPulsoSeleccionCorte.py)", C + "/codigo/plataforma/api_generacion_ute/src/crearPulsoSeleccionCorte.py"),
 ("Trade-off de VERSE", "B₁ pico mayor donde se comprime el tiempo: vigilar SAR y límites de amplificador", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("¿Por qué VERSE importa a TE ultracorto?", "Permite RF selectivo corto SIN sacrificar perfil: sin VERSE, selectivo ⇒ largo ⇒ TE imposible", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
]),
("Momento Nulo y Half-Pulse: Demostraciones", [
 ("Demostración k_z(t₁)=0", "k_z(t)=(γ/2π)∫G_z dτ; integral neta nula al fin del pulso ⇒ posición k=0", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
 ("¿Qué elimina el momento neto nulo?", "El lóbulo de refaseo (~1 ms): la lectura arranca inmediatamente tras el RF", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
 ("Gradiente bipolar = ", "Dos lóbulos de polaridad opuesta con áreas iguales: área neta cero", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
 ("El half pulse trade-off estructural", "Pulso completo: selectivo pero largo (ms). Half pulse: mitad de duración con mitad de cobertura ⇒ pareja con G invertido", C + "/narracion/texto/anexo1.txt"),
 ("Las 4 decisiones del anexo 1 (UTE)", "Half pulse + momento nulo, ramp sampling desde k=0, lectura radial center-out, TE=30 µs verificado", C + "/narracion/texto/anexo1.txt"),
 ("¿Por qué 'invisible a eco de gradiente convencional'?", "TE mínimo ~2 ms vs T2*_BW ~0.4 ms: e^(−5) < 1% de la señal ya se fue", C + "/narracion/texto/anexo1.txt"),
 ("Captura de BW con TE=30 µs (número)", "BW a 0.55 T ~0.5–1 ms ⇒ e^(−30µs/0.5ms) = e^(−0.06) ≈ 94% de la señal presente", C + "/narracion/texto/anexo1.txt"),
 ("Spoiling RF 117° cuadrático sirve para…", "Destruir coherencia de magnetización residual entre TRs (sin ella, y=Ex no describe el dato)", C + "/main.pdf"),
 ("Spoiler de gradiente (20% Gmax rotado) sirve para…", "Degradar la coherencia residual DIRECCIONAL de cada lectura radial", C + "/main.pdf"),
 ("Par de medios pulsos y el par de radios por TR: analogía", "Ambos 'dobles' completan lo que una sola instancia no puede: perfil completo / paridad de adquisición", PS + "/secuencia-ute/guion_secuencia_ute.pdf"),
]),
("Código Defendible: priors.py", [
 ("Δf agua-grasa a 0.55 T (derivación)", "Δf = 3.5 ppm × 42.577 MHz/T × 0.55 T ≈ 81.96 Hz (≈82 Hz)", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("¿Por qué Δf codificado y no medido por sesión?", "Deriva de constantes físicas (ppm del shift, γ, B₀ nominal): medirlo añadiría ruido sin información", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Frontera BW/PW y su valor", "1500 µs: separa bound de pore water según la teoría de confinamiento — el prior MÁS influyente", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Periodo de batido agua-grasa", "1/82 Hz ≈ 12.2 ms — dentro del rango de TEs (hasta 25 ms): la fase química es imprescindible", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Doble denominador de fracciones", "f_bw/f_pw al agua cortical (comparable con histología); f_bm sobre el total de señal del vóxel", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Modelo con fase del priors", "S(TE) = Σᵢ fᵢ·e^(−TE/T2ᵢ*)·e^(i2πΔfᵢ·TE) — el término de fase modela el batido", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Por qué se congela T2*_bm", "El ancla two-decay de médula lo fija: sin congelar, 7 parámetros degeneran con 12 TEs", COD + "/api_modelo_tricomponente/src/relajacionTransversalTri.py"),
 ("¿Qué codifica priors.py como conocimiento?", "Física DERIVADA con unidades y referencias — el prior documentado y justificado, no caja negra", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Análisis de sensibilidad dijo…", "La frontera 1500 µs es el parámetro más influyente del ajuste tri-componente", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("γ del protón (memorizar)", "42.577 MHz/T (o 2π·42.577 rad/s/T según contexto)", COD + "/api_modelo_tricomponente/src/priors.py"),
]),
("Código Defendible: Pipeline de Análisis", [
 ("differential_evolution por multimodalidad", "Fracciones intercambiables y T2* degenerados: el global evita mínimos locales dependientes del inicio", COD + "/api_modelo_tricomponente/src/relajacionTransversalTri.py"),
 ("ECC del solver", "10⁴ iteraciones, tolerancia 10⁻¹² — precisión de convergencia reproducible", COD + "/api_modelo_tricomponente/src/relajacionTransversalTri.py"),
 ("hmrGC resuelve…", "ΔB0 y R2* multi-eco en JERARQUÍA: campo lento y suave primero, relajación local después", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("¿Por qué jerarquía y no ajuste conjunto?", "Escalas distintas de fenómenos: la jerarquía rompe el mal condicionamiento con física conocida", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("ECC del preprocesamiento corrige…", "Ganancias y fases diferenciales por canal/eco del receptor antes del combine RSS", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("Combinación multi-canal", "RSS (root sum of squares): magnitud sin mapas de fase; ruido ≈ Rice efectivo validado por fantoma", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("Visualización validada (endpoint mapas T2*)", "Percentiles p5–p95 con alpha 0.65: defaults de visualización son parte del método", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("La cita de código defendible incluye…", "Archivo Y LÍNEAS exactas — el código navegable como evidencia (como página de paper)", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Exactitud vs precisión en el pipeline", "Fantoma = exactitud (verdad conocida); repetibilidad in-vivo = precisión: dos experimentos, dos números", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Parámetros editables vs metodología fija (Etapa R1)", "@dataclass(frozen=True) con min/max y validación central: grados de libertad controlados, sin spurious", D + "/codigo/plataforma/README.md"),
]),
("Plataforma: Arquitectura y Reproducibilidad", [
 ("¿Por qué la secuencia vive en código (.seq)?", "Es un artefacto científico versionable: TE=30 µs y rampa t² verificables desde el archivo por cualquiera", C + "/anexos/anexo2.tex"),
 ("División de roles KomaMRI vs Pypulseq", "KomaMRI SIMULA (valida pulso y TE antes de sujetos); Pypulseq GENERA el .seq ejecutable en escáner", C + "/anexos/anexo2.tex"),
 ("¿Por qué stack dockerizado multi-servicio?", "Entornos idénticos de adquisición a fracciones: cada número del paper sale del MISMO código versionado", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("api_modelo_tricomponente como servicio porque…", "Análisis re-ejecutable sobre datos nuevos sin tocar adquisición: capas versionadas independientes", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Respuesta a '¿por qué confiar en tu software?'", "Validación por capas: fantoma (pipeline), simulación (secuencia), repetibilidad (cadena) y tests del repo (unidades)", P + "/Content/3_Methods.tex"),
 ("Trazabilidad de un resultado", "Git por componente + .seq (hash) + parámetros del solver y del ajuste registrados por corrida", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("Reproducible ≠ repetible", "Repetible: mismo resultado en mis manos. Reproducible: en manos ajenas (.seq+código+datos abiertos)", D + "/Paper-MRI-US/Content/6_Conclusion.tex"),
 ("La contribución al linaje UTE", "No un pulso nuevo: un SISTEMA cuantitativo (integración+validación+reproducibilidad) a bajo campo", C + "/narracion/texto/cap3.txt"),
 ("Por qué NUFFT propia y no librería", "Geometría exacta de rampa (raster) + adjunto E^H consistente: librerías genéricas asumen trayectorias ideales", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Si empezara hoy, cambiaría…", "Menos acoplamiento temprano (priors antes de ancla) y reclutamiento paralelo del estudio mayor — núcleo igual", D + "/Paper-MRI-US/Content/6_Conclusion.tex"),
]),
("Ruido Rice y MLE (Avanzado)", [
 ("Distribución de la magnitud RM", "Rice: p(M|s,σ) = (M/σ²)·e^(−(M²+s²)/2σ²)·I₀(Ms/σ²)", D + "/marco-teorico/bloque-G-ruido-riciano/T25-distribucion-rice.md"),
 ("¿Por qué LSQ sesga a bajo SNR?", "E_Rice[M] ≠ s: la rectificación aplana la señal hacia σ; el ajuste ingenuo confunde ruido con cola lenta", D + "/marco-teorico/bloque-G-ruido-riciano/T25-distribucion-rice.md"),
 ("Casos límite de Rice", "s→0: Rayleigh; SNR alto: gaussiana en s — Rice une ambos regímenes", D + "/marco-teorico/bloque-G-ruido-riciano/T25-distribucion-rice.md"),
 ("Estimación de σ sin escaneo extra", "Del fondo (air): s≈0 ⇒ Rayleigh con E[M²]=2σ² — el fondo calibra el ruido gratis", D + "/marco-teorico/bloque-G-ruido-riciano/T25-distribucion-rice.md"),
 ("Ventaja del MLE Riciano", "Modela la rectificación DENTRO de la verosimilitud: insesgado a todo SNR (fantoma: 2.2%/0.8%)", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("Condición de primer orden del MLE", "Score = ∇lnL = 0 en el óptimo: un score final grande delata convergencia falsa (diagnóstico)", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("Asintótica del MLE", "√n(θ̂−θ) → N(0, I⁻¹): justifica los IC de la Hessiana (más validación empírica por fantoma)", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("Objeción 'sus IC no son gaussianos'", "Válidos asintóticamente (teorema central de ML) + confirmados empíricamente: doble línea de defensa", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("I₀ en la fórmula de Rice", "Función de Bessel modificada de orden 0: la probabilidad de M integra las fases gaussianas complejas", D + "/marco-teorico/bloque-G-ruido-riciano/T25-distribucion-rice.md"),
 ("Rice aparece porque…", "La magnitud |signal+ruido complejo| rectifica: módulo de dos gaussianas independientes = Rice", D + "/marco-teorico/bloque-G-ruido-riciano/T25-distribucion-rice.md"),
]),
("CRLB y Diseño Experimental", [
 ("Cota de Cramér-Rao (CRLB)", "Var(θ̂) ≥ [I(θ)]⁻¹: cota inferior de varianza de cualquier estimador insesgado", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("Información de Fisher", "I(θ) = −E[∇²lnL]: curvatura esperada de la log-verosimilitud — más curva = más información", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("Incertidumbre del pipeline vía Hessiana", "Cov(θ̂) ≈ [−∇²lnL]⁻¹: errores de f_bw/f_pw para análisis ponderados y mínima diferencia detectable", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("¿Por qué CRLB importa al DISEÑO?", "Depende de dónde se muestrea: TEs que minimizan la traza maximizan información por unidad de tiempo", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
 ("12 TEs log-espaciados ≈ diseño óptimo porque…", "Cubren 3 décadas (0.03–25 ms, ~4 puntos/década) para 5-7 parámetros sin inflar TR total", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("¿Por qué no 20 TEs?", "Mejora marginal de la CRLB pero duplica TR: la logística clínica entra al diseño", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Identificabilidad: 12 datos vs 7 parámetros", "Ajuste justo: ancla congela T2*_bm (5 libres) y AICc renuncia al 3er pool si el SNR no lo sostiene", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Mínima diferencia detectable longitudinal", "Gobernada por repetibilidad (CV entre sesiones): Δf_pw < CV es ruido, no señal", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Uso del CV reportado", "Traduce repetibilidad a lenguaje clínico: cambio mínimo detectable en seguimiento", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("D-optimal design (idea madre)", "Elegir el muestreo que maximiza det(I(θ)): la teoría detrás de 'dónde medir'", D + "/marco-teorico/bloque-G-ruido-riciano/T26-mle-t2-estrella.md"),
]),
("UTE vs ZTE vs SWIFT vs SPRITE", [
 ("ZTE: idea central", "RF continuo con gradiente de lectura NUNCA apagado: k arranca del centro sin rampa (TE≈0 efectivo)", MT + "/bloque-C-fisica-secuencia-ute/T13-ute-vs-zte.md"),
 ("Costo de ZTE", "Ancho de banda grande del receiver y hueco central en k (dead time): correcciones propias", MT + "/bloque-C-fisica-secuencia-ute/T13-ute-vs-zte.md"),
 ("SWIFT: idea central", "Pulsos freq-swept casi continuos (gapped): TE ultracorto por excitación distribuida", C + "/narracion/texto/cap3.txt"),
 ("SPRITE: idea y limitación", "Un punto por rampa (single point): gold-standard de laboratorio, inviable in-vivo por eficiencia", C + "/narracion/texto/cap3.txt"),
 ("¿Por qué el proyecto eligió UTE 2D radial?", "TE=30 µs VERIFICABLE en el .seq, implementación Pypulseq reproducible, suficiente para BW a 0.55 T", C + "/capitulos/capitulo4.tex"),
 ("La familia comparte…", "El imperativo físico: medir antes de que T2* ultracorto decaiga (hueso, pulmón, tendones)", C + "/narracion/texto/cap3.txt"),
 ("Linaje histórico", "Pauly → Conolly → Robson/Du/Seifert: física UTE establecida; el proyecto aporta el sistema a bajo campo", C + "/narracion/texto/cap3.txt"),
 ("UTE vs GRE en hueso (número clave)", "GRE TE~2 ms vs T2*_BW~0.4 ms ⇒ e^(−5)<1%: hueso invisible; UTE captura ~94% con 30 µs", C + "/narracion/texto/anexo1.txt"),
 ("Tejidos hermanos que exigen UTE", "Pulmón (interfase aire-tejido), tendones/ligamentos (colágeno ordenado): misma física de T2* corto", C + "/narracion/texto/cap3.txt"),
 ("SPRITE vs UTE en una frase", "SPRITE mide con precisión de laboratorio lo que UTE mide en tiempo clínico: el proyecto elige lo viable in-vivo", C + "/narracion/texto/cap3.txt"),
]),
("0.55 T: Argumentos Cuantitativos", [
 ("Argumento cuantitativo nº1 del bajo campo", "T2* ∝ 1/(γΔB₀): menor campo alarga T2* asimétricamente ⇒ pools MÁS separados temporalmente", MT + "/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("La desventaja real y su mitigación", "M₀ ∝ B₀ (~35% de 1.5 T): menor SNR — mitigado con bobina flexible, sobremuestreo central y CS", C + "/capitulos/capitulo4.tex"),
 ("f₀ de Larmor a 0.55 T", "42.577 × 0.55 ≈ 23.4 MHz (y de ahí Δf=82 Hz)", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("BW a 1.5 T (Seifert 2015)", "401 ± 119 µs; PW 4110 ± 1230 µs: a más campo, ambos se acortan", MT + "/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("Separación entre pools vecinos", "~100× (BW ~0.4 ms, PW ~4 ms, BM ~40 ms): lo que hace posible la descomposición", PS + "/relaxometria/guion_relaxometria.pdf"),
 ("El escáner", "MAGNETOM Free.Max 0.55 T, cuerpo completo, con bobina flexible de extremidad", C + "/capitulos/capitulo4.tex"),
 ("Impacto del bajo campo (no físico)", "Despistaje poblacional de calidad ósea sin centro de alto campo: escalabilidad de acceso", C + "/capitulos/capitulo4.tex"),
 ("Contraste T2* por campo (tabla Seifert)", "PW: 4110 µs (1.5 T) → ~4350 (3 T) → 1300 (7 T) → 886 (9.4 T): compresión con B₀", MT + "/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("SAR a bajo campo", "∝B₀²: ~30× menor que 3 T — margen para VERSE y repeticiones", C + "/main.pdf"),
 ("Menor susceptibilidad implica…", "ΔB₀ locales menores: menos artefactos de interfase y ventana temporal más ancha para decaimientos", MT + "/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
]),
("Defensa: Preguntas Trampa y Respuestas", [
 ("'¿Física, software o medicina tu tesis?'", "Problema de MEDICIÓN: física define qué medir, software asegura confianza, la clínica dirige — tres capas, un biomarcador", C + "/main.pdf"),
 ("'CS con 20% de datos ¿no es trampa?'", "La fidelidad mide exacto y la TV solo selecciona la solución compatible: validado por fantoma (2.2%/0.8%)", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("'Su N=20 no da conclusiones clínicas'", "Correcto: es factibilidad que estima variabilidades para dimensionar el estudio clínico siguiente", P + "/Content/1_Abstract.tex"),
 ("'¿Volumen parcial cortico-medular?'", "ROIs en corteza pura + ancla de médula + exclusión pre-declarada: control declarado, no inmunidad", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("'Escriba su modelo en la pizarra'", "S(TE)=Σᵢ fᵢ·e^(−TE/T2ᵢ*)·e^(i2πΔfᵢTE) — cada símbolo con unidades y denominadores claros", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("'¿Por qué confiar en su software?'", "Caja negra comercial vs código auditable: E, priors derivados y compuertas validados por capas", COD + "/plataforma/runbooks/contexto-mapas-t2-hmrGC.md"),
 ("'¿Error de fantoma vs repetibilidad?'", "Fantoma=exactitud (verdad conocida); repetibilidad=precisión in-vivo: no intercambiables", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("'¿Su contribución en una frase?'", "Calidad ósea cortical cuantificable a 0.55 T con cadena reproducible UTE+CS+tri-componente validada multimodal", P + "/Content/1_Abstract.tex"),
 ("'¿El límite más importante?'", "Sin referencia histológica/mecánica directa: el siguiente estudio debe incluir ese eslabón", D + "/Paper-MRI-US/Content/6_Conclusion.tex"),
 ("'¿Errores en mapas de bobina C?'", "Degradación suave de SNR y artefactos: C se estima del centro k sobremuestreado; fantoma acota el residual", P + "/Content/3_Methods.tex"),
 ("'¿Por qué 12 TEs y no 8 o 20?'", "Identificabilidad (CRLB) + tiempo clínico: ~4 puntos/década para 5-7 parámetros sin doblar TR", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("'¿Repetible o reproducible?'", "Reproducible: .seq+código+datos versionados — mismo resultado en manos ajenas", D + "/Paper-MRI-US/Content/6_Conclusion.tex"),
]),
("Vocabulario de Defensa Doctoral", [
 ("Bound water (BW)", "Agua ligada a colágeno-hidroxiapatita de la matriz; T2* ~50–500 µs; proxy de calidad de matriz", C + "/narracion/texto/cap3.txt"),
 ("Pore water (PW)", "Agua en poros de Havers y sistema lacunocanicular; T2* 1–50 ms; proxy de porosidad", C + "/narracion/texto/cap3.txt"),
 ("Ramp sampling", "Muestreo durante la subida del gradiente: trayectoria k no lineal (t²), habilita TE ultracorto", C + "/capitulos/capitulo4.tex"),
 ("Half pulse", "Medio pulso selectivo con gradiente bipolar: dos con polaridad invertida completan el perfil", C + "/narracion/texto/anexo1.txt"),
 ("VERSE", "Variable-Rate Selective Excitation: reparametrización temporal B₁'(t)=B₁(τ)|dτ/dt que conserva el flip", D + "/marco-teorico/bloque-D-pulsos-rf/T21-condicion-verse.md"),
 ("NUFFT", "Non-uniform FFT: transformada en puntos arbitrarios (radial) con regrilling y corrección de densidad", MT + "/bloque-C-fisica-secuencia-ute/T14-trayectoria-radial.md"),
 ("RIP (restricted isometry property)", "E preserva normas de ∇-dispersos — garantía de recuperación ℓ₁", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("US-BDAT", "Bidirectional Ultrasound Axial Transmission: ondas guiadas en corteza tibial (rigidez), comparador emparejado", P + "/Content/3_Methods/3.5_Multimodal_Analysis_US_BDAT.tex"),
 ("Bland-Altman", "Sesgo + límites de acuerdo (±1.96 SD): decide si dos métodos son intercambiables", P + "/Content/3_Methods/3.5_Multimodal_Analysis_US_BDAT.tex"),
 ("AICc", "Criterio de información con corrección de muestra pequeña: verosimilitud penalizada por complejidad", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Dwell time", "Tiempo entre muestras del ADC: cuantiza los puntos k al raster (la NUFFT usa tiempos exactos)", C + "/anexos/anexo2.tex"),
 ("SM-2 (anécdota de estudio)", "Algoritmo de repaso espaciado de las flashcards de esta plataforma: misma idea de intervalos crecientes", D + "/presentacion-especiales/secuencia-ute/guion_secuencia_ute.pdf"),
]),
("Números que Debes Recordar (Defensa)", [
 ("γ del protón", "42.577 MHz/T", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("f₀ a 0.55 T", "≈ 23.4 MHz", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Δf agua-grasa a 0.55 T", "≈ 82 Hz (3.5 ppm × 42.577 × 0.55)", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("Periodo de batido agua-grasa", "1/82 Hz ≈ 12.2 ms", COD + "/api_modelo_tricomponente/src/priors.py"),
 ("TE de la secuencia UTE 2D", "30 µs (del fin de RF a la primera muestra ADC)", C + "/anexos/anexo2.tex"),
 ("T2* típicos: BW / PW / BM", "~0.4 ms / ~4 ms / ~40 ms (separación ~100×)", PS + "/relaxometria/guion_relaxometria.pdf"),
 ("Validación por fantoma", "2.2% (BW) y 0.8% (PW) vs GRE", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Sujetos y TEs", "N=20 · 12 TEs log en 0.03–25 ms", P + "/Content/3_Methods/3.2_Tricomponent_Analysis_Validation.tex"),
 ("Pulso de selección de corte", "Flip 30°, TBW=2, 0.5 ms, corte 10 mm", PS + "/secuencia-ute/scripts/gen_guion.py"),
 ("FOV y resolución", "FOV=180 mm, Nx=500, Δx≈0.9 mm (kmax limitado por G=18 mT/m)", C + "/narracion/texto/anexo1.txt"),
 ("SAR relativo 3 T vs 0.55 T", "(3/0.55)² ≈ 30×", C + "/main.pdf"),
 ("CS del pipeline", "λ=10⁻⁴ · ADMM 50 iter · L-BFGS 10 · cs_factor 0.2–1.0", PS + "/compressed-sensing/guion_compressed_sensing.pdf"),
 ("Spoiling", "RF cuadrático 117° + gradiente al 20% Gmax rotado", C + "/main.pdf"),
 ("BW a 1.5 T (Seifert)", "401 ± 119 µs (PW: 4110 ± 1230 µs)", MT + "/bloque-B-fisica-resonancia-magnetica/T09-relajacion-T2-estrella.md"),
 ("Nyquist radial", "N_r ≥ π·Nx (con Nx=500: 1572 radios ⇒ 786 TRs a 2 radios/TR)", MT + "/bloque-C-fisica-secuencia-ute/T15-nyquist-radial.md"),
]),
]


async def main():
    async with SessionLocal() as db:
        tema = await db.get(Tema, TEMA)
        print(f"tema: {tema.nombre if tema else '??'}")
        existentes = {d.titulo for d in (await db.execute(select(Deck))).scalars().all()}
        hoy = date.today()
        nd = nt = 0
        for titulo, tarjetas in DECKS:
            if titulo in existentes:
                print(f"  = YA EXISTE, omitido: {titulo}")
                continue
            deck = Deck(titulo=titulo, tema_id=TEMA, estado="listo")
            db.add(deck)
            await db.flush()
            for frente, reverso, archivo in tarjetas:
                db.add(Flashcard(
                    deck_id=deck.id, frente=frente, reverso=reverso,
                    cita={"archivo": archivo, "pagina": ""},
                    proxima_repaso=hoy,
                ))
            nd += 1
            nt += len(tarjetas)
            print(f"  + {titulo} ({len(tarjetas)} tarjetas)")
        await db.commit()
        total = (await db.execute(select(Deck))).scalars().all()
        print(f"\nListo: {nd} decks nuevos, {nt} tarjetas. Total en BD: {len(total)} decks")

asyncio.run(main())
