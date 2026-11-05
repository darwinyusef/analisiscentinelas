"""Modelo de grupo (181 productos) con validacion walk-forward y criterio O3 explicito.

Refactor de ml/Centinela_Agro_Notebook.ipynb (Pasos 3-4). Cambios de fondo frente al cuaderno:
  - walk-forward mensual (origen movil, ventana expansiva) en vez de un solo corte 2023/2024
  - hiperparametros fijos (sin GridSearch sobre el periodo evaluado)
  - bases: repite ultima direccion, clase mayoritaria del entrenamiento, signo del indice estacional
  - IC95 Wilson, IC95 por bootstrap de MESES (los productos de un mes estan correlacionados) y McNemar
  - veredicto O3 calculado por el codigo, no escrito a mano
  - alertas con la tasa de acierto historica de cada banda; ninguna cifra inventada

Uso:  .venv/bin/python src/ml_features.py && .venv/bin/python src/ml_modelo.py   (~3-6 min)
Salida: salidas/ml_predicciones_oos.csv, ml_resumen.csv, ml_por_producto.csv, ml_resultados.json,
        ml_alertas_proximo_mes.csv, modelos/centinela_modelo.joblib
"""
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.contingency_tables import mcnemar

from ml_features import columnas, construir

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parent.parent
SAL = RAIZ / "salidas"
MOD = RAIZ / "modelos"
SAL.mkdir(exist_ok=True)
MOD.mkdir(exist_ok=True)
SEED = 42
INICIO, FIN = pd.Timestamp("2022-01-01"), pd.Timestamp("2024-11-01")  # protocolo ampliado: 35 origenes
INICIO_PREVIO = pd.Timestamp("2023-01-01")  # ventana del analisis anterior, se reporta para comparar
RUBROS_ALCANCE = {"papa", "papa criolla", "tomate chonto", "cebolla junca"}  # mismos rubros que ALCANCE en etl.py
BANDA_ALTA, BANDA_BAJA = 0.65, 0.35
MODELO_CANONICO = "rf_precio"  # fijado antes de ver resultados: el EDA mostro que clima/TRM no aportan
NOMBRES_MODELO = ("logit", "rf", "hgb")
CASOS = [(u, w) for w in ("2022-24", "2023-24") for u in ("foco", "ampliado", "todos")]


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return (100 * (c - h), 100 * (c + h))


def modelos():
    imp = lambda: SimpleImputer(strategy="median")
    return {
        "logit": lambda: make_pipeline(imp(), StandardScaler(), LogisticRegression(C=0.3, max_iter=2000)),
        "rf": lambda: make_pipeline(imp(), RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=30,
                                                                  class_weight="balanced", random_state=SEED, n_jobs=-1)),
        "hgb": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150,
                                                      min_samples_leaf=30, random_state=SEED),
    }


def walk_forward(d, cols):
    fabrica = modelos()
    salidas = []
    for T in pd.date_range(INICIO, FIN, freq="MS"):
        tr = d[(d.mes < T) & d.sube.notna()]  # el objetivo del mes T-1 (precio de T) ya se conoce al cierre de T
        te = d[d.mes == T]
        out = te[["mes", "producto", "rubro", "foco", "sube", "ret_lag1", "idx_estacional"]].copy()
        out["base_repite"] = (te.ret_lag1 > 0).astype(int)
        out["base_mayoria"] = int(tr.sube.mean() >= 0.5)
        out["base_estacional"] = (te.idx_estacional > 0).astype(int)
        for nombre, fab in fabrica.items():
            for conj in ("precio", "completo"):
                mod = fab().fit(tr[cols[conj]], tr.sube)
                out[f"{nombre}_{conj}"] = mod.predict_proba(te[cols[conj]])[:, 1]
        salidas.append(out)
        print(f"  origen {T:%Y-%m} entrenado con {len(tr):,} filas", flush=True)
    return pd.concat(salidas, ignore_index=True)


def es_modelo(c):
    return c.split("_")[0] in NOMBRES_MODELO


def recorte(oos, universo, ventana):
    d = oos
    if universo == "foco":
        d = d[d.foco]
    elif universo == "ampliado":
        d = d[d.rubro.isin(RUBROS_ALCANCE)]
    if ventana == "2023-24":
        d = d[d.mes >= INICIO_PREVIO]
    return d


