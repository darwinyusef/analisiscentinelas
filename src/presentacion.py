"""Genera entregables/Centinela_Agro_Pitch.pptx (pitch + resultados para el equipo de desarrollo).

Todas las cifras salen de analisis/resultados/*.json|csv, salidas/eda_stats.json y datos_limpios/.
Uso: .venv/bin/python src/presentacion.py
"""
import json
from pathlib import Path

import pandas as pd
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import (XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION,
                             XL_MARKER_STYLE, XL_TICK_MARK)
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "analisis" / "resultados"
PITCH_IMG = ROOT / "salidas" / "pitch"
OUT = ROOT / "entregables" / "Centinela_Agro_Pitch.pptx"

NAVY = RGBColor(0x1F, 0x3B, 0x5C)
BLUE = RGBColor(0x2C, 0x6E, 0x9B)
ORANGE = RGBColor(0xB5, 0x65, 0x1D)
GREEN = RGBColor(0x1F, 0x6E, 0x5C)
RED = RGBColor(0xC0, 0x39, 0x2B)
GRAY = RGBColor(0x6B, 0x72, 0x80)
INK = RGBColor(0x1E, 0x29, 0x3B)
LIGHT = RGBColor(0xF1, 0xF5, 0xF9)
LINE = RGBColor(0xD5, 0xDD, 0xE6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT_BLUE = RGBColor(0xDC, 0xE9, 0xF3)
SOFT_RED = RGBColor(0xFB, 0xE3, 0xE0)
SOFT_GREEN = RGBColor(0xDB, 0xEE, 0xE8)
SOFT_ORANGE = RGBColor(0xF6, 0xE6, 0xD3)
PALE = RGBColor(0x9F, 0xC5, 0xE0)
FONT = "Calibri"

PROD_COLORS = [BLUE, ORANGE, RED, GREEN]
PRODUCTOS = ["papa capira", "papa criolla limpia", "tomate chonto regional", "cebolla junca"]

# ---------------------------------------------------------------- datos
tablero = json.load(open(RES / "datos_tablero.json"))
robustez = json.load(open(RES / "robustez.json"))
maestra = pd.read_csv(ROOT / "datos_limpios" / "maestra_mensual.csv", parse_dates=["mes"])
precios = maestra.pivot(index="mes", columns="producto", values="precio")
maestra["idx"] = maestra.precio / maestra.groupby(
    ["producto", maestra.mes.dt.year]).precio.transform("mean")
indice = maestra.groupby(["producto", maestra.mes.dt.month]).idx.mean().unstack()

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
state = {"n": 0}


# ---------------------------------------------------------------- helpers
def P(text, size=16, bold=False, color=INK, after=0, align=None, bullet=False, italic=False):
    return dict(text=text, size=size, bold=bold, color=color, after=after,
                align=align, bullet=bullet, italic=italic)


def fill_paras(tf, paras):
    first = True
    for spec in paras:
        if isinstance(spec, str):
            spec = P(spec)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        runs = spec["text"] if isinstance(spec["text"], list) else [(spec["text"], spec["bold"], None)]
        for t, b, c in runs:
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(spec["size"])
            r.font.bold = b
            r.font.italic = spec["italic"]
            r.font.color.rgb = c or spec["color"]
        if spec["align"] is not None:
            p.alignment = spec["align"]
        p.space_after = Pt(spec["after"])
        if spec["bullet"]:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", "257175")
            pPr.set("indent", "-257175")
            bu = etree.SubElement(pPr, qn("a:buChar"))
            bu.set("char", "•")


def tb(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, margin=0.0):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(margin / 2)
    fill_paras(tf, paras if isinstance(paras, list) else [paras])
    return box


def shape(slide, kind, x, y, w, h, fill=LIGHT, line=None, radius=0.06):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    s.shadow.inherit = False
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def card(slide, x, y, w, h, fill=LIGHT, line=None, radius=0.05):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, radius)


def card_text(slide, x, y, w, h, paras, fill=LIGHT, line=None, anchor=MSO_ANCHOR.TOP,
              pad=0.25, radius=0.05):
    c = card(slide, x, y, w, h, fill, line, radius)
    tf = c.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(pad)
    tf.margin_top = tf.margin_bottom = Inches(pad * 0.7)
    fill_paras(tf, paras if isinstance(paras, list) else [paras])
    return c


def chip(slide, x, y, w, h, text, fill, color, size=12):
    c = card(slide, x, y, w, h, fill, None, 0.5)
    tf = c.text_frame
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    fill_paras(tf, [P(text, size, True, color, align=PP_ALIGN.CENTER)])
    return c


def circle_num(slide, x, y, d, n, color, size=22):
    c = shape(slide, MSO_SHAPE.OVAL, x, y, d, d, color)
    c.text_frame.margin_left = c.text_frame.margin_right = 0
    c.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    fill_paras(c.text_frame, [P(str(n), size, True, WHITE, align=PP_ALIGN.CENTER)])


def side_stat(slide, x, y, w, h, big, txt, col, big_size=26):
    card(slide, x, y, w, h)
    shape(slide, MSO_SHAPE.RECTANGLE, x, y, 0.09, h, col)
    tb(slide, x + 0.3, y + 0.1, w - 0.4, 0.6, P(big, big_size, True, col))
    tb(slide, x + 0.3, y + 0.72, w - 0.45, h - 0.75, P(txt, 14, False, INK))


def new_slide(tag=None, title=None, navy=False, notes=""):
    s = prs.slides.add_slide(BLANK)
    state["n"] += 1
    if navy:
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = NAVY
    if tag:
        tb(s, 0.6, 0.32, 9, 0.3, P(tag, 11, True, BLUE))
    if title:
        tb(s, 0.6, 0.62, 12.1, 1.0, P(title, 28, True, NAVY))
    if not navy:
        tb(s, 0.6, 7.07, 6, 0.3, P("CENTINELA AGRO", 10, True, GRAY))
        tb(s, 11.7, 7.07, 1.0, 0.3, P(str(state["n"]), 10, False, GRAY, align=PP_ALIGN.RIGHT))
    s.notes_slide.notes_text_frame.text = notes
    return s


