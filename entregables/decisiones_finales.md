# Centinela Agro · Decisiones finales (EDA + ML de grupo + confiabilidad del alcance + ONNX)

Fuente: `salidas/ml_resumen.csv`, `ml_resultados.json`, `ml_confiabilidad.json`, `ml_por_producto.csv`, `ml_calibracion.csv`, `ml_estabilidad_anual.csv`. Walk-forward mensual **2022-01 a 2024-11 (35 orígenes)**, 181 productos de la CMA con 60 meses. Todo se regenera con los comandos de la sección 6.

## 1. Qué cambió frente al plan anterior

1. El EDA con 4 productos daba un resultado negativo. Se pasó a **un modelo de grupo** (acción B del plan).
2. Para mejorar la confiabilidad del alcance se **fijó un protocolo antes de ver resultados**: ventana ampliada de 23 a 35 orígenes (incluye el pico de precios de 2022) y un universo "alcance ampliado" con los 6 productos de los mismos 4 rubros (papa capira + papa nevada, papa criolla, tomate chonto regional + larga vida, cebolla junca). Modelo, hiperparámetros y criterio O3 **no se tocaron**.

| Universo (2022-01 a 2024-11) | n | Exactitud RF | IC95 (bootstrap por mes) | Δ vs "repite última dirección" | IC95 de Δ | ¿Cumple O3? |
|---|---|---|---|---|---|---|
| **181 productos** | 6.335 | 60,4 % | 59,2 – 61,7 | **+4,6 pts** | **+3,2 – +6,1** | **Sí** |
| 6 del alcance ampliado | 210 | 60,0 % | 53,3 – 67,1 | +5,7 pts | −3,3 – +14,8 | No demostrable |
| 4 del alcance | 140 | 60,0 % | 52,9 – 67,1 | +4,3 pts | −4,3 – +12,9 | No demostrable |

Comparación con la ventana anterior (2023-24): 181 productos 59,5 % (Δ +5,4); 4 del alcance 57,6 % (Δ 0,0, IC −12,0 a +10,9). Ampliar la ventana subió el IC inferior de exactitud del alcance por encima de 50 %, pero **el IC de Δ sigue cruzando 0**.

## 2. Veredicto sobre el alcance: no se puede declarar O3 propio, y por qué

- **Es un límite de potencia, no del modelo.** Con 35 meses de prueba el efecto mínimo detectable en los 4 productos es 12,4 pts; el efecto del grupo es 4,6. Harían falta ~257 meses de prueba (~282 con 6 productos). Con 60 meses de historia no se puede llegar ahí; añadir 10 años (acción D) tampoco bastaría solo.
- **No se relajó el criterio.** O3 sigue siendo: IC inferior de exactitud > 50 % **y** IC inferior de Δ > 0.
- **Evidencia complementaria** (definida *después* de ver el resultado, por eso no sustituye a O3):

| Evidencia | Resultado | Lectura |
|---|---|---|
| AUC en los 4 productos | 0,637 (IC95 0,554 – 0,721); en 6: 0,638 (0,565 – 0,715) | Ordena mejor que el azar |
| Alcance vs resto de productos | Δ +5,7 vs +4,6; diferencia +1,2 (IC95 −7,9 a +10,5) | Sin evidencia de que se comporte distinto al grupo (no prueba que sea igual) |
| Calibración (181) | Tramo 0,65–1,0: dice 0,68, sube 0,71. Tramo ≤0,35: dice 0,29, sube 0,27 | Probabilidades confiables en el grupo |
| Estabilidad por año, 4 productos | 2022 +12,5 · 2023 +4,2 · **2024 −4,5** | **Alerta:** la ventaja del alcance vino de 2022-23. En el grupo es positiva los 3 años (+3,1, +4,4, +6,4) |
| Bandas en el alcance ampliado | ALZA 72,7 % (n=11); BAJA 77,8 % (n=18) | n demasiado chico para concluir |

- **Qué sí se puede afirmar:** el modelo cumple O3 en el grupo, el alcance es estadísticamente compatible con el grupo y ordena mejor que el azar. **Qué no:** que supere a "repite" en tomate o cebolla por separado, ni que la ventaja siga vigente en 2024 para el alcance.

## 3. Decisiones

