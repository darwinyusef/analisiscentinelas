"""EDA Centinela Agro: genera figuras (salidas/figuras) y estadisticas (salidas/eda_stats.json).

Uso:  .venv/bin/python src/eda.py     (despues de src/etl.py)
Las celdas '# %%' funcionan tambien en VS Code / Colab / Jupyter.
"""
# %% Configuracion
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parent.parent
DL, FIG, SAL = RAIZ / "datos_limpios", RAIZ / "salidas" / "figuras", RAIZ / "salidas"
FIG.mkdir(parents=True, exist_ok=True)

COL = {"papa capira": "#1F3A5F", "papa criolla limpia": "#2E7D9A",
       "tomate chonto regional": "#B5651D", "cebolla junca": "#1F7A5C"}
NOMBRE = {"papa capira": "Papa capira", "papa criolla limpia": "Papa criolla",
          "tomate chonto regional": "Tomate chonto", "cebolla junca": "Cebolla junca"}
PRODS = list(COL)
MES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
sns.set_theme(style="whitegrid", font_scale=0.95)
plt.rcParams.update({"figure.dpi": 130, "savefig.bbox": "tight", "axes.titleweight": "bold",
                     "axes.spines.top": False, "axes.spines.right": False})
S = {}  # estadisticas para el informe


def guardar(nombre):
    plt.savefig(FIG / f"{nombre}.png")
    plt.close()


m = pd.read_csv(DL / "maestra_mensual.csv", parse_dates=["mes"])
cma = pd.read_csv(DL / "sipsa_cma_limpio.csv", parse_dates=["mes"])
clima = pd.read_csv(DL / "clima_mensual.csv", parse_dates=["mes"])
trm = pd.read_csv(DL / "trm_mensual.csv", parse_dates=["mes"])
prod = pd.read_csv(DL / "produccion_limpia.csv")
etl = json.loads((SAL / "etl_log.json").read_text())
qa = pd.read_csv(SAL / "qa_precios_anual.csv")
P = m.pivot(index="mes", columns="producto", values="precio")[PRODS]
LR = np.log(P).diff()  # variacion logaritmica mensual

# %% 1. Calidad de datos: impacto de las correcciones
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
q = etl["qa_fechas"]
ax[0].bar(["Lectura\ningenua", "Corregido"], [q["meses_distintos_lectura_ingenua"], q["meses_distintos_corregidos"]],
          color=["#A63D5E", "#1F7A5C"])
for i, v in enumerate([q["meses_distintos_lectura_ingenua"], q["meses_distintos_corregidos"]]):
    ax[0].text(i, v + 1, str(v), ha="center", fontweight="bold")
ax[0].set(title="Meses distintos detectados (esperado: 60)", ylim=(0, 70))
w = 0.38; x = np.arange(len(qa))
ax[1].bar(x - w / 2, qa.mediana_cruda, w, color="#A63D5E", label="Lectura cruda")
ax[1].bar(x + w / 2, qa.mediana_corregida, w, color="#1F7A5C", label="Corregido")
ax[1].set_yscale("log"); ax[1].set_xticks(x); ax[1].set_xticklabels(qa.anio)
ax[1].set(title="Mediana de precio ($/kg, escala log)"); ax[1].legend()
cats = {"Fecha en texto\n('ene-22')": q["filas_fecha_texto_no_parseada"],
        "Mes leído como\naño 2026": q["filas_parseadas_como_2026"],
        "2020-21: día\n= mes": q["filas_2020_21_con_dia_como_mes"],
        "Precios ×1000\n(punto de miles)": etl["precios_escalados_x1000"]}
ax[2].barh(list(cats), list(cats.values()), color="#2E7D9A")
for i, v in enumerate(cats.values()):
    ax[2].text(v + 1500, i, f"{v:,}".replace(",", "."), va="center", fontsize=9)
