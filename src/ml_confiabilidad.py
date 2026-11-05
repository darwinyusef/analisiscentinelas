"""Confiabilidad del alcance (4 productos / 6 con sus rubros): lo que se puede y no se puede demostrar.

Lee salidas/ml_predicciones_oos.csv (walk-forward de src/ml_modelo.py). No reentrena nada.
Evidencia PRIMARIA = O3 de ml_modelo.py (no cambia). Aqui se agrega evidencia COMPLEMENTARIA, definida
despues de ver que el O3 del alcance no cruza 0; se etiqueta como tal y no reemplaza al O3.

Uso:  .venv/bin/python src/ml_confiabilidad.py
Salida: salidas/ml_confiabilidad.json, salidas/ml_calibracion.csv, salidas/ml_estabilidad_anual.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ml_modelo import MODELO_CANONICO, RUBROS_ALCANCE, SEED, wilson

RAIZ = Path(__file__).resolve().parent.parent
SAL = RAIZ / "salidas"
B = 4000
Z80 = 1.96 + 0.84  # alfa 5 % bilateral, potencia 80 %


def boot(parciales, rng, estadistico):
    """Bootstrap por MESES: los productos de un mismo mes estan correlacionados."""
    P = np.array(parciales, dtype=float)
    idx = rng.integers(0, len(P), size=(B, len(P)))
    return np.array([estadistico(P[i].sum(0)) for i in idx])


def ic(v):
    return [round(float(np.percentile(v, 2.5)), 1), round(float(np.percentile(v, 97.5)), 1)]


def main():
    oos = pd.read_csv(SAL / "ml_predicciones_oos.csv", parse_dates=["mes"])
    y = oos.sube.astype(int)
    oos["ok_mod"] = ((oos[MODELO_CANONICO] >= 0.5).astype(int) == y).astype(int)
    oos["ok_rep"] = (oos.base_repite == y).astype(int)
    oos["dif"] = oos.ok_mod - oos.ok_rep
    oos["amp"] = oos.rubro.isin(RUBROS_ALCANCE)
    meses = sorted(oos.mes.unique())
    rng = np.random.default_rng(SEED)
    out = {}

    # 1. Diferencia de diferencias: alcance ampliado vs resto de productos.
    par = []
    for m in meses:
        g = oos[oos.mes == m]
        a, r = g[g.amp], g[~g.amp]
        par.append([a.dif.sum(), len(a), r.dif.sum(), len(r)])
    dd = boot(par, rng, lambda s: 100 * (s[0] / s[1] - s[2] / s[3]))
    d_amp, d_res = oos[oos.amp].dif.mean() * 100, oos[~oos.amp].dif.mean() * 100
    incluye0 = np.percentile(dd, 2.5) < 0 < np.percentile(dd, 97.5)
    out["homogeneidad_alcance_vs_resto"] = dict(
        dif_alcance_ampliado=round(d_amp, 1), dif_resto=round(d_res, 1), diferencia=round(d_amp - d_res, 1), ic95=ic(dd),
        lectura=("IC incluye 0: sin evidencia de que el alcance se comporte distinto al grupo (no prueba que sea igual)"
                 if incluye0 else "IC excluye 0: el alcance se comporta distinto al grupo"))

    universos = {"foco": oos.foco, "ampliado": oos.amp, "todos": pd.Series(True, index=oos.index)}

    # 2. AUC con bootstrap por meses.
    out["auc"] = {}
    for nombre, mask in universos.items():
        d = oos[mask]
        grupos = [d[d.mes == m] for m in sorted(d.mes.unique())]
        aucs = [roc_auc_score(s.sube.astype(int), s[MODELO_CANONICO])
                for s in (pd.concat([grupos[i] for i in rng.integers(0, len(grupos), len(grupos))]) for _ in range(1500))]
        a = roc_auc_score(d.sube.astype(int), d[MODELO_CANONICO])
        lo, hi = float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))
        out["auc"][nombre] = dict(auc=round(a, 3), ic95=[round(lo, 3), round(hi, 3)], n=int(len(d)), mayor_que_azar=bool(lo > 0.5))

    # 3. Estabilidad por año.
    filas = []
    for nombre, mask in universos.items():
        d = oos[mask]
        for anio, g in d.groupby(d.mes.dt.year):
            filas.append(dict(universo=nombre, anio=int(anio), n=len(g), meses=g.mes.nunique(),
                              exactitud_modelo=round(100 * g.ok_mod.mean(), 1), exactitud_repite=round(100 * g.ok_rep.mean(), 1),
                              dif=round(100 * g.dif.mean(), 1)))
    est = pd.DataFrame(filas)
    est.to_csv(SAL / "ml_estabilidad_anual.csv", index=False)
    out["anios_con_dif_positiva"] = {u: f"{int((g.dif > 0).sum())} de {len(g)}" for u, g in est.groupby("universo")}

    # 4. Calibracion por tramo de probabilidad.
    oos["p"] = oos[MODELO_CANONICO]
    oos["tramo"] = pd.cut(oos.p, [0, .35, .45, .5, .55, .65, 1], include_lowest=True)
    cal = []
    for nombre in ("ampliado", "todos"):
        for t, g in oos[universos[nombre]].groupby("tramo", observed=True):
            lo, hi = wilson(int(g.sube.sum()), len(g))
            cal.append(dict(universo=nombre, tramo=str(t), n=len(g), p_media=round(g.p.mean(), 3),
                            frecuencia_sube=round(g.sube.mean(), 3), wilson_bajo=round(lo / 100, 3), wilson_alto=round(hi / 100, 3)))
    cal = pd.DataFrame(cal)
    cal.to_csv(SAL / "ml_calibracion.csv", index=False)

    # 5. Potencia: cuantos meses de prueba harian demostrable el efecto observado en el grupo.
    efecto_grupo = float(oos.dif.mean() * 100)
    out["potencia"] = {}
    for nombre in ("foco", "ampliado"):
        d = oos[universos[nombre]]
        par = [[g.dif.sum(), len(g)] for _, g in d.groupby("mes")]
        se = float(boot(par, rng, lambda s: 100 * s[0] / s[1]).std())
        meses_act = d.mes.nunique()
        nec = meses_act * (Z80 * se / efecto_grupo) ** 2 if efecto_grupo > 0 else None
        out["potencia"][nombre] = dict(
            meses_de_prueba=int(meses_act), se_dif=round(se, 2), dif_observada=round(float(d.dif.mean() * 100), 1),
            efecto_minimo_detectable_80=round(Z80 * se, 1), efecto_del_grupo=round(efecto_grupo, 1),
            meses_de_prueba_para_detectar_efecto_del_grupo=int(np.ceil(nec)) if nec else None)

    # 6. Bandas de alerta en el alcance ampliado.
    a = oos[oos.amp]
    out["bandas_alcance_ampliado"] = {}
    for etiqueta, sel, val in (("ALZA PROBABLE", a.p >= .65, 1), ("BAJA PROBABLE", a.p <= .35, 0)):
        g = a[sel]
        k = int((g.sube == val).sum())
        r = dict(n=int(len(g)))
        if len(g):
            lo, hi = wilson(k, len(g))
            r.update(acierto_pct=round(100 * k / len(g), 1), wilson=[round(lo, 1), round(hi, 1)])
        out["bandas_alcance_ampliado"][etiqueta] = r

    (SAL / "ml_confiabilidad.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print(est.to_string(index=False))
    print(cal.to_string(index=False))


if __name__ == "__main__":
    main()
