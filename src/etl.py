"""ETL Centinela Agro: limpia las 4 fuentes y arma la tabla maestra mensual.

Uso:  .venv/bin/python src/etl.py
Salida: datos_limpios/*.csv y salidas/etl_log.json
"""
import json
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "datos_limpios"
OUT.mkdir(exist_ok=True)
(RAIZ / "salidas").mkdir(exist_ok=True)

CMA = "medellin, central mayorista de antioquia"
MESES_ES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
            "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
log = {}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


# ---------------------------------------------------------------- SIPSA
def arreglar_fecha(x):
    """Tres corrupciones de Excel sobre fechas mensuales:
    - 2020/2021: el DIA (1-12) es el mes real (d/m leido como m/d).
    - 2022-2024 con texto 'ene-22': mes en espanol sin parsear.
    - 2022-2024 parseados como dia-del-ano 2026 ('feb-22' -> 2026-02-22): año = dia.
    """
    if isinstance(x, str):
        m, y = x.strip().split("-")
        return pd.Timestamp(2000 + int(y), MESES_ES[m[:3]], 1)
    if x.year == 2026:
        return pd.Timestamp(2000 + x.day, x.month, 1)
    if x.year in (2020, 2021):
        return pd.Timestamp(x.year, x.day, 1)
    return pd.Timestamp(x.year, x.month, 1)


def cargar_sipsa():
    xl = RAIZ / "precios_sipsa_modificado.xlsx"
    s1 = pd.read_excel(xl, sheet_name="precios_sipsa_1")
    s2 = pd.read_excel(xl, sheet_name="precios_sipsa_2")
    log["sipsa_filas_crudas"] = int(len(s1) + len(s2))
    mal1 = s1.producto.isna() | (s1.producto == "producto")
    log["sipsa_filas_encabezado_o_vacias"] = int(mal1.sum())
    s1 = s1[~mal1].copy()
    s1["precio_raw"] = pd.to_numeric(s1.precio_promedio_kilogramo)
    s2 = s2.copy()
    s2["precio_raw"] = s2.precio_promedio_kilogramo.astype(float)
    cols = ["fecha", "grupo", "producto", "mercado", "precio_raw", "informe"]
    a = pd.concat([s1[cols], s2[cols]], ignore_index=True)
    a["mes"] = a.fecha.map(arreglar_fecha)
    ing = a.fecha.map(lambda x: pd.Period(x, "M") if not isinstance(x, str) else pd.NaT)
    log["qa_fechas"] = {
        "meses_distintos_lectura_ingenua": int(ing.nunique()),
        "filas_fecha_texto_no_parseada": int(a.fecha.map(lambda x: isinstance(x, str)).sum()),
        "filas_parseadas_como_2026": int(a.fecha.map(lambda x: (not isinstance(x, str)) and x.year == 2026).sum()),
        "filas_2020_21_con_dia_como_mes": int(a.fecha.map(lambda x: (not isinstance(x, str)) and x.year in (2020, 2021)).sum()),
        "meses_distintos_corregidos": int(a.mes.nunique()),
    }
    for c in ("grupo", "producto", "mercado"):
        a[c] = a[c].map(norm)
    return a