ax[2].set(title="Filas afectadas por cada defecto", xlim=(0, 175000)); ax[2].invert_yaxis()
plt.suptitle("Calidad de datos SIPSA: defectos de Excel detectados y corregidos", fontweight="bold", y=1.03)
guardar("fig01_calidad")
S["calidad"] = {"fechas": q, "escalados": etl["precios_escalados_x1000"],
                "filas_limpias": etl["sipsa_filas_limpias"], "productos": etl["sipsa_productos"],
                "mercados": etl["sipsa_mercados"], "cma_productos": etl["cma_productos"],
                "cma_filas": etl["cma_filas"], "encabezados": etl["sipsa_filas_encabezado_o_vacias"],
                "repetidas": etl["sipsa_combinaciones_repetidas"], "dup_prod": etl["produccion_duplicados_exactos"]}

# %% 2. Cobertura del mercado objetivo
cob = cma.groupby("producto").mes.nunique().sort_values()
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
ax[0].hist(cob.values, bins=np.arange(0.5, 61.5, 3), color="#2E7D9A", edgecolor="white")
for p in PRODS:
    ax[0].axvline(cob[p], color=COL[p], lw=2, ls="--")
ax[0].set(title=f"Cobertura en la Central Mayorista ({len(cob)} productos)",
          xlabel="Meses con precio (de 60)", ylabel="N.º de productos")
n_mes = cma.groupby("mes").producto.nunique()
ax[1].plot(n_mes.index, n_mes.values, color="#1F3A5F", lw=2)
ax[1].set(title="Productos reportados por mes en la CMA", ylabel="N.º de productos")
guardar("fig02_cobertura")
S["cobertura"] = {"productos_completos_60": int((cob == 60).sum()), "total": int(len(cob)),
                  "min_mes": int(n_mes.min()), "max_mes": int(n_mes.max())}

# %% 3. Series de precio
fig, axes = plt.subplots(2, 2, figsize=(14, 7), sharex=True)
for a, p in zip(axes.ravel(), PRODS):
    a.plot(P.index, P[p], color=COL[p], lw=1.8, marker="o", ms=3, label="Precio mensual")
    a.plot(P.index, P[p].rolling(12, min_periods=6).mean(), color="black", lw=1.4, ls="--", label="Media móvil 12m")
    a.set_title(NOMBRE[p]); a.set_ylabel("$/kg")
    mx, mn = P[p].idxmax(), P[p].idxmin()
    a.annotate(f"máx {P[p].max():,.0f}".replace(",", "."), (mx, P[p].max()), (0, 8), textcoords="offset points", ha="center", fontsize=8)
    a.annotate(f"mín {P[p].min():,.0f}".replace(",", "."), (mn, P[p].min()), (0, -14), textcoords="offset points", ha="center", fontsize=8)
axes[0, 0].legend(loc="upper left", fontsize=8)
plt.suptitle("Precio mayorista mensual en la Central Mayorista de Antioquia, 2020-2024", fontweight="bold")
plt.tight_layout(); guardar("fig03_series")
res = P.describe().T[["mean", "std", "min", "50%", "max"]]
res["cv_%"] = res["std"] / res["mean"] * 100
res["var_total_%"] = (P.iloc[-1] / P.iloc[0] - 1) * 100
S["precios"] = res.round(1).rename(index=NOMBRE).to_dict("index")

# %% 4. Indice base 100 vs mercado
todo = cma.pivot_table(index="mes", columns="producto", values="precio")
completos = cob[cob == 60].index
idx_mercado = (todo[completos] / todo[completos].iloc[0] * 100).median(axis=1)
fig, ax = plt.subplots(figsize=(11, 4.5))
for p in PRODS:
    ax.plot(P.index, P[p] / P[p].iloc[0] * 100, color=COL[p], lw=2, label=NOMBRE[p])
ax.plot(idx_mercado.index, idx_mercado.values, color="black", lw=2.2, ls="--",
        label=f"Mediana CMA ({len(completos)} productos completos)")
ax.axhline(100, color="grey", lw=0.8)
ax.set(title="Índice de precios (ene-2020 = 100) frente al mercado", ylabel="Índice")
ax.legend(ncol=3, fontsize=9)
guardar("fig04_indice")
S["indice_mercado_fin"] = round(float(idx_mercado.iloc[-1]), 1)