def evaluar(oos, universo, ventana, rng, B=2000):
    d = recorte(oos, universo, ventana)
    y = d.sube.values.astype(int)
    pred = {c: d[c].values for c in ("base_repite", "base_mayoria", "base_estacional")}
    probs = {c: d[c].values for c in d if es_modelo(c)}
    pred.update({c: (p >= 0.5).astype(int) for c, p in probs.items()})
    meses = d.mes.values
    um = np.unique(meses)
    idx = [np.where(meses == mm)[0] for mm in um]
    n_m = np.array([len(i) for i in idx])
    ok_ref = (pred["base_repite"] == y).astype(int)
    ref_m = np.array([ok_ref[i].sum() for i in idx])
    muestras = rng.integers(0, len(um), size=(B, len(um)))
    filas = []
    for nombre, p in pred.items():
        ok = (p == y).astype(int)
        k, n = int(ok.sum()), len(y)
        lo, hi = wilson(k, n)
        ok_m = np.array([ok[i].sum() for i in idx])
        den = n_m[muestras].sum(1)
        acc_b = ok_m[muestras].sum(1) / den
        dif_b = (ok_m[muestras].sum(1) - ref_m[muestras].sum(1)) / den
        tabla = [[int(((ok == 1) & (ok_ref == 1)).sum()), int(((ok == 1) & (ok_ref == 0)).sum())],
                 [int(((ok == 0) & (ok_ref == 1)).sum()), int(((ok == 0) & (ok_ref == 0)).sum())]]
        filas.append(dict(
            universo=universo, ventana=ventana, metodo=nombre, n=n, exactitud=100 * k / n,
            wilson_bajo=lo, wilson_alto=hi,
            boot_meses_bajo=100 * np.percentile(acc_b, 2.5), boot_meses_alto=100 * np.percentile(acc_b, 97.5),
            dif_vs_repite=100 * (k - ok_ref.sum()) / n,
            dif_boot_bajo=100 * np.percentile(dif_b, 2.5), dif_boot_alto=100 * np.percentile(dif_b, 97.5),
            mcnemar_p=1.0 if nombre == "base_repite" else float(mcnemar(tabla, exact=True).pvalue),
            f1=f1_score(y, p), auc=roc_auc_score(y, probs[nombre]) if nombre in probs else np.nan))
    return pd.DataFrame(filas)


def veredicto_o3(res):
    out = {}
    for u, w in CASOS:
        r = res[(res.universo == u) & (res.ventana == w) & res.metodo.map(es_modelo)]
        mejor = r.sort_values("exactitud", ascending=False).iloc[0]
        out[f"{u}_{w}"] = dict(mejor_modelo=mejor.metodo, exactitud=round(mejor.exactitud, 1),
                      ic95_meses=[round(mejor.boot_meses_bajo, 1), round(mejor.boot_meses_alto, 1)],
                      dif_vs_repite=round(mejor.dif_vs_repite, 1),
                      dif_ic95=[round(mejor.dif_boot_bajo, 1), round(mejor.dif_boot_alto, 1)],
                      cumple_O3=bool(mejor.boot_meses_bajo > 50 and mejor.dif_boot_bajo > 0))
    return out


def bandas(oos, col):
    d = oos.copy()
    d["banda"] = np.where(d[col] >= BANDA_ALTA, "ALZA PROBABLE", np.where(d[col] <= BANDA_BAJA, "BAJA PROBABLE", "SIN SEÑAL"))
    res = {}
    for b, g in d.groupby("banda"):
        res[b] = dict(n=int(len(g)), pct_del_total=round(100 * len(g) / len(d), 1))
        if b != "SIN SEÑAL":
            k = int((g.sube == (1 if b == "ALZA PROBABLE" else 0)).sum())
            lo, hi = wilson(k, len(g))
            res[b].update(acierto_pct=round(100 * k / len(g), 1), wilson=[round(lo, 1), round(hi, 1)])
    return res


