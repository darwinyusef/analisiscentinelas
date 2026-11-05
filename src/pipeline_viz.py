"""Genera entregables/pipeline_interactivo.html: pipeline de produccion con agentes de IA.

HTML + CSS puro (sin JavaScript): la interaccion usa radios y checkboxes con :checked.
Uso:  .venv/bin/python src/pipeline_viz.py
"""
from html import escape as e
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "entregables" / "pipeline_interactivo.html"

# autonomia: s = sugiere (humano decide) | a = ejecuta con aprobacion | x = autonomo acotado
AUT = {"s": "Sugiere", "a": "Ejecuta con aprobación", "x": "Autónomo acotado"}

ETAPAS = [
    dict(
        id=1, nombre="Captura de fuentes", capa="Bronze (crudo)", estado="parcial",
        entrada="SIPSA (Excel/DANE), Open-Meteo (API), TRM (datos.gov.co), producción UPRA / Datos Colombia",
        salida="data/raw/AAAA-MM/*.parquet + manifiesto (hash, filas, fecha de descarga)",
        herramientas="requests, pandas, Parquet, DuckDB",
        codigo=["Hoy se lee el Excel manual (`precios_sipsa_modificado.xlsx`). A producción: descarga programada de cada fuente.",
                "Los datos crudos son de solo lectura y se versionan por mes: nunca se sobrescriben.",
                "Cada descarga guarda un manifiesto: hash del archivo, número de filas y columnas."],
        agente=dict(nombre="Agente de Ingesta", aut="x",
                    hace="Vigila las fuentes, detecta un informe nuevo o un cambio de esquema (columna renombrada, hoja nueva), descarga y valida el manifiesto.",
                    limite="Solo escribe en `raw/`. No toca datos limpios. Si el esquema cambia, detiene la corrida y avisa; no intenta adivinar."),
        humano=None,
        gate="Manifiesto completo y esquema igual al contrato; si no, la corrida se detiene.",
        escala="Una tarea por fuente y por mes, en paralelo. Particionado por AAAA-MM. Reintentos con espera.",
        esfuerzo="3 días", riesgo="Medio: SIPSA no tiene API estable; puede requerir scraping o carga manual asistida.",
    ),
    dict(
        id=2, nombre="Limpieza y calidad", capa="Silver (limpio)", estado="hecho",
        entrada="raw/ del mes",
        salida="datos_limpios/sipsa_limpio, clima_mensual, trm_mensual, produccion_limpia + salidas/etl_log.json",
        herramientas="pandas, pandera / Great Expectations",
        codigo=["`arreglar_fecha`: corrige día-como-mes (2020-21), texto `ene-22` y año 2026 (11 → 60 meses).",
                "`arreglar_escala`: reescala ×1000 por distancia logarítmica a la mediana 2020-21 (154.433 filas).",
                "Deduplica, quita encabezados, convierte negativos a nulo. Todo queda en `etl_log.json`."],
        agente=dict(nombre="Agente de Calidad y Anomalías", aut="s",
                    hace="Perfila cada carga contra la línea base (meses distintos, mediana anual por producto, saltos de ×1000, productos nuevos). "
                         "Si aparece un defecto nuevo, redacta una regla de corrección propuesta con evidencia (ejemplos y gráfico). "
                         "También unifica nombres de producto y mercado con LLM + embeddings.",
                    limite="Nunca modifica `src/etl.py` ni los datos por su cuenta: entrega una propuesta. Las reglas nuevas pasan por revisión humana."),
        humano="Aprobar cada regla nueva de limpieza antes de que entre al ETL.",
        gate="Meses = 60 esperados, 0 filas en 2026, mediana anual continua entre 2021 y 2022. Si falla, la carga no avanza.",
        escala="Particionado por mercado y producto. Validación declarativa que corre en segundos sobre 271.740 filas y escala a decenas de millones con DuckDB.",
        esfuerzo="4 días (el ETL ya existe)", riesgo="Bajo en el código; medio en la resolución de nombres (falsos emparejamientos).",
    ),
    dict(
        id=3, nombre="Maestra y variables", capa="Gold (analítico)", estado="hecho",
        entrada="datos_limpios/*",
        salida="datos_limpios/maestra_mensual (240 filas) + datos_limpios/features_grupo.csv (10.863 filas, 181 productos × 60 meses)",
        herramientas="pandas / DuckDB, Parquet",
        codigo=["`src/etl.py` une precio + clima ponderado por producción + TRM + producción t-1 (maestra de los 4 productos).",
                "`src/ml_features.py` arma las variables de los 181 productos: rezagos de retorno, media móvil, volatilidad, seno/coseno del mes, índice estacional con solo pasado y grupo.",
                "Regla de validez: toda columna del mes t usa solo información al cierre de t. El ETL falla si los meses ≠ 60."],
        agente=dict(nombre="Agente de Variables", aut="a",
                    hace="Propone variables candidatas, las construye en un entorno aislado, pasa la prueba de fuga y mide su ganancia con walk-forward. Descarta las que no aportan.",
                    limite="Trabaja en rama separada. Solo se fusiona una variable con aprobación y con ganancia demostrada (IC95), para no inflar el modelo."),
        humano="Aprobar la fusión de variables nuevas.",
        gate="Prueba de fuga en verde (desplazar la variable y verificar que el resultado no mejora) y cero nulos inesperados.",
        escala="Cálculo por producto en paralelo. De 4 a 181 productos con 60 meses (45 veces más muestra).",
        esfuerzo="Hecho; falta la prueba automática de fuga por desplazamiento (1 día)", riesgo="Medio: la fuga temporal es el error más común y el más silencioso.",
    ),
    dict(
        id=4, nombre="EDA automático", capa="Reporte", estado="hecho",
        entrada="datos_limpios/* + etl_log.json",
        salida="salidas/figuras (16) + eda_stats.json → informe_eda.ipynb / .html / .css",
        herramientas="matplotlib, seaborn, statsmodels (STL, ACF), nbformat",
        codigo=["`src/eda.py` genera 16 figuras y `eda_stats.json` (~80 s).",
                "`src/informe.py` arma el notebook, lo ejecuta y exporta el espejo HTML+CSS.",
                "Toda cifra del informe sale del JSON, no de texto escrito a mano."],
        agente=dict(nombre="Agente de Reporte", aut="x",
                    hace="Regenera el informe cada mes y redacta los hallazgos en lenguaje claro a partir de `eda_stats.json`. Señala qué cambió frente al mes anterior.",
                    limite="Un validador compara cada número del texto con el JSON; si no coincide, bloquea la publicación. No puede citar cifras que no estén en el JSON."),
        humano=None,
        gate="Cada cifra citada en el texto coincide con el JSON. 16 figuras generadas.",
        escala="Un informe por grupo de productos (alimentos, hortalizas, tubérculos) en vez de uno gigante.",
        esfuerzo="2 días", riesgo="Bajo. El riesgo real es un LLM que invente cifras: lo cubre el validador.",
    ),
    dict(
        id=5, nombre="Modelado y experimentos", capa="ML", estado="hecho",
        entrada="maestra / feature store",
        salida="salidas/ml_predicciones_oos.csv (walk-forward 2022-01 a 2024-11, 35 orígenes) + modelos/centinela_modelo.joblib",
        herramientas="scikit-learn, HistGradientBoosting, LightGBM, MLflow, joblib / Dask",
        codigo=["`src/ml_modelo.py`: un modelo de grupo (181 productos). Canónico: Random Forest solo con precio, fijado antes de ver resultados.",
                "Walk-forward con ventana expansiva, hiperparámetros fijos, sin GridSearch sobre el periodo evaluado.",
                "Siempre se calculan las bases: clase mayoritaria, \"repite la última dirección\" y signo del índice estacional."],
        agente=dict(nombre="Agente Experimentador", aut="x",
                    hace="Lanza la búsqueda de hiperparámetros y de combinaciones de variables, registra cada corrida y resume qué probó y qué no funcionó.",
                    limite="Presupuesto de cómputo y de número de corridas fijado de antemano. No puede cambiar el criterio de éxito ni los datos de prueba."),
        humano=None,
        gate="Todas las corridas registradas con semilla, versión de datos y versión de código (reproducibles).",
        escala="Corridas independientes en paralelo (por grupo y por ventana). Aquí se concentra el cómputo.",
        esfuerzo="Hecho (~1 min de cómputo)", riesgo="Alto: con 60 meses por serie es fácil sobreajustar. Por eso existe la etapa 6 con otro agente.",
    ),
    dict(
        id=6, nombre="Evaluación y compuerta", capa="ML", estado="hecho",
        entrada="predicciones walk-forward + bases",
        salida="salidas/ml_resumen.csv, ml_resultados.json (veredicto O3 por código), ml_confiabilidad.json, ml_calibracion.csv",
        herramientas="statsmodels, scipy (Wilson, McNemar), bootstrap por meses",
        codigo=["Exactitud con IC95 por bootstrap de MESES (los productos de un mes están correlacionados), Wilson, McNemar, F1, AUC.",
                "O3 calculado por el código: IC inferior > 50 % y IC inferior de la diferencia vs \"repite\" > 0.",
                "`src/ml_confiabilidad.py`: homogeneidad alcance vs grupo, AUC, estabilidad por año, calibración y potencia."],
        agente=dict(nombre="Agente Revisor Estadístico", aut="s",
                    hace="Segunda opinión independiente: recalcula las métricas desde las predicciones crudas, corrige por comparaciones múltiples y escribe el veredicto con su motivo.",
                    limite="No comparte contexto con el Experimentador, así no hereda sus sesgos. Su rechazo bloquea; la promoción siempre la decide un humano."),
        humano="Decidir la promoción a producción.",
        gate="181 productos: 60,4 % vs 55,8 % de la base, Δ +4,6 pts (IC95 +3,2 a +6,1): cumple O3. "
             "Los 4 productos: 60,0 %, Δ +4,3 (IC95 −4,3 a +12,9): O3 propio no demostrable (harían falta ~257 meses de prueba). Se publica el nivel de grupo.",
        escala="Evaluación por producto y agregada; las métricas son baratas, escalan sin problema.",
        esfuerzo="Hecho", riesgo="Medio: la tentación de relajar el criterio cuando el resultado del alcance es débil. La evidencia complementaria se etiqueta como tal y no reemplaza al O3.",
    ),
    dict(
        id=7, nombre="Servicio y alertas", capa="Producción", estado="parcial",
        entrada="modelo en ONNX + últimos precios",
        salida="modelos/centinela_modelo.onnx (1,1 MB) + salidas/ml_alertas_onnx.csv + entregables/tablero_centinela.html",
        herramientas="skl2onnx, onnxruntime, HTML+CSS estático (FastAPI / WhatsApp: pendiente)",
        codigo=["`src/ml_onnx.py` exporta el modelo a ONNX y resuelve las alertas con onnxruntime; falla si la diferencia con sklearn supera 1e-4 (hoy 1,4e-07). Hash SHA-256 en `centinela_modelo.json`.",
                "`src/tablero.py` arma el tablero: nivel 1 alertas de grupo con su acierto histórico; nivel 2 los 4 productos con la señal marcada experimental."],
        agente=dict(nombre="Agente Narrador", aut="a",
                    hace="Convierte la salida del modelo en un mensaje claro para productores y compradores, con el lenguaje del sector.",
                    limite="Solo puede citar números que vengan de la API. Usa plantillas aprobadas. No da consejos de compra o venta. Los mensajes nuevos de otro tipo requieren aprobación."),
        humano="Aprobar las plantillas de mensaje y cualquier tipo de alerta nuevo.",
        gate="Cada mensaje incluye incertidumbre y fecha de datos. Sin eso no sale.",
        escala="Alertas por lotes y por suscripción. Cacheo de la predicción mensual (una sola corrida, muchas lecturas).",
        esfuerzo="Tablero y ONNX hechos; faltan API y mensajería (4 días)", riesgo="Alto reputacional si se promete exactitud que el modelo no tiene.",
    ),
    dict(
        id=8, nombre="Monitoreo y reentrenamiento", capa="Operación", estado="propuesto",
        entrada="predicciones publicadas + precios reales del mes siguiente",
        salida="panel de desempeño real, alertas de deriva, disparo de reentrenamiento",
        herramientas="Evidently / PSI y KS, Prometheus o logs, Dagster / Prefect",
        codigo=["Cada mes se compara lo predicho con lo ocurrido y se actualiza la exactitud con su IC.",
                "Deriva de datos: PSI y KS sobre las variables; cambio de escala o de fechas dispara la etapa 2.",
                "Reentrenamiento mensual programado en un entorno de prueba."],
        agente=dict(nombre="Agente Monitor", aut="a",
                    hace="Detecta deriva y caídas de desempeño, abre un incidente con diagnóstico y lanza el reentrenamiento en el entorno de prueba.",
                    limite="Nunca promueve un modelo solo. Si el desempeño real cae bajo la base durante 3 meses, retira la alerta de predicción y deja la vista estacional."),
        humano="Revisar el incidente y aprobar un modelo reentrenado.",
        gate="Desempeño real ≥ base en ventana móvil de 6 meses; si no, se degrada a modo estacional.",
        escala="Monitoreo por producto, con umbrales por grupo. Cierra el ciclo: vuelve a las etapas 2 y 5.",
        esfuerzo="5 días", riesgo="Medio: con pocos datos mensuales la señal de deriva es lenta y ruidosa.",
    ),
]

