import pandas as pd
s1=pd.read_pickle("cache/s1.pkl"); s2=pd.read_pickle("cache/s2.pkl")
s1=s1[s1.informe.astype(str).str.startswith('mensual')]
isdt=lambda x:hasattr(x,'year')
for inf,g in s1.groupby('informe'):
    d=g[g.fecha.map(isdt)].fecha
    print(inf,"datetime n=",len(d),"| (año,mes,día) combos:",d.map(lambda x:(x.year,x.month,x.day)).value_counts().sort_index().head(14).to_dict())
    st=g[~g.fecha.map(isdt)].fecha
    print("   strings:",st.value_counts().to_dict())
d=s2[s2.fecha.map(isdt)]
print("s2:",d.fecha.map(lambda x:(x.year,x.month,x.day)).value_counts().sort_index().to_dict())
print("s2 strings:",s2[~s2.fecha.map(isdt)].fecha.value_counts().to_dict())
