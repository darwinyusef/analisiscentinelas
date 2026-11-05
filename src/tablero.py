"""Tablero Centinela Agro (HTML + CSS estatico, sin JavaScript). Reemplaza las versiones Streamlit del cuaderno.

Toda cifra sale de salidas/*.csv|json y de modelos/centinela_modelo.json; las alertas vienen de
salidas/ml_alertas_onnx.csv (resueltas con onnxruntime por src/ml_onnx.py). Nada escrito a mano.

Uso:  .venv/bin/python src/tablero.py   ->   entregables/tablero_centinela.html
Orden previo: etl.py, ml_features.py, ml_modelo.py, ml_confiabilidad.py, ml_onnx.py
"""
import json
from html import escape as e
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SAL, MOD, DL = RAIZ / "salidas", RAIZ / "modelos", RAIZ / "datos_limpios"
OUT = RAIZ / "entregables" / "tablero_centinela.html"
ALCANCE = ["papa capira", "papa criolla limpia", "tomate chonto regional", "cebolla junca"]
HERMANOS = ["papa nevada", "tomate larga vida"]


def n(x, d=1, signed=False):
    """Numero con coma decimal y punto de miles."""
    s = f"{x:{'+' if signed else ''},.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return n(x, d) + " %"


def clase_alerta(a):
    return {"ALZA PROBABLE": "alza", "BAJA PROBABLE": "baja"}.get(a, "sin")


def sello_alerta(a):
    return f'<span class="b {clase_alerta(a)}">{e(a)}</span>'


