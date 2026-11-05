> **Reemplazada** por `Propuesta_Final_Implementacion_Centinela_Agro.md` (v1.1) y `Propuesta_Gerencial_Centinela_Agro.md` (v1.1). Se conserva solo como historia; su alcance (3 productos, clima/TRM como features) ya no aplica.

# Propuesta técnica — App Centinela Agro

Versión 0.1 · 2026-11-04 · Base: `Centinela_Agro_Documento_con_Tablero.pdf` + 3 Excel del proyecto.

## 1. Objetivo de la app

Decir, con un mes de anticipación, si el precio mayorista de **papa, tomate chonto y cebolla junca** en la Central Mayorista de Antioquia **sube o baja**, y mostrarlo con alertas simples.

Usuarios: productores, comerciantes, consumidores de Antioquia.
Criterio de éxito: el modelo supera la regla base "precio del próximo mes = precio de este mes" en 2024 (año de prueba).

## 2. Hallazgos sobre los datos (verificados en los Excel)

| Archivo | Contenido | Observación |
|---|---|---|
| `precios_sipsa_modificado.xlsx` | Hojas `precios_sipsa_1` (2020–23) y `precios_sipsa_2` (2024) | 2024 trae `codigo_cpc_ac` extra y precios con punto de miles (`1.387` = 1387). Fechas en dos formatos (`2020-01-01` y `ene-24`). |
| `clima.xlsx` | Diario, por `subregion` + `municipio_ref` | Temp. media/máx/mín, precipitación, ET0. Hay que agregar a mes y recortar a 2024. |
| `proyecto agro.xlsx` | `Hoja2` = TRM (valor, vigencia_desde/hasta); `Hoja3` = producción (rubro, subregión, año, área, volumen) | TRM cubre rangos de días: expandir a diario y promediar por mes. Producción es anual, no mensual. |

Riesgo principal: ~60 meses por producto. Entrenar un modelo global con todos los productos y una variable categórica `producto`.

## 3. Arquitectura

```
Fuentes abiertas ──► Ingesta (Python) ──► Staging SQL Server ──► ETL/limpieza
 SIPSA · TRM · Open-Meteo · Producción                              │
                                                                    ▼
                     Vista maestra mensual  (mes × producto)  ◄── SQL Server
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
         Entrenamiento (scikit-learn)    EDA (notebooks)
                  │ modelo .joblib + métricas
                  ▼
         API REST (FastAPI)  ──►  App web (Streamlit o React)
```

### Stack recomendado

| Capa | Elección | Por qué |
|---|---|---|
| Base de datos | SQL Server (ya definido) | Requisito del equipo. |
| ETL | Python + pandas + SQLAlchemy/pyodbc | Reproducible, un notebook por fuente. |
| Modelo | scikit-learn: baseline vs Random Forest (+ opcional LightGBM) | Pocos datos; evita deep learning. |
| API | FastAPI | Contrato claro entre modelo y tablero. |
| App | **Streamlit** (MVP, 8 semanas) → React si hay tiempo | Daniel entrega tablero sin montar frontend completo. |
| Gráficos | Plotly | Interactivo, funciona en Streamlit y React. |
| Despliegue | Docker + Streamlit Community Cloud / Azure | Demo pública con un enlace. |

## 4. Modelo de datos

**Staging**: `stg_sipsa`, `stg_trm`, `stg_clima`, `stg_produccion` (datos crudos, sin tocar).

**Limpias**:
- `dim_producto(producto_id, nombre_normalizado, grupo)`: agrupa variedades (decisión pendiente del equipo).
- `fact_precio_mes(mes, producto_id, precio_kg)`
- `fact_clima_mes(mes, subregion, temp_media, lluvia_total, et0)`
- `fact_trm_mes(mes, trm_promedio)`
- `fact_produccion_anio(anio, rubro, subregion, area, volumen)`

**Vista maestra** `vw_maestra_mensual`: una fila por `mes × producto` con precio, rezagos (t-1, t-2, t-3), lluvia, temperatura, TRM, variación de TRM, volumen de producción del año, mes (estacionalidad).

## 5. Modelo predictivo

- **Variable objetivo**: `sube = 1 si precio(t+1) > precio(t)`, si no 0 (clasificación). Opcional: regresión del % de cambio.
- **Features**: rezagos de precio, medias móviles 3 y 6 meses, lluvia acumulada con rezago 1–3 meses, TRM, mes, producto.
- **Validación**: temporal. Entrenar 2020–2023, probar 2024. Sin mezcla aleatoria, para no filtrar el futuro.
- **Baseline**: "igual al mes anterior" (y "sube si subió el mes pasado").
- **Métricas**: accuracy, F1, matriz de confusión; MAE si hay regresión. Reportar siempre contra el baseline.
- **Salida**: probabilidad de alza + etiqueta de alerta (Alta ≥ 0.65, Media 0.5–0.65, Baja < 0.5; umbrales a calibrar).
- **Explicabilidad**: importancia de variables, para decir "sube por lluvia baja + dólar alto".

