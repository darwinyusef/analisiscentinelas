import pandas as pd, numpy as np, json, warnings
warnings.filterwarnings("ignore")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score,f1_score,roc_auc_score,balanced_accuracy_score,mean_absolute_error
import etl_aux
R={}
d=pd.read_pickle("analisis/sipsa_limpio.pkl")
m=d[d.mercado.str.contains("central mayorista de antioquia")]
full=m.groupby('producto').mes.nunique(); full=full[full==60].index
m=m[m['producto'].isin(full)].sort_values(['producto','mes']).reset_index(drop=True)
KEY={"papa capira":"Papa capira","tomate chonto regional":"Tomate chonto","cebolla junca":"Cebolla junca"}
R['n_productos_modelo']=len(full); R['filas_maestra']=len(m)
_,cl=etl_aux.clima(); _,tr=etl_aux.trm()
prod=etl_aux.produccion().drop_duplicates()
pm={"papa capira":"papa","tomate chonto regional":"tomate chonto","cebolla junca":"cebolla junca"}
pa=prod[prod.rubro.isin(pm.values())].groupby(['rubro','anio']).volumen_produccion.sum().reset_index()
R['produccion_antioquia_t']={r: pa[pa.rubro==r].set_index('anio').volumen_produccion.loc[2019:2024].to_dict() for r in pm.values()}
m=m.merge(cl,on='mes',how='left').merge(tr,on='mes',how='left')
m['trm_lag']=m.trm
# ---------- EDA 1: estacionalidad
seas={}; 
for p,n in KEY.items():
    s=m[m['producto']==p].set_index('mes').precio
    ly=np.log(s); df=pd.DataFrame({'y':ly,'anio':ly.index.year,'mes':ly.index.month})
    X0=pd.get_dummies(df.anio,drop_first=True).astype(float); X1=pd.concat([X0,pd.get_dummies(df.mes,drop_first=True).astype(float)],axis=1)
    def r2(X):
        X=np.column_stack([np.ones(len(X)),X.values]); b=np.linalg.lstsq(X,df.y.values,rcond=None)[0]; e=df.y.values-X@b; return 1-e.var()/df.y.var()
    # índice estacional = precio / media del año
    idx=(s/s.groupby(s.index.year).transform('mean')).groupby(s.index.month).mean()
    seas[n]=dict(R2_solo_tendencia_anual=round(r2(X0),3),R2_con_mes=round(r2(X1),3),mes_mas_caro=int(idx.idxmax()),indice_max=round(idx.max(),3),mes_mas_barato=int(idx.idxmin()),indice_min=round(idx.min(),3),precio_medio=round(s.mean()),cv=round(s.std()/s.mean(),3),var_2020_2024=round(s.iloc[-1]/s.iloc[0]-1,3))
    seas[n]['_idx']=idx.round(3).to_dict()
R['estacionalidad']=seas
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
for p,n in KEY.items():
    s=m[m['producto']==p].set_index('mes').precio; ax[0].plot(s.index,s.values,label=n,lw=2)
    ax[1].plot(range(1,13),[seas[n]['_idx'][k] for k in range(1,13)],marker='o',label=n,lw=2)
