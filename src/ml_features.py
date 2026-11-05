"""Variables para el modelo de grupo (181 productos x 60 meses).

Refactor de ml/Centinela_Agro_Notebook.ipynb (celda "Paso 3"). Lee la salida de src/etl.py.
Regla de validez: toda columna en la fila del mes t usa solo informacion disponible al cierre de t.

Uso:  .venv/bin/python src/ml_features.py   ->   datos_limpios/features_grupo.csv
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parent.parent
DL = RAIZ / "datos_limpios"
FOCO = ["papa capira", "papa criolla limpia", "tomate chonto regional", "cebolla junca"]
MESES_TOTALES = 60


def rubro_de(p):
    if p == "papa criolla limpia":
        return "papa criolla"
    if p.startswith("papa "):
        return "papa"
    if p.startswith("tomate chonto") or p == "tomate larga vida":
        return "tomate chonto"
    if p == "tomate de arbol":
        return "tomate de arbol"
    if p == "cebolla junca":
        return "cebolla junca"
    if p.startswith("cebolla cabezona"):
        return "cebolla cabezona"
    return None


def indice_estacional(r):
    """Para el origen t: media de r(t-11), r(t-23), ... = variaciones de los mismos meses calendario
    que la transicion t -> t+1. Todas ya conocidas al cierre de t."""
    return pd.concat([r.shift(k) for k in (11, 23, 35, 47)], axis=1).mean(axis=1)


def construir():
    cma = pd.read_csv(DL / "sipsa_cma_limpio.csv", parse_dates=["mes"])
    completos = cma.groupby("producto").mes.nunique()
    completos = completos[completos == MESES_TOTALES].index
    assert len(completos) > 0, "Ningun producto con 60 meses: revisar src/etl.py"
    m = cma[cma.producto.isin(completos)].sort_values(["producto", "mes"]).reset_index(drop=True)
    g = m.groupby("producto")

    m["lp"] = np.log(m.precio)
    m["r1"] = g.lp.diff()
    for k in (1, 2, 3):
        m[f"ret_lag{k}"] = m.groupby("producto").r1.shift(k - 1)
    m["ret_lag6"] = m.lp - g.lp.shift(6)
    m["var_3m"] = m.lp - g.lp.shift(3)
    m["media_6m_ratio"] = m.lp - g.lp.transform(lambda s: s.rolling(6).mean())
    m["vol_3m"] = m.groupby("producto").r1.transform(lambda s: s.rolling(3).std())
    m["mes_sin"] = np.sin(2 * np.pi * m.mes.dt.month / 12)
    m["mes_cos"] = np.cos(2 * np.pi * m.mes.dt.month / 12)
    m["idx_estacional"] = m.groupby("producto").r1.transform(indice_estacional)

    clima = pd.read_csv(DL / "clima_mensual.csv", parse_dates=["mes"])
    cm = clima.groupby("mes")[["lluvia_mm", "temp_media", "et0_mm"]].mean().sort_index()
    cm["lluvia_lag1"] = cm.lluvia_mm.shift(1)
    cm["lluvia_lag2"] = cm.lluvia_mm.shift(2)
    cm["lluvia_3m"] = cm.lluvia_mm.rolling(3).sum()
    trm = pd.read_csv(DL / "trm_mensual.csv", parse_dates=["mes"]).set_index("mes").sort_index()
    cm["trm"] = trm.trm
    cm["trm_var1m"] = trm.trm.pct_change()
    cm["trm_var3m"] = trm.trm.pct_change(3)
    m = m.merge(cm.reset_index(), on="mes", how="left")

    prod = pd.read_csv(DL / "produccion_limpia.csv")
    pa = prod.groupby(["rubro", "anio"], as_index=False).volumen_produccion.sum(min_count=1)
    pa["anio_prod"] = pa.anio + 1  # el dato del año t se conoce al cerrar t: se usa en t+1
    m["rubro"] = m.producto.map(rubro_de)
    m["anio_prod"] = m.mes.dt.year
    m = m.merge(pa[["rubro", "anio_prod", "volumen_produccion"]], on=["rubro", "anio_prod"], how="left").drop(columns="anio_prod")
    m["log_vol_prod"] = np.log1p(m.volumen_produccion)
    m["tiene_prod"] = m.volumen_produccion.notna().astype(int)
    m = pd.concat([m, pd.get_dummies(m.grupo, prefix="g", dtype=int)], axis=1)

    g = m.groupby("producto")
    m["precio_sig"] = g.precio.shift(-1)
    m["ret_sig"] = np.log(m.precio_sig) - m.lp
    m["sube"] = np.where(m.precio_sig.notna(), (m.precio_sig > m.precio).astype(float), np.nan)
    m["foco"] = m.producto.isin(FOCO)
    return m.sort_values(["mes", "producto"]).reset_index(drop=True)


def columnas(m):
    base = ["ret_lag1", "ret_lag2", "ret_lag3", "ret_lag6", "var_3m", "media_6m_ratio", "vol_3m",
            "mes_sin", "mes_cos", "idx_estacional"]
    grupos = [c for c in m if c.startswith("g_")]
    ext = ["lluvia_mm", "lluvia_lag1", "lluvia_lag2", "lluvia_3m", "temp_media", "et0_mm",
           "trm", "trm_var1m", "trm_var3m", "log_vol_prod", "tiene_prod"]
    return {"precio": base + grupos, "completo": base + grupos + ext}


if __name__ == "__main__":
    f = construir()
    f.to_csv(DL / "features_grupo.csv", index=False)
    print(f"features_grupo.csv: {f.shape} | productos {f.producto.nunique()} | meses {f.mes.nunique()} | filas foco {int(f.foco.sum())}")