GUARDARRAILES = [
    ("Datos crudos intocables", "Ningún agente escribe en `raw/`, salvo el de Ingesta, y solo para añadir."),
    ("Nada se promueve solo", "Un modelo o una regla de limpieza nueva siempre pasa por una persona."),
    ("Cero cifras inventadas", "Todo texto generado se valida contra el JSON o la API de origen."),
    ("Presupuesto y bitácora", "Cada agente tiene límite de cómputo y registro completo de lo que hizo y por qué."),
    ("Revisión independiente", "Quien entrena no es quien evalúa: agentes distintos, contextos separados."),
]

ESTADO = {"hecho": "Hecho", "parcial": "Parcial", "propuesto": "Propuesto"}


def lista(items):
    return "<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"


def nodo(et, ultimo_fila):
    a = et["agente"]
    flecha = "" if ultimo_fila else '<span class="flecha" aria-hidden="true"></span>'
    cont = '<span class="sigue" aria-hidden="true">continúa abajo ↓</span>' if et["id"] == 4 else ""
    humano = '<span class="chip humano">Persona aprueba</span>' if et["humano"] else ""
    return (
        f'<label for="n{et["id"]}" class="nodo est-{et["estado"]}">'
        f'<span class="num">{et["id"]}</span>'
        f'<span class="nombre">{e(et["nombre"])}</span>'
        f'<span class="capa">{e(et["capa"])}</span>'
        f'<span class="estado">{ESTADO[et["estado"]]}</span>'
        f'<span class="chip agente aut-{a["aut"]}" title="{e(AUT[a["aut"]])}">IA · {e(a["nombre"])}</span>'
        f'{humano}{cont}{flecha}</label>'
    )


