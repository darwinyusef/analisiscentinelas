import pandas as pd, re
s1=pd.read_pickle("cache/s1.pkl"); s2=pd.read_pickle("cache/s2.pkl")
st=s1[s1.fecha.map(lambda x:isinstance(x,str))].fecha
print("s1 strings únicos:",sorted(st.unique())[:60])
dt=s1[s1.fecha.map(lambda x:hasattr(x,'year'))].fecha
print("s1 datetime: años",dt.map(lambda x:x.year).value_counts().sort_index().to_dict(),"días",dt.map(lambda x:x.day).value_counts().sort_index().to_dict())
d2=s2[s2.fecha.map(lambda x:hasattr(x,'year'))].fecha
print("s2 datetime años",d2.map(lambda x:x.year).value_counts().to_dict(),"días",d2.map(lambda x:x.day).value_counts().to_dict(),"meses",sorted(d2.map(lambda x:x.month).unique()))
print("s2 strings únicos:",sorted(s2[s2.fecha.map(lambda x:isinstance(x,str))].fecha.unique()))
print("s1 NaN fechas:",s1[s1.fecha.isna()|(s1.fecha.astype(str)=='fecha')].head())
print(s1.informe.value_counts().to_dict())
