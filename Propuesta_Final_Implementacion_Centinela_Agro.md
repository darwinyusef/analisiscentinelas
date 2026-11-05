# Propuesta final de implementación — Centinela Agro

Versión 1.1 · 2026-11-04 · Reemplaza a `Propuesta_Tecnica_Centinela_Agro.md` (v0.1).
Compañera de `Propuesta_Gerencial_Centinela_Agro.md`. Los números del modelo salen de `analisis/resultados/` (incl. `datos_tablero.json`); los de datos y EDA, de `entregables/` y `salidas/` (EDA cerrado).

**Fuentes de verdad.** Pipeline de datos canónico: `src/etl.py` (`analisis/` es histórico; ambos coinciden en 271.740 filas y 60 meses). Alcance: 4 productos (papa capira, papa criolla limpia, tomate chonto regional, cebolla junca; maestra de 240 filas). Modelo: panel de 181 productos con 60 meses (10.863 filas), evaluado en los 4 del alcance.
**Diseño móvil:** `diseno/centinela_agro.figcraft` (marcos M1–M5, D1, sistema de diseño), generado por `diseno/gen.py` desde `datos_tablero.json`.

## 1. Objetivo refactorizado

| Antes (v0.1) | Ahora |
|---|---|
| Predecir precio del próximo mes con clima, dólar y producción | **Clasificar la dirección** del precio del próximo mes (sube / baja) + **calendario estacional** |
| Modelo global con clima y TRM | Modelo global con **historia de precio + patrón estacional + grupo** |
| Éxito: superar "igual al mes pasado" en 2024 | Éxito: superar los baselines en walk-forward 2022–24 con IC 95 % (cumplido: 58,9 % vs 55,8 %) |

Por qué: clima y dólar no mejoraron el modelo (57,8 % con clima vs 58,2 % sin él) y el modelo de nivel de precio no superó la regla ingenua (MAPE 2024: 9,84 % vs 9,97 %, y peor en MAE).

## 2. Arquitectura

```
SIPSA (xlsx/API) ─► ETL Python ─► SQL Server (staging → dims/facts) ─► vw_maestra_mensual
TRM · Clima (contexto)                                                      │
                                                  ┌─────────────────────────┤
                                                  ▼                         ▼
                                     Entrenamiento (sklearn)        Calendario estacional
                                     RF clasificador + joblib       (índices por mes)
                                                  └───────────┬─────────────┘
                                                              ▼
                                                     API FastAPI (/v1)
                                                  ┌───────────┴───────────┐
                                                  ▼                       ▼
                                          App móvil (MVP)          Tablero Streamlit
```

| Capa | Decisión |
|---|---|
| Base | SQL Server |
| ETL | Python + pandas + SQLAlchemy/pyodbc, con pruebas pytest |
| Modelo | scikit-learn RandomForestClassifier |
| API | FastAPI + Pydantic |
| App móvil | React Native (Expo) o Flutter — decisión del equipo en semana 1 |
| Tablero | Streamlit (interno) |
| Despliegue | Docker; cron/Azure Function mensual para reentrenar |

## 3. ETL (código ya validado en `analisis/etl.py` y `analisis/etl_aux.py`)

Reglas que **deben** pasar a producción y tener prueba automática:

1. **Mes**: para 2020–21 el mes está en `datetime.day`; para 2022–24 viene como texto (mapa `MES`) o `datetime.month`. El año sale del nombre del archivo `informe`, no de la celda.
2. **Escala de precio**: si `anio >= 2022` y (`precio < 100` o (`precio < 1000` y tiene decimales)) entonces `precio × 1000`.
3. **Mercado**: filtrar "Medellín, Central Mayorista de Antioquia".
4. **Deduplicación**: algunos productos aparecen en dos grupos (p. ej. arveja enlatada). Dejar una fila por `producto × mes` con prioridad definida en `dim_producto`.
5. **Clima**: promedio diario→mensual de las 3 subregiones. **TRM**: expandir rangos de vigencia a diario, luego mensual.

Pruebas mínimas (`tests/test_etl.py`):

| Prueba | Criterio |
|---|---|
| Mes 2020–21 | 12 meses únicos por año |
| Continuidad de escala | abs(ln(precio ene-22 / precio dic-21)) < 0,7 para papa, tomate y cebolla |
| Sin duplicados | `producto × mes` único en la vista maestra |
| Cobertura | 60 meses por producto clave (4) |
| Guardia de carga | `assert` que falla si los meses distintos ≠ 60 (pendiente en `src/etl.py`; registra QA en `salidas/etl_log.json`) |