# %% 5. Estacionalidad
rel = P / P.groupby(P.index.year).transform("mean")
fig, axes = plt.subplots(2, 2, figsize=(13, 7), sharey=True)
est = {}
for a, p in zip(axes.ravel(), PRODS):
    d = pd.DataFrame({"r": rel[p], "m": rel.index.month})
    g = d.groupby("m").r
    a.fill_between(range(1, 13), g.min(), g.max(), color=COL[p], alpha=0.18, label="Rango 2020-24")
    a.plot(range(1, 13), g.mean(), color=COL[p], lw=2.5, marker="o", label="Promedio")
    a.axhline(1, color="grey", lw=0.8)
    a.set_xticks(range(1, 13)); a.set_xticklabels(MES, fontsize=8); a.set_title(NOMBRE[p])
    est[NOMBRE[p]] = {"mes_mas_caro": MES[int(g.mean().idxmax()) - 1], "indice_max": round(float(g.mean().max()), 2),
                      "mes_mas_barato": MES[int(g.mean().idxmin()) - 1], "indice_min": round(float(g.mean().min()), 2)}
axes[0, 0].legend(fontsize=8); axes[0, 0].set_ylabel("Precio / promedio del año")
plt.suptitle("Estacionalidad: precio relativo al promedio de su año", fontweight="bold")
plt.tight_layout(); guardar("fig05_estacionalidad")
S["estacionalidad"] = est

# %% 6. Descomposicion STL y fuerza estacional
fig, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True)
fuerza = {}
for a, p in zip(axes, PRODS):
    r = STL(np.log(P[p]), period=12, robust=True).fit()
    a.plot(P.index, r.seasonal, color=COL[p], lw=2)
    a.axhline(0, color="grey", lw=0.8)
    a.set_ylabel("log"); a.set_title(NOMBRE[p], fontsize=10, loc="left")
    fuerza[NOMBRE[p]] = {"estacional": round(float(max(0, 1 - r.resid.var() / (r.seasonal + r.resid).var())), 2),
                         "tendencia": round(float(max(0, 1 - r.resid.var() / (r.trend + r.resid).var())), 2)}
plt.suptitle("Componente estacional (STL, periodo 12) del log-precio", fontweight="bold", y=0.995)
plt.tight_layout(); guardar("fig06_stl")
S["fuerza_stl"] = fuerza

# %% 7. Variaciones mensuales y balance de clases
fig, axes = plt.subplots(1, 3, figsize=(16, 4.3))
for p in PRODS:
    sns.kdeplot(LR[p].dropna() * 100, ax=axes[0], color=COL[p], lw=2, label=NOMBRE[p])
axes[0].set(title="Distribución de la variación mensual", xlabel="% de cambio (log)"); axes[0].legend(fontsize=8)
sube = (LR > 0).sum() / LR.notna().sum() * 100
axes[1].bar([NOMBRE[p] for p in PRODS], [sube[p] for p in PRODS], color=[COL[p] for p in PRODS])
axes[1].axhline(50, color="black", ls="--"); axes[1].set(title="% de meses con alza", ylim=(0, 100))
for i, p in enumerate(PRODS):
    axes[1].text(i, sube[p] + 2, f"{sube[p]:.0f}%", ha="center", fontweight="bold")
axes[1].tick_params(axis="x", labelrotation=15)
umbral = 0.05
tres = pd.DataFrame({NOMBRE[p]: [(LR[p] > umbral).sum() / LR[p].notna().sum(),
                                 (LR[p].abs() <= umbral).sum() / LR[p].notna().sum(),
                                 (LR[p] < -umbral).sum() / LR[p].notna().sum()] for p in PRODS},
                    index=["Sube >5%", "Estable ±5%", "Baja >5%"]).T * 100