def source(slide, text):
    tb(slide, 0.6, 6.78, 12.1, 0.28, P(text, 10, False, GRAY, italic=True))


def style_chart(chart, legend=True, size=12):
    chart.font.name = FONT
    chart.font.size = Pt(size)
    chart.font.color.rgb = INK
    chart.has_title = False
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)
    va = chart.value_axis
    va.major_gridlines.format.line.color.rgb = LINE
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(size)
    va.tick_labels.font.color.rgb = GRAY
    ca = chart.category_axis
    ca.format.line.color.rgb = LINE
    ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.tick_labels.font.size = Pt(size)
    ca.tick_labels.font.color.rgb = GRAY


def force_every_label(chart):
    ax = chart.category_axis._element
    skip = etree.SubElement(ax, qn("c:tickLblSkip"))
    skip.set("val", "1")
    nm = ax.find(qn("c:noMultiLvlLbl"))
    if nm is not None:
        nm.addprevious(skip)
    ax.find(qn("c:txPr")).find(qn("a:bodyPr")).set("rot", "0")


def set_value_axis(ch, vmin, vmax, unit, fmt):
    ch.value_axis.minimum_scale = vmin
    ch.value_axis.maximum_scale = vmax
    ch.value_axis.major_unit = unit
    ch.value_axis.tick_labels.number_format = fmt
    ch.value_axis.tick_labels.number_format_is_linked = False


def bar_chart(slide, x, y, w, h, cats, vals, colors, vmin, vmax, unit, size=13, gap=55):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("v", vals)
    gf = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y),
                                Inches(w), Inches(h), cd)
    ch = gf.chart
    style_chart(ch, legend=False, size=size)
    set_value_axis(ch, vmin, vmax, unit, '0"%"')
    plot = ch.plots[0]
    plot.gap_width = gap
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = '0.0"%"'
    dl.number_format_is_linked = False
    dl.font.size = Pt(size + 1)
    dl.font.bold = True
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    for i, c in enumerate(colors):
        pt = plot.series[0].points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = c
    return ch


def table(slide, x, y, w, col_w, rows, size=13, row_h=0.5):
    nrows, ncols = len(rows), len(rows[0])
    gf = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(row_h * nrows))
    t = gf.table
    tblPr = gf._element.graphic.graphicData.tbl.tblPr
    tblPr.set("bandRow", "0")
    tblPr.set("firstRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is not None:
        sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # sin estilo
    for i, cw in enumerate(col_w):
        t.columns[i].width = Inches(cw)
    for r in range(nrows):
        t.rows[r].height = Inches(row_h)
        for c in range(ncols):
            cell = t.cell(r, c)
            val = rows[r][c]
            color, bold, fillc = INK, c == 0, (WHITE if r % 2 else LIGHT)
            if isinstance(val, tuple):
                val, color, bold = val[0], val[1], True
            if r == 0:
                color, bold, fillc = WHITE, True, NAVY
            cell.fill.solid()
            cell.fill.fore_color.rgb = fillc
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.margin_top = cell.margin_bottom = Inches(0.05)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            fill_paras(cell.text_frame, [P(val, size, bold, color)])
    return t


def pct(v, d=1):
    return f"{v * 100:.{d}f}".replace(".", ",") + " %"


# ================================================================ PARTE 1: PITCH
# 1 -- portada
s = new_slide(navy=True, notes=(
    "Abrir con la promesa, no con la tecnología: 'saber antes si el precio de lo que comemos sube o baja'. "
    "Decir de entrada para quién es: productores, comerciantes y familias de Antioquia. "
    "Duración total del pitch: 8-10 minutos; la parte 2 es para el equipo de desarrollo."))
tb(s, 0.8, 0.9, 8, 0.4, P("PITCH · NOVIEMBRE 2026", 13, True, PALE))
tb(s, 0.8, 1.6, 8.0, 1.0, P("CENTINELA AGRO", 54, True, WHITE))
tb(s, 0.8, 2.85, 7.8, 1.8, P("Sepa antes si el precio de su canasta sube o baja", 34, False, WHITE))
tb(s, 0.8, 4.85, 7.6, 1.0, P("Alertas mensuales con inteligencia artificial para papa, tomate y cebolla "
                              "de la Central Mayorista de Antioquia.", 18, False, RGBColor(0xC9, 0xD8, 0xE6)))
chip(s, 0.8, 6.1, 3.3, 0.45, "Datos reales SIPSA 2020–2024", BLUE, WHITE, 13)
s.shapes.add_picture(str(PITCH_IMG / "m1_alertas.png"), Inches(9.3), Inches(0.9), height=Inches(6.6))

# 2 -- problema
s = new_slide("EL PROBLEMA", "El precio de la canasta se mueve sin avisar", notes=(
    "Tres cifras reales de la Central Mayorista. 1) La papa capira pasó de $1.138 a $2.349 por kilo en cinco años. "
    "2) Uno de cada veinte meses la papa sube más de 39 %. 3) El tomate chonto llegó a valer $4.471 y a caer a $1.271. "
    "Mensaje: quien produce, vende o compra decide sin saber qué viene."))
assert round(precios["papa capira"].iloc[0]) == 1138 and round(precios["papa capira"].iloc[-1]) == 2349
assert round(precios["tomate chonto regional"].min()) == 1271 and round(precios["tomate chonto regional"].max()) == 4471
stats = [
    ("×2", BLUE, "La papa capira pasó de $1.138 a $2.349 por kg entre enero 2020 y diciembre 2024 (+106 %)."),
    ("1 de 20", ORANGE, "meses la papa capira sube más de 39 % de un mes a otro. La variación mensual típica es ±20 %."),
    ("$1.271 → $4.471", RED, "Rango del tomate chonto en cinco años (precio mayorista por kg)."),
]
for i, (big, col, txt) in enumerate(stats):
    x = 0.6 + i * 4.1
    card(s, x, 1.85, 3.9, 3.5)
    shape(s, MSO_SHAPE.RECTANGLE, x, 1.85, 0.1, 3.5, col)
    tb(s, x + 0.35, 2.1, 3.4, 1.0, P(big, 40 if len(big) < 9 else 30, True, col), anchor=MSO_ANCHOR.MIDDLE)
    tb(s, x + 0.35, 3.3, 3.3, 1.9, P(txt, 16, False, INK))
card_text(s, 0.6, 5.65, 12.1, 1.0, P("Quien produce, vende o compra decide sin saber qué viene.", 22, True, WHITE),
          fill=NAVY, anchor=MSO_ANCHOR.MIDDLE, pad=0.4)
source(s, "Fuente: SIPSA-DANE, Central Mayorista de Antioquia, precio promedio mensual 2020–2024.")

# 3 -- gráfico de precios
s = new_slide("EL PROBLEMA", "Cinco años de precios: picos y caídas bruscas en los cuatro productos", notes=(
    "Dejar que el gráfico hable 10 segundos. Señalar que no hay una tendencia simple: hay ciclos y saltos. "
    "Esto es lo que la app quiere anticipar."))
cd = CategoryChartData()
cd.categories = [str(d.year) if d.month == 1 else " " for d in precios.index]
for col in PRODUCTOS:
    cd.add_series(col.capitalize(), [float(v) for v in precios[col]])
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE, Inches(0.6), Inches(1.7), Inches(12.1), Inches(5.0), cd)
ch = gf.chart
style_chart(ch, size=13)
force_every_label(ch)
ch.value_axis.tick_labels.number_format = '"$"#,##0'
ch.value_axis.tick_labels.number_format_is_linked = False
ch.value_axis.minimum_scale = 500
for ser, col in zip(ch.plots[0].series, PROD_COLORS):
    ser.smooth = False
    ser.marker.style = XL_MARKER_STYLE.NONE
    ser.format.line.color.rgb = col
    ser.format.line.width = Pt(2.5)
