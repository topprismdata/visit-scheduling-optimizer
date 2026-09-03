# -*- coding: utf-8 -*-
"""全部 10 条线: 每条 3 组数 (计划距离 / 仅优化顺序 / 完全优化). 全部骑行路网距离."""
import pandas as pd, numpy as np, math, json, time, urllib.request, warnings, sys
warnings.filterwarnings("ignore")
URL = "https://routing.openstreetmap.de/routed-bike/table/v1/driving/"

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str); pv["拜访日期"]=pd.to_datetime(pv["拜访日期"])
pv["date"]=pv["拜访日期"].dt.date

LINES = ["02","03","04","05","06","07","08","09","10","11"]
BATCH = 40
results = []

def fetch_matrix(codes, LON, LAT):
    n=len(codes)
    D = np.full((n,n), np.nan)
    coord = ";".join(f"{lo:.6f},{la:.6f}" for lo,la in zip(LON,LAT))
    for s0 in range(0,n,BATCH):
        s1 = min(s0+BATCH,n)
        srcs = ";".join(str(i) for i in range(s0,s1))
        url = f"{URL}{coord}?sources={srcs}&annotations=distance"
        for attempt in range(6):
            try:
                r = json.loads(urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"gz-eval/1.0"}),timeout=90).read())
                if r.get("code")=="Ok":
                    for li,row in enumerate(r["distances"]):
                        for j in range(n):
                            if row[j] is not None: D[s0+li][j]=row[j]/1000.0
                    break
            except Exception:
                time.sleep(2+attempt)
        time.sleep(0.3)
    return np.nan_to_num(D, nan=float(np.nanmax(D)))

def nn2opt(seq, D):
    seq=list(seq); n=len(seq)
    if n<=3: return seq
    unv=set(range(1,n)); out=[0]
    while unv:
        l=out[-1]; out.append(min(unv,key=lambda j:D[seq[l]][seq[j]])); unv.discard(out[-1])
    route=[seq[t] for t in out]
    for _ in range(30):
        imp=False
        for a in range(1,n-2):
            for b in range(a+1,n-1):
                if D[route[a-1]][route[b]]+D[route[a]][route[b+1]] < D[route[a-1]][route[a]]+D[route[b]][route[b+1]]-1e-9:
                    route[a:b+1]=route[a:b+1][::-1]; imp=True
        if not imp: break
    return route
def day_km(seq,D):
    return 0.0 if len(seq)<2 else float(sum(D[seq[k]][seq[k+1]] for k in range(len(seq)-1)))

for lid in LINES:
    t0=time.time()
    g = pv[pv["销售名称"].str.contains(f"海珠荔湾{lid}")]
    if g.empty:
        print(f"线 {lid}: 空"); continue
    pts = g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").set_index("客户编码")
    codes=pts.index.tolist(); idx={c:i for i,c in enumerate(codes)}
    LON=pts["经度"].astype(float).tolist(); LAT=pts["纬度"].astype(float).tolist()
    n=len(codes); DATES=sorted(g["date"].unique())
    D = fetch_matrix(codes,LON,LAT)
    # 原始顺序
    days_orig={}
    for dd in DATES:
        days_orig[dd]=[idx[c] for c in g[g["date"]==dd].sort_values("拜访顺序")["客户编码"] if c in idx]
    orig=sum(day_km(s,D) for s in days_orig.values())
    # ① 仅顺序
    d1={dd:nn2opt(s,D) for dd,s in days_orig.items()}
    km1=sum(day_km(s,D) for s in d1.values())
    # ② 完全优化 (跨日 + 顺序)
    d2={dd:list(s) for dd,s in d1.items()}
    moves=0; start=time.time()
    for _ in range(40):
        imp=False
        for dd1 in DATES:
            for dd2 in DATES:
                if dd1==dd2: continue
                s1=d2[dd1]; s2=d2[dd2]
                if len(s1)<=5: continue
                for c in list(s1):
                    if c in s2: continue
                    ns1=[x for x in s1 if x!=c]; ns2=s2+[c]
                    if len(ns1)<2: continue
                    r1o=nn2opt(s1,D); r2o=nn2opt(s2,D); r1n=nn2opt(ns1,D); r2n=nn2opt(ns2,D)
                    old=day_km(r1o,D)+day_km(r2o,D); new=day_km(r1n,D)+day_km(r2n,D)
                    if new<old-0.05:
                        d2[dd1]=r1n; d2[dd2]=r2n; moves+=1; imp=True
            if time.time()-start>150: break
        if not imp or time.time()-start>150: break
    km2=sum(day_km(nn2opt(s,D),D) for s in d2.values())
    # 次数校验
    freq0=g.groupby("客户编码").size().to_dict(); cnt2={}
    for dd in DATES:
        for c in d2[dd]: cnt2[codes[c]]=cnt2.get(codes[c],0)+1
    ok = all(cnt2.get(c,0)==freq0.get(c,0) for c in freq0)
    results.append(dict(line=lid, stores=n, visits=len(g), days=len(DATES),
                       plan=round(orig,1), seq_only=round(km1,1), full=round(km2,1),
                       sav1=round((orig-km1)/orig*100,1), sav2=round((orig-km2)/orig*100,1),
                       moves=moves, count_ok=bool(ok), sec=round(time.time()-t0)))
    print(f"线 {lid}: 计划 {orig:.1f} | 顺序 {km1:.1f} (-{(orig-km1)/orig:.0%}) | 完全 {km2:.1f} (-{(orig-km2)/orig:.0%})  [{moves}次,{time.time()-t0:.0f}s]", flush=True)

t=pd.DataFrame(results)
print("\n=== 全办汇总 (骑行路网) ===")
print(t[["line","stores","visits","plan","seq_only","full","sav1","sav2","count_ok"]].to_string(index=False))
print(f"\n合计: 计划 {t.plan.sum():.0f} | 顺序 {t.seq_only.sum():.0f} (-{(t.plan.sum()-t.seq_only.sum())/t.plan.sum():.0%}) | 完全 {t.full.sum():.0f} (-{(t.plan.sum()-t.full.sum())/t.plan.sum():.0%})")
t.to_csv("output/all_lines_result.csv", index=False)
json.dump(results, open("output/all_lines_result.json","w"), ensure_ascii=False, indent=1)
print("saved output/all_lines_result.csv")