tres.plot.barh(stacked=True, ax=axes[2], color=["#A63D5E", "#BDBDBD", "#1F7A5C"], width=0.7)
axes[2].set(title="Clases con umbral ±5%", xlabel="% de meses"); axes[2].legend(fontsize=8, loc="lower right")
guardar("fig07_variaciones")
S["variaciones"] = {NOMBRE[p]: {"sube_%": round(float(sube[p]), 1), "desv_mensual_%": round(float(LR[p].std() * 100), 1),
                                "p5_%": round(float(LR[p].quantile(.05) * 100), 1),
                                "p95_%": round(float(LR[p].quantile(.95) * 100), 1),
                                "estable_5%": round(float(tres.loc[NOMBRE[p], "Estable ±5%"]), 1)} for p in PRODS}

# %% 8. Autocorrelacion (¿hay memoria en la variacion?)
fig, axes = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
acfs = {}
for a, p in zip(axes, PRODS):
    v = LR[p].dropna()
    r = acf(v, nlags=12, fft=False)
    a.bar(range(1, 13), r[1:], color=COL[p])
    lim = 1.96 / np.sqrt(len(v))
    a.axhline(lim, color="red", ls="--", lw=1); a.axhline(-lim, color="red", ls="--", lw=1)
    a.set_title(NOMBRE[p]); a.set_xlabel("Rezago (meses)")
    acfs[NOMBRE[p]] = {"rezago1": round(float(r[1]), 2), "rezago12": round(float(r[12]), 2),
                       "rezagos_significativos": [int(i) for i in range(1, 13) if abs(r[i]) > lim]}
axes[0].set_ylabel("Autocorrelación")
plt.suptitle("Autocorrelación de la variación mensual (líneas rojas = límite 95%)", fontweight="bold", y=1.04)
guardar("fig08_acf")
S["acf"] = acfs

# %% 9. Clima
fig, axes = plt.subplots(2, 2, figsize=(14, 7))
for z, c in zip(["norte", "occidente", "oriente"], ["#1F3A5F", "#B5651D", "#1F7A5C"]):
    d = clima[clima.subregion == z]
    axes[0, 0].plot(d.mes, d.lluvia_mm, color=c, label=z.capitalize())
    axes[0, 1].plot(d.mes, d.temp_media, color=c, label=z.capitalize())
    cic = d.groupby(d.mes.dt.month).lluvia_mm.mean()
    axes[1, 0].plot(range(1, 13), cic.values, color=c, marker="o", label=z.capitalize())
    axes[1, 1].plot(d.mes, d.dias_lluvia, color=c, label=z.capitalize())
axes[0, 0].set(title="Lluvia mensual (mm)"); axes[0, 1].set(title="Temperatura media (°C)")
axes[1, 0].set(title="Ciclo anual de lluvia (promedio 2020-24)"); axes[1, 0].set_xticks(range(1, 13)); axes[1, 0].set_xticklabels(MES, fontsize=8)
axes[1, 1].set(title="Días con lluvia ≥1 mm por mes"); axes[0, 0].legend(fontsize=8)
plt.suptitle("Clima por subregión (municipio de referencia)", fontweight="bold")
plt.tight_layout(); guardar("fig09_clima")
S["clima"] = {z: {"lluvia_anual_mm": round(float(clima[clima.subregion == z].groupby(clima.mes.dt.year).lluvia_mm.sum().mean())),
                  "temp_media": round(float(clima[clima.subregion == z].temp_media.mean()), 1),
                  "municipio": {"norte": "Santa Rosa de Osos", "occidente": "San Jerónimo", "oriente": "El Peñol"}[z]}
              for z in ["norte", "occidente", "oriente"]}

# %% 10. TRM y precios
fig, ax = plt.subplots(figsize=(11, 4.3))
t = trm[(trm.mes >= "2020-01-01")].set_index("mes").trm
ax.plot(t.index, t.values, color="black", lw=2.2, label="TRM promedio mensual")
ax.set_ylabel("COP por USD")
ax2 = ax.twinx(); ax2.grid(False)
for p in PRODS:
    ax2.plot(P.index, P[p], color=COL[p], lw=1.3, alpha=0.8, label=NOMBRE[p])