| # | Decisión | Evidencia | Revisión |
|---|---|---|---|
| D1 | **Producto en dos niveles.** Nivel 1: alertas de grupo (181) con la tasa de acierto histórica de su banda. Nivel 2: los 4 productos con estacionalidad + rango 12 meses y la señal del modelo marcada "experimental". | §1 y §2 | Cuando el IC de Δ del alcance excluya 0 |
| D2 | **Modelo canónico: Random Forest solo con precio** (rezagos, media, volatilidad, seno/coseno, índice estacional con solo pasado, grupo). Sin clima, TRM ni producción. | Con variables externas no mejora: RF 59,8 % vs 60,4 % (2022-24) y 58,1 % vs 59,5 % (2023-24) | Reabrir con clima por municipio productor (acción C) |
| D3 | **Bandas 0,65 / 0,35**, mostrando el acierto de la banda. Grupo 2022-24: ALZA 70,6 % (n=671), BAJA 72,9 % (n=373); 83,5 % de los casos "sin señal". | `ml_resultados.json` | Wilson ignora la correlación entre productos del mismo mes: leer como optimista |
| D4 | **Servir el modelo en ONNX** (`modelos/centinela_modelo.onnx`, 1,1 MB). Paridad con sklearn 1,4e-07; el script falla si supera 1e-4. SHA-256 en `centinela_modelo.json`. | `ml_onnx.py` | Re-exportar en cada reentrenamiento |
| D5 | **Papa: mostrar el modelo junto a la regla simple.** Papa capira: "repite" 80,0 % vs RF 65,7 % (n=35, IC se solapan). | `ml_por_producto.csv` | No elegir ganador hasta tener más meses |
| D6 | **Nada se publica sin revisión humana**; el estado del tablero lo fija `estado_alertas` calculado por el código. | Guardarraíles | Cada mes |
| D7 | **El cuaderno `ml/` queda como referencia histórica.** `src/` es canónico. | §4 | — |
| D8 | **La evidencia complementaria no sustituye a O3.** Se publica con esa etiqueta y la alerta de 2024. | §2 | — |
| D9 | **El alcance se "demuestra" hacia adelante:** registrar cada mes la predicción publicada y su resultado (etapa 8) y re-evaluar O3 del alcance cuando haya ≥ 24 meses nuevos fuera de muestra, o cuando se amplíe el histórico (acción D). | Potencia | Cada trimestre |

## 4. Qué NO se reutiliza del cuaderno

| Hallazgo | Acción |
|---|---|
| Token de ngrok en texto plano, 8 veces en el `.ipynb` | **Revocarlo en dashboard.ngrok.com y borrarlo del archivo antes de compartirlo** |
| Celda 23: alertas con probabilidades inventadas | No usar |
| Celdas 75 y 77: importancia de variables escrita a mano | No usar; la importancia debe salir del modelo entrenado |
| ETL propio sobre CSV crudos | Reemplazado por `src/etl.py` (falla si meses ≠ 60) |
| GridSearch y prueba en un solo corte (2024) | Reemplazado por walk-forward con hiperparámetros fijos |
| App Streamlit con 6 versiones y rutas de Colab | Reemplazada por `entregables/tablero_centinela.html` (`src/tablero.py`), que lee `salidas/` y las alertas de ONNX |

## 5. Límites vigentes

1. El resultado positivo es del **grupo**. Por producto, con n=35, ningún intervalo es concluyente (tomate chonto regional: 54,3 %; cebolla junca: 60,0 %).
2. Ventana de prueba de 35 meses y 3 regímenes de precios; el alcance perdió ventaja en 2024.
3. Alertas para 2025-01 en los 4 productos: todas "SIN SEÑAL" (papa capira 0,61; papa criolla 0,54; tomate chonto 0,47; cebolla junca 0,48). En el grupo: 14 ALZA, 8 BAJA, 159 sin señal.
4. "Cumple O3" en el grupo es una condición necesaria, no una garantía de ganancia económica para el productor.

## 6. Reproducir

```
.venv/bin/python src/etl.py              # datos_limpios/ (falla si meses != 60)
.venv/bin/python src/ml_features.py      # datos_limpios/features_grupo.csv
.venv/bin/python src/ml_modelo.py        # walk-forward 2022-24 + modelo canónico (~1 min)
.venv/bin/python src/ml_confiabilidad.py # homogeneidad, AUC, calibración, potencia
.venv/bin/python src/ml_onnx.py          # modelos/*.onnx + salidas/ml_alertas_onnx.csv
.venv/bin/python src/tablero.py          # entregables/tablero_centinela.html
.venv/bin/python src/pipeline_viz.py     # entregables/pipeline_interactivo.html
(cd diseno && ../.venv/bin/python gen.py && figcraft-cli run pantallas.json --out centinela_agro.figcraft)  # pantallas móviles con cifras de salidas/
for n in "M1 Alertas:M1" "M3 Calendario:M3" "M4 Confiabilidad:M4"; do figcraft-cli export diseno/centinela_agro.figcraft -o "diseno/moviles/${n##*:}.png" --node "${n%%:*}" --scale 2; done
.venv/bin/python src/pptx_actualizar.py  # entregables/Centinela_Agro_Pitch.pptx (21 diapositivas, cifras desde salidas/)
```
