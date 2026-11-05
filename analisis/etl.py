import pandas as pd, numpy as np, unicodedata, re
MES={'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
def norm(s): 
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower().strip()
    return re.sub(r'\s+',' ',s)
def mes_ok(r):
    f,anio=r['fecha'],int(re.search(r'(\d{4})',r['informe']).group(1))
    if isinstance(f,str): return pd.Timestamp(anio,MES[f[:3]],1)
    if anio in (2020,2021): return pd.Timestamp(anio,f.day,1)   # el mes quedó como "día"
    return pd.Timestamp(anio,f.month,1)
def cargar_sipsa():
    s1=pd.read_pickle("cache/s1.pkl"); s2=pd.read_pickle("cache/s2.pkl")
    n0=len(s1)+len(s2)
    s1=s1[s1.informe.astype(str).str.startswith('mensual')]
    s2=s2.drop(columns='codigo_cpc_ac')
    d=pd.concat([s1,s2],ignore_index=True)
    d['mes']=d.apply(mes_ok,axis=1)
    d['precio']=pd.to_numeric(d.precio_promedio_kilogramo,errors='coerce')
    anio=d.informe.str.extract(r'(\d{4})')[0].astype(int)
    d['escala_corregida']=(anio>=2022)&((d.precio<100)|((d.precio<1000)&(d.precio%1!=0)))
    d.loc[d.escala_corregida,'precio']*=1000
    for c in ['grupo','producto','mercado']: d[c]=d[c].map(norm)
    d=d.dropna(subset=['precio'])
    ndup=d.duplicated(['mes','producto','mercado']).sum()
    d=d.groupby(['mes','grupo','producto','mercado'],as_index=False).agg(precio=('precio','mean'),esc=('escala_corregida','max'))
    return d,dict(filas_crudas=n0,encabezados_o_vacias_eliminadas=n0-len(s1)-len(s2)-0,duplicados=ndup)
if __name__=="__main__":
    d,info=cargar_sipsa(); print(info, "filas limpias:",len(d))
    d.to_pickle("analisis/sipsa_limpio.pkl")
    print("precios 2024 reescalados x1000:",int(d.esc.sum()))
    print(d.groupby(d.mes.dt.year).precio.describe()[['count','min','50%','max']])