ax2.set_ylabel("$/kg"); ax.set_title("Dólar (TRM) y precio de los 4 productos")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, ncol=3, fontsize=8, loc="upper left")
guardar("fig10_trm")
S["trm"] = {"min": round(float(t.min())), "max": round(float(t.max())), "mes_max": str(t.idxmax())[:7]}

# %% 11. Produccion de Antioquia
rubros = {"papa": "Papa", "papa criolla": "Papa criolla", "tomate chonto": "Tomate chonto", "cebolla junca": "Cebolla junca"}
fig, axes = plt.subplots(2, 4, figsize=(17, 7))
sr = {}
for j, (r, nombre) in enumerate(rubros.items()):
    d = prod[(prod.rubro == r) & (prod.anio >= 2010) & (prod.anio <= 2024)]
    v = d.groupby("anio").volumen_produccion.sum() / 1000
    ar = d.groupby("anio").area_produccion.sum()
    axes[0, j].bar(v.index, v.values, color=list(COL.values())[j])
    axes[0, j].set(title=f"{nombre}: volumen (mil t)"); axes[0, j].tick_params(axis="x", labelsize=7)
    s = (d[d.anio >= 2020].groupby("subregion").volumen_produccion.sum().sort_values(ascending=False))
    s = (s / s.sum() * 100).head(5)
    axes[1, j].barh(s.index[::-1], s.values[::-1], color=list(COL.values())[j])
    axes[1, j].set(title=f"{nombre}: % del volumen 2020-24")
    sr[nombre] = {"top": {k: round(float(x), 1) for k, x in s.items()},
                  "vol_2024_t": round(float(v.get(2024, np.nan) * 1000)), "vol_2019_t": round(float(v.get(2019, np.nan) * 1000)),
                  "area_2024_ha": round(float(ar.get(2024, np.nan)))}
plt.suptitle("Producción agrícola anual de Antioquia (Datos Colombia)", fontweight="bold")
plt.tight_layout(); guardar("fig11_produccion")
S["produccion"] = sr

# %% 12. Correlaciones con la variacion del mes siguiente
feat = m.pivot(index="mes", columns="producto")
cols = {}
for p in PRODS:
    lluvia = feat[("lluvia_mm", p)]; temp = feat[("temp_media", p)]
    dtrm = np.log(feat[("trm", p)]).diff()
    cols[p] = {f"Δ precio (t-{k})": LR[p].shift(k) for k in (0, 1, 2)}
    cols[p].update({f"Lluvia (t-{k})": lluvia.shift(k) for k in (0, 1, 2, 3)})
    cols[p].update({"Lluvia acum. 3m": lluvia.rolling(3).sum(), "Temp. media": temp,
                    **{f"Δ TRM (t-{k})": dtrm.shift(k) for k in (0, 1, 2)},
                    "Nivel TRM": feat[("trm", p)], "Volumen prod. año ant.": feat[("volumen_prod_t1", p)]})
objetivo = {p: LR[p].shift(-1) for p in PRODS}  # variacion t -> t+1
filas, pvals = {}, {}
for p in PRODS:
    df = pd.DataFrame(cols[p]); df["y"] = objetivo[p]
    df = df.dropna()
    filas[NOMBRE[p]] = {c: stats.spearmanr(df[c], df["y"])[0] for c in cols[p]}
    pvals[NOMBRE[p]] = {c: stats.spearmanr(df[c], df["y"])[1] for c in cols[p]}
C, PV = pd.DataFrame(filas), pd.DataFrame(pvals)
fig, ax = plt.subplots(figsize=(8.5, 7))
ann = C.round(2).astype(str) + np.where(PV < 0.05, "*", "")
sns.heatmap(C, annot=ann, fmt="", cmap="RdBu_r", center=0, vmin=-0.6, vmax=0.6, linewidths=0.5, ax=ax,
            cbar_kws={"label": "Spearman"})
