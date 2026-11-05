"""Arma el informe EDA como notebook ejecutado (.ipynb) y su espejo HTML + CSS.

Uso:  .venv/bin/python src/eda.py && .venv/bin/python src/informe.py
Salida: entregables/informe_eda.ipynb, informe_eda.html (autonomo), informe_eda.css
"""
import json
from pathlib import Path

import nbformat as nbf
from nbconvert import HTMLExporter
from nbconvert.preprocessors import ExecutePreprocessor

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "entregables"
OUT.mkdir(exist_ok=True)
S = json.loads((RAIZ / "salidas" / "eda_stats.json").read_text())

CELDAS = []


def md(t):
    CELDAS.append(nbf.v4.new_markdown_cell(t.strip()))


def code(t):
    CELDAS.append(nbf.v4.new_code_cell(t.strip()))


def fig(nombre):
    code(f'mostrar("{nombre}")')


c, cob = S["calidad"], S["cobertura"]
f = c["fechas"]

md(f"""
# Centinela Agro · Informe de Análisis Exploratorio (EDA)
**Pregunta:** ¿se puede anticipar si el precio mayorista de papa, papa criolla, tomate chonto y cebolla junca
sube o baja el mes siguiente en la Central Mayorista de Antioquia (CMA)?

| Dato | Valor |
|---|---|
| Periodo | ene-2020 a dic-2024 (60 meses) |
| Fuentes | SIPSA (precios), Open-Meteo (clima, 3 subregiones), TRM, producción agrícola de Antioquia |
| Mercado objetivo | CMA · {c['cma_productos']} productos, {c['cma_filas']:,} filas limpias |
| Alcance del modelo | 4 productos: papa capira, papa criolla, tomate chonto, cebolla junca |

**Hallazgo central:** los datos son utilizables tras una limpieza fuerte, la estacionalidad es real en papa, y **ningún modelo supera de forma
estadísticamente significativa a la regla simple "repite la última dirección"** con 60 meses por producto.
""")

code("""
import json, warnings
from pathlib import Path
import pandas as pd
from IPython.display import Image, display, HTML
warnings.filterwarnings("ignore")
RAIZ = Path.cwd().parent if Path.cwd().name == "entregables" else Path.cwd()
FIG = RAIZ / "salidas" / "figuras"
def mostrar(nombre):
    display(Image(filename=str(FIG / f"{nombre}.png")))
def tabla(df):
    display(HTML(df.to_html(classes="tabla", border=0)))
""")

md("## 1 · Calidad de datos y limpieza (ETL)")
md(f"""
El Excel de SIPSA llegó con **tres corrupciones sistemáticas** que, sin corregir, habrían producido conclusiones falsas:

1. **Fechas mal leídas.** Lectura ingenua: solo **{f['meses_distintos_lectura_ingenua']} meses distintos**; corregida: **{f['meses_distintos_corregidos']}**.
   {f['filas_2020_21_con_dia_como_mes']:,} filas de 2020-21 con el día como mes, {f['filas_parseadas_como_2026']:,} filas 2022-24 leídas como 2026
   y {f['filas_fecha_texto_no_parseada']:,} con texto `ene-22`.
2. **Escala de precios.** Desde 2022 los precios con punto de miles se leyeron como decimales (`2.367` en vez de `2367`).
   Se corrigieron **{c['escalados']:,} filas** (×1000), eligiendo por fila el valor más cercano a la mediana 2020-21 del mismo producto.
3. **Duplicados y encabezados:** {c['encabezados']} filas de encabezado/vacías, {c['repetidas']} combinaciones mes-producto-mercado repetidas (promediadas)
   y {c['dup_prod']} duplicados exactos en producción.

Resultado: **{c['filas_limpias']:,} filas limpias**, {c['productos']} productos, {c['mercados']} mercados.
""")
fig("fig01_calidad")

md(f"""
### Verificación contra el pipeline previo (`analisis/`)
Se compararon las {c['filas_limpias']:,} combinaciones mes-producto-mercado del pipeline anterior (`analisis/etl.py`) con el nuevo (`src/etl.py`):
**mismas filas, mismos 60 meses, 14 celdas con diferencia >1 %** (0,005 %). Las diferencias reales son productos sin precio de referencia 2020-21
(café instantáneo, langostino) donde la regla anterior no reescalaba; el pipeline nuevo sí. Las otras dos son un intercambio de orden en arveja enlatada.
Ninguna toca los 4 productos del alcance.
""")