## 4. Esquema SQL Server

```sql
-- staging: crudo, sin tocar
stg_sipsa(fila_id, archivo, hoja, fecha_raw, grupo, producto, mercado, precio_raw)
stg_trm(vigencia_desde, vigencia_hasta, valor)
stg_clima(fecha, subregion, municipio_ref, temp_media, temp_max, temp_min, precipitacion, et0)
stg_produccion(rubro, subregion, anio, area, volumen)

-- limpio
dim_producto(producto_id PK, nombre_normalizado, grupo, es_clave BIT)
fact_precio_mes(mes DATE, producto_id, precio_kg, PRIMARY KEY(mes, producto_id))
fact_contexto_mes(mes DATE PK, trm_promedio, lluvia_prom, temp_prom)   -- solo contexto
fact_produccion_anio(anio, rubro, subregion, area, volumen)

-- predicciones
modelo_version(version_id PK, entrenado_en, accuracy_wf, ic_inf, ic_sup, ruta_joblib)
fact_prediccion(mes_objetivo DATE, producto_id, version_id, p_alza FLOAT, alerta VARCHAR(20),
                PRIMARY KEY(mes_objetivo, producto_id, version_id))
```

Vista `vw_maestra_mensual`: una fila por `mes × producto` con `precio`, `ret` (log-retorno), `ret_l1..l3`, `r_ma3`, `r_ma6`, `vol3`, `sin`, `cos`, `esp`, dummies de grupo y `y`.

## 5. Modelo (refactor de `analisis/06_estacional.py` + `08_final.py`)

**Objetivo**: `y = 1` si `precio(t+1) > precio(t)`.

**Features** (3 familias; importancia: 71 % historia, 24 % estacionalidad, 5 % grupo):

| Feature | Definición |
|---|---|
| `ret_l1..l3` | Log-retornos de los últimos 3 meses |
| `r_ma3`, `r_ma6` | Medias móviles del retorno |
| `vol3` | Volatilidad a 3 meses |
| `sin`, `cos` | Mes como ciclo |
| `esp` | Retorno esperado del mes objetivo, leave-one-out, suavizado hacia la media mensual (k=2) |
| `g_*` | Grupo del producto |

**Se eliminan** de producción: clima y TRM como features. Se conservan en la base como contexto de la pantalla "Factores".

**Hiperparámetros**: `RandomForestClassifier(n_estimators=500, min_samples_leaf=8, max_features='sqrt', random_state=42)`.

**Umbrales de alerta** (calibrados en `robustez.json`):

| p_alza | Alerta | Acierto histórico |
|---|---|---|
| > 0,60 | ALZA PROBABLE | 62,6 % sube |
| ≤ 0,40 | BAJA PROBABLE | 63,5 % baja |
| resto | SIN SEÑAL CLARA | — |

**Calendario estacional**: índice mensual por producto (precio del mes / media anual), tabla `estacionalidad` de `datos_tablero.json`.

**Reentrenamiento (walk-forward)**:

1. Cada mes, cuando SIPSA publica: ETL → `fact_precio_mes`.
2. Entrenar con todo el histórico excepto el último mes; evaluar en el último mes (nuevo punto walk-forward).
3. Guardar `modelo_version` con la exactitud acumulada.
4. Si la exactitud móvil de 12 meses baja de 52 % (casi azar), la app muestra aviso "modelo en revisión" y solo el calendario.

**Compuerta de calidad** para publicar un modelo nuevo: exactitud walk-forward ≥ baseline momentum + 1 punto; si no, se mantiene el anterior.

## 6. API (FastAPI)

| Endpoint | Devuelve |
|---|---|
| `GET /v1/productos` | Los 4 productos clave + los 181 con bandera `es_clave` |
| `GET /v1/alertas` | Lista: producto, último precio, variación mes, `p_alza`, `alerta`, mes objetivo |
| `GET /v1/precios?producto=&desde=&hasta=` | Serie mensual |
| `GET /v1/estacionalidad?producto=` | Índice por mes, mes más caro/barato |
| `GET /v1/modelo/confiabilidad` | Exactitud por año, vs baselines, IC, calibración y `por_producto` (n, `acc_modelo`, `acc_repite_direccion`) |
| `GET /v1/datos/info` | Fuentes, periodo, fecha de última actualización, versión del modelo |