def entrenar_final(d, cols):
    nombre, conj = MODELO_CANONICO.split("_")
    tr = d[d.sube.notna()]
    mod = modelos()[nombre]().fit(tr[cols[conj]], tr.sube)
    joblib.dump({"modelo": mod, "features": cols[conj], "entrenado_hasta": str(tr.mes.max().date()),
                 "n_filas": int(len(tr)), "nombre": MODELO_CANONICO}, MOD / "centinela_modelo.joblib")
    hoy = d[d.mes == d.mes.max()].copy()
    hoy["prob_sube"] = mod.predict_proba(hoy[cols[conj]])[:, 1]
    hoy["alerta"] = np.where(hoy.prob_sube >= BANDA_ALTA, "ALZA PROBABLE",
                             np.where(hoy.prob_sube <= BANDA_BAJA, "BAJA PROBABLE", "SIN SEÑAL"))
    hoy["mes_objetivo"] = hoy.mes + pd.offsets.MonthBegin(1)
    return hoy[["mes", "mes_objetivo", "producto", "grupo", "foco", "precio", "prob_sube", "alerta", "idx_estacional"]]


def estado(v):
    grupo = v["todos_2022-24"]["cumple_O3"]
    alcance = v["ampliado_2022-24"]["cumple_O3"] and v["foco_2022-24"]["cumple_O3"]
    if alcance:
        return "Alcance: cumple O3 en los 4 productos y en el alcance ampliado; requiere revision humana"
    if v["ampliado_2022-24"]["cumple_O3"]:
        return "Alcance ampliado cumple O3; los 4 productos por separado no lo demuestran: señal experimental por producto, requiere revision humana"
    if grupo:
        return "Candidato de grupo: cumple O3 en los 181 productos; en el alcance es EXPERIMENTAL, requiere revision humana"
    return "EXPERIMENTAL: ningun universo cumple O3"


def main():
    d = construir()
    cols = columnas(d)
    print(f"Maestra de grupo: {d.shape}, {d.producto.nunique()} productos. Walk-forward {INICIO:%Y-%m} a {FIN:%Y-%m}")
    oos = walk_forward(d, cols)
    oos.to_csv(SAL / "ml_predicciones_oos.csv", index=False)

    rng = np.random.default_rng(SEED)
    res = pd.concat([evaluar(oos, u, w, rng) for u, w in CASOS], ignore_index=True)
    res.round(3).to_csv(SAL / "ml_resumen.csv", index=False)

    por_prod = []
    for p, g in recorte(oos, "ampliado", "2022-24").groupby("producto"):
        y = g.sube.astype(int).values
        for c in ("base_repite", "base_estacional", MODELO_CANONICO):
            pr = g[c].values if c.startswith("base") else (g[c].values >= 0.5).astype(int)
            k = int((pr == y).sum())
            lo, hi = wilson(k, len(y))
            por_prod.append(dict(producto=p, metodo=c, n=len(y), exactitud=round(100 * k / len(y), 1),
                                 wilson_bajo=round(lo, 1), wilson_alto=round(hi, 1)))
    pd.DataFrame(por_prod).to_csv(SAL / "ml_por_producto.csv", index=False)

    alertas = entrenar_final(d, cols)
    alertas.round(4).to_csv(SAL / "ml_alertas_proximo_mes.csv", index=False)

    v = veredicto_o3(res)
    resultados = dict(
        ventana=f"{INICIO:%Y-%m} a {FIN:%Y-%m} (origenes mensuales; objetivo = mes siguiente)",
        modelo_canonico=MODELO_CANONICO, hiperparametros="fijos, sin busqueda sobre el periodo evaluado",
        veredicto_O3=v,
        bandas_modelo_canonico={u: bandas(recorte(oos, u, "2022-24"), MODELO_CANONICO) for u in ("foco", "ampliado", "todos")},
        estado_alertas=estado(v),
        alertas_mes=alertas.alerta.value_counts().to_dict(),
        mes_origen=f"{alertas.mes.max():%Y-%m}", mes_objetivo=f"{alertas.mes_objetivo.max():%Y-%m}")
    (SAL / "ml_resultados.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    pd.set_option("display.width", 220)
    print(res[["universo", "ventana", "metodo", "n", "exactitud", "boot_meses_bajo", "boot_meses_alto", "dif_vs_repite",
               "dif_boot_bajo", "dif_boot_alto", "mcnemar_p", "auc"]].round(1).to_string(index=False))
    print(json.dumps(resultados, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