def panel(et):
    a = et["agente"]
    humano = (f'<div class="caja humano"><h4>Punto de control humano</h4><p>{e(et["humano"])}</p></div>'
              if et["humano"] else "")
    return f"""
<section class="panel" id="p{et['id']}">
  <header>
    <span class="num grande">{et['id']}</span>
    <div><h3>{e(et['nombre'])}</h3><p class="sub">{e(et['capa'])} · <span class="tag est-{et['estado']}">{ESTADO[et['estado']]}</span> · Esfuerzo estimado: {e(et['esfuerzo'])}</p></div>
  </header>
  <div class="io">
    <div class="caja"><h4>Entra</h4><p>{e(et['entrada'])}</p></div>
    <div class="io-flecha" aria-hidden="true"></div>
    <div class="caja"><h4>Sale</h4><p>{e(et['salida'])}</p></div>
  </div>
  <div class="cols">
    <div class="caja"><h4>Qué hace el código (determinista)</h4>{lista(et['codigo'])}<p class="mini"><b>Herramientas:</b> {e(et['herramientas'])}</p></div>
    <div class="caja agente-box aut-{a['aut']}">
      <h4>Agente de IA · {e(a['nombre'])}</h4>
      <p class="nivel">Autonomía: <b>{e(AUT[a['aut']])}</b></p>
      <p><b>Qué hace.</b> {e(a['hace'])}</p>
      <p><b>Límite.</b> {e(a['limite'])}</p>
    </div>
  </div>
  {humano}
  <div class="cols tres">
    <div class="caja"><h4>Compuerta de calidad</h4><p>{e(et['gate'])}</p></div>
    <div class="caja"><h4>Cómo escala</h4><p>{e(et['escala'])}</p></div>
    <div class="caja"><h4>Riesgo</h4><p>{e(et['riesgo'])}</p></div>
  </div>
</section>"""


