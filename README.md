# Centinela Agro

Alertas de dirección de precio (sube, baja, sin señal) a un mes para papa, tomate y cebolla, con datos oficiales de SIPSA-DANE, clima (Open-Meteo) y dólar (TRM).

**Resultado honesto:** el modelo acierta la dirección 58,9 % de las veces (IC95 57,5–60,3 %, prueba 2022–2024 sin mirar el futuro). La mejor regla simple acierta 55,8 %. Es una señal de dirección, no un precio exacto.

## Contenido

| Carpeta | Qué hay |
|---|---|
| `src/` | ETL, EDA, modelo (`ml_modelo.py`), tablero, generador de la presentación |
| `analisis/` | Análisis estadístico, figuras y resultados |
| `ml/` | Notebook del modelo |
| `modelos/` | Modelo entrenado (`.joblib`, `.onnx`, `.json`) |
| `datos_limpios/` | Tablas limpias pequeñas (maestra mensual, clima, TRM) |
| `entregables/` | Pitch (`.pptx`), informe EDA, tablero y pipeline interactivos, plan de acciones |
| `diseno/` | Prototipo de la app (FigCraft): `gen.py` genera `pantallas.json` y `centinela_agro.figcraft`; fotos agro en `img/` |
| `salidas/` | Métricas del modelo, figuras y capturas de la app |
| `Propuesta_*.md` | Propuesta técnica, gerencial y de implementación |

## Qué no está en el repo

Datos crudos (`*.xlsx`), caché (`*.pkl`) y tablas intermedias grandes. Se excluyen en `.gitignore`. Para regenerarlos, descarga los datos de SIPSA-DANE y corre `analisis/etl.py`.

## Regenerar el prototipo

```bash
python diseno/gen.py
figcraft-cli run diseno/pantallas.json --out diseno/centinela_agro.figcraft
```

Las fotos se generan con fal.ai. La clave se pasa solo como variable de entorno:

```bash
FAL_KEY=... python diseno/imagenes_fal.py
```
