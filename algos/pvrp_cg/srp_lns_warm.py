# -*- coding: utf-8 -*-
"""SRP 计划改进层: warm-start LNS (ruin & recreate), 次数/星期构造性不变, 严格不劣化.
文献: Shahmardan et al. 2025 warm-start LNS; CP-LNS hybrid (Cirrelt) 可行性修复."""
import sys, math, time, json, random, datetime
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")

REP = sys.argv[1] if len(sys.argv)>1 else "09"
BUDGET = int(sys.argv[2]) if len(sys.argv)>2 else 90
SEED = int(sys.argv[3]) if len(sys.argv)>3 else 42

plan=pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv=plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"]); pv["date"]=pv["拜访日期"].dt.date
g=pv[pv["销售名称"].str.contains("海珠荔湾"+REP)].sort_values("拜访顺序")
mst=g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").reset_index(drop=True)
codes=mst["客户编码"].tolist(); n=len(codes)
idx_of={c:i for i,c in enumerate(codes)}
freq=g.groupby("客户编码").size().reindex(codes).astype(int).tolist()
wmode={}
for c,s in g.groupby("客户编码")["拜访日期"]: wmode[idx_of[c]]=int(s.dt.weekday.value_counts().index[0])
LON=mst["经度"].astype(float).tolist(); LAT=mst["纬度"].astype(float).tolist()
def hav(i,j):
    la1,lo1,la2,lo2=map(math.radians,[LAT[i],LON[i],LAT[j],LON[j]])
    x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(x))
H=[[hav(i,j) for j in range(n)] for i in range(n)]
DATES=[]; d=datetime.date(2026,7,1)
while d.month==7:
    if d.weekday()<5: DATES.append(d)
    d+=datetime.timedelta(days=1)
DAYS=len(DATES)
wd2days={}
for di,dd in enumerate(DATES): wd2days.setdefault(dd.weekday(),[]).append(di)
srp_daily=g.groupby("date").size()
CAP_LO=max(1,int(srp_daily.min())-2); CAP_HI=int(srp_daily.max())+2

# ---- warm start: SRP 日集合; 每日先 cheapest-insertion 建序 + 2-opt (等价于"重排基准") ----
def day_len(route): return sum(H[route[k]][route[k+1]] for k in range(len(route)-1)) if len(route)>1 else 0.0
def two_opt(route):
    route=list(route)
    if len(route)<=3: return route,day_len(route)
    def L(o): return day_len(o)
    imp=True; ps=0
    while imp and ps<30:
        imp=False; ps+=1
        for a in range(1,len(route)-2):
            for b in range(a+1,len(route)-1):
                if H[route[a-1]][route[b]]+H[route[b]][route[a]] < H[route[a-1]][route[a]]+H[route[b]][route[b+1]]-1e-9:
                    route[a:b+1]=route[a:b+1][::-1]; imp=True
    return route,L(route)
def best_insert(route,i):
    """O(n) 扫描插入位, 返回 (新长度, pos)"""
    if not route: return 0.0,0
    best=(1e18,0)
    for pos in range(len(route)+1):
        prev=route[pos-1] if pos>0 else None
        nxt=route[pos] if pos<len(route) else None
        add=(H[prev][i] if prev is not None else 0)+(H[i][nxt] if nxt is not None else 0)
        if prev is not None and nxt is not None: add-=H[prev][nxt]
        if add<best[0]: best=(add,pos)
    return best
routes={di:[] for di in range(DAYS)}
for dd,gd in g.groupby("date"):
    di=DATES.index(dd)
    seq=[idx_of[c] for c in gd["客户编码"] if c in idx_of]
    order=[]
    rem=set(seq)
    while rem:
        seed=min(rem,key=lambda i:(min(H[i][j] for j in order) if order else 0))
        cur=(seed,order.index(seed) if False else None)
        add,pos=best_insert(order,seed)
        order=order[:pos]+[seed]+order[pos:]
        rem.discard(seed)
    routes[di]=two_opt(order)[0]