source(s, "Fuente: SIPSA-DANE, Central Mayorista de Antioquia. Precio mayorista promedio mensual, COP por kg.")

# 4 -- solución
s = new_slide("LA SOLUCIÓN", "Centinela Agro responde tres preguntas simples", notes=(
    "Presentar las tres pantallas como tres preguntas. Recalcar la tercera: la app dice cuánto confiar en ella. "
    "Cierre del slide: el modelo aprende de 181 productos de la canasta; la app arranca con 4."))
qs = [
    ("1", BLUE, "¿Sube o baja el próximo mes?",
     "Alerta de dirección con probabilidad: alza probable, baja probable o sin señal clara."),
    ("2", ORANGE, "¿Cuándo suele estar caro o barato?",
     "Calendario estacional por producto: el mes típico de pico y el de valle."),
    ("3", GREEN, "¿Cuánto me puedo fiar?",
     "Pantalla de confiabilidad: cuánto ha acertado el modelo y cuáles son sus límites."),
]
for i, (n, col, q, a) in enumerate(qs):
    x = 0.6 + i * 4.1
    card(s, x, 1.85, 3.9, 3.7)
    circle_num(s, x + 0.3, 2.1, 0.7, n, col, 24)
    tb(s, x + 0.3, 3.0, 3.35, 0.9, P(q, 21, True, NAVY))
    tb(s, x + 0.3, 3.95, 3.35, 1.5, P(a, 16, False, INK))
card_text(s, 0.6, 5.85, 12.1, 0.85, P([
    ("El modelo aprende de 181 productos de la canasta. ", True, WHITE),
    ("La app arranca con 4: papa capira, papa criolla, tomate chonto y cebolla junca.", False, WHITE)], 17),
    fill=NAVY, anchor=MSO_ANCHOR.MIDDLE, pad=0.35)

# 5 -- calendario estacional
s = new_slide("LA SOLUCIÓN · CALENDARIO", "Cada producto tiene sus meses caros y sus meses baratos", notes=(
    "Leer el gráfico: 1,0 es el precio medio del año. La papa capira sube a 1,19 en marzo y baja a 0,81 en septiembre: "
    "casi 40 % de diferencia entre el mes caro y el barato. Ser honestos: en papa el patrón es fiable; en tomate es débil."))
cd = CategoryChartData()
cd.categories = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
for col in PRODUCTOS:
    cd.add_series(col.capitalize(), [round(float(indice.loc[col, m]), 3) for m in range(1, 13)])
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.6), Inches(1.95), Inches(7.4), Inches(4.75), cd)
ch = gf.chart
style_chart(ch, size=13)
set_value_axis(ch, 0.7, 1.35, 0.1, "0.0")
for ser, col in zip(ch.plots[0].series, PROD_COLORS):
    ser.smooth = False
    ser.format.line.color.rgb = col
    ser.format.line.width = Pt(2.75)
    ser.marker.style = XL_MARKER_STYLE.CIRCLE
    ser.marker.size = 6
    ser.marker.format.fill.solid()
    ser.marker.format.fill.fore_color.rgb = col
    ser.marker.format.line.color.rgb = col