ax[0].set_title("Precio mayorista mensual (COP/kg) - Central Mayorista de Antioquia"); ax[0].legend(); ax[0].grid(alpha=.3)
ax[1].axhline(1,color='gray',ls='--'); ax[1].set_title("Índice estacional (1 = promedio del año)"); ax[1].set_xticks(range(1,13)); ax[1].set_xticklabels(list("EFMAMJJASOND")); ax[1].legend(); ax[1].grid(alpha=.3)
plt.tight_layout(); plt.savefig("analisis/figuras/f1_precios_estacionalidad.png",dpi=140); plt.close()
# ---------- features
g=m.groupby('producto')
m['ret']=g.precio.transform(lambda s:np.log(s).diff())
for k in (1,2,3): m[f'ret_l{k}']=g.ret.shift(k-1)    # ret_l1 = retorno de este mes
m['r_ma3']=g.precio.transform(lambda s:s/s.rolling(3).mean()); m['r_ma6']=g.precio.transform(lambda s:s/s.rolling(6).mean())
m['vol3']=g.ret.transform(lambda s:s.rolling(3).std())
m['mes_n']=m.mes.dt.month; m['sin']=np.sin(2*np.pi*m.mes_n/12); m['cos']=np.cos(2*np.pi*m.mes_n/12)
clim=m[m.mes<'2024-01-01'].drop_duplicates('mes').groupby('mes_n')[['lluvia','temp']].mean()
m['lluvia_an']=m.lluvia-m.mes_n.map(clim.lluvia); m['temp_an']=m.temp-m.mes_n.map(clim.temp)
cm=m.drop_duplicates('mes').sort_values('mes').set_index('mes')
cm['lluvia_an_l1']=cm.lluvia_an.shift(1); cm['lluvia_an_l2']=cm.lluvia_an.shift(2); cm['lluvia_acum3']=cm.lluvia.rolling(3).sum()
cm['trm_ret1']=np.log(cm.trm).diff(); cm['trm_ret3']=np.log(cm.trm).diff(3)
m=m.merge(cm[['lluvia_an_l1','lluvia_an_l2','lluvia_acum3','trm_ret1','trm_ret3']].reset_index(),on='mes')
for gr in m.grupo.unique(): m['g_'+gr[:5]]=(m.grupo==gr).astype(float)
m['ret_next']=g.ret.shift(-1) if False else m.groupby('producto').ret.shift(-1)
m['y']=(m.ret_next>0).astype(float); m.loc[m.ret_next.isna(),'y']=np.nan
R['balance_clase_sube']=round(float(m.y.mean()),3); R['empates_0']=round(float((m.ret_next==0).mean()),4)
# ---------- EDA 2: relación con lluvia y dólar (retorno mensual vs anomalía lluvia / var. dólar, con rezagos)
rows=[]
for k in range(0,4):
    for var,col in [('lluvia',lambda df:df.lluvia_an),('dolar',lambda df:df.trm_ret1)]:
        for p,n in list(KEY.items())+[('_todos',"Todos (181 prod.)")]:
            cs=[]
            sub=m if p=='_todos' else m[m['producto']==p]
            for q,df in sub.groupby('producto'):
                df=df.sort_values('mes'); x=col(df).shift(k); ok=x.notna()&df.ret.notna()
                if ok.sum()>20: cs.append(spearmanr(x[ok],df.ret[ok])[0])
            rows.append(dict(variable=var,rezago_meses=k,producto=n,rho=np.nanmean(cs)))
cor=pd.DataFrame(rows); cor.to_csv("analisis/resultados/correlaciones.csv",index=False)
R['correlaciones']=cor.pivot_table(index=['variable','rezago_meses'],columns='producto',values='rho').round(3).reset_index().to_dict('records')
# precio en nivel vs lluvia/dólar (nivel real, no cambio)
niv={}
for p,n in KEY.items():
    s=m[m['producto']==p].set_index('mes'); niv[n]=dict(rho_precio_trm=round(spearmanr(s.precio,s.trm)[0],3),rho_precio_lluvia=round(spearmanr(s.precio,s.lluvia)[0],3))
R['correlacion_nivel']=niv
fig,ax=plt.subplots(figsize=(7.5,4)); w=.2
for i,(v,lab) in enumerate([('lluvia','Anomalía de lluvia'),('dolar','Var. del dólar (TRM)')]):
    pass
sub=cor[cor.producto.isin(KEY.values())]
sub=sub.assign(et=sub.variable+" r"+sub.rezago_meses.astype(str))
pv=sub.pivot(index='et',columns='producto',values='rho'); pv.plot.barh(ax=ax,width=.8); ax.axvline(0,color='k',lw=.6); ax.set_title("Correlación (Spearman) retorno mensual del precio vs lluvia y dólar"); ax.grid(alpha=.3,axis='x'); plt.tight_layout(); plt.savefig("analisis/figuras/f2_correlaciones.png",dpi=140); plt.close()
# ---------- modelo
FE={'precio':['ret_l1','ret_l2','ret_l3','r_ma3','r_ma6','vol3'],'estac':['sin','cos'],'clima':['lluvia_an','lluvia_an_l1','lluvia_an_l2','lluvia_acum3','temp_an'],'dolar':['trm_ret1','trm_ret3'],'grupo':[c for c in m.columns if c.startswith('g_')]}
def sets(name):
    return {'Solo precio+estacionalidad':FE['precio']+FE['estac']+FE['grupo'],
            '+ clima':FE['precio']+FE['estac']+FE['grupo']+FE['clima'],
            '+ dólar':FE['precio']+FE['estac']+FE['grupo']+FE['dolar'],
            'Todo (precio+clima+dólar)':FE['precio']+FE['estac']+FE['grupo']+FE['clima']+FE['dolar']}[name]