def css_dinamico():
    r = []
    for i in range(1, len(ETAPAS) + 1):
        r.append(f"#n{i}:checked ~ .flujo label[for=n{i}],#n{i}:focus-visible ~ .flujo label[for=n{i}]"
                 "{border-color:var(--verde);box-shadow:0 0 0 3px rgba(31,110,92,.25);transform:translateY(-3px)}")
        r.append(f"#n{i}:checked ~ .paneles #p{i}{{display:block}}")
    return "\n".join(r)


CSS = """
:root{--verde:#1F6E5C;--azul:#1F3A5F;--gris:#f3f6f5;--linea:#d6dfdc;--texto:#1d2b27;
--ia:#6b4fbb;--ia-bg:#f1edfb;--hu:#b9731c;--hu-bg:#fdf3e4;--hecho:#1F6E5C;--parcial:#c28a12;--prop:#7a8a86}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--texto);background:#fff;line-height:1.55}
.envuelve{max-width:1180px;margin:0 auto;padding:28px 22px 60px}
h1{color:var(--azul);margin:0 0 4px;font-size:1.7em}
.lead{margin:0 0 18px;color:#44544f;max-width:860px}
.aviso{background:var(--hu-bg);border-left:5px solid var(--hu);padding:10px 14px;border-radius:4px;margin:0 0 20px;font-size:.93em}
.sr{position:absolute;opacity:0;pointer-events:none}
.controles{display:flex;flex-wrap:wrap;gap:10px 22px;align-items:center;margin:0 0 18px;padding:10px 14px;background:var(--gris);border:1px solid var(--linea);border-radius:8px}
.controles label.sw{cursor:pointer;user-select:none;font-size:.92em;display:inline-flex;gap:8px;align-items:center}
.controles label.sw::before{content:"";width:34px;height:18px;border-radius:9px;background:#b8c4c0;transition:.2s;box-shadow:inset 0 0 0 2px #fff}
#ag:checked ~ .controles label[for=ag]::before{background:var(--ia)}
#hu:checked ~ .controles label[for=hu]::before{background:var(--hu)}
.leyenda{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.82em;margin-left:auto}
.leyenda i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.flujo{display:grid;grid-template-columns:repeat(4,1fr);gap:26px 34px;margin:0 0 14px}
.nodo{position:relative;display:flex;flex-direction:column;gap:5px;padding:14px 14px 12px;background:#fff;border:2px solid var(--linea);border-radius:12px;cursor:pointer;transition:.18s}
.nodo:hover{border-color:var(--azul);transform:translateY(-3px);box-shadow:0 6px 16px rgba(31,58,95,.12)}
.num{display:inline-flex;width:28px;height:28px;border-radius:50%;background:var(--azul);color:#fff;font-weight:700;align-items:center;justify-content:center;font-size:.9em}
.num.grande{width:44px;height:44px;font-size:1.3em;flex:none}
.nombre{font-weight:700;color:var(--azul);font-size:1.02em}
.capa{font-size:.8em;color:#5a6b66}
.estado,.tag{align-self:flex-start;font-size:.72em;font-weight:700;padding:2px 8px;border-radius:10px;color:#fff;letter-spacing:.02em}
.est-hecho .estado,.tag.est-hecho{background:var(--hecho)}
.est-parcial .estado,.tag.est-parcial{background:var(--parcial)}
.est-propuesto .estado,.tag.est-propuesto{background:var(--prop)}
.nodo.est-hecho{border-left:6px solid var(--hecho)}
.nodo.est-parcial{border-left:6px solid var(--parcial)}
.nodo.est-propuesto{border-left:6px dashed var(--prop)}
.chip{align-self:flex-start;font-size:.74em;padding:3px 9px;border-radius:12px;font-weight:600}
.chip.agente{background:var(--ia-bg);color:var(--ia);border:1px solid #d6cdf2}
.chip.humano{background:var(--hu-bg);color:var(--hu);border:1px solid #f0d9b3}
.flecha{position:absolute;top:50%;right:-31px;width:28px;height:4px;margin-top:-2px;background:repeating-linear-gradient(90deg,var(--verde) 0 6px,transparent 6px 10px);background-size:20px 4px;animation:fluye .9s linear infinite}
.flecha::after{content:"";position:absolute;right:-3px;top:-4px;border:6px solid transparent;border-left:9px solid var(--verde)}
@keyframes fluye{to{background-position:20px 0}}
.sigue{font-size:.72em;color:#5a6b66;font-style:italic}
#ag:not(:checked) ~ .flujo .chip.agente,#ag:not(:checked) ~ .paneles .agente-box,#ag:not(:checked) ~ .tabla-agentes{display:none}
#hu:not(:checked) ~ .flujo .chip.humano,#hu:not(:checked) ~ .paneles .caja.humano{display:none}
.orq{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;padding:11px 16px;background:var(--azul);color:#fff;border-radius:10px;margin:0 0 6px;font-size:.9em}
.orq b{color:#fff}
.orq .bucle{margin-left:auto;background:rgba(255,255,255,.14);padding:3px 11px;border-radius:12px;font-size:.88em}
.pista{margin:8px 2px 18px;font-size:.88em;color:#5a6b66}
.paneles{min-height:120px}
.panel{display:none;border:2px solid var(--verde);border-radius:14px;padding:20px 22px;background:#fff;animation:entra .25s ease}
@keyframes entra{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.panel>header{display:flex;gap:14px;align-items:center;margin-bottom:14px}
.panel h3{margin:0;color:var(--azul);font-size:1.3em}
.sub{margin:2px 0 0;color:#5a6b66;font-size:.9em}
.caja{background:var(--gris);border:1px solid var(--linea);border-radius:9px;padding:11px 14px}
.caja h4{margin:0 0 6px;font-size:.78em;text-transform:uppercase;letter-spacing:.06em;color:var(--verde)}
.caja p{margin:0 0 6px;font-size:.92em}
.caja ul{margin:0 0 8px;padding-left:18px;font-size:.92em}
.caja li{margin-bottom:4px}
.mini{font-size:.84em!important;color:#44544f}
.io{display:grid;grid-template-columns:1fr 46px 1fr;align-items:center;gap:8px;margin-bottom:12px}
.io-flecha{height:4px;background:repeating-linear-gradient(90deg,var(--verde) 0 6px,transparent 6px 10px);background-size:20px 4px;position:relative;animation:fluye .9s linear infinite}
.io-flecha::after{content:"";position:absolute;right:-3px;top:-6px;border:8px solid transparent;border-left:11px solid var(--verde)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.cols.tres{grid-template-columns:repeat(3,1fr);margin-bottom:0}
.agente-box{background:var(--ia-bg);border-color:#d6cdf2}
.agente-box h4{color:var(--ia)}
.nivel{display:inline-block;padding:2px 9px;border-radius:10px;font-size:.8em!important;color:#fff;background:var(--ia)}
.agente-box.aut-s .nivel{background:#8a6fd1}.agente-box.aut-a .nivel{background:var(--ia)}.agente-box.aut-x .nivel{background:#3f2d85}
.caja.humano{background:var(--hu-bg);border-color:#f0d9b3;margin-bottom:12px}
.caja.humano h4{color:var(--hu)}
h2{color:var(--verde);border-left:6px solid var(--verde);padding-left:12px;margin:34px 0 12px;font-size:1.25em}
table{border-collapse:collapse;width:100%;font-size:.88em}
th{background:var(--azul);color:#fff;text-align:left;padding:8px 10px}
td{padding:8px 10px;border-bottom:1px solid var(--linea);vertical-align:top}
tr:nth-child(even) td{background:var(--gris)}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;font-size:.82em;font-weight:600}
.pill.s{background:#8a6fd1}.pill.a{background:var(--ia)}.pill.x{background:#3f2d85}
.guard{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.guard div{background:var(--gris);border:1px solid var(--linea);border-top:4px solid var(--verde);border-radius:8px;padding:10px 12px;font-size:.88em}
.guard b{display:block;color:var(--azul);margin-bottom:4px}
code{background:#e8eeec;padding:1px 5px;border-radius:3px;font-size:.92em}
@media (max-width:980px){.flujo{grid-template-columns:repeat(2,1fr)}.guard{grid-template-columns:1fr 1fr}.cols,.cols.tres{grid-template-columns:1fr}.sigue{display:none}}
@media (max-width:640px){.flujo{grid-template-columns:1fr;gap:34px}.flecha{top:auto;bottom:-31px;right:50%;margin:0 -14px 0 0;transform:rotate(90deg)}.io{grid-template-columns:1fr}.io-flecha{display:none}.guard{grid-template-columns:1fr}}
"""


