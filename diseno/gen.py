import json, math, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")
steps = []; nid = [1]; FR = {}; LINKS = []


def add(cmd, params, creates=True):
    steps.append({"command": cmd, "params": params})
    if creates:
        nid[0] += 1
        return nid[0]


def frame(key, name, w, h, x, y, fill="#F4F7FA", radius=None):
    pr = {"fill": fill, "clip": True}
    if radius: pr["cornerRadius"] = radius
    i = add("frame.create", {"width": w, "height": h, "name": name, "x": x, "y": y, "props": pr})
    FR[key] = i
    return i


def rect(par, x, y, w, h, fill, r=8, stroke=None, grad=None):
    pr = {"cornerRadius": r}
    if grad: pr["fills"] = [grad]
    else: pr["fill"] = fill
    if stroke: pr["stroke"] = stroke; pr["strokeWeight"] = 1
    return add("shape.rectangle", {"x": x, "y": y, "width": w, "height": h, "parent": par, "props": pr})


def text(par, s, x, y, size=14, fill="#1F2933", w=None, weight=None, align=None):
    pr = {"fontSize": size, "fill": fill}
    if weight: pr["fontStyle"] = weight
    if align: pr["textAlign"] = align
    p = {"text": s, "x": x, "y": y, "parent": par, "props": pr}
    if w: p["width"] = w
    return add("text.create", p)


def pic(par, key, x, y, w, h, r=None):
    i = add("image.place", {"path": os.path.join(IMG, key + ".jpg"), "x": x, "y": y, "width": w, "height": h,
                             "parent": par, "mode": "fill"})
    if r is not None:
        add("node.set", {"ids": [i], "cornerRadius": r}, creates=False)
    return i


def fade(par, x, y, w, h, col, a0="00", a1="F0", r=0):
    g = {"type": "linearGradient", "stops": [col + a0, col + a1], "from": [0.5, 0], "to": [0.5, 1]}
    return rect(par, x, y, w, h, None, r, grad=g)


def hit(par, x, y, w, h, dest, kind="navigate"):
    i = rect(par, x, y, w, h, "#00000000", 0)
    LINKS.append((i, dest, kind))
    return i


def btn(par, x, y, w, h, label, fill, tc, size=16, stroke=None, dest=None, kind="navigate", r=14):
    rect(par, x, y, w, h, fill, r, stroke=stroke)
    text(par, label, x, y + (h - size * 1.25) / 2, size, tc, w=w, weight="Bold", align="center")
    if dest: hit(par, x, y, w, h, dest, kind)


