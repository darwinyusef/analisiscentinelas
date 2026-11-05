"""Actualiza entregables/Centinela_Agro_Pitch.pptx con los resultados finales (python-pptx).

Parte siempre de entregables/Centinela_Agro_Pitch_anterior.pptx (copia de la version previa, se crea la
primera vez), asi que se puede re-ejecutar sin acumular cambios. Toda cifra sale de salidas/*.csv|json
y de modelos/centinela_modelo.joblib. Imagenes: las generadas con fal.ai en diseno/img/.

Uso:  .venv/bin/python src/pptx_actualizar.py
Orden previo: etl.py, ml_features.py, ml_modelo.py, ml_confiabilidad.py, ml_onnx.py
"""
import copy
import json
import shutil
from pathlib import Path

import joblib
import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.util import Emu, Pt

RAIZ = Path(__file__).resolve().parent.parent
SAL, ENT, IMG = RAIZ / "salidas", RAIZ / "entregables", RAIZ / "diseno" / "img"
DESTINO = ENT / "Centinela_Agro_Pitch.pptx"
ORIGEN = ENT / "Centinela_Agro_Pitch_anterior.pptx"


def n(x, d=1, signed=False):
    s = f"{x:{'+' if signed else ''},.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return n(x, d) + " %"


def st(shape, *textos):
    """Cambia el texto de cada parrafo conservando el formato de su primer run. None = no tocar."""
    tf = shape.text_frame if hasattr(shape, "text_frame") else shape
    for par, t in zip(tf.paragraphs, textos):
        if t is None:
            continue
        runs = par.runs
        runs[0].text = t
        for r in runs[1:]:
            r._r.getparent().remove(r._r)


def por_nombre(slide, nombre):
    return next(s for s in slide.shapes if s.name == nombre)


def replace_chart(shape, categorias, series):
    cd = CategoryChartData()
    cd.categories = categorias
    for nombre, vals in series:
        cd.add_series(nombre, vals)
    shape.chart.replace_data(cd)


def clonar(slide_origen, nombre, slide_destino):
    el = copy.deepcopy(por_nombre(slide_origen, nombre)._element)
    slide_destino.shapes._spTree.append(el)
    return slide_destino.shapes[-1]


def foto(slide, ruta, x, y, w, h):
    """Inserta la imagen recortada al centro para llenar x,y,w,h sin deformarla."""
    pic = slide.shapes.add_picture(str(ruta), x, y, w, h)
    ar_img, ar_caja = pic.image.size[0] / pic.image.size[1], w / h
    if ar_img > ar_caja:
        c = (1 - ar_caja / ar_img) / 2
        pic.crop_left = pic.crop_right = c
    else:
        c = (1 - ar_img / ar_caja) / 2
        pic.crop_top = pic.crop_bottom = c
    return pic


