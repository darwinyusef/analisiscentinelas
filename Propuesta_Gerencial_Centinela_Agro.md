# Propuesta gerencial — Centinela Agro

Versión 1.1 · 2026-11-04 · Base: análisis reales en `analisis/resultados/` (modelo) y `entregables/informe_eda.html` + `entregables/plan_alcance_acciones.md` (EDA cerrado por el agente 5). 181 productos × 60 meses, 2020–2024, Central Mayorista de Antioquia. Ambos análisis se hicieron por separado y coinciden en datos y estacionalidad.

## 1. Decisión que se solicita

Aprobar el desarrollo de una **app móvil de alertas de dirección de precio + calendario estacional** para los 4 productos del alcance: papa capira, papa criolla limpia, tomate chonto regional y cebolla junca. Es la "Acción A" del plan de alcance del EDA (reposicionar a alerta estacional con el modelo mostrado con su incertidumbre), reforzada con el modelo por grupo de 181 productos (acción B), que ya se ejecutó.

El objetivo original era "predecir el precio del próximo mes". El análisis mostró que eso **no es demostrable** con los datos disponibles. Lo que sí es demostrable es decir si el precio **probablemente sube o baja**, y cuándo suele estar caro o barato. El ML se mantiene como motor central, con un objetivo más claro.

## 2. Qué se puede y qué no se puede prometer

| Se puede prometer (demostrado) | No se debe prometer (no demostrado) |
|---|---|
| Alerta de dirección: acierta 58,9 % (IC95 57,5–60,3 %) vs 55,8 % de la mejor regla simple, sobre 181 productos | Precio exacto del mes siguiente (el modelo de nivel no supera la regla "igual al mes pasado") |
| Calendario: en qué mes cada producto suele ser más caro o más barato (fiable en papa; moderado en cebolla; débil en tomate) | Explicar el precio con clima o dólar (correlaciones débiles; no mejoran el modelo) |
| Una ventaja del modelo en el conjunto de productos | Una ventaja demostrada producto por producto (36 meses cada uno; margen de error ±16 puntos) |
| Cuando el modelo está seguro (>60 %), acierta 62,6 % | Certeza en una alerta individual (el sistema acierta 6 de cada 10) |
| Cuando avisa baja (≤40 %), acierta 63,5 % | Cobertura de todos los productos con la misma calidad |

## 3. Los 5 objetivos del proyecto frente a los resultados

| # | Objetivo | Estado | Resultado |
|---|---|---|---|
| 1 | Cargar datos a SQL Server | Parcial | ETL listo y auditado (`src/etl.py`, canónico; 271.740 filas limpias, 60 meses, 0 nulos en la maestra de 4 productos); falta la carga a SQL Server |
| 2 | Tabla maestra mensual | Hecho | 240 filas del alcance (4 × 60, EDA) y 10.863 filas del panel de 181 productos (modelo) |
| 3 | Análisis exploratorio | Hecho | Informe EDA cerrado (`entregables/informe_eda.html`); estacionalidad clara en papa; clima y dólar sin poder predictivo |
| 4 | Modelo predictivo | Parcial | Clasificador de dirección supera los baselines en el panel de 181; por producto no es concluyente; el modelo de nivel de precio no supera la regla simple |
| 5 | Tablero / app | Pendiente | Diseño listo en Figma (móvil M1–M5 + tablero web); falta desarrollo |

## 4. Hallazgos que cambian el proyecto

1. **Nombres de producto.** En el Central Mayorista no existe "papa parda pastusa" ni "tomate chonto" tal cual. Los productos reales del alcance son **papa capira, papa criolla limpia, tomate chonto regional y cebolla junca**. Hay que confirmarlo con el equipo.
2. **Datos dañados por Excel.** Las fechas de 2020–2024 venían corrompidas (el mes quedó en el campo del día) y desde 2022 los precios perdieron el separador de miles (`1.387` = 1387). Se corrigieron con reglas validadas contra la continuidad de la serie (dic-2021 vs ene-2022). Sin esta corrección todo análisis habría sido incorrecto.
3. **Estacionalidad: sólida en papa, moderada en cebolla, débil en tomate.** Dos mediciones independientes coinciden en los meses extremos; difieren en cuánta fe darles.

| Producto | Mes más caro | Mes más barato | Fuerza estacional (STL, 0–1) | Memoria del mes anterior (ACF) |
|---|---|---|---|---|
| Papa capira | Marzo (1,19) | Septiembre (0,81) | **0,62** | 0,32 |
| Papa criolla limpia | Abril (1,29) | Enero (0,79) | **0,57** | 0,29 |
| Cebolla junca | Diciembre (1,21) | Mayo (0,85) | 0,33 | −0,02 |
| Tomate chonto regional | Diciembre (1,27) | Julio (0,75) | 0,17 | −0,12 |

Lectura: la papa es predecible por calendario e inercia (si bajó, suele seguir bajando). Tomate y cebolla tienen picos claros pero mucho ruido alrededor; el calendario es una guía, no una regla.

4. **Clima y dólar no predicen (con la cobertura actual).** Correlaciones con el cambio de precio entre −0,19 y 0,30, inestables entre productos. Agregar clima o dólar no mejora la exactitud (57,8 % con clima vs 58,2 % sin él). El sondeo del EDA lo confirma con otro clima: ponderado por producción de cada rubro y con producción del año anterior, empeora (RF 55,4 %, logística 50,0 %). Matiz importante: el clima disponible son 3 municipios y no cubre suroeste ni valle de Aburrá, donde se produce tomate y cebolla. "No aporta" puede ser falta de cobertura, no ausencia de efecto (acción C del plan, condicionada).
5. **Producción anual** (toneladas, Antioquia) sirve solo como contexto: papa 227 mil t en 2024, tomate 22 mil t, cebolla 17 mil t (en descenso desde 2019).

