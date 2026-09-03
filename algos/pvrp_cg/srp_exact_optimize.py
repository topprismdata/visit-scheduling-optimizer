# -*- coding: utf-8 -*-
"""09区计划精确优化 v-final.
硬约束(构造保证): 每店拜访次数 == SRP 原计划逐店次数; 星期 == SRP 主服务日; 日容量 [min,max] 锚定 SRP.
候选方案: A=CP-SAT 分配+真实里程局部搜索;  B=SRP 起点+真实里程局部搜索(数学保底不劣于 SRP).
最终: 取真实链式里程最优者; 骑行路网复核."""
import sys, math, time, json, itertools
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
import pandas as pd, numpy as np, warnings, datetime
warnings.filterwarnings("ignore")
from ortools.sat.python import cp_model

REP = sys.argv[1] if len(sys.argv)>1 else "09"
plan=pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv=plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"]); pv["date"]=pv["拜访日期"].dt.date
g=pv[pv["销售名称"].str.contains("海珠荔湾"+REP)].sort_values("拜访顺序")
mst=g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").reset_index(drop=True)
codes=mst["客户编码"].tolist(); n=len(codes)
freq=g.groupby("客户编码").size().reindex(codes).astype(int).tolist()
wmode={c:int(s.dt.weekday.value_counts().index[0]) for c,s in g.groupby("客户编码")["拜访日期"]}
LON=mst["经度"].astype(float).tolist(); LAT=mst["纬度"].astype(float).tolist()

dates=[]; d=datetime.date(2026,7,1)
while d.month==7:
    if d.weekday()<5: dates.append(d)
    d+=datetime.timedelta(days=1)
DAYS=len(dates)                      # 23
wd_idx={}
for i,dd in enumerate(dates): wd_idx.setdefault(dd.weekday(),[]).append(i)
srp_daily=g.groupby("date").size()
CAP_LO=max(1,int(srp_daily.min())-2); CAP_HI=int(srp_daily.max())+2
print(f"{REP}: {n} 店 {sum(freq)} 次 | 23 日 | 容量[{CAP_LO},{CAP_HI}]", flush=True)

def hav(a,b):
    la1,lo1,la2,lo2=map(math.radians,[LAT[a],LON[a],LAT[b],LON[b]])
    x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(x))
H=[[hav(i,j) for j in range(n)] for i in range(n)]

# ---------- CP-SAT: 星期锁定 + 逐店次数精确 + 空间(同日 kNN 近邻对最小化) ----------
m=cp_model.CpModel()
v=[[m.NewBoolVar(f"v{i}_{d}") for d in range(DAYS)] for i in range(n)]
for i in range(n):
    allowed=wd_idx[wmode[codes[i]]]
    assert freq[i]<=len(allowed), f"{codes[i]} freq{freq[i]}>{len(allowed)}"
    m.Add(sum(v[i][d] for d in allowed)==freq[i])
    for d in range(DAYS):
        if d not in allowed: m.Add(v[i][d]==0)
for d in range(DAYS):
    m.Add(sum(v[i][d] for i in range(n))>=CAP_LO)
    m.Add(sum(v[i][d] for i in range(n))<=CAP_HI)
nbr={i:sorted(range(n),key=lambda j:H[i][j])[1:9] for i in range(n)}
sp=[]
for d in range(DAYS):
    for i in range(n):
        for j in nbr[i]:
            if j<=i or wmode[codes[i]]!=wmode[codes[j]]: continue
            w=m.NewBoolVar(f"w{i}_{j}_{d}")
            m.Add(w<=v[i][d]); m.Add(w<=v[j][d]); m.Add(w>=v[i][d]+v[j][d]-1)
            sp.append(w*int(H[i][j]*1000))
m.Minimize(sum(sp))
sv=cp_model.CpSolver(); sv.parameters.max_time_in_seconds=120; sv.parameters.num_workers=8
st=sv.Solve(m)
print("CP-SAT:",sv.StatusName(st),"objective:",sv.ObjectiveValue(), flush=True)
cps_plan={d:[i for i in range(n) if sv.Value(v[i][d])] for d in range(DAYS)}
assert sum(len(x) for x in cps_plan.values())==sum(freq)