tb(s, 0.6, 1.65, 7.4, 0.3, P("Índice estacional (1,0 = precio medio del año)", 11, False, GRAY, italic=True))
cal = [
    ("Papa capira", BLUE, "Caro: marzo · Barato: septiembre", "Patrón fiable", SOFT_GREEN, GREEN),
    ("Papa criolla", ORANGE, "Caro: abril · Barato: enero", "Patrón fiable", SOFT_GREEN, GREEN),
    ("Tomate chonto", RED, "Caro: diciembre · Barato: julio", "Patrón débil", SOFT_RED, RED),
    ("Cebolla junca", GREEN, "Caro: diciembre · Barato: mayo", "Patrón moderado", SOFT_ORANGE, ORANGE),
]
for i, (name, col, txt, lab, bgc, fgc) in enumerate(cal):
    y = 1.95 + i * 1.18
    card(s, 8.3, y, 4.4, 1.05)
    shape(s, MSO_SHAPE.RECTANGLE, 8.3, y, 0.09, 1.05, col)
    tb(s, 8.55, y + 0.1, 2.4, 0.35, P(name, 16, True, NAVY))
    tb(s, 8.55, y + 0.55, 4.1, 0.4, P(txt, 13, False, INK))
    chip(s, 10.95, y + 0.12, 1.6, 0.3, lab, bgc, fgc, 11)
source(s, "Índice = precio del mes / promedio del año, promediado 2020–2024. Fuerza estacional (STL): papa 0,62 y 0,57; cebolla 0,33; tomate 0,17.")

# 6 -- demo app
s = new_slide("LA SOLUCIÓN · DEMO", "Así se ve: alerta real para enero de 2025", notes=(
    "Demo con datos reales hasta diciembre de 2024. Papa capira: alza probable (65,8 %). "
    "Los otros tres: sin señal clara. Decirlo es una virtud: la app no inventa certezas. "
    "En la pantalla de la derecha se ve la confiabilidad."))
tb(s, 0.6, 1.9, 4.5, 4.5, [
    P("Semáforo con flecha y texto, no solo color.", 18, True, NAVY, after=10),
    P("Papa capira: alza probable (65,8 %). Los otros tres: sin señal clara.", 16, False, INK, after=10, bullet=True),
    P("Calendario estacional con mes caro y mes barato.", 16, False, INK, after=10, bullet=True),
    P("Pantalla de confiabilidad: cuánto acierta y dónde falla.", 16, False, INK, after=10, bullet=True),
    P("Diseño móvil listo para desarrollo (marcos M1–M5).", 16, False, INK, bullet=True),
])
for i, f in enumerate(["m1_alertas", "m3_calendario", "m4_confiabilidad"]):
    s.shapes.add_picture(str(PITCH_IMG / f"{f}.png"), Inches(5.4 + i * 2.5), Inches(1.75), height=Inches(5.0))
source(s, "Demo con datos hasta dic-2024. Pantallas del diseño en diseno/centinela_agro.figcraft.")

# 7 -- cómo funciona
s = new_slide("CÓMO FUNCIONA", "De los datos oficiales a una alerta con probabilidad", notes=(
    "Explicación en lenguaje simple. El modelo mira dos cosas: qué ha hecho el precio recientemente (71 % del peso) "
    "y el patrón del calendario (25 %). Se validó mirando solo hacia atrás: entrena con el pasado y se prueba con el futuro."))
steps = [
    ("1", "Datos oficiales", BLUE,
     "Precios mayoristas SIPSA-DANE de la Central Mayorista de Antioquia, limpiados y unidos en una tabla mensual.",
     "271.740 registros · 181 productos"),
    ("2", "Modelo de IA", ORANGE,
     "Un Random Forest aprende de la historia reciente del precio (71 % del peso) y del patrón estacional (25 %).",
     "Entrena con el pasado, prueba con el futuro"),
    ("3", "Alerta", GREEN,
     "Cada mes entrega una probabilidad de alza y la traduce a semáforo: alza probable, baja probable o sin señal.",
     "Siempre muestra su exactitud histórica"),
]
for i, (n, name, col, txt, foot) in enumerate(steps):
    x = 0.6 + i * 4.3
    card(s, x, 1.85, 3.5, 4.2)
    shape(s, MSO_SHAPE.RECTANGLE, x, 1.85, 3.5, 0.12, col)
    tb(s, x + 0.3, 2.2, 2.9, 0.6, P(f"{n}  {name}", 20, True, col))
    tb(s, x + 0.3, 3.0, 2.95, 2.0, P(txt, 16, False, INK))
    chip(s, x + 0.3, 5.3, 2.9, 0.5, foot, WHITE, NAVY, 11)
    if i < 2:
        shape(s, MSO_SHAPE.RIGHT_ARROW, x + 3.6, 3.65, 0.6, 0.5, GRAY)
tb(s, 0.6, 6.3, 12.1, 0.4, P("Diseñado para reentrenarse con cada publicación nueva de SIPSA.", 15, False, GRAY, italic=True))

# 8 -- confianza
s = new_slide("CONFIANZA", "Acierta más que las reglas simples, y lo dice con honestidad", notes=(
    "El número clave: 58,9 % de aciertos frente a 55,8 % de la mejor regla simple, sobre 181 productos y 6.519 predicciones. "
    "La ventaja es modesta pero consistente: gana en 2022, 2023 y 2024. Cuando el modelo está seguro acierta 62,6 %. "
    "En 93 de 181 productos dice 'sin señal clara': eso protege al usuario. Nota: el eje parte de 50 % (lanzar una moneda)."))
tb(s, 0.6, 1.62, 6.9, 0.3, P("% de aciertos en alza/baja, 2022–2024 (el eje parte de 50 % = azar)", 11, False, GRAY, italic=True))
bar_chart(s, 0.6, 1.95, 6.9, 4.7,
          ["Centinela (IA)", "Regla estacional", "Sube si subió", "Siempre «sube»"],
          [58.9, 57.4, 55.8, 53.7], [BLUE, GRAY, GRAY, GRAY], 50, 60, 2)
kp = [("62,6 %", "acierto cuando el modelo está seguro de que sube (más de 60 %)", BLUE),
      ("63,5 %", "acierto cuando avisa que baja (40 % o menos)", GREEN),
      ("93 de 181", "productos reciben «sin señal clara»: la app no inventa certezas", ORANGE)]
for i, (big, txt, col) in enumerate(kp):
    side_stat(s, 7.9, 1.95 + i * 1.6, 4.8, 1.45, big, txt, col, 28)