md("## 2 · Cobertura")
md(f"""
De {cob['total']} productos en la CMA, **{cob['productos_completos_60']} tienen los 60 meses completos**.
Por mes hay entre {cob['min_mes']} y {cob['max_mes']} productos reportados.
""")
fig("fig02_cobertura")

md("## 3 · Series de precio")
rows = [f"| {p} | {d['mean']:,.0f} | {d['50%']:,.0f} | {d['min']:,.0f} – {d['max']:,.0f} | {d['cv_%']} % | {d['var_total_%']:+.0f} % |"
        for p, d in S["precios"].items()]
md("| Producto | Media $/kg | Mediana | Rango | CV | Cambio 2020→2024 |\n|---|---|---|---|---|---|\n" + "\n".join(rows))
fig("fig03_series")
md(f"El índice base 100 de los 4 productos cierra 2024 en **{S['indice_mercado_fin']}**: los precios subieron ~{S['indice_mercado_fin']-100:.0f} % en cinco años.")
fig("fig04_indice")

md("## 4 · Estacionalidad y tendencia")
rows = []
for p, d in S["estacionalidad"].items():
    st = S["fuerza_stl"][p]
    rows.append(f"| {p} | {d['mes_mas_caro']} ({d['indice_max']}) | {d['mes_mas_barato']} ({d['indice_min']}) | {st['estacional']} | {st['tendencia']} |")
md("| Producto | Mes más caro (índice) | Mes más barato | Fuerza estacional (STL) | Fuerza de tendencia |\n|---|---|---|---|---|\n" + "\n".join(rows))
md("**Lectura:** la papa (capira y criolla) tiene estacionalidad fuerte (>0.55); el tomate casi no la tiene (0.17) y su precio es el más difícil de anticipar.")
fig("fig05_estacionalidad")
fig("fig06_stl")

md("## 5 · Variaciones mensuales y balance de clases")
rows = [f"| {p} | {d['sube_%']} % | {d['desv_mensual_%']} % | {d['p5_%']} % / {d['p95_%']} % | {d['estable_5%']} % |"
        for p, d in S["variaciones"].items()]
md("| Producto | Meses con alza | Desv. mensual | P5 / P95 | Cambio < ±5 % |\n|---|---|---|---|---|\n" + "\n".join(rows))
md("Las clases alza/baja están **balanceadas (49–54 %)**, así que la exactitud es una métrica válida; el piso honesto es 50 %. "
   "Entre 15 y 25 % de los meses casi no se mueven: el umbral de \"alza\" importa.")
fig("fig07_variaciones")

md("## 6 · Autocorrelación")
rows = [f"| {p} | {d['rezago1']} | {d['rezago12']} | {d['rezagos_significativos'] or '—'} |" for p, d in S["acf"].items()]
md("| Producto | ACF rezago 1 | ACF rezago 12 | Rezagos significativos |\n|---|---|---|---|\n" + "\n".join(rows))
md("Papa capira y criolla tienen memoria (0.3 en rezago 1); tomate y cebolla se comportan casi como ruido. Anticipa qué productos tienen más opciones de predicción.")
fig("fig08_acf")

md("## 7 · Clima, TRM y producción")
fig("fig09_clima")
md(f"TRM: mínimo {S['trm']['min']:,}, máximo {S['trm']['max']:,} ({S['trm']['mes_max']}).")
fig("fig10_trm")
fig("fig11_produccion")
md("""
**Alerta de calidad:** la producción es anual y de ámbito Antioquia; el clima proviene de **un municipio por subregión** (Santa Rosa de Osos, San Jerónimo, El Peñol)
y se pondera por volumen de producción 2015-2024 del rubro. Tomate y cebolla se producen sobre todo en suroeste/valle de Aburrá, zonas **sin clima en la fuente**:
para esos productos el clima es una aproximación pobre.
""")

md("## 8 · ¿Qué se relaciona con el precio del mes siguiente?")
co = S["correlaciones"]
md(f"""
Spearman entre cada variable en *t* y la variación de precio *t→t+1*. De {co['n_total']} correlaciones, **{co['n_significativas']} son significativas (p<0.05)**,
pero por azar se esperarían **~{co['esperadas_por_azar']}**. Sin corrección por comparaciones múltiples, trátelas como hipótesis, no como hechos.
""")
fig("fig12_correlaciones")
md("Más destacadas: lluvia con 3 meses de rezago en papa criolla (ρ=0.54) y momentum del precio en papa capira (ρ=0.50).")
fig("fig13_dispersion")

