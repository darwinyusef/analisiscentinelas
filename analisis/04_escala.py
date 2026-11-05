import pandas as pd, numpy as np
s1=pd.read_pickle("cache/s1.pkl"); s2=pd.read_pickle("cache/s2.pkl")
s1=s1[s1.informe.astype(str).str.startswith('mensual')]
d=pd.concat([s1,s2.drop(columns='codigo_cpc_ac')])
d['raw']=d.precio_promedio_kilogramo
d['t']=d.raw.map(lambda x:type(x).__name__)
print(d.groupby('informe').t.value_counts().to_dict())
d['v']=pd.to_numeric(d.raw,errors='coerce')
for inf,g in d.groupby('informe'):
    v=g.v.dropna(); frac=(v%1!=0)
    bins=pd.cut(v,[0,10,100,1000,10000,1e6])
    print(inf, "por rango:",bins.value_counts().sort_index().to_dict())
    print("   con decimales por rango:",frac.groupby(bins).mean().round(2).to_dict())
g=d[d.informe=='mensual_2022.csv']
print(g[(g.v>=100)&(g.v<1000)&(g.v%1!=0)].v.head(8).tolist(), g[(g.v>=100)&(g.v<1000)&(g.v%1==0)].v.head(8).tolist())
print(g[(g.v>=10)&(g.v<100)].v.head(10).tolist())
