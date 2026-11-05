import pandas as pd, numpy as np
def clima():
    c=pd.read_excel("clima.xlsx"); c['time']=pd.to_datetime(c.time)
    c=c[(c.time>='2020-01-01')&(c.time<'2025-01-01')]
    c['mes']=c.time.dt.to_period('M').dt.to_timestamp()
    g=c.groupby(['mes','subregion']).agg(temp=('temperatura_2m_mean','mean'),lluvia=('precipitacion_sum','sum'),et0=('et0_fao_evapotranspiracion','sum')).reset_index()
    return c,g.groupby('mes').agg(temp=('temp','mean'),lluvia=('lluvia','mean'),et0=('et0','mean')).reset_index()
def trm():
    t=pd.read_excel("proyecto agro.xlsx",sheet_name="Hoja2"); 
    t['d0']=pd.to_datetime(t.vigencia_desde); t['d1']=pd.to_datetime(t.vigencia_hasta)
    rows=[(d,v) for v,a,b in zip(t.valor,t.d0,t.d1) for d in pd.date_range(a,b)]
    x=pd.DataFrame(rows,columns=['dia','trm']); x=x[(x.dia>='2019-12-01')&(x.dia<'2025-01-01')]
    x['mes']=x.dia.dt.to_period('M').dt.to_timestamp()
    return t,x.groupby('mes').trm.mean().reset_index()
def produccion():
    p=pd.read_excel("proyecto agro.xlsx",sheet_name="Hoja3"); return p
if __name__=="__main__":
    c,cm=clima(); print("clima subregiones:",c.subregion.unique(),c.municipio_ref.unique(),"| mensual",cm.shape,cm.mes.min(),cm.mes.max(),"nulos",cm.isna().sum().sum())
    print(cm.head(3).round(1).to_string())
    t,tm=trm(); print("TRM filas",len(t),"| mensual",tm.shape,tm.mes.min(),tm.mes.max()); print(tm.trm.describe()[['min','mean','max']].round(0).to_dict())
    p=produccion(); print("prod filas",len(p),"dup",p.duplicated().sum(),"nulos",p.isna().sum().to_dict())
    print(sorted([r for r in p.rubro.unique() if any(k in str(r) for k in ['papa','tomate','cebolla'])]))
    print(p[p.rubro.astype(str).str.contains('papa|tomate|cebolla')].groupby(['rubro']).anio.agg(['min','max','count']))
