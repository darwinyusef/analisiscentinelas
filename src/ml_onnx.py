"""Exporta el modelo entrenado a ONNX y lo usa (onnxruntime) para resolver las alertas del mes.

Por que ONNX: el tablero/API cargan un archivo portable, sin sklearn ni pickle, con paridad verificada.
Uso:  .venv/bin/python src/ml_modelo.py && .venv/bin/python src/ml_onnx.py
Salida: modelos/centinela_modelo.onnx, modelos/centinela_modelo.json, salidas/ml_alertas_onnx.csv
"""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import onnxruntime as ort
import pandas as pd
from skl2onnx import to_onnx

from ml_features import construir

RAIZ = Path(__file__).resolve().parent.parent
MOD, SAL = RAIZ / "modelos", RAIZ / "salidas"
BANDA_ALTA, BANDA_BAJA = 0.65, 0.35
TOLERANCIA = 1e-4  # float32 en ONNX vs float64 en sklearn


def exportar():
    art = joblib.load(MOD / "centinela_modelo.joblib")
    feats = art["features"]
    onx = to_onnx(art["modelo"], np.zeros((1, len(feats)), dtype=np.float32), options={"zipmap": False}, target_opset=17)
    ruta = MOD / "centinela_modelo.onnx"
    ruta.write_bytes(onx.SerializeToString())
    return art, ruta


def predecir(ruta, X):
    sesion = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
    entrada = sesion.get_inputs()[0].name
    salida = sesion.run(None, {entrada: X.astype(np.float32)})
    return salida[1][:, 1]  # probabilidad de clase "sube"


def main():
    art, ruta = exportar()
    d = construir()
    feats = art["features"]
    X = d[feats].to_numpy(dtype=np.float32)
    p_onnx = predecir(ruta, X)
    p_skl = art["modelo"].predict_proba(d[feats])[:, 1]
    desvio = float(np.abs(p_onnx - p_skl).max())
    assert desvio < TOLERANCIA, f"ONNX difiere de sklearn: {desvio:.2e}"

    hoy = d[d.mes == d.mes.max()].copy()
    hoy["prob_sube"] = predecir(ruta, hoy[feats].to_numpy(dtype=np.float32))
    hoy["alerta"] = np.where(hoy.prob_sube >= BANDA_ALTA, "ALZA PROBABLE",
                             np.where(hoy.prob_sube <= BANDA_BAJA, "BAJA PROBABLE", "SIN SEÑAL"))
    hoy["mes_objetivo"] = hoy.mes + pd.offsets.MonthBegin(1)
    cols = ["mes", "mes_objetivo", "producto", "grupo", "foco", "precio", "prob_sube", "alerta"]
    hoy[cols].round(4).to_csv(SAL / "ml_alertas_onnx.csv", index=False)

    ref = pd.read_csv(SAL / "ml_alertas_proximo_mes.csv").set_index("producto").prob_sube
    chequeo = float((hoy.set_index("producto").prob_sube - ref).abs().max())
    assert chequeo < TOLERANCIA, f"Alertas ONNX difieren del CSV de sklearn: {chequeo:.2e}"

    meta = dict(modelo=art["nombre"], features=feats, entrenado_hasta=art["entrenado_hasta"], n_filas=art["n_filas"],
                bandas=dict(alza=BANDA_ALTA, baja=BANDA_BAJA), sha256=hashlib.sha256(ruta.read_bytes()).hexdigest(),
                paridad_max_abs_vs_sklearn=desvio, tamano_kb=round(ruta.stat().st_size / 1024, 1))
    (MOD / "centinela_modelo.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"ONNX OK: {meta['tamano_kb']} KB | paridad max |dif| = {desvio:.2e} | alertas {hoy.alerta.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