def construir():
    n = len(ETAPAS)
    radios = "".join(f'<input class="sr" type="radio" name="etapa" id="n{i}"{" checked" if i == 1 else ""} aria-label="Etapa {i}">'
                     for i in range(1, n + 1))
    nodos = "".join(nodo(et, ultimo_fila=(et["id"] in (4, 8))) for et in ETAPAS)
    paneles = "".join(panel(et) for et in ETAPAS)
    filas = "".join(
        f'<tr><td><b>{e(et["agente"]["nombre"])}</b></td><td>{et["id"]} · {e(et["nombre"])}</td>'
        f'<td><span class="pill {et["agente"]["aut"]}">{e(AUT[et["agente"]["aut"]])}</span></td>'
        f'<td>{e(et["agente"]["hace"])}</td><td>{e(et["agente"]["limite"])}</td></tr>'
        for et in ETAPAS)
    guard = "".join(f"<div><b>{e(t)}</b>{e(d)}</div>" for t, d in GUARDARRAILES)
    total = "36 días-persona (≈7 semanas, 1 persona con experiencia en ML, ±40 %)"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Centinela Agro · Pipeline con agentes de IA</title>
<style>{CSS}
{css_dinamico()}</style></head>
<body><div class="envuelve">
<h1>Centinela Agro · Pipeline de producción con agentes de IA</h1>
<p class="lead">De los datos crudos a la alerta mensual: 8 etapas, 8 puntos donde un agente de IA ayuda y 5 donde una persona decide.
Haz clic en cada etapa para ver qué entra, qué sale, qué hace el código, qué hace el agente y dónde está su límite.</p>
<div class="aviso"><b>Las etapas 2 a 6 ya existen como código</b> (<code>etl.py</code>, <code>ml_features.py</code>, <code>ml_modelo.py</code>, <code>ml_confiabilidad.py</code>, <code>ml_onnx.py</code>) y la 7 está parcial (ONNX + tablero).
Los agentes siguen siendo una propuesta. El modelo cumple O3 en el grupo de 181 productos; en los 4 del alcance no es demostrable: ver la compuerta de la etapa 6.</div>