ax.set_title("Correlación de cada variable (en t) con la variación de precio\ndel mes siguiente (t→t+1)   * p<0.05", fontsize=11)
guardar("fig12_correlaciones")
pares = sorted(((c, p) for c in C.index for p in C.columns), key=lambda cp: -abs(C.loc[cp[0], cp[1]]))[:8]
S["correlaciones"] = {"top": [(f"{c} / {p}", round(float(C.loc[c, p]), 2), round(float(PV.loc[c, p]), 3)) for c, p in pares],
                      "n_significativas": int((PV < 0.05).sum().sum()), "n_total": int(PV.size),
                      "esperadas_por_azar": round(float(PV.size * 0.05), 1)}

# %% 13. Dispersion
fig, axes = plt.subplots(2, 4, figsize=(16, 6.5))
for j, p in enumerate(PRODS):
    x1 = feat[("lluvia_mm", p)].shift(2); y = LR[p]
    d = pd.DataFrame({"x": x1, "y": y * 100}).dropna()
    sns.regplot(data=d, x="x", y="y", ax=axes[0, j], color=COL[p], scatter_kws={"s": 18, "alpha": .6}, line_kws={"lw": 1.5})
    r, pv = stats.spearmanr(d.x, d.y)
    axes[0, j].set(title=f"{NOMBRE[p]}\nrho={r:.2f} (p={pv:.2f})", xlabel="Lluvia 2 meses antes (mm)", ylabel="Δ precio %" if j == 0 else "")
    x2 = np.log(feat[("trm", p)]).diff() * 100
    d = pd.DataFrame({"x": x2, "y": y * 100}).dropna()
    sns.regplot(data=d, x="x", y="y", ax=axes[1, j], color=COL[p], scatter_kws={"s": 18, "alpha": .6}, line_kws={"lw": 1.5})
    r, pv = stats.spearmanr(d.x, d.y)
    axes[1, j].set(title=f"rho={r:.2f} (p={pv:.2f})", xlabel="Δ TRM % (mismo mes)", ylabel="Δ precio %" if j == 0 else "")
plt.suptitle("Variación del precio frente a lluvia rezagada y dólar", fontweight="bold")
plt.tight_layout(); guardar("fig13_dispersion")

# %% 14. Sondeo de viabilidad (NO es el modelo final)
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def wilson(k, n, z=1.96):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def construir(df, con_clima=True):
    """Una fila por (producto, mes t); objetivo = log(P[t+1]/P[t]). Solo informacion hasta t."""
    out = []
    for p, g in df.groupby("producto"):
        g = g.sort_values("mes").set_index("mes")
        f = pd.DataFrame(index=g.index)
        lp = np.log(g.precio)
        f["ret0"], f["ret1"], f["ret2"] = lp.diff(), lp.diff().shift(1), lp.diff().shift(2)
        for k in (3, 6, 12):
            f[f"ma{k}"] = lp - lp.rolling(k, min_periods=k).mean()
        f["mes_sin"], f["mes_cos"] = np.sin(2 * np.pi * g.index.month / 12), np.cos(2 * np.pi * g.index.month / 12)
        f["dtrm0"], f["dtrm1"], f["trm_nivel"] = np.log(g.trm).diff(), np.log(g.trm).diff().shift(1), np.log(g.trm)
        if con_clima:
            for k in (0, 1, 2, 3):
                f[f"lluvia_t{k}"] = g.lluvia_mm.shift(k)
            f["lluvia_3m"] = g.lluvia_mm.rolling(3).sum()
            f["temp"] = g.temp_media
            f["vol_prod"] = np.log(g.volumen_prod_t1)
        f["y_ret"] = lp.shift(-1) - lp
        f["producto"] = p
        f["mes_t"] = f.index
        out.append(f.reset_index(drop=True))
    return pd.concat(out, ignore_index=True)