## 6. API (FastAPI)

| Endpoint | Devuelve |
|---|---|
| `GET /productos` | Lista de productos disponibles |
| `GET /precios?producto=papa&desde=2020-01&hasta=2024-12` | Serie mensual |
| `GET /prediccion?producto=papa` | Probabilidad de alza próximo mes, alerta, top-3 factores |
| `GET /factores?producto=papa` | Correlaciones con lluvia, TRM, producción |
| `GET /modelo/metricas` | Métricas del modelo vs baseline |

## 7. App — pantallas (insumo para FigCraft / Figma)

1. **Inicio / Alertas**: 3 tarjetas (papa, tomate, cebolla) con precio actual, flecha ↑/↓, probabilidad y semáforo.
2. **Detalle de producto**: línea de precio 2020–2024 + punto de predicción; selector de producto y rango.
3. **Estacionalidad**: mapa de calor mes × año o barras por mes.
4. **Factores**: dispersión precio vs lluvia y precio vs TRM, con correlación.
5. **Modelo**: tabla modelo vs baseline, matriz de confusión, aviso de limitaciones.
6. **Acerca de los datos**: fuentes, periodo, fecha de actualización.

Wireframe de la pantalla 1:

```
┌───────────────────────────────────────────────┐
│ CENTINELA AGRO        [Producto ▾] [Periodo ▾]│
├───────────────────────────────────────────────┤
│ ┌─Papa─────┐ ┌─Tomate───┐ ┌─Cebolla──┐        │
│ │ $1.850/kg│ │ $2.400/kg│ │ $1.600/kg│        │
│ │ ▲ 72%    │ │ ▼ 41%    │ │ ▲ 55%    │        │
│ │ ALERTA   │ │ ESTABLE  │ │ VIGILAR  │        │
│ └──────────┘ └──────────┘ └──────────┘        │
│ Precio histórico + predicción (línea)         │
│ ───────────────────────────────╱              │
│ Por qué: lluvia ↓ · dólar ↑ · mes de baja oferta│
└───────────────────────────────────────────────┘
```

## 8. Lineamientos gráficos

Tomados del PDF para mantener coherencia:

| Uso | Color aproximado |
|---|---|
| Título / primario | Azul marino `#1F3B5C` |
| Acento / tablas | Azul `#2C6E9B` |
| Por hacer | Gris verdoso |
| En progreso | Azul |
| En revisión | Naranja `#B5651D` |
| Hecho | Verde `#1F6E5C` |
| Alerta alta / media / baja (app) | Rojo / naranja / verde (nuevo, con ícono además del color) |

Tipografía: sans-serif tipo Helvetica/Inter. Accesibilidad: no usar solo color para la alerta; añadir flecha y texto.

## 9. Revisión gráfica del PDF actual

1. Página 2: el título "5. Qué debe resolver el ETL" queda solo al final y su lista pasa a la página 3. Forzar salto de página antes del título.
2. Páginas 3 y 5: más de la mitad en blanco. Unir las secciones 5 y 8 en menos páginas.
3. Página 4: el tablero es una imagen estática. En la leyenda, "Camilo: Base de datos" y "María P: ETL y limpieza" se cortan en dos líneas. Dar más ancho o abreviar.
4. Los colores de columnas (estado) y de personas (rol) comparten paleta, así que "naranja" significa dos cosas (En revisión y Pipe). Separar las paletas.
5. Contenido: el alcance dice 2020–2024 pero clima y TRM llegan a 2026; aclarar que se recortan. El texto "(por confirmar)" en productos debe resolverse antes de la semana 3.

## 10. Plan (alineado al cronograma de 8 semanas)

| Semana | Entregable técnico | Responsable |
|---|---|---|
| 1–2 | Staging cargado, esquema SQL | Camilo, María P |
| 3–4 | ETL completo, `vw_maestra_mensual` | María P, Camilo |
| 3–4 | Wireframes y sistema de diseño de la app | Daniel |
| 5 | EDA + baseline | Pipe, Alex |
| 6–7 | Random Forest, API, app conectada | Alex, Daniel |
| 8 | Informe, demo desplegada, presentación | Todos |

## 11. Riesgos

| Riesgo | Mitigación |
|---|---|
| Pocos datos (60 meses) | Modelo global multi-producto; reportar intervalos de incertidumbre. |
| Sin datos SIPSA 2025–26 | La app muestra "datos hasta dic-2024"; predicción es demostrativa. Evaluar SIPSA diario para actualizar. |
| Clima de un municipio por zona | Declararlo en "Acerca de los datos". |
| Agrupación de variedades | Decidir en semana 3 con tabla `dim_producto`. |
| Modelo no supera baseline | Mostrar el resultado con honestidad; la app sirve igual como panel de precios y alertas por reglas. |

## 12. Decisiones pendientes

1. Productos finales (papa, tomate chonto, cebolla junca).
2. Streamlit o React para la app.
3. Dónde se publica la demo.
