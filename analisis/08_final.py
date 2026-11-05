import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings("ignore")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
M=pd.read_csv("analisis/resultados/maestra_completa.csv",parse_dates=['mes'])
KEY={"papa capira":"Papa capira","papa criolla limpia":"Papa criolla","tomate chonto regional":"Tomate chonto","cebolla junca":"Cebolla junca"}
M['mes_t']=(M.mes+pd.offsets.MonthBegin(1)).dt.month
FE=['ret_l1','ret_l2','ret_l3','r_ma3','r_ma6','vol3','sin','cos']+[c for c in M.columns if c.startswith('g_')]
tr=M.dropna(subset=['y','ret_l3','r_ma6','vol3']).copy()
grp=tr.groupby(['producto','mes_t']).ret_next
tr['esp']=((grp.transform('sum')-tr.ret_next)/(grp.transform('count')-1).replace(0,np.nan)).fillna(0)
gm=tr.groupby('mes_t').ret_next.mean(); pm=tr.groupby(['producto','mes_t']).ret_next.agg(['mean','count']).reset_index(); pm['gm']=pm.mes_t.map(gm); pm['esp']=(pm['mean']*pm['count']+pm.gm*2)/(pm['count']+2)
rf=RandomForestClassifier(n_estimators=600,min_samples_leaf=8,max_features='sqrt',random_state=0,n_jobs=-1).fit(tr[FE+['esp']],tr.y)
imp=pd.Series(rf.feature_importances_,index=FE+['esp'])
fam={'Historia reciente del precio':['ret_l1','ret_l2','ret_l3','r_ma3','r_ma6','vol3'],'Patrón estacional del producto':['esp','sin','cos'],'Grupo de producto':[c for c in FE if c.startswith('g_')]}
fi={k:round(float(imp[v].sum()),3) for k,v in fam.items()}; print("importancia:",fi)
last=M[(M.mes=='2024-12-01')].dropna(subset=['ret_l3','r_ma6','vol3']).copy()
last=last.merge(pm[['producto','mes_t','esp']],on=['producto','mes_t'],how='left'); last['esp']=last.esp.fillna(0)
last['p_alza']=rf.predict_proba(last[FE+['esp']])[:,1]
def banda(p): return 'ALZA PROBABLE' if p>.6 else ('BAJA PROBABLE' if p<=.4 else 'SIN SEÑAL CLARA')
last['alerta']=last.p_alza.map(banda)
k=last[last['producto'].isin(KEY)].copy(); k['nombre']=k['producto'].map(KEY)
print(k[['nombre','precio','ret_l1','p_alza','alerta','esp']].round(3).to_string())
print("distribución alertas (181 prod.) ene-2025:",last.alerta.value_counts().to_dict())
hist={}
for p,n in KEY.items():
    s=M[M['producto']==p].set_index('mes').precio; hist[n]=dict(ultimo=float(s.iloc[-1]),mes_ant=float(s.iloc[-2]),min12=float(s.iloc[-12:].min()),max12=float(s.iloc[-12:].max()),serie={str(i.date()):float(v) for i,v in s.items()})
W=pd.read_csv("analisis/resultados/predicciones_walkforward.csv")
W['ok']=((W.p>.5)==W.y).astype(int); W['okm']=(W.mom==W.y).astype(int)
conf={n:dict(n=int((W.producto==p).sum()),acc_modelo=round(float(W[W.producto==p].ok.mean()),3),acc_repite_direccion=round(float(W[W.producto==p].okm.mean()),3)) for p,n in KEY.items()}
json.dump(dict(confiabilidad_producto=conf,importancia=fi,pred_ene2025={r.nombre:dict(p_alza=round(r.p_alza,3),alerta=r.alerta,precio_dic24=float(r.precio),var_mes=round(float(np.expm1(r.ret_l1)),3)) for r in k.itertuples()},alertas_181=last.alerta.value_counts().to_dict(),hist=hist),open("analisis/resultados/datos_tablero.json","w"),ensure_ascii=False,indent=1)
fig,ax=plt.subplots(figsize=(6.2,3)); pd.Series(fi).sort_values().plot.barh(ax=ax,color='#1F6E5C'); ax.set_title("Qué usa el modelo final (importancia por familia)"); plt.tight_layout(); plt.savefig("analisis/figuras/f4_importancia.png",dpi=140)