m.to_csv('analisis/resultados/maestra_completa.csv',index=False)
data=m.dropna(subset=['y','ret_l3','r_ma6','vol3','lluvia_an_l2','lluvia_acum3','trm_ret3']).copy()
data['t_target']=data.mes+pd.offsets.MonthBegin(1)
def folds(): return [2022,2023,2024]
def metr(y,p,pred):
    out=dict(accuracy=accuracy_score(y,pred),balanced_acc=balanced_accuracy_score(y,pred),f1=f1_score(y,pred,zero_division=0))
    out['auc']=roc_auc_score(y,p) if len(set(y))>1 else np.nan; return out
res=[]; probs={}
for yr in folds():
    tr=data[data.t_target<f'{yr}-01-01']; te=data[(data.t_target>=f'{yr}-01-01')&(data.t_target<f'{yr+1}-01-01')]
    maj=float(tr.y.mean()>=.5)
    base={'Base: "sube si subió el mes pasado"':(te.ret_l1>0).astype(float),'Base: clase mayoritaria':pd.Series(maj,index=te.index)}
    for bn,bp in base.items(): res.append(dict(anio=yr,modelo=bn,**metr(te.y,bp.values.astype(float),bp.values.astype(int)),n=len(te)))
    for fs in ['Solo precio+estacionalidad','+ clima','+ dólar','Todo (precio+clima+dólar)']:
        cols=sets(fs)
        rf=RandomForestClassifier(n_estimators=400,min_samples_leaf=8,max_features='sqrt',random_state=0,n_jobs=-1).fit(tr[cols],tr.y)
        p=rf.predict_proba(te[cols])[:,1]; res.append(dict(anio=yr,modelo='RF '+fs,**metr(te.y,p,(p>=.5).astype(int)),n=len(te)))
        if fs.startswith('Todo'): probs[yr]=pd.Series(p,index=te.index); imp=pd.Series(rf.feature_importances_,index=cols) if yr==2024 else None; imp24=imp if yr==2024 else locals().get('imp24')
    cols=sets('Todo (precio+clima+dólar)')
    lr=make_pipeline(StandardScaler(),LogisticRegression(C=.3,max_iter=500)).fit(tr[cols],tr.y); p=lr.predict_proba(te[cols])[:,1]
    res.append(dict(anio=yr,modelo='Regresión logística (todo)',**metr(te.y,p,(p>=.5).astype(int)),n=len(te)))
res=pd.DataFrame(res); res.to_csv("analisis/resultados/modelos_por_anio.csv",index=False)
resum=res.groupby('modelo')[['accuracy','balanced_acc','f1','auc']].mean().round(3).sort_values('auc',ascending=False)
R['modelos_promedio_2022_24']=resum.reset_index().to_dict('records'); R['modelos_2024']=res[res.anio==2024].round(3).drop(columns='anio').to_dict('records')
fam={'Historia del precio':FE['precio'],'Estacionalidad':FE['estac'],'Clima':FE['clima'],'Dólar':FE['dolar'],'Grupo de producto':FE['grupo']}
R['importancia_familias_2024']={k:round(float(imp24[v].sum()),3) for k,v in fam.items()}
# ---------- 3 productos clave (modelo global evaluado en ellos, 2022-24 apilado)
te_all=pd.concat([data.loc[probs[y].index].assign(p=probs[y],anio=y) for y in folds()])
key={}
for p,n in KEY.items():
    t=te_all[te_all['producto']==p]; b=(t.ret_l1>0).astype(int)
    key[n]=dict(n=len(t),acc_modelo=round(accuracy_score(t.y,(t.p>=.5).astype(int)),3),acc_base_momentum=round(accuracy_score(t.y,b),3),acc_mayoritaria=round(max(t.y.mean(),1-t.y.mean()),3),auc=round(roc_auc_score(t.y,t.p),3) if t.y.nunique()>1 else None,
                prop_sube=round(t.y.mean(),3))