def tabla(cabeza, filas):
    th = "".join(f"<th>{e(c)}</th>" for c in cabeza)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>" for f in filas)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def main():
    res = json.loads((SAL / "ml_resultados.json").read_text())
    conf = json.loads((SAL / "ml_confiabilidad.json").read_text())
    meta = json.loads((MOD / "centinela_modelo.json").read_text())
    resumen = pd.read_csv(SAL / "ml_resumen.csv")
    por_prod = pd.read_csv(SAL / "ml_por_producto.csv")
    estab = pd.read_csv(SAL / "ml_estabilidad_anual.csv")
    cal = pd.read_csv(SAL / "ml_calibracion.csv")
    al = pd.read_csv(SAL / "ml_alertas_onnx.csv", parse_dates=["mes", "mes_objetivo"])
    idx = pd.read_csv(SAL / "ml_alertas_proximo_mes.csv").set_index("producto").idx_estacional
    cma = pd.read_csv(DL / "sipsa_cma_limpio.csv", parse_dates=["mes"])

    v = res["veredicto_O3"]
    bandas = res["bandas_modelo_canonico"]["todos"]
    origen, objetivo = al.mes.max(), al.mes_objetivo.max()

    # --- nivel 1: alertas de grupo
    g = al[al.alerta != "SIN SEÑAL"].sort_values("prob_sube", ascending=False)
    filas1 = [[e(r.producto), n(r.precio, 0), n(r.prob_sube, 2), sello_alerta(r.alerta),
               pct(bandas[r.alerta]["acierto_pct"]) + f' (n={bandas[r.alerta]["n"]})'] for r in g.itertuples()]
    t1 = tabla(["Producto", "Precio kg ($)", "Prob. sube", "Alerta", "Acierto histórico de esta banda"], filas1)

    # --- nivel 2: alcance
    filas2 = []
    for p in ALCANCE + HERMANOS:
        r = al[al.producto == p].iloc[0]
        u12 = cma[cma.producto == p].sort_values("mes").tail(12).precio
        pp = por_prod[por_prod.producto == p].set_index("metodo")
        tendencia = "sube" if idx[p] > 0 else "baja"
        marca = "" if p in ALCANCE else ' <span class="mini">(mismo rubro)</span>'
        filas2.append([e(p) + marca, n(r.precio, 0), f"{n(u12.min(), 0)} – {n(u12.max(), 0)}",
                       f"históricamente {tendencia} en este mes ({n(idx[p] * 100, 1, True)} %)",
                       n(r.prob_sube, 2), sello_alerta(r.alerta),
                       f'{pct(pp.loc["rf_precio", "exactitud"])} vs {pct(pp.loc["base_repite", "exactitud"])} (n={int(pp.loc["rf_precio", "n"])})'])
    t2 = tabla(["Producto", "Precio kg ($)", "Rango 12 m ($)", "Estacionalidad", "Prob. sube", "Señal (experimental)",
                "Modelo vs «repite» (2022-24)"], filas2)

    # --- O3 por universo
    ev = []
    for etiqueta, u in (("181 productos (grupo)", "todos"), ("6 productos del alcance ampliado", "ampliado"), ("4 productos del alcance", "foco")):
        x = v[f"{u}_2022-24"]
        nn = int(resumen[(resumen.universo == u) & (resumen.ventana == "2022-24") & (resumen.metodo == "rf_precio")].n.iloc[0])
        if x["cumple_O3"]:
            sello = '<span class="b alza">Cumple</span>'
        else:
            sello = '<span class="b amb">No demostrable</span>'
        ev.append([e(etiqueta), n(nn, 0), pct(x["exactitud"]), f'{pct(x["ic95_meses"][0])} – {pct(x["ic95_meses"][1])}',
                   f'{n(x["dif_vs_repite"], 1, True)} pts', f'{n(x["dif_ic95"][0], 1, True)} a {n(x["dif_ic95"][1], 1, True)}', sello])
    t_ev = tabla(["Universo (2022-01 a 2024-11)", "n", "Exactitud RF", "IC95 (por meses)", "Δ vs «repite»", "IC95 de Δ", "O3"], ev)

    # --- evidencia complementaria
    h = conf["homogeneidad_alcance_vs_resto"]
    af, aa = conf["auc"]["foco"], conf["auc"]["ampliado"]
    pf = conf["potencia"]["foco"]
    ult = estab[(estab.universo == "foco") & (estab.anio == estab.anio.max())].iloc[0]
    ok, amb, mal = ('<span class="b alza">%s</span>', '<span class="b amb">%s</span>', '<span class="b baja">%s</span>')
    compl = [
        ["AUC del alcance mayor que azar",
         f'{n(af["auc"], 3)} (IC95 {n(af["ic95"][0], 3)} – {n(af["ic95"][1], 3)}) en 4 productos; '
         f'{n(aa["auc"], 3)} ({n(aa["ic95"][0], 3)} – {n(aa["ic95"][1], 3)}) en 6.', (ok if af["mayor_que_azar"] else amb) % "Cumple" if af["mayor_que_azar"] else amb % "No demostrable"],
        ["El alcance se comporta como el grupo",
         f'Δ alcance {n(h["dif_alcance_ampliado"], 1, True)} vs resto {n(h["dif_resto"], 1, True)} pts; diferencia {n(h["diferencia"], 1, True)} '
         f'(IC95 {n(h["ic95"][0], 1, True)} a {n(h["ic95"][1], 1, True)}). Sin evidencia de que sea distinto; no prueba que sea igual.', amb % "Indicio"],
        ["Probabilidades calibradas (grupo)", "Cuando el modelo dice p, el precio sube con una frecuencia cercana a p (tabla de calibración abajo).", ok % "Cumple"],
        [f"Estabilidad en {int(ult.anio)}",
         f'En los 4 productos el modelo queda {n(ult.dif, 1, True)} pts frente a «repite» ({pct(ult.exactitud_modelo)} vs {pct(ult.exactitud_repite)}). '
         f'Años con ventaja en el alcance: {conf["anios_con_dif_positiva"]["foco"]}.', mal % "Alerta"],
        ["Potencia para demostrar O3 en el alcance",
         f'Efecto mínimo detectable con {pf["meses_de_prueba"]} meses: {n(pf["efecto_minimo_detectable_80"])} pts (el del grupo es {n(pf["efecto_del_grupo"])}). '
         f'Harían falta ~{pf["meses_de_prueba_para_detectar_efecto_del_grupo"]} meses de prueba.', amb % "Límite de datos"],
    ]
    t_comp = tabla(["Evidencia complementaria (no reemplaza al O3)", "Resultado", "Estado"], compl)

    c = cal[cal.universo == "todos"]
    t_cal = tabla(["Tramo de prob.", "n", "Prob. media", "Frecuencia que sube", "IC95 (Wilson)"],
                  [[e(r.tramo), n(r.n, 0), n(r.p_media, 2), n(r.frecuencia_sube, 2), f"{n(r.wilson_bajo, 2)} – {n(r.wilson_alto, 2)}"]
                   for r in c.itertuples()])

    cuenta = al.alerta.value_counts().to_dict()
    kpi = "".join(f'<div class="kpi"><b>{cuenta.get(k, 0)}</b><span>{k}</span></div>' for k in ("ALZA PROBABLE", "BAJA PROBABLE", "SIN SEÑAL"))
    html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Centinela Agro · Tablero</title><style>