## 5. Calidad del modelo de dirección

Validación temporal (entrena con el pasado, prueba en el futuro, sin mezclar fechas). Se prueba en 2022, 2023 y 2024.

| Modelo | Exactitud 2022–24 |
|---|---|
| **Random Forest (precio + estacionalidad)** | **58,9 %** |
| Regla estacional | 57,4 % |
| Regla "sube si subió el mes pasado" | 55,8 % |
| Siempre "sube" (clase mayoritaria) | 53,7 % |

- El RF supera a la regla de momentum por 1,4 a 4,9 puntos (intervalo de confianza 95 %, bootstrap por mes) y a "siempre sube" por 3,2 a 7,4 puntos.
- Gana en los tres años: 61,2 % (2022), 56,9 % (2023), 58,7 % (2024).
- La ventaja es **modesta pero consistente**. No es un oráculo.

**Calibración de las alertas** (cuando el modelo dice X, qué pasa realmente):

| Señal del modelo | Casos | Sube realmente |
|---|---|---|
| Alza probable (>60 %) | 2.787 | 62,6 % |
| 50–60 % | 1.617 | 53,6 % |
| 40–50 % | 1.312 | 45,2 % |
| Baja probable (≤40 %) | 803 | 36,5 % (baja 63,5 %) |

- La diferencia contra la regla de momentum es significativa en el conjunto (McNemar p = 1,5e-5; 6.519 predicciones de prueba).

**Limitación importante:** en los 4 productos del alcance, con solo 36 meses de prueba cada uno (±16 puntos), el modelo no gana de forma clara producto por producto:

| Producto | Modelo | Regla "repite dirección" |
|---|---|---|
| Papa capira | 63,9 % | **80,6 %** |
| Papa criolla limpia | 55,6 % | 61,1 % |
| Tomate chonto regional | 55,6 % | 38,9 % |
| Cebolla junca | 58,3 % | 44,4 % |

La ventaja se sostiene en el conjunto de 181 productos, no en cada uno. En papa (con inercia) la regla simple gana: la app lo dice y remite al calendario.

**Contraste conservador del EDA (agente 5).** El sondeo de viabilidad sobre solo los 4 productos (92 meses de prueba) dio RF 62,0 % (IC95 51,7–71,2) vs 57,6 % de "repite dirección" (IC95 47,4–67,2): los intervalos se solapan, no concluyente. Con 4 series la muestra no alcanza; por eso el modelo se entrena por grupo con 181 productos. Ambos resultados son coherentes: ventaja modesta, demostrable solo en conjunto.

## 6. Demostración con datos reales (alerta para enero 2025)

| Producto | Último precio (dic-2024) | Prob. de alza | Alerta |
|---|---|---|---|
| Papa capira | $2.349/kg | 65,8 % | Alza probable |
| Papa criolla limpia | $1.996/kg | 53,8 % | Sin señal clara |
| Tomate chonto regional | $3.163/kg | 49,9 % | Sin señal clara |
| Cebolla junca | $3.318/kg | 55,6 % | Sin señal clara |

De los 181 productos: 68 con alza probable, 20 con baja probable, 93 sin señal clara. Decir "sin señal clara" en la mitad de los casos es **una virtud**: la app no inventa certezas.

## 7. Qué recibe el negocio

1. App móvil con 4 alertas (papa capira, papa criolla, tomate, cebolla) y semáforo con flecha y texto.
2. Calendario estacional: "este mes suele estar caro/barato".
3. Pantalla de confiabilidad: cuánto ha acertado el modelo y sus límites.
4. Pipeline que se reentrena solo con cada publicación nueva de SIPSA.
5. Documentación y diseño listos para el equipo de desarrollo.

## 8. Plan (8 semanas) y responsables

| Semana | Entrega | Responsables |
|---|---|---|
| 1–2 | Carga a SQL Server, esquema, pruebas del ETL | Camilo, María P |
| 3–4 | Tabla maestra deduplicada, API de precios | María P, Camilo |
| 3–4 | Diseño móvil validado con usuarios | Daniel |
| 5 | Pipeline de entrenamiento y reentrenamiento | Pipe, Alex |
| 6–7 | API de predicción + app conectada | Alex, Daniel |
| 8 | Despliegue de demo, informe, presentación | Todos |

## 9. Riesgos

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Rezago de publicación de DANE | El "mes de anticipación" puede ser menor en la práctica | Medir el rezago real en semana 1; si es mayor a 2 semanas, comunicar "próximos 30 días" |
| Datos solo hasta dic-2024 | Predicción demostrativa, no operativa | Mostrar "datos hasta dic-2024" y conseguir SIPSA 2025 |
| Ventaja modesta (≈3 puntos sobre la mejor regla) | Usuarios esperan más | Mensaje claro: dirección y probabilidad, no certeza |
| Ventaja no probada por producto | Alerta de tomate poco confiable | Mostrar la métrica por producto en la app |
| Clima de solo 3 municipios | Representatividad limitada | Declararlo en "Acerca de los datos" |

## 10. Decisiones gerenciales requeridas

1. Aprobar el replanteamiento: de "precio exacto" a "alerta de dirección + calendario".
2. Confirmar los 4 productos reales (papa capira, papa criolla limpia, tomate chonto regional, cebolla junca).
3. Confirmar app móvil (primero) y tablero web (después) y el uso de Streamlit para el MVP del tablero.
4. Asignar responsable para obtener SIPSA 2025 y medir el rezago de publicación.

## Anexo — figuras

`analisis/figuras/f1_precios_estacionalidad.png`, `f2_correlaciones.png`, `f3_modelos.png`, `f4_importancia.png`.