R['clave_2022_24']=key
t24=te_all[te_all.anio==2024]; R['clave_2024']={n:dict(n=int((t24['producto']==p).sum()),acc_modelo=round(accuracy_score(t24[t24['producto']==p].y,(t24[t24['producto']==p].p>=.5).astype(int)),3),acc_base=round(accuracy_score(t24[t24['producto']==p].y,(t24[t24['producto']==p].ret_l1>0).astype(int)),3)) for p,n in KEY.items()}
# ---------- regresión del precio: RF sobre retorno vs "precio = al del mes actual"
reg=[]
for yr in folds():
    tr=data[data.t_target<f'{yr}-01-01']; te=data[(data.t_target>=f'{yr}-01-01')&(data.t_target<f'{yr+1}-01-01')]
    cols=sets('Todo (precio+clima+dólar)')
    rr=RandomForestRegressor(n_estimators=400,min_samples_leaf=8,max_features=.5,random_state=0,n_jobs=-1).fit(tr[cols],tr.ret_next)
    pr=te.precio*np.exp(rr.predict(te[cols])); real=te.precio*np.exp(te.ret_next)
    for (p,n) in [(None,'Todos')]+list(KEY.items()):
        sel=slice(None) if p is None else (te['producto']==p).values
        reg.append(dict(anio=yr,grupo=n,MAPE_naive=float((abs(real-te.precio)/real)[sel].mean()),MAPE_RF=float((abs(real-pr)/real)[sel].mean()),MAE_naive=float(abs(real-te.precio)[sel].mean()),MAE_RF=float(abs(real-pr)[sel].mean())))
reg=pd.DataFrame(reg); reg.to_csv("analisis/resultados/regresion_precio.csv",index=False)
r24=reg[reg.anio==2024]; R['regresion_2024']=r24.round(4).to_dict('records'); R['regresion_prom']=reg.groupby('grupo')[['MAPE_naive','MAPE_RF']].mean().round(4).reset_index().to_dict('records')
# ---------- figura modelos
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
show=['Base: clase mayoritaria','Base: "sube si subió el mes pasado"','Regresión logística (todo)','RF Solo precio+estacionalidad','RF + clima','RF + dólar','RF Todo (precio+clima+dólar)']
rs=resum.loc[show]
rs['auc'].plot.barh(ax=ax[0],color=['#9aa5b1']*2+['#2C6E9B']*5); ax[0].axvline(.5,color='r',ls='--'); ax[0].set_title("AUC promedio walk-forward 2022-24 (0.5 = azar)"); ax[0].set_xlim(.4,.8)
rs['accuracy'].plot.barh(ax=ax[1],color=['#9aa5b1']*2+['#2C6E9B']*5); ax[1].set_title("Exactitud promedio 2022-24"); ax[1].set_xlim(.4,.8); ax[1].set_yticklabels([])
plt.tight_layout(); plt.savefig("analisis/figuras/f3_modelos.png",dpi=140); plt.close()
fig,ax=plt.subplots(figsize=(6,3.6)); pd.Series(R['importancia_familias_2024']).sort_values().plot.barh(ax=ax,color='#1F6E5C'); ax.set_title("Qué usa el modelo (importancia por familia, RF 2024)"); plt.tight_layout(); plt.savefig("analisis/figuras/f4_importancia.png",dpi=140); plt.close()
data.to_csv("analisis/resultados/vista_maestra.csv",index=False)
json.dump(R,open("analisis/resultados/resultados.json","w"),ensure_ascii=False,indent=1,default=str)
print(json.dumps({k:R[k] for k in ['n_productos_modelo','filas_maestra','balance_clase_sube','empates_0','estacionalidad','correlacion_nivel']},ensure_ascii=False,indent=1,default=str)[:3500])
print(resum.to_string()); print(json.dumps(R['importancia_familias_2024']))