source(s, "Validación temporal sobre 181 productos y 6.519 predicciones (2022–2024). Ventaja modesta, no un oráculo.")

# 9 -- para quién
s = new_slide("VALOR", "Una señal útil para quien produce, vende y compra", notes=(
    "Tres usuarios, tres usos. Cuidar el lenguaje: es una señal de dirección, no una recomendación de inversión "
    "ni un precio exacto."))
who = [
    ("Productores", BLUE, "Ver en qué meses el mercado suele estar bajo y planear cuándo vender.",
     "Calendario + alerta de baja"),
    ("Comerciantes", ORANGE, "Anticipar compras: la alerta de alza acierta 62,6 % y la de baja 63,5 %.",
     "Alerta + confiabilidad"),
    ("Familias", GREEN, "Saber cuándo la papa suele estar más cara (marzo) y más barata (septiembre).",
     "Calendario estacional"),
]
for i, (name, col, txt, feat) in enumerate(who):
    x = 0.6 + i * 4.1
    card(s, x, 1.85, 3.9, 3.9)
    shape(s, MSO_SHAPE.RECTANGLE, x, 1.85, 3.9, 0.7, col)
    tb(s, x + 0.3, 1.85, 3.4, 0.7, P(name, 22, True, WHITE), anchor=MSO_ANCHOR.MIDDLE)
    tb(s, x + 0.3, 2.85, 3.35, 1.9, P(txt, 17, False, INK))
    chip(s, x + 0.3, 5.0, 3.3, 0.45, feat, WHITE, col, 13)
card_text(s, 0.6, 6.0, 12.1, 0.7, P("Es una señal de dirección: no es un precio exacto ni asesoría de inversión.", 16, True, NAVY),
          fill=SOFT_BLUE, anchor=MSO_ANCHOR.MIDDLE, pad=0.35)

# 10 -- puente
s = new_slide(navy=True, notes=(
    "Transición: hasta aquí el pitch para el público. Ahora pasamos al equipo de desarrollo: qué nos propusimos, "
    "qué respondieron los datos y qué hay que construir."))
tb(s, 0.8, 1.2, 10, 0.4, P("PARTE 2", 14, True, PALE))
tb(s, 0.8, 1.8, 11.5, 1.8, P("Para el equipo de desarrollo: ¿qué respondió el análisis?", 42, True, WHITE))
items = ["Qué se puede y qué no se puede predecir", "Objetivos del proyecto y su estado",
         "Resultados del modelo", "Arquitectura, plan de 8 semanas y decisiones"]
tb(s, 0.8, 4.1, 11, 2.6, [P(t, 22, False, SOFT_BLUE, after=10, bullet=True) for t in items])

# ================================================================ PARTE 2: EQUIPO
# 11 -- qué se puede prometer
s = new_slide("PARTE 2 · LA RESPUESTA", "Se predice la dirección del precio, no el valor exacto", notes=(
    "Slide central para el equipo. El objetivo original era predecir el precio del próximo mes. Los datos mostraron "
    "que eso no es demostrable: el modelo de nivel no supera la regla 'igual al mes pasado' (MAPE 2024 9,84 % vs 9,97 %). "
    "Lo que sí es demostrable es la dirección. Esto cambia el diseño de la app: probabilidad y semáforo, no un precio."))
for x, col, head, items in [
    (0.6, GREEN, "Se puede prometer (demostrado)", [
        "Alerta de dirección: 58,9 % de acierto (IC95 57,5–60,3 %) vs 55,8 % de la mejor regla simple.",
        "Calendario: mes típico caro y barato. Fiable en papa, moderado en cebolla, débil en tomate.",
        "Seguro (>60 %): acierta 62,6 %. Avisa baja (≤40 %): acierta 63,5 %.",
        "Ventaja demostrada en el conjunto de 181 productos."]),
    (6.75, RED, "No se debe prometer (no demostrado)", [
        "El precio exacto del mes siguiente: no supera la regla «igual al mes pasado».",
        "Explicar el precio con clima o dólar: correlaciones débiles, no mejoran el modelo.",
        "Ventaja probada producto por producto: solo 36 meses de prueba (±16 puntos).",
        "Certeza en una alerta individual: el sistema acierta 6 de cada 10."]),
]:
    card(s, x, 1.8, 5.95, 4.85)
    shape(s, MSO_SHAPE.RECTANGLE, x, 1.8, 5.95, 0.6, col)
    tb(s, x + 0.3, 1.8, 5.4, 0.6, P(head, 19, True, WHITE), anchor=MSO_ANCHOR.MIDDLE)
    tb(s, x + 0.3, 2.6, 5.4, 4.0, [P(t, 15, False, INK, after=9, bullet=True) for t in items])

# 12 -- objetivos vs estado
s = new_slide("PARTE 2 · OBJETIVOS", "Cinco objetivos: dos listos, dos parciales, uno por construir", notes=(
    "Repasar fila por fila. Lo pendiente que más pesa: la carga a SQL Server y el desarrollo de la app/tablero. "
    "El modelo está 'parcial' porque el resultado por producto no es concluyente aunque sí lo es en el conjunto."))
H, PA, PE = ("● Hecho", GREEN), ("● Parcial", ORANGE), ("● Pendiente", GRAY)
rows = [
    ["#", "Objetivo", "Estado", "Resultado"],
    ["1", "Cargar datos a SQL Server", PA, "ETL listo y auditado (271.740 filas limpias, 0 nulos en la maestra). Falta la carga."],
    ["2", "Tabla maestra mensual", H, "240 filas del alcance (4 × 60) y 10.863 filas del panel de 181 productos."],
    ["3", "Análisis exploratorio", H, "Informe EDA cerrado. Estacionalidad clara en papa; clima y dólar sin poder predictivo."],
    ["4", "Modelo predictivo", PA, "Supera los baselines en el panel de 181. Por producto no es concluyente."],
    ["5", "Tablero / app", PE, "Diseño listo en Figma (móvil M1–M5 + tablero web). Falta el desarrollo."],
]
table(s, 0.6, 1.8, 12.1, [0.5, 2.9, 1.5, 7.2], rows, size=14, row_h=0.78)
source(s, "Fuente: Propuesta gerencial v1.1 y plan de alcance del EDA.")

