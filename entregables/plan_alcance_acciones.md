# Centinela Agro · Plan de análisis, alcance y evaluación de acciones

Base: EDA ejecutado (`entregables/informe_eda.ipynb`), 60 meses (2020-2024), 4 productos en la Central Mayorista de Antioquia (CMA).

---

## 1. Objetivo

**General.** Entregar a productores y compradores de Antioquia una alerta mensual y confiable sobre el precio mayorista de papa, papa criolla, tomate chonto y cebolla junca.

**Específicos (medibles).**

| # | Objetivo | Criterio de éxito |
|---|---|---|
| O1 | Pipeline de datos reproducible y auditado | `src/etl.py` corre de punta a punta; 271.740 filas limpias, 60 meses, 0 nulos en la maestra (cumplido) |
| O2 | Caracterizar estacionalidad y riesgo por producto | Índice estacional y rango histórico publicados por producto (cumplido, ver EDA §4-5) |
| O3 | Evaluar si un modelo anticipa alza/baja a t+1 | Exactitud con IC95 inferior > 50 % **y** mejor que "repite última dirección" en walk-forward (cumplido en el grupo de 181; no demostrable en los 4 productos por falta de potencia, ver `decisiones_finales.md`) |
| O4 | Tablero con alertas y su incertidumbre | Cada alerta muestra probabilidad, base de comparación y exactitud histórica con intervalo (cumplido: `entregables/tablero_centinela.html`) |

---

## 2. Alcance

**Dentro.**
- Mercado: CMA (Medellín). Productos: papa capira, papa criolla limpia, tomate chonto regional, cebolla junca.
- Horizonte: un mes adelante (t+1), clasificación alza/baja y, opcionalmente, % de cambio.
- Fuentes: SIPSA (precios), Open-Meteo (clima, 3 subregiones), TRM, producción agrícola anual de Antioquia.
- Entregables: ETL, EDA (.ipynb + HTML/CSS), sondeo de viabilidad, tablero.

**Fuera (por ahora).**
- Predicción de nivel de precio en pesos, horizontes > 1 mes, otros mercados mayoristas.
- Deep learning (60 puntos por serie no lo justifican).
- Recomendaciones de siembra o venta como "asesoría" (la exactitud actual no lo respalda).

**Supuestos y límites conocidos.**
- Clima: un municipio por subregión; tomate y cebolla se producen sobre todo en suroeste y valle de Aburrá, sin clima en la fuente.
- Producción: anual y de ámbito Antioquia; se usa el dato del año t-1 para evitar fuga.
- Muestra: 60 meses por producto. Con 4 productos y 35 meses de prueba el IC95 de la ventaja sobre "repite" mide ~17 pts; por eso el modelo se valida como grupo de 181 productos.
- Origen de los datos: Excel con corrupciones de fecha y escala; la corrección es determinista y está auditada, pero depende de la mediana 2020-21 como referencia.

---

## 3. Plan de análisis de datos con ML

| Fase | Qué se hace | Herramienta | Estado |
|---|---|---|---|
| 1. Ingesta y limpieza | Corregir fechas y escala, deduplicar, agregar a mensual | pandas (`src/etl.py`) | Hecho |
| 2. Maestra mensual | Unir precio + clima ponderado por producción + TRM + producción t-1 | pandas | Hecho (240 filas) |
| 3. EDA | Calidad, series, STL, ACF, Spearman, balance de clases | statsmodels, scipy, seaborn | Hecho |
| 4. Sondeo de viabilidad | Walk-forward 2023-01 a 2024-11 con los 4 productos | scikit-learn | Hecho, resultado negativo (n=92) |
| 5. Ingeniería de variables | Rezagos de retorno, media móvil, volatilidad, seno/coseno del mes, **índice estacional con solo pasado**, grupo | pandas (`src/ml_features.py`) | Hecho |
| 6. Modelado ampliado | Un modelo por **grupo** (181 productos con 60 meses): logística, Random Forest, HistGB. Canónico: RF solo precio | scikit-learn (`src/ml_modelo.py`) | Hecho |
| 7. Validación | Walk-forward 2022-01 a 2024-11 (35 orígenes), ventana expansiva, hiperparámetros fijos, sin fuga | código propio | Hecho |
| 8. Evaluación | IC95 por bootstrap de meses, Wilson, McNemar, F1, AUC; O3 calculado por código; bases: repite, mayoritaria, estacional | scikit-learn, statsmodels | Hecho: grupo cumple O3 (60,4 %, Δ +4,6, IC +3,2 a +6,1) |
| 9. Confiabilidad del alcance | Homogeneidad alcance vs grupo, AUC, estabilidad por año, calibración, potencia | `src/ml_confiabilidad.py` | Hecho: O3 propio no demostrable (harían falta ~257 meses de prueba) |
| 10. Despliegue | Modelo en ONNX + alertas con onnxruntime + tablero HTML | skl2onnx, onnxruntime (`src/ml_onnx.py`, `src/tablero.py`) | Parcial: falta API y mensajería |

**Reglas de validez (no negociables).**
1. Toda variable usa solo información disponible al cierre del mes t.
2. Se compara siempre contra: clase mayoritaria y "repite última dirección".
3. Se reporta el IC95 junto a la exactitud. Una mejora cuyo IC incluye la base no cuenta como mejora.
4. Las correlaciones del EDA son hipótesis: 11 de 56 salieron significativas y por azar se esperarían ~3.

---

## 4. Qué dijeron los datos (resumen del EDA)