def walk_forward(F, feats, desde, hasta, objetivos):
    """Origen movil: para cada mes t de prueba se entrena solo con filas cuyo objetivo (t'+1) ya ocurrio (t'+1 <= t)."""
    prm = dict(n_estimators=300, max_depth=4, min_samples_leaf=5, random_state=0, n_jobs=-1)
    F = F.dropna(subset=feats + ["y_ret"]).copy()
    F["y"] = (F.y_ret > 0).astype(int)
    res = []
    for t in pd.date_range(desde, hasta, freq="MS"):
        tr = F[F.mes_t <= t - pd.DateOffset(months=1)]
        te = F[(F.mes_t == t) & F.producto.isin(objetivos)]
        if te.empty or len(tr) < 40 or tr.y.nunique() < 2:
            continue
        rf = RandomForestClassifier(**prm, class_weight="balanced").fit(tr[feats], tr.y)
        lg = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=500)).fit(tr[feats], tr.y)
        rr = RandomForestRegressor(**prm).fit(tr[feats], tr.y_ret)
        d = te[["producto", "mes_t", "y", "y_ret", "ret0"]].copy()
        d["rf"], d["logit"] = rf.predict(te[feats]), lg.predict(te[feats])
        d["rf_reg_ret"] = rr.predict(te[feats])
        d["base_mayoria"] = int(tr.y.mean() >= 0.5)
        d["base_persistencia"] = (te.ret0 > 0).astype(int).values
        res.append((d, dict(zip(feats, rf.feature_importances_))))
    return res


FEATS_PRECIO = ["ret0", "ret1", "ret2", "ma3", "ma6", "ma12", "mes_sin", "mes_cos", "dtrm0", "dtrm1", "trm_nivel"]
FEATS_CLIMA = FEATS_PRECIO + ["lluvia_t0", "lluvia_t1", "lluvia_t2", "lluvia_t3", "lluvia_3m", "temp", "vol_prod"]
metodos = {"base_mayoria": "Base: clase mayoritaria", "base_persistencia": "Base: repite última dirección",
           "logit": "Regresión logística", "rf": "Random Forest"}


def evaluar(res, etiqueta, desde=None):
    d = pd.concat([r[0] for r in res])
    if desde is not None:
        d = d[d.mes_t >= desde]
    filas = []
    for k, nom in metodos.items():
        ok = int((d[k] == d.y).sum()); lo, hi = wilson(ok, len(d))
        filas.append({"escenario": etiqueta, "metodo": nom, "n": len(d), "accuracy_%": ok / len(d) * 100,
                      "ic95_bajo": lo * 100, "ic95_alto": hi * 100})
    g = {"mae_rf_pp": float((d.rf_reg_ret - d.y_ret).abs().mean() * 100), "mae_naive_pp": float(d.y_ret.abs().mean() * 100),
         "dir_reg_%": float(((d.rf_reg_ret > 0) == (d.y_ret > 0)).mean() * 100)}
    return pd.DataFrame(filas), d, g


F_core = construir(m)
completos_all = cob[cob == 60].index
big = cma[cma.producto.isin(completos_all)].merge(trm[["mes", "trm"]], on="mes", how="left")
F_big = construir(big, con_clima=False)
runs = {"A. 4 productos · precio+TRM": walk_forward(F_core, FEATS_PRECIO, "2023-01-01", "2024-11-01", PRODS),
        "B. Todos los productos CMA · precio+TRM": walk_forward(F_big, FEATS_PRECIO, "2023-01-01", "2024-11-01", PRODS),
        "C. 4 productos · +clima+producción": walk_forward(F_core, FEATS_CLIMA, "2023-01-01", "2024-11-01", PRODS)}
tab, t24, dets, reg, reg24 = [], [], {}, {}, {}
for etq, r in runs.items():
    a, d_, g_ = evaluar(r, etq); tab.append(a); dets[etq] = d_; reg[etq] = g_
    b, _, g24 = evaluar(r, etq, desde="2023-12-01"); t24.append(b); reg24[etq] = g24