def chip(par, x, y, w, label, c, bg, size=12, h=28):
    rect(par, x, y, w, h, bg, h // 2)
    text(par, label, x, y + (h - size * 1.25) / 2, size, c, w=w, weight="Bold", align="center")


def info_btn(par, x, y, dest, dark=False):
    rect(par, x, y, 30, 30, "#FFFFFF33" if dark else "#EAF1F7", 15)
    text(par, "i", x, y + 5, 17, "#FFFFFF" if dark else BLUE, w=30, weight="Bold", align="center")
    hit(par, x - 6, y - 6, 42, 42, dest, "overlay")


D = json.load(open(os.path.join(HERE, "../analisis/resultados/datos_tablero.json")))
EDA = json.load(open(os.path.join(HERE, "../salidas/eda_stats.json")))
M = pd.read_csv(os.path.join(HERE, "../analisis/resultados/maestra_completa.csv"), parse_dates=["mes"])
SIPSA = {"Papa capira": "papa capira", "Papa criolla": "papa criolla limpia",
         "Tomate chonto": "tomate chonto regional", "Cebolla junca": "cebolla junca"}


def indice(k):
    s = M[M.producto == SIPSA[k]].drop_duplicates("mes").set_index("mes").precio
    r = s / s.groupby(s.index.year).transform("mean")
    return r.groupby(r.index.month).mean()


IDX = {k: indice(k) for k in SIPSA}

# Cifras del modelo final (salidas/); reemplazan las del modelo anterior de datos_tablero.json
SAL = os.path.join(HERE, "../salidas")
_res = json.load(open(os.path.join(SAL, "ml_resultados.json")))
_al = pd.read_csv(os.path.join(SAL, "ml_alertas_onnx.csv"))
_pp = pd.read_csv(os.path.join(SAL, "ml_por_producto.csv"))
_oos = pd.read_csv(os.path.join(SAL, "ml_predicciones_oos.csv"))
_rs = pd.read_csv(os.path.join(SAL, "ml_resumen.csv"))
_g = _rs[(_rs.universo == "todos") & (_rs.ventana == "2022-24")].set_index("metodo")
G_ACC, G_LO, G_HI = _g.loc["rf_precio", "exactitud"], _g.loc["rf_precio", "boot_meses_bajo"], _g.loc["rf_precio", "boot_meses_alto"]
G_REP, G_EST, G_MAY = _g.loc["base_repite", "exactitud"], _g.loc["base_estacional", "exactitud"], _g.loc["base_mayoria", "exactitud"]
BD = _res["bandas_modelo_canonico"]["todos"]
N_PROD = int(_pp.n.iloc[0])
_p = _oos.rf_precio


def _c(v): return f"{v:.1f}".replace(".", ",")


CAL_BANDAS = [("Alza probable (≥65 %)", f"sube {_c(BD['ALZA PROBABLE']['acierto_pct'])} %"),
              ("Entre 50 y 65 %", f"sube {_c(100 * _oos[(_p >= 0.5) & (_p < 0.65)].sube.mean())} %"),
              ("Entre 35 y 50 %", f"sube {_c(100 * _oos[(_p > 0.35) & (_p < 0.5)].sube.mean())} %"),
              ("Baja probable (≤35 %)", f"baja {_c(BD['BAJA PROBABLE']['acierto_pct'])} %")]
D["pred_ene2025"] = {}
D["confiabilidad_producto"] = {}
for _k, _s in SIPSA.items():
    _r = _al[_al.producto == _s].iloc[0]
    D["pred_ene2025"][_k] = dict(p_alza=float(_r.prob_sube), precio_dic24=float(_r.precio),
                                 alerta="SIN SEÑAL CLARA" if _r.alerta == "SIN SEÑAL" else _r.alerta)
    _q = _pp[_pp.producto == _s].set_index("metodo")
    D["confiabilidad_producto"][_k] = dict(acc_modelo=_q.loc["rf_precio", "exactitud"] / 100,
                                           acc_repite_direccion=_q.loc["base_repite", "exactitud"] / 100, n=int(_q.loc["rf_precio", "n"]))
NAVY = "#1F3B5C"; BLUE = "#2C6E9B"; RED = "#C0392B"; GREEN = "#1F6E5C"; GRAY = "#6B7785"; LINE = "#D5DCE4"
HARVEST = "#E4A02B"; INK = "#1F2933"; BG = "#F4F7FA"; PALE = "#DCE6F0"


def fmt(v): return "$" + f"{int(v):,}".replace(",", ".") + " /kg"
def pct(p): return f"{round(p * 100)} %"
def dec(v, n=1): return f"{v:.{n}f}".replace(".", ",")


ALERTA = {"ALZA PROBABLE": ("▲", RED, "#FDECEA"), "BAJA PROBABLE": ("▼", GREEN, "#E6F4F0"),
          "SIN SEÑAL CLARA": ("●", GRAY, "#EEF1F4")}
PRODS = [("Papa capira", "Papa capira", "papa"), ("Papa criolla", "Papa criolla", "papa"),
         ("Tomate chonto", "Tomate chonto", "tomate"), ("Cebolla junca", "Cebolla junca", "cebolla")]
MESES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
MN = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def tabbar(f, activo):
    rect(f, 0, 764, 390, 80, "#FFFFFF", 0, stroke=LINE)
    for i, (n, dest) in enumerate([("Alertas", "M1"), ("Calendario", "M3"), ("Confianza", "M4"), ("Datos", "M5")]):
        c = NAVY if i == activo else GRAY
        if i == activo: rect(f, 24 + i * 90, 764, 60, 4, NAVY, 2)
        text(f, n, 10 + i * 90, 786, 13, c, w=76, weight="Bold" if i == activo else None, align="center")
        hit(f, i * 90 + 8, 766, 84, 70, dest)


def header(f, titulo, sub, img, h=140, back=None, avatar=False, info=None):
    pic(f, img, 0, 0, 390, h)
    fade(f, 0, 0, 390, h, NAVY, "70", "F2")
    if back:
        text(f, "‹", 14, 36, 34, "#FFFFFF")
        hit(f, 0, 30, 60, 50, back)
    else:
        text(f, "CENTINELA AGRO", 20, 44 if h >= 130 else 28, 12, "#F1D9A6", weight="Bold")
    text(f, titulo, 20, h - 76, 25, "#FFFFFF", w=300, weight="Bold")
    text(f, sub, 20, h - 40, 13, PALE, w=330)
    if avatar:
        rect(f, 330, 34, 40, 40, HARVEST, 20)
        text(f, "MR", 330, 44, 15, NAVY, w=40, weight="Bold", align="center")
        hit(f, 322, 28, 56, 56, "P1")
    if info:
        info_btn(f, 340, h - 56, info, dark=True)


# ======================= FLUJO DE ACCESO (fila A, y=0) =======================
# ---- W1 Bienvenida
w1 = frame("W1", "W1 Bienvenida", 390, 844, 0, 0, NAVY)
pic(w1, "bienvenida", 0, 0, 390, 844)
fade(w1, 0, 0, 390, 200, NAVY, "66", "00")
fade(w1, 0, 280, 390, 564, NAVY, "00", "F7")
rect(w1, 24, 56, 38, 38, HARVEST, 19)
text(w1, "C", 24, 62, 22, NAVY, w=38, weight="Bold", align="center")
text(w1, "CENTINELA AGRO", 72, 66, 15, "#FFFFFF", weight="Bold")
text(w1, "Sabe cuándo se mueve el precio de tu canasta", 24, 458, 33, "#FFFFFF", w=342, weight="Bold")
text(w1, "Alertas de alza y baja de papa, tomate y cebolla, con datos oficiales del mercado mayorista.", 24, 596, 15, PALE, w=330)
btn(w1, 24, 664, 342, 54, "Iniciar sesión", HARVEST, NAVY, 17, dest="L1")
btn(w1, 24, 730, 342, 54, "Crear cuenta", "#FFFFFF22", "#FFFFFF", 17, stroke="#FFFFFF", dest="L2")
text(w1, "Explorar como invitado", 0, 800, 14, PALE, w=390, align="center")
hit(w1, 90, 788, 210, 40, "M1")

# ---- L1 Iniciar sesion
l1 = frame("L1", "L1 Iniciar sesión", 390, 844, 430, 0, BG)
pic(l1, "bienvenida", 0, 0, 390, 300)
fade(l1, 0, 0, 390, 300, NAVY, "55", "99")
text(l1, "‹", 14, 36, 34, "#FFFFFF"); hit(l1, 0, 30, 60, 50, "W1")
rect(l1, 24, 92, 38, 38, HARVEST, 19)
text(l1, "C", 24, 98, 22, NAVY, w=38, weight="Bold", align="center")
text(l1, "CENTINELA AGRO", 72, 102, 15, "#FFFFFF", weight="Bold")
rect(l1, 0, 230, 390, 614, "#FFFFFF", [28, 28, 0, 0])
text(l1, "Inicia sesión", 24, 262, 29, NAVY, weight="Bold")
text(l1, "Bienvenida de nuevo a tu tablero de precios", 24, 304, 15, GRAY, w=342)
text(l1, "Correo", 24, 346, 13, NAVY, weight="Bold")
rect(l1, 20, 368, 350, 52, BG, 12, stroke=LINE); text(l1, "marta@correo.com", 36, 384, 16, INK)
text(l1, "Contraseña", 24, 436, 13, NAVY, weight="Bold")
rect(l1, 20, 458, 350, 52, BG, 12, stroke=LINE); text(l1, "••••••••", 36, 474, 16, INK)
text(l1, "Mostrar", 290, 475, 14, BLUE, w=64, weight="Bold", align="right")
text(l1, "¿Olvidaste tu contraseña?", 160, 526, 14, BLUE, w=210, align="right")
btn(l1, 20, 566, 350, 56, "Entrar", NAVY, "#FFFFFF", 17, dest="B1")
rect(l1, 20, 652, 150, 1, LINE, 0); rect(l1, 220, 652, 150, 1, LINE, 0)
text(l1, "o", 170, 642, 15, GRAY, w=50, align="center")
btn(l1, 20, 678, 350, 54, "Continuar con Google", "#FFFFFF", NAVY, 15, stroke=LINE)
text(l1, "¿No tienes cuenta?  Crear cuenta", 0, 764, 15, GRAY, w=390, align="center")
hit(l1, 60, 752, 270, 40, "L2")

# ---- L2 Crear cuenta
l2 = frame("L2", "L2 Crear cuenta", 390, 844, 860, 0, BG)
pic(l2, "tomate", 0, 0, 390, 220)
fade(l2, 0, 0, 390, 220, NAVY, "55", "99")
text(l2, "‹", 14, 36, 34, "#FFFFFF"); hit(l2, 0, 30, 60, 50, "W1")
rect(l2, 24, 76, 38, 38, HARVEST, 19)
text(l2, "C", 24, 82, 22, NAVY, w=38, weight="Bold", align="center")
text(l2, "CENTINELA AGRO", 72, 86, 15, "#FFFFFF", weight="Bold")
rect(l2, 0, 170, 390, 674, "#FFFFFF", [28, 28, 0, 0])
text(l2, "Crea tu cuenta", 24, 198, 27, NAVY, weight="Bold")
for i, (lab, val) in enumerate([("Nombre", "Marta Rodríguez"), ("Correo", "marta@correo.com"), ("Contraseña", "••••••••")]):
    y = 254 + i * 84
    text(l2, lab, 24, y, 13, NAVY, weight="Bold")
    rect(l2, 20, y + 22, 350, 50, BG, 12, stroke=LINE); text(l2, val, 36, y + 37, 16, INK)
text(l2, "Soy…", 24, 508, 13, NAVY, weight="Bold")
for i, (lab, sel) in enumerate([("Productor", True), ("Comerciante", False), ("Familia", False)]):
    x = 20 + i * 119
    rect(l2, x, 530, 112, 42, NAVY if sel else "#FFFFFF", 21, stroke=None if sel else LINE)
    text(l2, lab, x, 541, 14, "#FFFFFF" if sel else NAVY, w=112, weight="Bold", align="center")
rect(l2, 20, 598, 24, 24, HARVEST, 7); text(l2, "✓", 20, 600, 15, NAVY, w=24, weight="Bold", align="center")
text(l2, "Acepto el tratamiento de mis datos", 56, 600, 15, INK, w=310)
btn(l2, 20, 646, 350, 56, "Crear cuenta", NAVY, "#FFFFFF", 17, dest="B1")
text(l2, "¿Ya tienes cuenta?  Inicia sesión", 0, 722, 15, GRAY, w=390, align="center")
hit(l2, 60, 710, 270, 40, "L1")
text(l2, "Tus datos solo personalizan tus alertas.", 0, 784, 13, GRAY, w=390, align="center")

# ---- B1 Bienvenida con productos
b1 = frame("B1", "B1 Bienvenida personalizada", 390, 844, 1290, 0, BG)
pic(b1, "campesino", 0, 0, 390, 250)
fade(b1, 0, 0, 390, 250, NAVY, "33", "F2")
text(b1, "¡Hola, Marta!", 24, 136, 32, "#FFFFFF", weight="Bold")
text(b1, "Bienvenida a Centinela Agro", 24, 182, 16, PALE)
text(b1, "¿Qué productos quieres seguir?", 24, 270, 21, NAVY, w=350, weight="Bold")
text(b1, "Te avisamos cuando se mueva su precio.", 24, 302, 14, GRAY, w=350)
tiles = [("Papa", "papa", True), ("Tomate chonto", "tomate", True), ("Cebolla junca", "cebolla", True), ("Explorar todos", "mercado", False)]
for i, (n, im, sel) in enumerate(tiles):
    x = 16 + (i % 2) * 188; y = 336 + (i // 2) * 180
    pic(b1, im, x, y, 170, 168, 16)
    fade(b1, x, y + 70, 170, 98, NAVY, "00", "E6", r=[0, 0, 16, 16])
    text(b1, n, x + 14, y + 134, 16, "#FFFFFF", w=146, weight="Bold")
    rect(b1, x + 132, y + 10, 28, 28, HARVEST if sel else "#FFFFFF66", 14)
    if sel: text(b1, "✓", x + 132, y + 14, 15, NAVY, w=28, weight="Bold", align="center")
btn(b1, 16, 708, 358, 54, "Continuar", NAVY, "#FFFFFF", 17, dest="M1")
text(b1, "Omitir por ahora", 0, 784, 14, GRAY, w=390, align="center")
hit(b1, 100, 772, 190, 40, "M1")

# ======================= APP (fila B, y=940) =======================
YB = 940
# ---- M1 Alertas
m1 = frame("M1", "M1 Alertas", 390, 844, 0, YB, BG)
header(m1, "Alertas del próximo mes", "Demo: enero 2025 · datos hasta dic-2024", "campesino", 140, avatar=True)
for i, (k, nom, im) in enumerate(PRODS):
    p = D["pred_ene2025"][k]; ic, c, bg = ALERTA[p["alerta"]]
    y = 154 + i * 124
    rect(m1, 16, y, 358, 116, "#FFFFFF", 16, stroke=LINE)
    pic(m1, im, 26, y + 12, 92, 92, 12)
    rect(m1, 16, y + 20, 5, 76, c, 3)
    text(m1, nom, 130, y + 12, 16, NAVY, w=170, weight="Bold")
    text(m1, f"{ic} {pct(p['p_alza'])}", 290, y + 12, 16, c, w=72, weight="Bold", align="right")
    text(m1, fmt(p["precio_dic24"]), 130, y + 38, 24, INK, w=230, weight="Bold")
    chip(m1, 130, y + 76, 176, f"{ic} {p['alerta']}", c, bg)
    hit(m1, 16, y, 358, 116, "M2")
btn(m1, 16, 660, 174, 60, "ⓘ  Cómo leer", "#EAF1F7", NAVY, 15, dest="m_alerta", kind="overlay")
btn(m1, 200, 660, 174, 60, f"{_c(G_ACC)} % de acierto", "#FFF7E8", "#8A5A14", 15, dest="m_conf", kind="overlay")
tabbar(m1, 0)

# ---- M2 Detalle
m2 = frame("M2", "M2 Detalle - Papa capira", 390, 844, 430, YB, BG)
pic(m2, "papa", 0, 0, 390, 196)
fade(m2, 0, 0, 390, 196, NAVY, "55", "F0")
text(m2, "‹", 14, 36, 34, "#FFFFFF"); hit(m2, 0, 30, 60, 50, "M1")
text(m2, "Papa capira", 20, 124, 29, "#FFFFFF", weight="Bold")
text(m2, "Central Mayorista de Antioquia", 20, 164, 13, PALE)
p = D["pred_ene2025"]["Papa capira"]; h = D["hist"]["Papa capira"]
ic, c, bg = ALERTA[p["alerta"]]
text(m2, fmt(p["precio_dic24"]), 20, 208, 32, INK, w=190, weight="Bold")
chip(m2, 196, 216, 178, f"{ic} {p['alerta']} · {pct(p['p_alza'])}", c, bg, h=32)
rect(m2, 16, 262, 358, 190, "#FFFFFF", 16, stroke=LINE)
text(m2, "Últimos 24 meses", 30, 274, 14, NAVY, weight="Bold")
ser = list(h["serie"].items())[-24:]; vals = [v for _, v in ser]; lo, hi = min(vals), max(vals)
text(m2, f"mín {fmt(lo)[:-4]} · máx {fmt(hi)[:-4]}", 200, 276, 12, GRAY, w=160, align="right")
for i, (mes, v) in enumerate(ser):
    bh = 20 + (v - lo) / (hi - lo) * 100
    rect(m2, 28 + i * 14.3, 436 - bh, 11, bh, BLUE if i < 23 else c, 2)
I = IDX["Papa capira"]; cm = int(I.idxmax()); bm = int(I.idxmin())
rect(m2, 16, 466, 358, 98, "#FFFFFF", 16, stroke=LINE)
text(m2, f"▲ Más cara en {MN[cm]}  (+{round((I.max() - 1) * 100)} % sobre su promedio)", 30, 482, 14, RED, w=330, weight="Bold")
text(m2, f"▼ Más barata en {MN[bm]}  ({round((I.min() - 1) * 100)} % bajo su promedio)", 30, 520, 14, GREEN, w=330, weight="Bold")
btn(m2, 16, 580, 174, 60, "ⓘ  Por qué esta alerta", "#FFF7E8", "#8A5A14", 14, dest="m_porque", kind="overlay")
btn(m2, 200, 580, 174, 60, "ⓘ  Fuerza estacional", "#EAF1F7", NAVY, 14, dest="m_fuerza", kind="overlay")
btn(m2, 16, 658, 358, 54, "★  Seguir este producto", NAVY, "#FFFFFF", 16)
tabbar(m2, 0)

# ---- M3 Calendario
m3 = frame("M3", "M3 Calendario", 390, 844, 860, YB, BG)
header(m3, "Calendario estacional", "Precio de cada mes vs su promedio anual", "cebolla", 128, info="m_cal")


def col(v):
    if v >= 1.15: return "#C0392B"
    if v >= 1.05: return "#E8A59C"
    if v >= 0.95: return "#E4E8ED"
    if v >= 0.85: return "#9CCBBE"
    return "#1F6E5C"


for j, m in enumerate(MESES): text(m3, m, 98 + j * 22.5, 138, 12, GRAY, w=20, align="center")
for i, (k, nom, im) in enumerate(PRODS):
    y = 160 + i * 52
    text(m3, nom.split()[0] + "\n" + nom.split()[1], 16, y + 6, 12, NAVY, w=76, weight="Bold")
    for j in range(12):
        rect(m3, 92 + j * 22.5, y, 20, 44, col(float(IDX[k][j + 1])), 4)
for i, cc in enumerate(["#1F6E5C", "#9CCBBE", "#E4E8ED", "#E8A59C", "#C0392B"]):
    rect(m3, 92 + i * 54, 376, 50, 12, cc, 4)
text(m3, "Más barato", 16, 374, 12, GRAY, w=74)
text(m3, "Más caro", 300, 392, 12, GRAY, w=74, align="right")
text(m3, "Mejor y peor mes", 16, 420, 17, NAVY, weight="Bold")
for i, (k, nom, im) in enumerate(PRODS):
    y = 450 + i * 76
    Ik = IDX[k]; s = EDA["fuerza_stl"][k]["estacional"]
    rect(m3, 16, y, 358, 68, "#FFFFFF", 14, stroke=LINE)
    pic(m3, im, 24, y + 10, 48, 48, 10)
    text(m3, nom, 84, y + 10, 15, NAVY, w=170, weight="Bold")
    text(m3, f"Caro: {MN[int(Ik.idxmax())]}  ·  Barato: {MN[int(Ik.idxmin())]}", 84, y + 36, 14, INK, w=190)
    chip(m3, 276, y + 20, 88, f"Fuerza {dec(s, 2)}", NAVY, "#EAF1F7")
tabbar(m3, 1)

# ---- M4 Confiabilidad
m4 = frame("M4", "M4 Confiabilidad", 390, 844, 1290, YB, BG)
header(m4, "Confiabilidad", "Prueba real 2022–2024, sin mirar el futuro", "bienvenida", 124)
text(m4, f"{_c(G_ACC)} %", 20, 134, 44, NAVY, weight="Bold")
text(m4, "de aciertos en la dirección", 20, 190, 14, GRAY, w=250)
chip(m4, 270, 150, 100, "ⓘ  IC95", BLUE, "#EAF1F7", 13, 32)
hit(m4, 262, 142, 116, 46, "m_ic", "overlay")
text(m4, "Frente a reglas simples (el eje parte de 50 %)", 20, 218, 14, NAVY, weight="Bold")
modelos = [("Modelo (RF)", G_ACC, BLUE), ("Regla estacional", G_EST, "#7FA8C6"), ("Repite dirección", G_REP, "#B8C7D6"), ("Clase mayoritaria", G_MAY, "#D5DCE4")]
for i, (n, v, cc) in enumerate(modelos):
    y = 242 + i * 30
    text(m4, n, 20, y + 5, 13, INK, w=112)
    rect(m4, 134, y, (v - 50) * 16, 24, cc, 5)
    text(m4, f"{dec(v)} %", 140 + (v - 50) * 16, y + 5, 13, INK, weight="Bold")
text(m4, "Cuando el modelo avisa…", 20, 372, 14, NAVY, weight="Bold")
for i, (a, b) in enumerate(CAL_BANDAS):
    y = 396 + i * 31
    rect(m4, 16, y, 358, 27, "#FFFFFF", 7, stroke=LINE)
    text(m4, a, 26, y + 6, 13, INK, w=200); text(m4, b, 244, y + 6, 13, NAVY, w=120, weight="Bold", align="right")
text(m4, f"Por producto ({N_PROD} meses): modelo vs regla simple", 20, 528, 14, NAVY, weight="Bold")
for i, (k, nom, im) in enumerate(PRODS):
    c4 = D["confiabilidad_producto"][k]; y = 552 + i * 28
    rect(m4, 16, y, 358, 24, "#FFFFFF", 6, stroke=LINE)
    text(m4, nom, 26, y + 5, 13, INK, w=150)
    text(m4, f"{dec(c4['acc_modelo'] * 100)} %  vs  {dec(c4['acc_repite_direccion'] * 100)} %", 200, y + 5, 13, NAVY, w=164, weight="Bold", align="right")
btn(m4, 16, 676, 358, 64, "ⓘ  Límites: acierta cerca de 6 de cada 10", "#FFF7E8", "#8A5A14", 15, dest="m_lim", kind="overlay")
tabbar(m4, 2)

# ---- M5 Datos
m5 = frame("M5", "M5 Acerca de los datos", 390, 844, 1720, YB, BG)
header(m5, "Acerca de los datos", "De dónde sale cada número", "mercado", 124)
FUENTES = [("Precios", "SIPSA-DANE · mensual 2020–2024", "SIPSA-DANE, Central Mayorista de Antioquia, mensual 2020–2024. 181 de 220 productos tienen los 60 meses completos.", "papa"),
           ("Calidad", "Fechas y escala corregidas", "Fechas y escala de precio corregidas y auditadas: de 11 a 60 meses distintos y 154.433 precios reescalados.", "tomate"),
           ("Clima", "Open-Meteo · solo contexto", "Open-Meteo, 3 municipios ponderados por producción. No cubre el suroeste ni el valle de Aburrá. Se usa solo como contexto.", "bienvenida"),
           ("Dólar (TRM)", "datos.gov.co · solo contexto", "datos.gov.co, promedio mensual. Se muestra como contexto: no mejora la predicción.", "mercado"),
           ("Producción", "Anual, Antioquia · solo contexto", "Producción anual de Antioquia en toneladas. Se muestra solo como contexto.", "cebolla"),
           ("Actualización", "Datos hasta dic-2024", "Datos hasta dic-2024. La predicción es demostrativa hasta cargar SIPSA 2025.", "campesino")]
for i, (a, b, long, im) in enumerate(FUENTES):
    y = 140 + i * 100
    rect(m5, 16, y, 358, 90, "#FFFFFF", 16, stroke=LINE)
    rect(m5, 30, y + 22, 46, 46, "#EAF1F7", 23)
    text(m5, str(i + 1), 30, y + 33, 20, BLUE, w=46, weight="Bold", align="center")
    text(m5, a, 90, y + 20, 17, NAVY, w=230, weight="Bold")
    text(m5, b, 90, y + 48, 13, GRAY, w=240)
    text(m5, "›", 336, y + 26, 34, GRAY, w=28)
    hit(m5, 16, y, 358, 90, f"m_dato{i}", "overlay")
tabbar(m5, 3)

# ---- P1 Perfil
p1 = frame("P1", "P1 Perfil", 390, 844, 2150, YB, BG)
pic(p1, "campesino", 0, 0, 390, 220)
fade(p1, 0, 0, 390, 220, NAVY, "40", "F0")
text(p1, "‹", 14, 36, 34, "#FFFFFF"); hit(p1, 0, 30, 60, 50, "M1")
rect(p1, 143, 150, 104, 104, "#FFFFFF", 52)
rect(p1, 149, 156, 92, 92, HARVEST, 46)
text(p1, "MR", 149, 182, 32, NAVY, w=92, weight="Bold", align="center")
text(p1, "Marta Rodríguez", 0, 268, 24, NAVY, w=390, weight="Bold", align="center")
chip(p1, 110, 304, 170, "Productora · Antioquia", GREEN, "#E6F4F0", 13, 30)
text(p1, "Productos que sigo", 20, 358, 17, NAVY, weight="Bold")
for i, (n, im) in enumerate([("Papa", "papa"), ("Tomate", "tomate"), ("Cebolla", "cebolla")]):
    x = 16 + i * 122
    pic(p1, im, x, 392, 114, 114, 16)
    fade(p1, x, 450, 114, 56, NAVY, "00", "E6", r=[0, 0, 16, 16])
    text(p1, n, x + 12, 480, 15, "#FFFFFF", weight="Bold")
rect(p1, 16, 528, 358, 64, "#FFFFFF", 16, stroke=LINE)
text(p1, "Alertas por correo", 32, 548, 16, INK, weight="Bold")
rect(p1, 316, 546, 44, 26, GREEN, 13); rect(p1, 338, 549, 20, 20, "#FFFFFF", 10)
rect(p1, 16, 604, 358, 64, "#FFFFFF", 16, stroke=LINE)
text(p1, "Acerca de los datos", 32, 624, 16, INK, weight="Bold"); text(p1, "›", 336, 616, 30, GRAY, w=24)
hit(p1, 16, 604, 358, 64, "M5")
btn(p1, 16, 688, 358, 54, "Cerrar sesión", "#FFFFFF", RED, 16, stroke="#E8B4AE", dest="W1")
tabbar(p1, -1)

# ======================= MODALES (filas C y D) =======================
CP = D["confiabilidad_producto"]["Papa capira"]
MODALES = [
    ("m_alerta", "Cómo leer una alerta",
     "▲ Alza probable: al menos 65 % de probabilidad de que el precio suba el próximo mes.\n▼ Baja probable: 35 % o menos.\n● Sin señal clara: entre 35 y 65 %; pasa en 8 de cada 10 casos y no significa que no vaya a pasar nada.\nEs una señal de dirección, no un precio exacto.", "mercado"),
    ("m_conf", "Qué tan confiable es",
     f"El modelo acierta la dirección {_c(G_ACC)} % de las veces (IC95: {_c(G_LO)}–{_c(G_HI)} %). La mejor regla simple acierta {_c(G_EST)} %.\nSe probó con datos de 2022 a 2024, sin mirar el futuro. Abre Confiabilidad para ver el detalle.", "campesino"),
    ("m_porque", "Por qué esta alerta",
     f"En papa capira la regla «repite la dirección del último mes» acertó más ({dec(CP['acc_repite_direccion'] * 100)} % frente a {dec(CP['acc_modelo'] * 100)} % del modelo, {CP['n']} meses).\nLa papa tiene inercia: si bajó, suele seguir. Úsalo junto al calendario.", "papa"),
    ("m_fuerza", "Fuerza estacional",
     f"Mide de 0 a 1 cuánto del precio sigue un patrón anual (STL). Papa capira: {dec(EDA['fuerza_stl']['Papa capira']['estacional'], 2)}, la más alta de los 4 productos.\nEn papa es fiable; en cebolla es moderada y en tomate débil. Tómalo como tendencia del mes, no como regla.\nContexto: producción de Antioquia 2024, 227 mil t.", "papa"),
    ("m_cal", "Cómo leer el calendario",
     "Cada casilla compara el precio de ese mes con el promedio de su año.\nRojo: más caro de lo normal (≥ 1,05 caro, ≥ 1,15 muy caro). Verde: más barato (< 0,95 barato, < 0,85 muy barato).\nSirve para planear la temporada, no para predecir un mes puntual.", "cebolla"),
    ("m_ic", "Qué es el IC95",
     f"Es el margen de error del {_c(G_ACC)} %: con 95 % de confianza, el acierto real está entre {_c(G_LO)} % y {_c(G_HI)} %.\nPor producto ({N_PROD} meses) el margen sube a ±16 puntos.", "bienvenida"),
    ("m_lim", "Límites de esta cifra",
     f"Acierta cerca de 6 de cada 10 veces.\nLa ventaja se probó sobre 181 productos juntos. Por producto son solo {N_PROD} meses (±16 puntos): no es concluyente, y en papa capira la regla simple gana.\nLa señal de estos 4 productos es experimental.\nNo predice el precio exacto ni es una garantía.", "mercado"),
]
for i, (a, b, long, im) in enumerate(FUENTES):
    MODALES.append((f"m_dato{i}", a, long, im))

WM = 330; TW = 290
for n, (key, title, body, im) in enumerate(MODALES):
    row, colx = divmod(n, 7)
    x = colx * 370; y = 2000 + row * 560
    tl = max(1, math.ceil(len(title) / (TW / 12.5)))
    bl = sum(max(1, math.ceil(len(par) / (TW / 8.1))) for par in body.split("\n"))
    top = 136
    ty = top + 18; by = ty + tl * 30 + 8
    bh = bl * 22 + body.count("\n") * 8
    btn_y = by + bh + 22
    H = btn_y + 50 + 22
    f = frame(key, f"Modal - {title}", WM, int(H), x, y, "#FFFFFF", 22)
    pic(f, im, 0, 0, WM, top, [22, 22, 0, 0])
    fade(f, 0, 0, WM, top, NAVY, "00", "55", r=[22, 22, 0, 0])
    text(f, title, 20, ty, 22, NAVY, w=TW + 20, weight="Bold")
    text(f, body, 20, by, 15, INK, w=TW + 20)
    btn(f, 20, btn_y, WM - 40, 50, "Entendido", NAVY, "#FFFFFF", 16)
    hit(f, 20, btn_y, WM - 40, 50, None, "close")

# ======================= Escritorio y sistema =======================
f = frame("D1", "D1 Tablero web - Alertas", 1280, 800, 0, 3300, BG)
pic(f, "bienvenida", 0, 0, 1280, 140)
fade(f, 0, 0, 1280, 140, NAVY, "99", "F2")
text(f, "CENTINELA AGRO", 40, 40, 24, "#FFFFFF", weight="Bold")
text(f, "Alertas del próximo mes", 40, 84, 22, "#FFFFFF", weight="Bold")
text(f, "Demo: enero 2025 · datos hasta dic-2024", 900, 48, 14, PALE)
for i, (k, nom, im) in enumerate(PRODS):
    p = D["pred_ene2025"][k]; ic, c, bg = ALERTA[p["alerta"]]; x = 40 + i * 300
    rect(f, x, 170, 280, 170, "#FFFFFF", 14, stroke=LINE); rect(f, x, 170, 8, 170, c, 4)
    pic(f, im, x + 196, 184, 68, 68, 12)
    text(f, nom, x + 24, 184, 16, NAVY, w=170, weight="Bold")
    text(f, fmt(p["precio_dic24"]), x + 24, 214, 26, INK, w=180, weight="Bold")
    text(f, f"{ic} Prob. de alza {pct(p['p_alza'])}", x + 24, 260, 14, c, w=240)
    chip(f, x + 24, 296, 190, f"{ic} {p['alerta']}", c, bg)
text(f, "Precio histórico y señal", 40, 366, 18, NAVY, weight="Bold")
rect(f, 40, 400, 780, 330, "#FFFFFF", 14, stroke=LINE)
ser = list(D["hist"]["Papa capira"]["serie"].values()); lo, hi = min(ser), max(ser)
for i, v in enumerate(ser):
    bh = 20 + (v - lo) / (hi - lo) * 250
    rect(f, 56 + i * 12.4, 705 - bh, 9, bh, BLUE, 2)
text(f, "Papa capira, mensual 2020–2024", 60, 410, 13, GRAY)
rect(f, 850, 400, 390, 330, "#FFFFFF", 14, stroke=LINE)
text(f, "Confiabilidad", 875, 420, 18, NAVY, weight="Bold")
text(f, f"{_c(G_ACC)} % de aciertos 2022–24\n(IC95 {_c(G_LO)}–{_c(G_HI)} %)\nRegla simple: {_c(G_REP)} %\nAlza ≥65 %: acierta {_c(BD['ALZA PROBABLE']['acierto_pct'])} %\nBaja ≤35 %: acierta {_c(BD['BAJA PROBABLE']['acierto_pct'])} %\n\nPor producto aún no concluyente.\nNo es precio exacto ni garantía.", 875, 460, 15, INK, w=340)
text(f, "Fuentes: SIPSA-DANE, Open-Meteo, datos.gov.co", 40, 755, 13, GRAY)

d = frame("DS", "0 Sistema de diseno", 640, 560, 1360, 3300, "#FFFFFF")
text(d, "Sistema de diseño", 32, 24, 24, NAVY, weight="Bold")
sw = [("Primario", NAVY), ("Acento", BLUE), ("Cosecha (CTA)", HARVEST), ("Alza probable", RED), ("Baja probable", GREEN), ("Sin señal", GRAY),
      ("Fondo", BG), ("Aviso", "#FFF7E8"), ("Info", "#EAF1F7")]
for i, (n, c) in enumerate(sw):
    x = 32 + (i % 3) * 200; y = 80 + (i // 3) * 112
    rect(d, x, y, 170, 66, c, 10, stroke=LINE); text(d, f"{n}  {c}", x, y + 74, 13, INK, w=190)
text(d, "Tipografía: Inter. La alerta siempre lleva símbolo (▲ ▼ ●) y texto, no solo color. Toque mínimo 44 px.", 32, 424, 14, GRAY, w=580)
text(d, "Fotografía: escenas agro 9:16 generadas con IA (fal, flux/dev). Siempre con degradado navy para que el texto se lea.", 32, 480, 14, GRAY, w=580)

# ======================= Interacciones =======================
for src, dest, kind in LINKS:
    if kind == "navigate":
        act = {"type": "navigate", "dest": FR[dest]}
    elif kind == "overlay":
        act = {"type": "openOverlay", "dest": FR[dest], "position": "center", "background": "#0B1A2A99"}
    else:
        act = {"type": "closeOverlay"}
    add("proto.interaction.add", {"id": src, "trigger": {"type": "onClick"}, "action": act,
                                   "transition": {"type": "dissolve"}, "durationMs": 220}, creates=False)
add("proto.flow.add", {"start": FR["W1"], "name": "Flujo completo"}, creates=False)

json.dump(steps, open(os.path.join(HERE, "pantallas.json"), "w"), ensure_ascii=False)
print(len(steps), "steps; last id", nid[0], "frames", len(FR))