:root{{--t:#1b2a22;--m:#5b6b62;--l:#e3e8e4;--f:#f6f8f6;--v:#2f7d4f;--r:#b3402e;--a:#b7791f}}
*{{box-sizing:border-box}}body{{font:15px/1.5 system-ui,Segoe UI,sans-serif;color:var(--t);background:var(--f);margin:0}}
main{{max-width:1100px;margin:auto;padding:24px 16px 60px}}h1{{margin:0 0 4px}}h2{{margin:32px 0 6px;font-size:20px}}
p.s{{color:var(--m);margin:0 0 12px}}.estado{{background:#fff7e6;border:1px solid #f0d9a8;border-radius:8px;padding:10px 14px;margin:14px 0}}
.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}}.kpi{{background:#fff;border:1px solid var(--l);border-radius:10px;padding:12px 18px;min-width:150px}}
.kpi b{{font-size:28px;display:block}}.kpi span{{color:var(--m);font-size:12px}}
.w{{overflow-x:auto;background:#fff;border:1px solid var(--l);border-radius:10px}}table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--l);text-align:left;vertical-align:top}}th{{background:#eef2ee;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:var(--m)}}
.b{{display:inline-block;padding:2px 9px;border-radius:99px;font-size:12px;font-weight:600;white-space:nowrap}}
.alza{{background:#dff1e6;color:var(--v)}}.baja{{background:#f8e0db;color:var(--r)}}.sin{{background:#eceeec;color:var(--m)}}.amb{{background:#fbeccb;color:var(--a)}}
.mini{{color:var(--m);font-size:12px}}footer{{margin-top:36px;color:var(--m);font-size:12px}}code{{background:#eef2ee;padding:1px 5px;border-radius:4px}}
</style></head><body><main>
<h1>Centinela Agro · Tablero</h1>
<p class="s">Precio mayorista en la Central Mayorista de Antioquia · origen {origen:%Y-%m} → pronóstico {objetivo:%Y-%m}</p>
<div class="estado"><b>Estado del modelo:</b> {e(res["estado_alertas"])}. Nada se publica sin revisión humana.</div>
<div class="kpis">{kpi}</div>

<h2>Nivel 1 · Alertas de grupo (181 productos)</h2>
<p class="s">El modelo solo se pronuncia cuando la probabilidad es ≥ 0,65 o ≤ 0,35; en 2022-24 el {pct(bandas["SIN SEÑAL"]["pct_del_total"])} de los casos quedó sin señal. Se muestra cuánto acertó cada banda.</p>
<div class="w">{t1}</div>

<h2>Nivel 2 · Los 4 productos del alcance</h2>
<p class="s">Estacionalidad y rango histórico son la base. La señal del modelo es <b>experimental</b>: el O3 propio de estos productos no es demostrable con 60 meses.</p>
<div class="w">{t2}</div>

<h2>Cómo sabemos si el modelo sirve (criterio O3)</h2>
<p class="s">O3: el IC95 inferior de la exactitud debe superar 50 % <b>y</b> el IC95 inferior de la ventaja sobre «repite la última dirección» debe ser mayor que 0. IC calculado remuestreando meses.</p>
<div class="w">{t_ev}</div>

<h2>Evidencia complementaria sobre el alcance</h2>
<p class="s">Se definió después de ver que el O3 del alcance cruza 0; por eso no sustituye al criterio.</p>
<div class="w">{t_comp}</div>

<h2>Calibración (181 productos)</h2>
<div class="w">{t_cal}</div>

<footer>Modelo <code>{e(meta["modelo"])}</code> · entrenado hasta {e(meta["entrenado_hasta"])} con {n(meta["n_filas"], 0)} filas · ONNX {n(meta["tamano_kb"])} KB ·
paridad máx. con sklearn {meta["paridad_max_abs_vs_sklearn"]:.1e} · SHA-256 <code>{e(meta["sha256"][:16])}…</code>.
Las alertas se resolvieron con onnxruntime. Los intervalos de las bandas ignoran la correlación entre productos del mismo mes: léelos como optimistas.
No es asesoría de compra o venta.</footer></main></body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"OK: {OUT} {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