def arreglar_escala(a):
    """Desde 2022 los precios con punto de miles se leyeron como decimal
    ('2.367' -> 2.367 en vez de 2367). Para cada fila se elige entre v y v*1000
    el valor mas cercano (en log) a la mediana 2020-21 del mismo producto."""
    a = a.copy()
    ref = a[a.mes.dt.year <= 2021].groupby("producto").precio_raw.median()
    tarde = a[a.mes.dt.year >= 2022]
    ref_alt = (tarde[(tarde.precio_raw % 1) > 0].assign(p=lambda d: d.precio_raw * 1000)
               .groupby("producto").p.median())
    a["ref"] = a.producto.map(ref).fillna(a.producto.map(ref_alt))
    v = a.precio_raw
    t = a.mes.dt.year >= 2022
    tiene_ref = a.ref.notna()
    d_igual = (np.log(v.clip(lower=1e-9)) - np.log(a.ref)).abs()
    d_mil = (np.log((v * 1000).clip(lower=1e-9)) - np.log(a.ref)).abs()
    escalar = pd.Series(False, index=a.index)
    escalar[t & tiene_ref] = (d_mil < d_igual)[t & tiene_ref]
    escalar[t & ~tiene_ref] = ((v % 1 > 0) | (v < 100))[t & ~tiene_ref]
    a["precio"] = np.where(escalar, v * 1000, v)
    a["escalado_x1000"] = escalar
    (a.assign(anio=a.mes.dt.year).groupby("anio")
     .agg(mediana_cruda=("precio_raw", "median"), mediana_corregida=("precio", "median"),
          filas=("precio", "size"), filas_escaladas=("escalado_x1000", "sum"))
     .to_csv(RAIZ / "salidas" / "qa_precios_anual.csv"))
    log["precios_escalados_x1000"] = int(escalar.sum())
    log["precios_2022_24_sin_escalar"] = int((t & ~escalar).sum())
    return a.drop(columns=["ref"])


def limpiar_sipsa():
    a = arreglar_escala(cargar_sipsa())
    claves = ["mes", "producto", "mercado"]
    dup = a.duplicated(claves, keep=False)
    log["sipsa_combinaciones_repetidas"] = int(a[dup].groupby(claves).ngroups)
    a = (a.groupby(claves + ["grupo"], as_index=False)
         .agg(precio=("precio", "mean"), n_obs=("precio", "size")))
    log["sipsa_filas_limpias"] = int(len(a))
    log["sipsa_meses"] = int(a.mes.nunique())
    log["sipsa_productos"] = int(a.producto.nunique())
    log["sipsa_mercados"] = int(a.mercado.nunique())
    assert log["sipsa_meses"] == 60, f"Se esperaban 60 meses y hay {log['sipsa_meses']}: la correccion de fechas fallo"
    return a


# ----------------------------------------------------------------- clima
def clima_mensual():
    c = pd.read_excel(RAIZ / "clima.xlsx")
    log["clima_filas_crudas"] = int(len(c))
    c = c[(c.time >= "2020-01-01") & (c.time <= "2024-12-31")].copy()
    c["mes"] = c.time.dt.to_period("M").dt.to_timestamp()
    c["dia_lluvioso"] = (c.precipitacion_sum >= 1).astype(int)
    m = (c.groupby(["subregion", "mes"], as_index=False)
         .agg(temp_media=("temperatura_2m_mean", "mean"),
              temp_max=("temperatura_2m_max", "mean"),
              temp_min=("temperatura_2m_min", "mean"),
              lluvia_mm=("precipitacion_sum", "sum"),
              dias_lluvia=("dia_lluvioso", "sum"),
              et0_mm=("et0_fao_evapotranspiracion", "sum")))
    log["clima_filas_mensuales"] = int(len(m))
    return m


# ------------------------------------------------------------------- TRM
def trm_mensual():
    t = pd.read_excel(RAIZ / "proyecto agro.xlsx", sheet_name="Hoja2")
    log["trm_filas_crudas"] = int(len(t))
    filas = [pd.DataFrame({"dia": pd.date_range(r.vigencia_desde, r.vigencia_hasta), "trm": r.valor})
             for r in t.itertuples()]
    d = pd.concat(filas).drop_duplicates("dia").sort_values("dia")
    d = d[(d.dia >= "2019-12-01") & (d.dia <= "2024-12-31")]
    d["mes"] = d.dia.dt.to_period("M").dt.to_timestamp()
    m = d.groupby("mes", as_index=False).agg(trm=("trm", "mean"), trm_min=("trm", "min"), trm_max=("trm", "max"))
    log["trm_dias_expandidos"] = int(len(d))
    return m


# ------------------------------------------------------------ produccion
def produccion_anual():
    p = pd.read_excel(RAIZ / "proyecto agro.xlsx", sheet_name="Hoja3")
    log["produccion_filas_crudas"] = int(len(p))
    p["rubro"] = p.rubro.map(norm)
    for c in ("tipo", "subregion", "municipio"):
        p[c] = p[c].map(norm)
    n0 = len(p)
    p = p.drop_duplicates()
    log["produccion_duplicados_exactos"] = int(n0 - len(p))
    log["produccion_area_negativa"] = int((p.area_produccion < 0).sum())
    p.loc[p.area_produccion < 0, "area_produccion"] = np.nan  # nulos quedan vacios, no 0
    return p