# 13 -- datos
s = new_slide("PARTE 2 · DATOS", "Los datos venían dañados por Excel; se repararon antes de modelar", notes=(
    "Sin la corrección todo análisis habría sido incorrecto: las fechas de 2020-2021 tenían el mes en el campo día "
    "(11 meses distintos en vez de 60) y desde 2022 los precios perdieron el separador de miles. "
    "Las reglas están en src/etl.py y deben pasar a producción con pruebas automáticas."))
kp = [("11 → 60", "meses distintos tras corregir las fechas", BLUE),
      ("154.433", "precios reescalados ×1000 (perdieron el separador de miles)", ORANGE),
      ("271.740", "filas limpias, 0 nulos en la maestra", GREEN),
      ("181 de 220", "productos de la CMA con los 60 meses completos", NAVY)]
for i, (big, txt, col) in enumerate(kp):
    x = 0.6 + i * 3.07
    card(s, x, 1.8, 2.9, 2.0)
    shape(s, MSO_SHAPE.RECTANGLE, x, 1.8, 2.9, 0.09, col)
    tb(s, x + 0.2, 2.0, 2.5, 0.6, P(big, 28, True, col))
    tb(s, x + 0.2, 2.7, 2.55, 1.05, P(txt, 14, False, INK))
card(s, 0.6, 4.05, 7.0, 2.6)
tb(s, 0.9, 4.2, 6.5, 0.4, P("Reglas del ETL que pasan a producción", 16, True, NAVY))
tb(s, 0.9, 4.7, 6.5, 1.9, [
    P("Mes: en 2020–21 está en el campo día; en 2022–24 viene como texto. El año sale del nombre del archivo.", 14, False, INK, after=5, bullet=True),
    P("Escala: desde 2022, si el precio es < 100 (o < 1000 con decimales), se multiplica ×1000.", 14, False, INK, after=5, bullet=True),
    P("Mercado: solo Medellín, Central Mayorista. Una fila por producto × mes.", 14, False, INK, bullet=True)])
card(s, 7.8, 4.05, 4.9, 2.6)
tb(s, 8.1, 4.2, 4.4, 0.4, P("Fuentes", 16, True, NAVY))
tb(s, 8.1, 4.7, 4.4, 1.9, [
    P("SIPSA-DANE: precios mayoristas (2020–2024)", 14, False, INK, after=5, bullet=True),
    P("Open-Meteo: clima, 3 subregiones", 14, False, INK, after=5, bullet=True),
    P("TRM mensual", 14, False, INK, after=5, bullet=True),
    P("Producción agrícola anual de Antioquia", 14, False, INK, bullet=True)])

# 14 -- resultados por año
s = new_slide("PARTE 2 · MODELO", "El modelo gana a las reglas simples en 2022, 2023 y 2024", notes=(
    "Validación temporal: entrena con el pasado y prueba en el futuro, sin mezclar fechas. "
    "Gana a la regla de momentum por 1,4 a 4,9 puntos (IC95, bootstrap por mes) y a 'siempre sube' por 3,2 a 7,4. "
    "McNemar p = 1,5e-5 sobre 6.519 predicciones. Ventaja modesta pero consistente."))
cd = CategoryChartData()
cd.categories = ["2022", "2023", "2024"]
py = robustez["por_anio"]
cd.add_series("Centinela (Random Forest)", [round(py[a]["ok_rf"] * 100, 1) for a in ("2022", "2023", "2024")])
cd.add_series("Regla «sube si subió»", [round(py[a]["ok_mom"] * 100, 1) for a in ("2022", "2023", "2024")])
cd.add_series("Siempre «sube»", [round(py[a]["ok_maj"] * 100, 1) for a in ("2022", "2023", "2024")])
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.95), Inches(7.4), Inches(4.7), cd)
ch = gf.chart
style_chart(ch, size=13)
set_value_axis(ch, 40, 65, 5, '0"%"')
plot = ch.plots[0]
plot.gap_width = 60
plot.overlap = -5
plot.has_data_labels = True
plot.data_labels.number_format = '0.0"%"'
plot.data_labels.number_format_is_linked = False
plot.data_labels.font.size = Pt(12)
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
for ser, col in zip(plot.series, [BLUE, GRAY, LINE]):
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = col
tb(s, 0.6, 1.65, 7.4, 0.3, P("% de aciertos en alza/baja por año de prueba (el eje parte de 40 %)", 11, False, GRAY, italic=True))
sig = [("+1,4 a +4,9 pts", "sobre la regla «sube si subió» (IC95)", BLUE),
       ("+3,2 a +7,4 pts", "sobre «siempre sube» (IC95)", BLUE),
       ("p = 1,5e-5", "McNemar vs regla de momentum, 6.519 predicciones", GREEN)]
for i, (big, txt, col) in enumerate(sig):
    side_stat(s, 8.3, 1.95 + i * 1.6, 4.4, 1.45, big, txt, col)

# 15 -- calibración
s = new_slide("PARTE 2 · MODELO", "Las probabilidades son honestas: más confianza, más aciertos", notes=(
    "Calibración: cuando el modelo dice alza probable (>60 %), el precio realmente subió 62,6 % de las veces en 2.787 casos. "
    "Cuando dice baja probable (<=40 %), bajó el 63,5 % en 803 casos. En la demo de enero 2025: 68 alza probable, 20 baja probable, "
    "93 sin señal clara. Los umbrales de la app salen de esta tabla."))