<input class="sr" type="checkbox" id="ag" checked aria-label="Mostrar agentes de IA">
<input class="sr" type="checkbox" id="hu" checked aria-label="Mostrar puntos de control humanos">
{radios}
<div class="controles">
  <label class="sw" for="ag">Agentes de IA</label>
  <label class="sw" for="hu">Puntos de control humanos</label>
  <div class="leyenda">
    <span><i style="background:var(--hecho)"></i>Hecho</span>
    <span><i style="background:var(--parcial)"></i>Parcial</span>
    <span><i style="background:var(--prop)"></i>Propuesto</span>
    <span><i style="background:var(--ia)"></i>Agente IA</span>
    <span><i style="background:var(--hu)"></i>Persona</span>
  </div>
</div>
<nav class="flujo" aria-label="Etapas del pipeline">{nodos}</nav>
<div class="orq"><b>Orquestador</b> Dagster o Prefect · corrida mensual programada · cada etapa es una tarea con reintentos y registro
<span class="bucle">Ciclo: 8 Monitoreo → vuelve a 2 Limpieza y a 5 Modelado</span></div>
<p class="pista">Las etapas son selectores: con el teclado, usa las flechas ← → sobre el selector de etapa.</p>
<div class="paneles">{paneles}</div>

<h2>Mapa de agentes y su autonomía</h2>
<div class="tabla-agentes"><table>
<tr><th>Agente</th><th>Etapa</th><th>Autonomía</th><th>Qué hace</th><th>Su límite</th></tr>{filas}</table></div>

<h2>Cinco reglas para todos los agentes</h2>
<div class="guard">{guard}</div>

<h2>Esfuerzo total y orden de construcción</h2>
<p>{e(total)}. Orden sugerido: <b>1)</b> compuerta de la etapa 2 y validador del 4 (bajo costo, alto valor) →
<b>2)</b> etapas 3 y 5 con el modelo por grupo de productos → <b>3)</b> Revisor Estadístico (6) antes de cualquier alerta →
<b>4)</b> servicio y monitoreo (7 y 8) solo si la etapa 6 aprueba un modelo; si no, se publica la vista estacional.</p>
</div></body></html>"""


if __name__ == "__main__":
    OUT.write_text(construir(), encoding="utf-8")
    print("OK:", OUT, f"{OUT.stat().st_size/1024:.0f} KB")