tab, t24 = pd.concat(tab), pd.concat(t24)
tab.to_csv(SAL / "sondeo_viabilidad.csv", index=False)
t24.to_csv(SAL / "sondeo_viabilidad_2024.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
n_all, n_24 = int(tab.n.iloc[0]), int(t24.n.iloc[0])
for a, (T, ttl) in zip(axes, [(tab, f"Prueba 2023-2024 (origen móvil, n={n_all})"),
                              (t24, f"Solo 2024 (año de prueba del PDF, n={n_24})")]):
    piv = T.pivot(index="escenario", columns="metodo", values="accuracy_%")
    lo = T.pivot(index="escenario", columns="metodo", values="ic95_bajo"); hi = T.pivot(index="escenario", columns="metodo", values="ic95_alto")
    w = 0.2
    for i, mt in enumerate(metodos.values()):
        xs = np.arange(len(piv)) + (i - 1.5) * w
        v = piv[mt]
        a.bar(xs, v, w, color=["#BDBDBD", "#8E8E8E", "#2E7D9A", "#1F3A5F"][i], label=mt,
              yerr=[v - lo[mt], hi[mt] - v], error_kw=dict(lw=1, capsize=2))
    a.axhline(50, color="red", ls="--", lw=1)
    a.set_xticks(np.arange(len(piv))); a.set_xticklabels([s.replace(" · ", "\n") for s in piv.index], fontsize=9)
    a.set_title(ttl); a.set_ylim(0, 100)
axes[0].set_ylabel("Exactitud en alza/baja (%)  con IC 95%"); axes[0].legend(fontsize=8, loc="upper left")
plt.suptitle("Sondeo de viabilidad: ¿supera el modelo a las reglas simples? (no es el modelo final)", fontweight="bold")
plt.tight_layout(); guardar("fig14_sondeo")
S["sondeo"] = {"todo": tab.round(1).to_dict("records"), "solo2024": t24.round(1).to_dict("records"),
               "regresion": {k: {a: round(b, 2) for a, b in v.items()} for k, v in reg.items()},
               "regresion_2024": {k: {a: round(b, 2) for a, b in v.items()} for k, v in reg24.items()},
               "n_productos_big": int(len(completos_all)),
               "clase_alza_pct": round(float(dets["A. 4 productos · precio+TRM"].y.mean() * 100), 1)}

# %% 15. Importancia de variables (escenario C) y matriz de confusion
imp = pd.DataFrame([r[1] for r in runs["C. 4 productos · +clima+producción"]]).mean().sort_values()
dC = dets["C. 4 productos · +clima+producción"]
fig, axes = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [1.5, 1]})
axes[0].barh(imp.index, imp.values, color="#2E7D9A"); axes[0].set_title("Importancia media de variables (Random Forest, esc. C)")
cm = confusion_matrix(dC.y, dC.rf)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=axes[1], cbar=False,
            xticklabels=["Pred. baja", "Pred. sube"], yticklabels=["Real baja", "Real sube"])
axes[1].set_title("Matriz de confusión RF 2023-24 (esc. C)")
guardar("fig15_importancia")
S["importancia_top"] = {k: round(float(v), 3) for k, v in imp.sort_values(ascending=False).head(6).items()}

# %% 16. Error de precio: modelo vs regla "igual al mes anterior"
fig, ax = plt.subplots(figsize=(9, 4))
nombres = [e.replace(" · ", "\n") for e in reg]
x = np.arange(len(nombres))
ax.bar(x - 0.2, [g["mae_naive_pp"] for g in reg.values()], 0.4, color="#BDBDBD", label='Regla "igual al mes anterior"')
ax.bar(x + 0.2, [g["mae_rf_pp"] for g in reg.values()], 0.4, color="#1F3A5F", label="Random Forest (regresión)")
ax.set_xticks(x); ax.set_xticklabels(nombres, fontsize=8); ax.set_ylabel("Error absoluto medio (pp de cambio)")
ax.set_title("Error al predecir el cambio del mes siguiente (2023-24)"); ax.legend(fontsize=8)
guardar("fig16_error")

# %% Guardar estadisticas
S["periodo"] = {"inicio": str(P.index.min())[:7], "fin": str(P.index.max())[:7], "meses": int(len(P))}
S["maestra_filas"] = etl["maestra_filas"]
S["pesos_clima"] = etl["pesos_clima_por_rubro"]
(SAL / "eda_stats.json").write_text(json.dumps(S, indent=2, ensure_ascii=False, default=str))
print("OK. Figuras:", len(list(FIG.glob("*.png"))))