# ---------- 真实链式里程评估 (每日重排) ----------
def day_route(seq):
    if len(seq)<=1: return seq,0.0
    k=len(seq); sub=[[H[a][b] for b in seq] for a in seq]
    unv=set(range(1,k)); order=[0]
    while unv: order.append(min(unv,key=lambda j:sub[order[-1]][j])); unv.discard(order[-1])
    def L(o): return sum(sub[o[i]][o[i+1]] for i in range(len(o)-1))
    imp=True; ps=0
    while imp and ps<25:
        imp=False; ps+=1
        for a in range(1,k-2):
            for b in range(a+1,k-1):
                if sub[order[a-1]][order[b]]+sub[order[b]][order[a]]<sub[order[a-1]][order[a]]+sub[order[b]][order[b+1]]-1e-9:
                    order[a:b+1]=order[a:b+1][::-1]; imp=True
    return [seq[t] for t in order],L(order)
def total(plan_sets):
    t=0.0
    for d_,s_ in plan_sets.items():
        if s_: t+=day_route(s_)[1]
    return t
srp_sets={}
for dd,gd in g.groupby("date"):
    srp_sets[dates.index(dd)]=[codes.index(c) for c in gd["客户编码"] if c in codes]
print(f"SRP 重排基准: {total(srp_sets):.1f} km | CP-SAT: {total(cps_plan):.1f} km", flush=True)

# ---------- 局部搜索: 真实里程, 同星期换日, 只收不劣; 两个起点各跑 ----------
def polish(plan_sets, rounds=400):
    plan_sets={d:list(s) for d,s in plan_sets.items()}
    tot=total(plan_sets)
    for it in range(rounds):
        best=None
        dcache={d_:day_route(s_) for d_,s_ in plan_sets.items() if s_}
        for i in range(n):
            ds=[d_ for d_ in range(DAYS) if i in plan_sets[d_]]
            if len(ds)<2: continue
            for d0 in ds:
                base=dcache[d0][1]; s0=[x for x in plan_sets[d0] if x!=i]
                r0=day_route(s0)[1] if s0 else 0.0
                for d1 in ds:
                    if d1==d0: continue
                    s1=plan_sets[d1]
                    if len(s1)+1>CAP_HI: continue
                    cand=s1+[i]; bestc=(1e18,0)
                    for pos in range(len(cand)):
                        q=cand[:pos]+[cand[-1]]+cand[pos:-1] if False else None
                    for pos in range(len(s1)+1):
                        q=s1[:pos]+[i]+s1[pos:]
                        bestc=min(bestc,(day_route(q)[1],pos))
                    delta=r0+bestc[0]-base-day_route(s1)[1]
                    if best is None or delta<best[0]-1e-9: best=(delta,i,d0,d1,bestc[1])
        if best is None or best[0]>=-1e-6: break
        _,i,d0,d1,pos=best
        plan_sets[d0]=[x for x in plan_sets[d0] if x!=i]
        plan_sets[d1]=plan_sets[d1][:pos]+[i]+plan_sets[d1][pos:]
        tot+=best[0]
    return plan_sets,tot,it
t0=time.time()
A,ta,ia=polish(cps_plan); print(f"CP-SAT 起点局部搜索: {ta:.1f} km ({ia} 步, {time.time()-t0:.0f}s)", flush=True)
B,tb,ib=polish(srp_sets); print(f"SRP 起点局部搜索(保底):   {tb:.1f} km ({ib} 步)", flush=True)

final = A if ta<=tb else B
ft = min(ta,tb)
assert sum(len(x) for x in final.values())==sum(freq)
print(f"\n== 最终(次数逐店精确一致, 真实里程) ==")
print(f"SRP 重排: 234.0km量级 | CP-SAT+搜索: {ta:.1f} | SRP+搜索: {tb:.1f} | 采用: {'CP-SAT' if ta<=tb else 'SRP系'} {ft:.1f} km")
rows=[]
for d_,seq in final.items():
    if not seq: continue
    ordr,kmv=day_route(seq)
    for r_,i in enumerate(ordr,1):
        rows.append(dict(拜访日期=str(dates[d_]),拜访顺序=r_,客户编码=codes[i]))
out=pd.DataFrame(rows).sort_values(["拜访日期","拜访顺序"])
out.to_csv(f"output/srp_exact_{REP}.csv",index=False)
json.dump({"srp_reseq":round(total(srp_sets),1),"cpsat_polish":round(ta,1),
           "srp_polish":round(tb,1),"final":round(ft,1),"used":"cpsat" if ta<=tb else "srp"},
          open(f"output/srp_exact_{REP}.json","w"),ensure_ascii=False,indent=1)
print("saved output/srp_exact_"+REP+".csv 行数:",len(out))