tb(s, 0.6, 1.65, 7.4, 0.3, P("% de veces que el precio realmente subió, según la señal del modelo", 11, False, GRAY, italic=True))
bar_chart(s, 0.6, 1.95, 7.4, 4.7,
          ["Baja probable (≤ 40 %)", "40–50 %", "50–60 %", "Alza probable (> 60 %)"],
          [36.5, 45.2, 53.6, 62.6], [GREEN, GRAY, GRAY, RED], 0, 80, 20, size=12)
cal_n = [("2.787", "casos con alza probable → sube 62,6 %", RED),
         ("803", "casos con baja probable → baja 63,5 %", GREEN),
         ("68 · 20 · 93", "de los 181 productos en la demo de enero 2025: alza · baja · sin señal", NAVY)]
for i, (big, txt, col) in enumerate(cal_n):
    side_stat(s, 8.3, 1.95 + i * 1.6, 4.4, 1.45, big, txt, col)

# 16 -- lo que no funcionó
s = new_slide("PARTE 2 · LÍMITES", "Lo que no funcionó, y por qué queda fuera del producto", notes=(
    "Tres límites honestos. 1) Clima y dólar: 57,8 % con clima vs 58,2 % sin él. Matiz: el clima disponible son 3 municipios y "
    "no cubre suroeste ni valle de Aburrá, donde se produce tomate y cebolla; 'no aporta' puede ser falta de cobertura. "
    "2) Precio exacto: MAPE 2024 9,84 % vs 9,97 % de la regla ingenua. "
    "3) Por producto: solo 36 meses de prueba; en papa capira la regla simple gana (80,6 % vs 63,9 %), por eso la app muestra la métrica por producto."))
card_text(s, 0.6, 1.8, 5.2, 2.35, [
    P("Clima y dólar no predicen", 17, True, NAVY, after=6),
    P("57,8 % con clima vs 58,2 % sin él. Correlaciones entre −0,19 y 0,30.", 14, False, INK, after=6),
    P("Matiz: el clima cubre 3 municipios, no suroeste ni valle de Aburrá.", 14, False, GRAY)], pad=0.28)
card_text(s, 0.6, 4.3, 5.2, 2.35, [
    P("El precio exacto no se demuestra", 17, True, NAVY, after=6),
    P("Error 2024 (MAPE): 9,84 % del modelo vs 9,97 % de «igual al mes pasado».", 14, False, INK, after=6),
    P("Por eso la app muestra dirección y probabilidad.", 14, False, GRAY)], pad=0.28)
tb(s, 6.1, 1.8, 6.6, 0.5, P("Por producto la ventaja no es concluyente (36 meses de prueba, ±16 pts)", 15, True, NAVY))
cp = tablero["confiabilidad_producto"]
rows = [["Producto", "Modelo", "Regla «repite»"]]
for k in ("Papa capira", "Papa criolla", "Tomate chonto", "Cebolla junca"):
    m_, r_ = cp[k]["acc_modelo"], cp[k]["acc_repite_direccion"]
    rows.append([k, (pct(m_), GREEN if m_ > r_ else INK), (pct(r_), GREEN if r_ > m_ else INK)])
table(s, 6.1, 2.4, 6.6, [2.8, 1.8, 2.0], rows, size=15, row_h=0.62)
card_text(s, 6.1, 5.65, 6.6, 1.0, P("En papa gana la regla simple (inercia del precio): la app lo dice y remite al calendario.", 14, True, NAVY),
          fill=SOFT_BLUE, anchor=MSO_ANCHOR.MIDDLE, pad=0.3)

# 17 -- arquitectura
s = new_slide("PARTE 2 · ARQUITECTURA", "Arquitectura propuesta: de SIPSA a la app móvil", notes=(
    "Flujo de izquierda a derecha. Decisiones ya tomadas: SQL Server, Python, scikit-learn, FastAPI, Streamlit para el tablero. "
    "Pendiente para la semana 1: elegir React Native (Expo) o Flutter para la app móvil."))
boxes = [
    ("Fuentes", "SIPSA, TRM, clima, producción", GRAY),
    ("ETL Python", "pandas + SQLAlchemy, pruebas pytest", BLUE),
    ("SQL Server", "staging → dimensiones y hechos", NAVY),
    ("Modelo", "Random Forest + calendario estacional", ORANGE),
    ("API", "FastAPI + Pydantic (/v1)", GREEN),
    ("App y tablero", "Móvil (Expo o Flutter) + Streamlit", RED),
]
bw, gap = 1.8, 0.26
for i, (name, det, col) in enumerate(boxes):
    x = 0.6 + i * (bw + gap)
    card(s, x, 1.9, bw, 2.2)
    shape(s, MSO_SHAPE.RECTANGLE, x, 1.9, bw, 0.55, col)
    tb(s, x + 0.08, 1.9, bw - 0.16, 0.55, P(name, 15, True, WHITE, align=PP_ALIGN.CENTER), anchor=MSO_ANCHOR.MIDDLE)
    tb(s, x + 0.12, 2.6, bw - 0.24, 1.4, P(det, 13, False, INK, align=PP_ALIGN.CENTER))
    if i < len(boxes) - 1:
        shape(s, MSO_SHAPE.RIGHT_ARROW, x + bw + 0.02, 2.9, gap - 0.04, 0.3, GRAY)
rows = [["Capa", "Decisión", "Estado"],
        ["Base de datos", "SQL Server (requisito del equipo)", ("Definido", GREEN)],
        ["Modelo y reentreno", "scikit-learn + joblib; cron o Azure Function mensual", ("Definido", GREEN)],
        ["Tablero interno", "Streamlit para el MVP", ("Definido", GREEN)],
        ["App móvil", "React Native (Expo) o Flutter", ("Decidir en semana 1", ORANGE)]]
table(s, 0.6, 4.45, 12.1, [2.8, 6.6, 2.7], rows, size=13, row_h=0.44)