| Hallazgo | Número |
|---|---|
| Fechas corregidas | 11 → 60 meses distintos |
| Precios reescalados ×1000 | 154.433 filas |
| Productos con los 60 meses completos | 181 de 220 en la CMA |
| Estacionalidad (STL) | papa capira 0.62, papa criolla 0.57, cebolla 0.33, tomate 0.17 |
| Memoria (ACF rezago 1) | papa capira 0.32, papa criolla 0.29, cebolla −0.02, tomate −0.12 |
| Sondeo con 4 productos (n=92) | RF 62,0 % (IC95 51,7–71,2) vs "repite" 57,6 %: no concluyente |
| Modelo de grupo, 181 productos (n=6.335) | RF solo precio 60,4 % vs "repite" 55,8 %: Δ +4,6 pts (IC95 +3,2 a +6,1) |
| Los 4 productos con el modelo de grupo (n=140) | 60,0 %, Δ +4,3 (IC95 −4,3 a +12,9): no demostrable |
| Efecto de añadir clima + TRM + producción | no mejora: RF 59,8 % vs 60,4 % |

**Conclusión:** el modelo de grupo supera a la regla simple y sus probabilidades están calibradas. En los 4 productos el efecto es del mismo tamaño pero el intervalo no excluye 0 (potencia insuficiente) y en 2024 el alcance perdió ventaja (−4,5 pts). La estacionalidad de la papa sigue respaldada. Producto en dos niveles: alertas de grupo con su acierto histórico y, para los 4 productos, estacionalidad + rango con la señal marcada experimental.

---

## 5. Evaluación de acciones posibles

Ordenadas por recomendación.

| # | Acción | Esfuerzo | Riesgo | Valor | Veredicto |
|---|---|---|---|---|---|
| **A** | **Reposicionar a "alerta estacional + rango histórico"** y mostrar el modelo solo como experimental con su IC | 1-2 semanas | Bajo | Alto: se apoya en lo que los datos sí sostienen | **Hecha** (nivel 2 del tablero) |
| **B** | **Modelo por grupo de productos** (181 series × 60 meses) y evaluar en los 4 del alcance | 2-3 semanas | Medio | Medio-alto: multiplica la muestra ~45 veces | **Hecha**: cumple O3 en el grupo |
| C | Mejorar clima: datos por municipio productor (suroeste, valle de Aburrá) y producción mensual | 3-4 semanas + gestión de datos | Medio | Medio: hoy el clima no aporta señal; quizá es falta de cobertura y no de efecto | Condicionada a B |
| D | Ampliar el histórico (SIPSA desde 2013 o más) | 2-4 semanas | Bajo | Alto: más años → IC más estrecho | Muy recomendable si la fuente existe |
| E | Lanzar el tablero tal cual prometiendo exactitud de alza/baja | 1 semana | **Alto** (reputacional) | Bajo | No recomendada |

**Secuencia sugerida.** A (entregable inmediato) → B y D en paralelo → C solo si B muestra señal → decidir con el criterio O3.

**Punto de decisión (resuelto).** B cumple O3 en el grupo y no en los 4 productos. Se publica en dos niveles (D1). El alcance se demuestra hacia adelante: registrar cada mes predicción y resultado y re-evaluar O3 con ≥ 24 meses nuevos fuera de muestra o con histórico ampliado (D9). D sigue siendo muy recomendable pero por sí sola no basta (~257 meses de prueba necesarios).

---

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Resultado débil en el alcance | Nivel 2 entrega estacionalidad y rango sin depender del modelo; la señal va marcada experimental |
| Corrupción del Excel reaparece en datos nuevos | `src/etl.py` registra QA en `salidas/etl_log.json` y **falla si los meses ≠ 60** (hecho) |
| Fuga temporal | Reglas de validez 1 y 2; walk-forward obligatorio |
| Sobreajuste por muestra pequeña | Modelo de grupo, hiperparámetros fijos (`max_depth=8`, `min_samples_leaf=30`), sin GridSearch sobre el periodo evaluado, IC95 por bootstrap de meses |
| Relajar el criterio cuando el alcance no pasa | O3 no cambia; la evidencia complementaria se etiqueta aparte (D8) |
| Token de ngrok expuesto en `ml/Centinela_Agro_Notebook.ipynb` | Revocarlo y borrarlo antes de compartir el cuaderno |
| Dos pipelines en el repo (`analisis/` y `src/`) | Verificado: coinciden en 271.740 filas; `src/` queda como canónico y `analisis/` como histórico |

---

## 7. Reproducir

```
.venv/bin/python src/etl.py              # datos_limpios/ + salidas/etl_log.json
.venv/bin/python src/eda.py              # salidas/figuras/ + eda_stats.json (~80 s)
.venv/bin/python src/informe.py          # entregables/informe_eda.{ipynb,html,css}
.venv/bin/python src/ml_features.py      # datos_limpios/features_grupo.csv
.venv/bin/python src/ml_modelo.py        # walk-forward 2022-24 + modelo canónico (~1 min)
.venv/bin/python src/ml_confiabilidad.py # confiabilidad del alcance
.venv/bin/python src/ml_onnx.py          # modelos/*.onnx + alertas con onnxruntime
.venv/bin/python src/tablero.py          # entregables/tablero_centinela.html
.venv/bin/python src/pipeline_viz.py     # entregables/pipeline_interactivo.html

Decisiones finales: `entregables/decisiones_finales.md`.
```
