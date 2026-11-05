import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings("ignore")
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,roc_auc_score,balanced_accuracy_score,f1_score
d=pd.read_csv("analisis/resultados/vista_maestra.csv",parse_dates=['mes','t_target'])
d['mes_t']=d.t_target.dt.month
KEY={"papa capira":"Papa capira","tomate chonto regional":"Tomate chonto","cebolla junca":"Cebolla junca"}
FE=['ret_l1','ret_l2','ret_l3','r_ma3','r_ma6','vol3','sin','cos']+[c for c in d.columns if c.startswith('g_')]
rows=[];allp=[]
for yr in (2022,2023,2024):
    tr=d[d.t_target<f'{yr}-01-01'].copy(); te=d[(d.t_target>=f'{yr}-01-01')&(d.t_target<f'{yr+1}-01-01')].copy()
    # retorno esperado por producto y mes (solo entrenamiento), contraído hacia la media del mes de todos los productos
    pm=tr.groupby(['producto','mes_t']).ret_next.agg(['mean','count']).reset_index(); gm=tr.groupby('mes_t').ret_next.mean().rename('gm')
    pm=pm.merge(gm,on='mes_t'); k=2; pm['esp']=(pm['mean']*pm['count']+pm.gm*k)/(pm['count']+k)
    for df in (tr,te):
        x=df[['producto','mes_t']].merge(pm[['producto','mes_t','esp']],on=['producto','mes_t'],how='left'); df['esp']=x.esp.values
        df['esp']=df.esp.fillna(0)
    # en entrenamiento, la expectativa incluye la propia fila (fuga leve) -> usar leave-one-year-out aproximado: quitar el aporte propio
    tr['esp']=((tr.groupby(['producto','mes_t']).ret_next.transform('sum')-tr.ret_next)/(tr.groupby(['producto','mes_t']).ret_next.transform('count')-1).replace(0,np.nan)).fillna(0)
    cols=FE+['esp']
    rf=RandomForestClassifier(n_estimators=400,min_samples_leaf=8,max_features='sqrt',random_state=0,n_jobs=-1).fit(tr[cols],tr.y)
    te['p']=rf.predict_proba(te[cols])[:,1]; te['anio']=yr
    te['reg_est']=(te.esp>0).astype(int); te['mom']=(te.ret_l1>0).astype(int)
    allp.append(te)
A=pd.concat(allp)
def sc(df,name,pred,p=None):
    return dict(modelo=name,accuracy=accuracy_score(df.y,pred),balanced=balanced_accuracy_score(df.y,pred),f1=f1_score(df.y,pred),auc=roc_auc_score(df.y,p if p is not None else pred))
out=[]
for sub,lab in [(A,'Todos 2022-24'),(A[A.anio==2024],'Todos 2024')]+[(A[A['producto']==p],n+' 2022-24') for p,n in KEY.items()]:
    for nm,pred,p in [('Base: momentum',sub.mom,None),('Regla estacional',sub.reg_est,sub.esp),('RF + estacional',(sub.p>=.5).astype(int),sub.p)]:
        try: out.append(dict(grupo=lab,n=len(sub),**sc(sub,nm,pred,p)))
        except Exception as e: pass
o=pd.DataFrame(out); o.to_csv("analisis/resultados/estacional.csv",index=False); print(o.round(3).to_string())
A.to_csv("analisis/resultados/predicciones_walkforward.csv",index=False)
# autocorrelación del retorno mensual (persistencia) para los 3 productos
for p,n in KEY.items():
    s=d[d['producto']==p].sort_values('mes').ret_l1.dropna(); print(n,"autocorr lag1 del retorno:",round(s.autocorr(1),3))
print("todos:",round(d.groupby('producto').ret_l1.apply(lambda s:s.autocorr(1)).mean(),3))