# 18 -- plan 8 semanas
s = new_slide("PARTE 2 · PLAN", "Plan de 8 semanas y responsables", notes=(
    "Ruta crítica: carga a SQL Server (S1-2) → tabla maestra y API de precios (S3-4) → pipeline de entrenamiento (S5) → "
    "API de predicción con la app conectada (S6-7) → demo (S8). El diseño móvil corre en paralelo en S3-4."))
tasks = [
    ("Carga a SQL Server y esquema", "Camilo, María P", 1, 2, BLUE),
    ("Tabla maestra y API de precios", "María P, Camilo", 3, 4, BLUE),
    ("Diseño móvil validado con usuarios", "Daniel", 3, 4, ORANGE),
    ("Pipeline de entrenamiento y reentreno", "Pipe, Alex", 5, 5, GREEN),
    ("API de predicción y app conectada", "Alex, Daniel", 6, 7, GREEN),
    ("Demo desplegada, informe y presentación", "Todos", 8, 8, RED),
]
x0, lw, ow, ww = 0.6, 4.4, 1.9, 0.725
hy = 1.8
shape(s, MSO_SHAPE.RECTANGLE, x0, hy, lw + ow + 8 * ww, 0.5, NAVY)
tb(s, x0 + 0.15, hy, lw, 0.5, P("Entrega", 14, True, WHITE), anchor=MSO_ANCHOR.MIDDLE)
tb(s, x0 + lw + 0.1, hy, ow, 0.5, P("Responsables", 14, True, WHITE), anchor=MSO_ANCHOR.MIDDLE)
for w in range(8):
    tb(s, x0 + lw + ow + w * ww, hy, ww, 0.5, P(f"S{w + 1}", 14, True, WHITE, align=PP_ALIGN.CENTER), anchor=MSO_ANCHOR.MIDDLE)
for i, (name, who_, a, b, col) in enumerate(tasks):
    y = hy + 0.5 + i * 0.7
    shape(s, MSO_SHAPE.RECTANGLE, x0, y, lw + ow + 8 * ww, 0.7, LIGHT if i % 2 == 0 else WHITE)
    tb(s, x0 + 0.15, y, lw - 0.2, 0.7, P(name, 14, True, INK), anchor=MSO_ANCHOR.MIDDLE)
    tb(s, x0 + lw + 0.1, y, ow - 0.1, 0.7, P(who_, 13, False, GRAY), anchor=MSO_ANCHOR.MIDDLE)
    bx = x0 + lw + ow + (a - 1) * ww + 0.06
    card(s, bx, y + 0.17, (b - a + 1) * ww - 0.12, 0.36, col, None, 0.4)
tb(s, 0.6, 6.55, 12.1, 0.35, P("Ruta crítica: SQL Server → tabla maestra y API → entrenamiento → predicción conectada → demo.", 13, False, GRAY, italic=True))

# 19 -- riesgos
s = new_slide("PARTE 2 · RIESGOS", "Cinco riesgos conocidos y cómo se mitigan", notes=(
    "El riesgo que más puede afectar la promesa de 'un mes de anticipación' es el rezago de publicación de DANE: medirlo en la semana 1. "
    "Los datos llegan solo hasta diciembre de 2024: la demo es demostrativa, no operativa, hasta conseguir SIPSA 2025."))
rows = [
    ["Riesgo", "Efecto", "Mitigación"],
    ["Rezago de publicación de DANE", "El «mes de anticipación» puede ser menor", "Medirlo en la semana 1; si pasa de 2 semanas, comunicar «próximos 30 días»"],
    ["Datos solo hasta dic-2024", "Predicción demostrativa, no operativa", "Mostrar «datos hasta dic-2024» y conseguir SIPSA 2025"],
    ["Ventaja modesta (≈3 puntos)", "Los usuarios esperan más", "Mensaje claro: dirección y probabilidad, no certeza"],
    ["Ventaja no probada por producto", "Alerta de tomate poco confiable", "Mostrar la métrica por producto en la app"],
    ["Clima de solo 3 municipios", "Representatividad limitada", "Declararlo en «Acerca de los datos»"],
]
table(s, 0.6, 1.8, 12.1, [3.3, 3.6, 5.2], rows, size=14, row_h=0.78)

# 20 -- cierre / decisiones
s = new_slide(navy=True, notes=(
    "Cerrar pidiendo las cuatro decisiones. Primer paso concreto: confirmar los 4 productos y asignar a alguien para medir "
    "el rezago de publicación de DANE y conseguir SIPSA 2025."))
tb(s, 0.8, 0.7, 10, 0.4, P("DECISIONES REQUERIDAS", 14, True, PALE))
tb(s, 0.8, 1.2, 11.7, 1.0, P("Cuatro decisiones para arrancar la semana 1", 38, True, WHITE))
dec = [
    "Aprobar el replanteamiento: de «precio exacto» a «alerta de dirección + calendario».",
    "Confirmar los 4 productos reales: papa capira, papa criolla limpia, tomate chonto regional y cebolla junca.",
    "Confirmar app móvil primero y tablero web después (Streamlit para el MVP).",
    "Asignar responsable para conseguir SIPSA 2025 y medir el rezago de publicación.",
]
for i, t in enumerate(dec):
    y = 2.6 + i * 0.95
    circle_num(s, 0.8, y, 0.6, i + 1, BLUE, 20)
    tb(s, 1.65, y - 0.05, 10.8, 0.75, P(t, 19, False, WHITE), anchor=MSO_ANCHOR.MIDDLE)
card_text(s, 0.8, 6.45, 11.7, 0.6, P("Primer paso: elegir hoy a quien mide el rezago de DANE y consigue SIPSA 2025.", 16, True, WHITE),
          fill=BLUE, anchor=MSO_ANCHOR.MIDDLE, pad=0.3)

OUT.parent.mkdir(exist_ok=True)
prs.save(OUT)
print("OK", OUT, state["n"], "diapositivas")