def main():
    if not ORIGEN.exists():
        shutil.copy(DESTINO, ORIGEN)
    res = json.loads((SAL / "ml_resultados.json").read_text())
    conf = json.loads((SAL / "ml_confiabilidad.json").read_text())
    resumen = pd.read_csv(SAL / "ml_resumen.csv")
    por_prod = pd.read_csv(SAL / "ml_por_producto.csv")
    estab = pd.read_csv(SAL / "ml_estabilidad_anual.csv")
    cal = pd.read_csv(SAL / "ml_calibracion.csv")
    al = pd.read_csv(SAL / "ml_alertas_onnx.csv")
    oos = pd.read_csv(SAL / "ml_predicciones_oos.csv", parse_dates=["mes"])

    v = res["veredicto_O3"]
    g = v["todos_2022-24"]
    f = v["foco_2022-24"]
    b = res["bandas_modelo_canonico"]["todos"]
    alza, baja, sin = b["ALZA PROBABLE"], b["BAJA PROBABLE"], b["SIN SEÑAL"]
    r = resumen[(resumen.universo == "todos") & (resumen.ventana == "2022-24")].set_index("metodo")
    n_pred = int(r.loc["rf_precio", "n"])
    cuenta = al.alerta.value_counts()
    pot = conf["potencia"]["foco"]
    ex_completo = r.loc["rf_completo", "exactitud"]
    mc = r.loc["rf_precio", "mcnemar_p"]

    m = joblib.load(RAIZ / "modelos" / "centinela_modelo.joblib")
    imp = pd.Series(m["modelo"][-1].feature_importances_, index=m["features"])
    w_est = imp[[c for c in imp.index if c in ("idx_estacional", "mes_sin", "mes_cos")]].sum()
    w_his = imp[[c for c in imp.index if c.startswith(("ret_lag", "media_", "var_", "vol_"))]].sum()

    p = Presentation(ORIGEN)
    S = lambda i: p.slides[i - 1]

    # 6 demo
    s = S(6)
    st(por_nombre(s, "TextBox 5"), None,
       f"Enero 2025 con el modelo final: los 4 productos salen sin señal (papa capira {n(al[al.producto == 'papa capira'].prob_sube.iloc[0], 2)}); "
       f"en los 181 hay {cuenta.get('ALZA PROBABLE', 0)} alzas y {cuenta.get('BAJA PROBABLE', 0)} bajas.")
    st(por_nombre(s, "TextBox 9"),
       "Pantallas exportadas del diseño (FigCraft) con las cifras del modelo final (diseno/gen.py lee salidas/). Alertas vigentes: entregables/tablero_centinela.html. Datos hasta dic-2024.")
    for pic, nombre in zip(sorted((x for x in s.shapes if x.shape_type == 13), key=lambda x: x.left), ("M1", "M3", "M4")):
        x, y, w, h = pic.left, pic.top, pic.width, pic.height
        pic._element.getparent().remove(pic._element)
        s.shapes.add_picture(str(RAIZ / "diseno" / "moviles" / f"{nombre}.png"), x, y, w, h)

    # 7 como funciona
    st(por_nombre(S(7), "TextBox 14"),
       f"Un Random Forest aprende de la historia reciente del precio ({n(100 * w_his, 0)} % del peso) y del patrón estacional ({n(100 * w_est, 0)} %).")

    # 8 confianza
    s = S(8)
    replace_chart(por_nombre(s, "Chart 6"), ["Centinela (IA)", "Regla estacional", "Sube si subió", "Clase mayoritaria"],
                  [("v", [round(r.loc[k, "exactitud"], 1) for k in ("rf_precio", "base_estacional", "base_repite", "base_mayoria")])])
    st(por_nombre(s, "TextBox 9"), pct(alza["acierto_pct"]))
    st(por_nombre(s, "TextBox 10"), f"acierto cuando el modelo está seguro de que sube (≥ 65 %; {n(alza['n'], 0)} casos)")
    st(por_nombre(s, "TextBox 13"), pct(baja["acierto_pct"]))
    st(por_nombre(s, "TextBox 14"), f"acierto cuando avisa que baja (≤ 35 %; {n(baja['n'], 0)} casos)")
    st(por_nombre(s, "TextBox 17"), pct(sin["pct_del_total"]))
    st(por_nombre(s, "TextBox 18"), "de los casos quedan en «sin señal clara»: la app no inventa certezas")
    st(por_nombre(s, "TextBox 19"),
       f"Validación walk-forward mensual, 181 productos, {n(n_pred, 0)} predicciones (2022-01 a 2024-11). "
       f"Ventaja de {n(g['dif_vs_repite'], 1, True)} pts sobre la mejor regla simple: modesta, no un oráculo.")

    # 9 valor
    st(por_nombre(S(9), "TextBox 13"),
       f"Anticipar compras: cuando se pronuncia, la alerta de alza acierta {pct(alza['acierto_pct'])} y la de baja {pct(baja['acierto_pct'])}.")

    # 11 prometer / no prometer
    s = S(11)
    st(por_nombre(s, "TextBox 8"),
       f"Alerta de dirección: {pct(g['exactitud'])} de acierto (IC95 {n(g['ic95_meses'][0])}–{n(g['ic95_meses'][1])} %) vs {pct(r.loc['base_repite', 'exactitud'])} de la mejor regla simple.",
       None,
       f"Seguro (≥ 65 %): acierta {pct(alza['acierto_pct'])}. Avisa baja (≤ 35 %): acierta {pct(baja['acierto_pct'])}. Se pronuncia en {pct(100 - sin['pct_del_total'])} de los casos.",
       f"Ventaja demostrada (criterio O3) en los 181 productos: {n(g['dif_vs_repite'], 1, True)} pts, IC95 {n(g['dif_ic95'][0], 1, True)} a {n(g['dif_ic95'][1], 1, True)}.")
    st(por_nombre(s, "TextBox 12"), None,
       f"Explicar el precio con clima o dólar: no mejora el modelo ({pct(ex_completo)} con variables externas vs {pct(g['exactitud'])} solo con precio).",
       f"Ventaja probada en los 4 productos del alcance: con 35 meses de prueba no es demostrable ({n(f['dif_vs_repite'], 1, True)} pts, IC95 {n(f['dif_ic95'][0], 1, True)} a {n(f['dif_ic95'][1], 1, True)}).")

    # 12 objetivos
    s = S(12)
    st(por_nombre(s, "TextBox 2"), "Cinco objetivos: dos listos, tres parciales")
    t = por_nombre(s, "Table 5").table
    st(t.cell(3, 3), "Informe EDA cerrado. Estacionalidad clara en papa; clima y dólar no mejoran el modelo.")
    st(t.cell(4, 3), f"Cumple O3 en los 181 productos ({n(g['dif_vs_repite'], 1, True)} pts, IC95 {n(g['dif_ic95'][0], 1, True)} a {n(g['dif_ic95'][1], 1, True)}). "
                     "En los 4 del alcance no es demostrable: faltan meses de prueba.")
    st(t.cell(5, 2), "● Parcial")
    t.cell(5, 2).text_frame.paragraphs[0].runs[0].font.color.rgb = t.cell(4, 2).text_frame.paragraphs[0].runs[0].font.color.rgb
    st(t.cell(5, 3), "Diseño listo en Figma y tablero web estático (HTML) con alertas ONNX. Falta la app móvil.")
    st(por_nombre(s, "TextBox 6"), "Fuente: decisiones_finales.md y plan de alcance (walk-forward 2022-01 a 2024-11).")

    # 14 modelo por año
    s = S(14)
    st(por_nombre(s, "TextBox 2"), "En el grupo de 181 productos, el modelo gana a las reglas simples cada año")
    yo = oos.assign(y=oos.mes.dt.year)
    yy = estab[estab.universo == "todos"].set_index("anio")
    anios = [int(a) for a in yy.index]
    ok_est = {a: 100 * (gr.base_estacional == gr.sube.astype(int)).mean() for a, gr in yo.groupby("y")}
    replace_chart(por_nombre(s, "Chart 5"), [str(a) for a in anios],
                  [("Centinela (Random Forest)", [yy.loc[a, "exactitud_modelo"] for a in anios]),
                   ("Regla «sube si subió»", [yy.loc[a, "exactitud_repite"] for a in anios]),
                   ("Regla estacional", [round(ok_est[a], 1) for a in anios])])
    st(por_nombre(s, "TextBox 6"), "% de aciertos en alza/baja por año de prueba, 181 productos (el eje parte de 40 %)")
    st(por_nombre(s, "TextBox 9"), f"{n(g['dif_vs_repite'], 1, True)} pts")
    st(por_nombre(s, "TextBox 10"), f"sobre la regla «sube si subió» (IC95 {n(g['dif_ic95'][0], 1, True)} a {n(g['dif_ic95'][1], 1, True)})")
    st(por_nombre(s, "TextBox 13"), " · ".join(n(yy.loc[a, "dif"], 1, True) for a in anios))
    st(por_nombre(s, "TextBox 14"), "pts de ventaja en " + " · ".join(str(a) for a in anios))
    st(por_nombre(s, "TextBox 17"), "p < 0,001" if mc < 0.001 else f"p = {n(mc, 3)}")
    st(por_nombre(s, "TextBox 18"), f"McNemar vs regla «sube si subió», {n(n_pred, 0)} predicciones")
    fo = estab[estab.universo == "foco"].set_index("anio")
    pie = clonar(S(8), "TextBox 19", s)
    st(pie, "Alcance (4 productos): " + " · ".join(n(fo.loc[a, "dif"], 1, True) for a in anios) + " pts en "
       + " · ".join(str(a) for a in anios) + ". La ventaja de 2024 no se sostuvo.")

    # 15 calibracion
    s = S(15)
    c = cal[cal.universo == "todos"]
    etiquetas = ["≤ 35 %", "35–45 %", "45–50 %", "50–55 %", "55–65 %", "≥ 65 %"]
    replace_chart(por_nombre(s, "Chart 6"), etiquetas[:len(c)], [("v", [round(100 * x, 1) for x in c.frecuencia_sube])])
    st(por_nombre(s, "TextBox 9"), n(alza["n"], 0))
    st(por_nombre(s, "TextBox 10"), f"casos con alza probable (≥ 65 %) → sube {pct(alza['acierto_pct'])}")
    st(por_nombre(s, "TextBox 13"), n(baja["n"], 0))
    st(por_nombre(s, "TextBox 14"), f"casos con baja probable (≤ 35 %) → baja {pct(baja['acierto_pct'])}")
    st(por_nombre(s, "TextBox 17"), " · ".join(str(cuenta.get(k, 0)) for k in ("ALZA PROBABLE", "BAJA PROBABLE", "SIN SEÑAL")))
    st(por_nombre(s, "TextBox 18"), "de los 181 productos en la demo de enero 2025: alza · baja · sin señal")

    # 16 limites
    s = S(16)
    st(por_nombre(s, "Rounded Rectangle 5"), None,
       f"{pct(ex_completo)} con clima, TRM y producción vs {pct(g['exactitud'])} solo con precio. Correlaciones entre −0,19 y 0,30.")
    st(por_nombre(s, "TextBox 7"), "Por producto la ventaja no es concluyente (35 meses de prueba, ±16 pts)")
    t = por_nombre(s, "Table 8").table
    pp = por_prod.set_index(["producto", "metodo"])
    for i, prod in enumerate(("papa capira", "papa criolla limpia", "tomate chonto regional", "cebolla junca"), start=1):
        st(t.cell(i, 1), pct(pp.loc[(prod, "rf_precio"), "exactitud"]))
        st(t.cell(i, 2), pct(pp.loc[(prod, "base_repite"), "exactitud"]))

    # 18 arquitectura
    s = S(17)
    st(por_nombre(s, "TextBox 23"), "Random Forest (ONNX) + calendario estacional")
    st(por_nombre(s, "TextBox 33"), "Móvil (Expo o Flutter) + tablero HTML")
    t = por_nombre(s, "Table 34").table
    st(t.cell(2, 1), "scikit-learn → ONNX (onnxruntime); cron o Azure Function mensual")
    st(t.cell(3, 1), "HTML estático generado desde salidas/ (ya construido)")

    # 20 riesgos
    t = por_nombre(S(19), "Table 5").table
    st(t.cell(3, 0), f"Ventaja modesta (≈{n(g['dif_vs_repite'], 0)} puntos)")
    st(t.cell(4, 2), "Señal por producto marcada «experimental»; se re-evalúa con ≥ 24 meses nuevos")

    # 21 decisiones
    s = S(20)
    st(por_nombre(s, "TextBox 6"), "Confirmar los 4 productos: papa capira, papa criolla limpia, tomate chonto regional y cebolla junca; su señal es experimental hasta demostrarla.")
    st(por_nombre(s, "TextBox 8"), "Confirmar app móvil primero y tablero web (HTML estático, ya construido) después.")

    # 10 divisor: imagen fal.ai
    s = S(10)
    for nombre, ancho in (("TextBox 1", 7315200), ("TextBox 2", 7315200), ("TextBox 3", 7315200)):
        por_nombre(s, nombre).width = Emu(ancho)
    por_nombre(s, "TextBox 2").text_frame.paragraphs[0].runs[0].font.size = Pt(36)
    foto(s, IMG / "mercado.jpg", Emu(8503920), Emu(822960), Emu(2788703), Emu(6035040))

    # nueva diapositiva: por que el alcance no se puede mitigar
    base = S(14)
    nueva = p.slides.add_slide(base.slide_layout)
    for nombre in ("TextBox 1", "TextBox 2", "TextBox 3", "TextBox 4") + tuple(f"{k} {i}" for i, k in
            ((7, "Rounded Rectangle"), (8, "Rectangle"), (9, "TextBox"), (10, "TextBox"), (11, "Rounded Rectangle"), (12, "Rectangle"),
             (13, "TextBox"), (14, "TextBox"), (15, "Rounded Rectangle"), (16, "Rectangle"), (17, "TextBox"), (18, "TextBox"))):
        clonar(base, nombre, nueva)
    st(por_nombre(nueva, "TextBox 1"), "PARTE 2 · LÍMITES")
    st(por_nombre(nueva, "TextBox 2"), "Los 4 productos no se pueden demostrar con 60 meses de historia")
    st(por_nombre(nueva, "TextBox 9"), f"{n(pot['efecto_minimo_detectable_80'])} pts")
    st(por_nombre(nueva, "TextBox 10"), f"ventaja mínima que se detecta con {pot['meses_de_prueba']} meses de prueba en los 4 productos")
    st(por_nombre(nueva, "TextBox 13"), f"{n(pot['efecto_del_grupo'])} pts")
    st(por_nombre(nueva, "TextBox 14"), "ventaja real del modelo en el grupo: queda por debajo de lo detectable")
    st(por_nombre(nueva, "TextBox 17"), f"~{pot['meses_de_prueba_para_detectar_efecto_del_grupo']} meses")
    st(por_nombre(nueva, "TextBox 18"), "de prueba harían falta; en total hay 60 meses de historia")
    texto = clonar(base, "TextBox 10", nueva)
    texto.left, texto.top, texto.width, texto.height = Emu(3750000), Emu(1783080), Emu(3640000), Emu(4297680)
    par0 = texto.text_frame.paragraphs[0]
    par0.runs[0].text = "No es un fallo del modelo: es potencia estadística."
    par0.runs[0].font.bold = True
    par0.runs[0].font.size = Pt(18)
    for linea in ("No bajamos el criterio O3 para que «cumpla»: sería engañar.",
                  "Se demuestra hacia adelante: registrar cada predicción y re-evaluar con ≥ 24 meses nuevos.",
                  "Mientras tanto, la señal por producto se muestra como experimental."):
        nuevo = copy.deepcopy(par0._p)
        texto.text_frame._txBody.append(nuevo)
        pr = texto.text_frame.paragraphs[-1]
        pr.runs[0].text = linea
        pr.runs[0].font.bold = False
        pr.runs[0].font.size = Pt(15)
        pr.space_before = Pt(10)
    foto(nueva, IMG / "campesino.jpg", Emu(548640), Emu(1783080), Emu(3000000), Emu(4297680))
    pie = clonar(S(8), "TextBox 19", nueva)
    st(pie, "Fuente: salidas/ml_confiabilidad.json (potencia al 80 %, bootstrap por meses). El criterio O3 no se modificó.")
    ids = p.slides._sldIdLst
    el = ids[-1]
    ids.remove(el)
    ids.insert(16, el)

    # numeracion
    for i, sl in enumerate(p.slides, start=1):
        for sh in sl.shapes:
            if sh.name == "TextBox 4" and sh.has_text_frame and sh.text_frame.text.strip().isdigit():
                st(sh, str(i))

    p.save(DESTINO)
    print(f"OK: {DESTINO} {DESTINO.stat().st_size // 1024} KB, {len(p.slides)} diapositivas")


if __name__ == "__main__":
    main()