md("## 9 · Sondeo de viabilidad (no es el modelo final)")
md("""
Validación **walk-forward** (origen móvil, sin fuga temporal): se entrena con el pasado y se predice el mes siguiente, de 2023-01 a 2024-11.
Tres escenarios de variables y dos bases de comparación. Intervalos de confianza de Wilson al 95 %.
""")
code("""
t = pd.read_csv(RAIZ / "salidas" / "sondeo_viabilidad.csv")
t = t.rename(columns={"accuracy_%": "Exactitud %", "ic95_bajo": "IC95 bajo", "ic95_alto": "IC95 alto"}).round(1)
tabla(t.set_index(["escenario", "metodo"]))
""")
fig("fig14_sondeo")
md("""
**Lectura honesta:** el mejor resultado (Random Forest, escenario A, 62 %) tiene un IC de 52–71 %, que **incluye** el 57.6 % de "repite la última dirección".
Añadir clima y producción (escenario C) **empeora** el resultado (55 %). Con n=92 (o 48 en solo 2024) la diferencia entre modelos es indistinguible del azar.
""")
fig("fig15_importancia")
fig("fig16_error")

md("## 10 · Conclusiones y siguientes pasos")
md("""
| # | Conclusión | Evidencia |
|---|---|---|
| 1 | Los datos sirven **solo después** de corregir fechas y escala | fig01, tabla de calidad |
| 2 | La papa tiene estacionalidad y memoria; tomate y cebolla casi no | fig05, fig06, fig08 |
| 3 | Clima y TRM no aportan señal robusta con estos datos | fig12, escenario C |
| 4 | Ningún modelo supera con significancia a la regla simple | fig14 |
| 5 | El tamaño de muestra (60 meses × 4 productos) es el límite principal | IC95 de 20 puntos |

**Acciones recomendadas (en orden):**
1. Posicionar el producto como **alerta de estacionalidad y rango histórico** (valor real hoy), no como predictor de alza/baja con exactitud garantizada.
2. Ampliar la muestra: entrenar un modelo por **grupo de productos** (181 productos con 60 meses) y evaluar sobre los 4 del alcance.
3. Conseguir clima diario por municipio productor (suroeste, valle de Aburrá) y producción mensual.
4. Fijar el criterio de éxito **antes** de entrenar: superar a "repite última dirección" con IC95 inferior > 50 %.
5. Reportar siempre la exactitud con su intervalo y la base de comparación.
""")

nb = nbf.v4.new_notebook(cells=CELDAS)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
ExecutePreprocessor(timeout=300, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(OUT)}})
nbf.write(nb, OUT / "informe_eda.ipynb")

CSS = r"""
:root{--verde:#1F6E5C;--azul:#1F3A5F;--gris:#f5f7f6;--texto:#1d2b27}
body{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--texto);background:#fff;line-height:1.6}
.jp-Notebook{max-width:980px;margin:0 auto;padding:32px 24px}
h1{color:var(--azul);border-bottom:4px solid var(--verde);padding-bottom:10px}
h2{color:var(--verde);margin-top:2.4em;border-left:6px solid var(--verde);padding-left:12px}
h3{color:var(--azul)}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:.92em}
th{background:var(--azul);color:#fff;text-align:left;padding:8px 10px}
td{padding:7px 10px;border-bottom:1px solid #dfe6e3}
tr:nth-child(even) td{background:var(--gris)}
img{max-width:100%;height:auto;border:1px solid #e3e9e6;border-radius:6px;margin:12px 0}
strong{color:var(--azul)}
code{background:var(--gris);padding:1px 5px;border-radius:3px}
.jp-InputArea,.jp-InputPrompt,.jp-OutputPrompt{display:none!important}
@media print{img{page-break-inside:avoid}}
"""
(OUT / "informe_eda.css").write_text(CSS)

html, _ = HTMLExporter(template_name="lab").from_notebook_node(nb)
html = html.replace("</head>", f"<style>{CSS}</style>\n<link rel=\"stylesheet\" href=\"informe_eda.css\">\n</head>", 1)
(OUT / "informe_eda.html").write_text(html)
print("OK:", sorted(p.name for p in OUT.iterdir()))
