import pandas as pd, numpy as np, re
s1=pd.read_pickle("cache/s1.pkl"); s2=pd.read_pickle("cache/s2.pkl")
print("s1 fecha tipos:",s1.fecha.map(type).value_counts().to_dict())
print("s2 fecha ejemplos:",s2.fecha.unique()[:5], "| precio tipos:",s2.precio_promedio_kilogramo.map(type).value_counts().to_dict())
print("mercados con medellin:",sorted({m for m in pd.concat([s1.mercado,s2.mercado]).unique() if 'medell' in str(m).lower()}))
for k in ["papa","tomate","cebolla"]:
    print(k,sorted({p for p in pd.concat([s1.producto,s2.producto]).unique() if k in str(p).lower()}))
print(s1.fecha.astype(str).str[:7].agg(['min','max']).tolist(), "filas encabezado s1:", (s1.fecha.astype(str).str.lower().str.contains('fecha')).sum())
print(s2.precio_promedio_kilogramo.astype(str).str.len().describe()[['min','max']].tolist())
print(s2[s2.mercado.str.contains('medell',na=False)&s2['producto'].str.contains('papa negra',na=False)].head(12)[['fecha','producto','precio_promedio_kilogramo']])
