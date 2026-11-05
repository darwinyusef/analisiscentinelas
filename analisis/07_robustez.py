import pandas as pd, numpy as np, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
A=pd.read_csv("analisis/resultados/predicciones_walkforward.csv",parse_dates=['mes','t_target'])
A['ok_rf']=((A.p>=.5).astype(int)==A.y).astype(int); A['ok_mom']=((A.ret_l1>0).astype(int)==A.y).astype(int)
maj=A.groupby('anio').y.mean()
A['ok_maj']=A.apply(lambda r:int(int(r.y)==1),axis=1)  # "siempre sube" (clase mayoritaria global 54%)
print(A.groupby('anio')[['ok_rf','ok_mom','ok_maj']].mean().round(3))
# bootstrap por mes (bloques): remuestrear los 36 meses objetivo
rng=np.random.default_rng(0); meses=A.t_target.unique(); g=A.groupby('t_target')[['ok_rf','ok_mom','ok_maj']].agg(['sum','count'])
diffs=[];dm=[]
for _ in range(5000):
    s=rng.choice(len(meses),len(meses)); sub=g.iloc[s]
    rf=sub[('ok_rf','sum')].sum()/sub[('ok_rf','count')].sum(); mo=sub[('ok_mom','sum')].sum()/sub[('ok_mom','count')].sum(); mj=sub[('ok_maj','sum')].sum()/sub[('ok_maj','count')].sum()
    diffs.append(rf-mo); dm.append(rf-mj)
ci=lambda x:[round(float(np.percentile(x,2.5)),3),round(float(np.percentile(x,97.5)),3)]
print("RF - momentum: media",round(np.mean(diffs),3),"IC95%",ci(diffs),"| P(>0)",round(np.mean(np.array(diffs)>0),3))
print("RF - siempre-sube: media",round(np.mean(dm),3),"IC95%",ci(dm),"| P(>0)",round(np.mean(np.array(dm)>0),3))
# meses acertados: en cuántos de 36 meses RF > 50%
mm=A.groupby('t_target').ok_rf.mean(); print("meses con acierto>50%:",int((mm>.5).sum()),"de",len(mm))
# calibración de alertas
A['banda']=pd.cut(A.p,[0,.4,.5,.6,1],labels=['<=0.40 (baja prob.)','0.40-0.50','0.50-0.60','>0.60 (alza probable)'])
c=A.groupby('banda').agg(n=('y','size'),prop_sube_real=('y','mean')).round(3); c['cobertura']=(c.n/len(A)).round(3); print(c)
# acierto de alerta en extremos
hi=A[A.p>.6]; lo=A[A.p<=.4]
print("p>0.6: n",len(hi),"sube real",round(hi.y.mean(),3),"| p<=0.4: n",len(lo),"baja real",round(1-lo.y.mean(),3))
out=dict(por_anio=A.groupby('anio')[['ok_rf','ok_mom','ok_maj']].mean().round(3).to_dict('index'),ic_rf_menos_momentum=ci(diffs),ic_rf_menos_siempre_sube=ci(dm),p_gt0_mom=round(float(np.mean(np.array(diffs)>0)),3),p_gt0_maj=round(float(np.mean(np.array(dm)>0)),3),meses_gt50=int((mm>.5).sum()),
         calibracion=c.reset_index().assign(banda=lambda x:x.banda.astype(str)).to_dict('records'),hi=dict(n=len(hi),acierto=round(float(hi.y.mean()),3)),lo=dict(n=len(lo),acierto=round(float(1-lo.y.mean()),3)))
json.dump(out,open("analisis/resultados/robustez.json","w"),ensure_ascii=False,indent=1)
# figura final de modelos
o=pd.read_csv("analisis/resultados/estacional.csv"); t=o[o.grupo=='Todos 2022-24'].set_index('modelo')
fig,ax=plt.subplots(1,2,figsize=(12,3.8))
lab=['Base: momentum','Regla estacional','RF + estacional']; col=['#9aa5b1','#9aa5b1','#1F6E5C']
ax[0].barh(lab,t.loc[lab,'accuracy'],color=col); ax[0].axvline(.541,color='r',ls='--',label='"siempre sube" 54%'); ax[0].set_xlim(.4,.7); ax[0].set_title("Exactitud al predecir sube/baja (2022-24)"); ax[0].legend(loc='lower right')
for i,v in enumerate(t.loc[lab,'accuracy']): ax[0].text(v+.005,i,f"{v:.1%}",va='center')
ax[1].bar(['2022','2023','2024'],[A[A.anio==y].ok_rf.mean() for y in (2022,2023,2024)],color='#1F6E5C',label='RF + estacional'); ax[1].plot(['2022','2023','2024'],[A[A.anio==y].ok_mom.mean() for y in (2022,2023,2024)],'o--',color='#B5651D',label='Base momentum')
ax[1].set_ylim(.4,.7); ax[1].axhline(.5,color='gray',lw=.6); ax[1].legend(); ax[1].set_title("Estabilidad por año de prueba")
plt.tight_layout(); plt.savefig("analisis/figuras/f3_modelos.png",dpi=140)