Ejemplo de respuesta `/v1/alertas` (enero 2025, datos reales):

```json
[
 {"producto":"Papa capira","precio_kg":2349,"var_mes":-0.005,"p_alza":0.658,"alerta":"ALZA PROBABLE"},
 {"producto":"Papa criolla","precio_kg":1996,"p_alza":0.538,"alerta":"SIN SEÑAL CLARA"},
 {"producto":"Tomate chonto","precio_kg":3163,"var_mes":0.263,"p_alza":0.499,"alerta":"SIN SEÑAL CLARA"},
 {"producto":"Cebolla junca","precio_kg":3318,"var_mes":0.098,"p_alza":0.556,"alerta":"SIN SEÑAL CLARA"}
]
```

`var_mes` de papa criolla: tomarlo de `pred_ene2025` en `datos_tablero.json` (campo `var_mes`).

## 7. App móvil — pantallas (ver Figma, marcos "M1…M5")

| # | Pantalla | Contenido |
|---|---|---|
| M1 | Alertas | 4 tarjetas con precio, probabilidad, flecha, texto de alerta; nota 58,9 % (IC95 57,5–60,3 %) vs 55,8 % |
| M2 | Detalle de producto | Barras de precio (24 meses), alerta, "meses caros/baratos", fuerza estacional STL, aviso por producto (en papa capira la regla simple gana 80,6 % vs 63,9 %) |
| M3 | Calendario | Mapa de calor 12 meses × 4 productos + fuerza STL (papa fiable, cebolla moderada, tomate débil) |
| M4 | Confiabilidad | 58,9 % vs baselines, calibración, tabla por producto (36 meses, ±16 pp), aviso de límites |
| M5 | Acerca de los datos | Fuentes, periodo, rezago, clima de 3 municipios sin cobertura de suroeste/valle de Aburrá |

Mapeo pantalla → endpoint: M1 `/alertas`; M2 `/precios` + `/estacionalidad` + `/modelo/confiabilidad` (`por_producto`); M3 `/estacionalidad`; M4 `/modelo/confiabilidad`; M5 `/datos/info`.

Accesibilidad: la alerta nunca depende solo del color (flecha + texto + color). Tamaño mínimo de toque 44 px.

## 8. Plan (8 semanas)

| Semana | Entrega | Criterio de aceptación | Responsables |
|---|---|---|---|
| 1 | Medir rezago DANE, decidir stack móvil, pytest del ETL | 4 pruebas de la sección 3 pasan | Camilo, María P |
| 2 | Carga a SQL Server | `fact_precio_mes` = 181 × 60, sin duplicados | Camilo |
| 3–4 | `vw_maestra_mensual`, `/precios`, `/estacionalidad` | Endpoints responden con datos reales | María P |
| 4 | Pipeline de entrenamiento + compuerta de calidad | Reproduce 58,9 % ± 0,5 | Pipe, Alex |
| 5 | `/alertas`, `/modelo/confiabilidad` | Coincide con `datos_tablero.json` | Alex |
| 6–7 | App móvil M1–M5 conectada | Flujo completo en dispositivo real | Daniel |
| 8 | Demo desplegada, informe, presentación | Enlace público | Todos |

## 9. Riesgos técnicos

| Riesgo | Mitigación |
|---|---|
| Rezago de publicación de DANE | Medirlo en semana 1; ajustar el texto "próximo mes" |
| Datos solo hasta dic-2024 | Fijar "datos hasta" en `/datos/info`; conseguir SIPSA 2025 |
| Deriva del modelo | Exactitud móvil de 12 meses y aviso automático |
| Excel vuelve a dañar fechas/precios | Pruebas de continuidad de escala en cada carga |
| Ventaja no probada por producto | Mostrar exactitud por producto en M4 |

## 10. Preguntas abiertas

**Punto de decisión (criterio O3 del plan de alcance):** si tras ampliar el histórico (acción D, SIPSA desde 2013) y mejorar el clima por municipio productor (acción C) el IC95 inferior sigue ≤ 50 % o no supera a "repite última dirección", el producto se queda en alerta estacional y no promete predicción.

1. ¿Unidad de producción (toneladas)? Solo afecta el contexto.
2. ¿Cómo deduplicar productos listados en dos grupos (prioridad en `dim_producto`)?
2. ¿React Native o Flutter? Decidir en semana 1.
3. ¿Dónde se publica la demo?