# --------------------------------------------------- productos del alcance
ALCANCE = {
    "papa capira": ("papa", "papa"),
    "papa criolla limpia": ("papa criolla", "papa criolla"),
    "tomate chonto regional": ("tomate chonto", "tomate chonto"),
    "cebolla junca": ("cebolla junca", "cebolla junca"),
}


def main():
    sipsa = limpiar_sipsa()
    sipsa.to_csv(OUT / "sipsa_limpio.csv", index=False)
    cma = sipsa[sipsa.mercado == CMA]
    cma.to_csv(OUT / "sipsa_cma_limpio.csv", index=False)
    log["cma_filas"] = int(len(cma))
    log["cma_productos"] = int(cma.producto.nunique())

    clima = clima_mensual(); clima.to_csv(OUT / "clima_mensual.csv", index=False)
    trm = trm_mensual(); trm.to_csv(OUT / "trm_mensual.csv", index=False)
    prod = produccion_anual(); prod.to_csv(OUT / "produccion_limpia.csv", index=False)

    base = cma[cma.producto.isin(ALCANCE)].copy()
    base["producto_alcance"] = base.producto.map(lambda p: ALCANCE[p][0])
    base["rubro"] = base.producto.map(lambda p: ALCANCE[p][1])
    zonas = ["norte", "occidente", "oriente"]
    pesos = (prod[(prod.anio >= 2015) & (prod.anio <= 2024) & prod.subregion.isin(zonas)]
             .groupby(["rubro", "subregion"]).volumen_produccion.sum())
    pesos = pesos / pesos.groupby(level=0).transform("sum")
    rubros_alcance = {v[1] for v in ALCANCE.values()}
    log["pesos_clima_por_rubro"] = {r: {z: round(float(w), 3) for z, w in g.droplevel(0).items()}
                                    for r, g in pesos.groupby(level=0) if r in rubros_alcance}
    clima_p = clima.pivot(index="mes", columns="subregion")
    filas = []
    for rubro in {v[1] for v in ALCANCE.values()}:
        w = pesos.loc[rubro] if rubro in pesos.index.get_level_values(0) else pd.Series(1 / 3, index=zonas)
        w = w.reindex(zonas).fillna(0)
        w = w / w.sum()
        for var in ("lluvia_mm", "temp_media", "dias_lluvia", "et0_mm"):
            s = sum(clima_p[(var, z)] * w[z] for z in zonas)
            filas.append(pd.DataFrame({"mes": s.index, "rubro": rubro, "variable": var, "valor": s.values}))
    cp = pd.concat(filas).pivot_table(index=["mes", "rubro"], columns="variable", values="valor").reset_index()
    prod_a = (prod.groupby(["rubro", "anio"], as_index=False)
              .agg(volumen_antioquia=("volumen_produccion", "sum"), area_antioquia=("area_produccion", "sum")))
    prod_a["anio_prod"] = prod_a.anio + 1  # el dato del año t solo se conoce al cerrar t: se usa t-1
    prod_a = prod_a.rename(columns={"volumen_antioquia": "volumen_prod_t1", "area_antioquia": "area_prod_t1"})
    maestra = (base.merge(cp, on=["mes", "rubro"], how="left")
               .merge(trm, on="mes", how="left")
               .assign(anio_prod=lambda d: d.mes.dt.year)
               .merge(prod_a[["rubro", "anio_prod", "volumen_prod_t1", "area_prod_t1"]],
                      on=["rubro", "anio_prod"], how="left")
               .drop(columns="anio_prod")
               .sort_values(["producto", "mes"]))
    maestra.to_csv(OUT / "maestra_mensual.csv", index=False)
    log["maestra_filas"] = int(len(maestra))
    log["maestra_nulos"] = {k: int(v) for k, v in maestra.isna().sum().items() if v}
    (RAIZ / "salidas" / "etl_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))
    print(json.dumps(log, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