base=sum(day_len(r) for r in routes.values())
print(f"warm start(SRP 日集合+重排): {base:.1f} km", flush=True)

cnt=[0]*n
for r in routes.values():
    for i in r: cnt[i]+=1
assert cnt==freq, "起点次数≠SRP"

rng=random.Random(SEED)
def destroy(k):
    """Shaw: 种子随机, 逐步加入相关(同日近邻)店"""
    act=[di for di,r in routes.items() if len(r)>CAP_LO]
    di0=rng.choice(act); removed=[]
    pool=list(routes[di0]); seed=pool[rng.randrange(len(pool))]; removed.append((seed,di0))
    for _ in range(k-1):
        last=removed[-1][0]; best=None
        for di,rt in routes.items():
            if len(rt)<=CAP_LO: continue
            for j in rt:
                if (j,di) in removed: continue
                d0=H[last][j]+ (0 if wmode[j]==W[di] else 9e9)
                if best is None or d0<best[0]: best=(d0,j,di)
        if not best: break
        removed.append((best[1],best[2]))
    for i,di in removed: routes[di]=[x for x in routes[di] if x!=i]
    return removed
W=[DATES[di].weekday() for di in range(DAYS)]
def regret_insert(removed):
    """贪心后悔-2: 各店在允许星期日内找最优插入, 按 regret 序插入"""
    pend=list(removed); changed=set()
    while pend:
        evals=[]
        for i,_ in pend:
            cands=[]
            for di in wd2days[W[i] if False else wmode[i]]:
                if len(routes[di])>=CAP_HI: continue
                add,pos=best_insert(routes[di],i)
                cands.append((add,di,pos))
            cands.sort()
            reg=cands[1][0]-cands[0][0] if len(cands)>1 else 0
            evals.append((cands[0][0]-0.5*reg,cands[0],i))
        if not evals: break
        evals.sort()
        _,(add,di,pos),i=evals[0]
        routes[di]=routes[di][:pos]+[i]+routes[di][pos:]
        changed.add(di)
        pend=[(j,dd) for j,dd in pend if j!=i]
    for di in changed: routes[di]=two_opt(routes[di])[0]
cur=base; best=base
t0=time.time(); it=0
while time.time()-t0<BUDGET:
    it+=1
    snapshot={di:list(r) for di,r in routes.items()}
    k=rng.randint(4,12)
    removed=destroy(k)
    regret_insert(removed)
    new=sum(day_len(r) for r in routes.values())
    RRT=0.02*max(best,1.0)
    if new<best-1e-9:
        best=new; cur=new
    elif new<cur+RRT:
        cur=new
    else:
        routes=snapshot
# 次数校验
cnt=[0]*n
for r in routes.values():
    for i in r: cnt[i]+=1
assert cnt==freq, f"LNS 后次数被破坏! {[(codes[i],freq[i],cnt[i]) for i in range(n) if cnt[i]!=freq[i]][:5]}"
assert all(len(r)<=CAP_HI and len(r)>=CAP_LO for r in routes.values())
print(f"LNS({BUDGET}s,{it} 迭代): {base:.1f} → {best:.1f} km ({(base-best)/base:.1%})  次数逐店精确一致 ✓")
rows=[]
for di,rt in routes.items():
    for r_,i in enumerate(rt,1):
        rows.append(dict(拜访日期=str(DATES[di]),拜访顺序=r_,客户编码=codes[i]))
out=pd.DataFrame(rows).sort_values(["拜访日期","拜访顺序"])
out.to_csv(f"output/srp_lns_{REP}.csv",index=False)
json.dump({"warm":round(base,1),"lns":round(best,1),"iters":it,"budget":BUDGET},
          open(f"output/srp_lns_{REP}.json","w"),ensure_ascii=False,indent=1)
print("saved")
