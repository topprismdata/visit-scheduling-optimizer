# -*- coding: utf-8 -*-
"""修正 ③ 的测量 bug: warm-ALNS 日集合 + 与②同尺的 NN/2-opt 做序 → OSRM 骑行重测.
构造性预期: ③ 起点=SRP日集合(=②), 逐周 min 保底 ⇒ ③ ≤ ②, 等号成立说明换日无益."""
import pandas as pd, json, math, time, urllib.request, warnings
warnings.filterwarnings("ignore")
OSRM = "https://routing.openstreetmap.de/routed-bike/route/v1/driving/"
def road_km(coords):
    s = ";".join(f"{lo:.6f},{la:.6f}" for lo, la in coords)
    req = urllib.request.Request(f"{OSRM}{s}?overview=false", headers={"User-Agent":"gz-eval/1.0"})
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read())["routes"][0]["distance"]/1000.0
        except Exception:
            time.sleep(1.5)
    return None

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"]); pv["date"]=pv["拜访日期"].dt.date
g = pv[pv["销售名称"].str.contains("海珠荔湾09")].sort_values("拜访顺序")
mst = g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").set_index("客户编码")
LON=mst["经度"].astype(float).to_dict(); LAT=mst["纬度"].astype(float).to_dict()
def hav(a,b):
    la1,lo1,la2,lo2=map(math.radians,[LAT[a],LON[a],LAT[b],LON[b]])
    x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(x))
def nn2opt(cs):
    cs=list(cs); n=len(cs)
    if n<=2: return cs
    H={a:{b:hav(a,b) for b in cs} for a in cs}
    out=[cs[0]]; unv=set(cs[1:])
    while unv:
        l=out[-1]; out.append(min(unv,key=lambda j:H[l][j])); unv.discard(out[-1])
    def L(o): return sum(H[o[k]][o[k+1]] for k in range(len(o)-1))
    imp=True; ps=0
    while imp and ps<25:
        imp=False; ps+=1
        for a in range(1,n-2):
            for b in range(a+1,n-1):
                if H[out[a-1]][out[b]]+H[out[b]][out[a]] < H[out[a-1]][out[a]]+H[out[b]][out[b+1]]-1e-9:
                    out[a:b+1]=out[a:b+1][::-1]; imp=True
    return out

opt = pd.read_csv("/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/output/srp_alns_09.csv")
opt["客户编码"]=opt["客户编码"].astype(str)
t=0.0; v=0; rows=[]
for dd,gd in opt.groupby("拜访日期"):
    cs=[c for c in gd.sort_values("拜访顺序")["客户编码"] if c in LON]
    if len(cs)<2: continue
    seq=nn2opt(cs)
    km=road_km([(LON[c],LAT[c]) for c in seq]); t+=km; v+=len(seq)
    for r_,c in enumerate(seq,1):
        rows.append(dict(拜访日期=dd,拜访顺序=r_,客户编码=c))
    time.sleep(0.25)
pd.DataFrame(rows).to_csv("/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/output/srp_alns_09_fixed.csv",index=False)
print(f"③ 修正(日集合+同尺NN/2opt做序): {t:.1f} km / {v} 次")
print(f"对照: ②=636.3 km | ①=1116.0 km")
print(f"③ vs ②: {(t-636.3)/636.3:+.1%}  (≥②则换日无益但保底成立; <②则换日有增益)")
json.dump({"n3_fixed":round(t,1),"visits":v},
          open("/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/output/final_09_n3fix.json","w"))
