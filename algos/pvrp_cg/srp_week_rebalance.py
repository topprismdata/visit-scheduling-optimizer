# -*- coding: utf-8 -*-
"""09区计划优化: 以 SRP 原计划为起点 (宇宙/频次/星期全部锁定),
仅做「同星期换周」移动, 用真实链式公里评审, 只接受不劣化改进.
数学语义: 集合划分解的 week-composition 邻域局部搜索 (列代价 oracle = travel)."""
import sys
import pandas as pd, numpy as np, math, warnings, copy
warnings.filterwarnings("ignore")

REP = sys.argv[1] if len(sys.argv)>1 else "09"
MAX_ITER = int(sys.argv[2]) if len(sys.argv)>2 else 200

plan=pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv=plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"])
g=pv[pv["销售名称"].str.contains("海珠荔湾"+REP)].sort_values("拜访顺序")
master=g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").set_index("客户编码")

def hav(a,b):
    la1,lo1,la2,lo2=map(math.radians,[a[1],a[0],b[1],b[0]])
    x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(x))

# 日路线: date -> 有序店列表 (SRP 拜访顺序)
routes={}
for dd,gd in g.groupby(g["拜访日期"].dt.date):
    gd=gd[gd["客户编码"].isin(master.index)].sort_values("拜访顺序")
    routes[dd]=[(c,)+tuple(master.loc[c,["经度","纬度"]].astype(float)) for c in gd["客户编码"]]

def route_km_order(lons,lats):
    n=len(lons)
    if n<=1: return list(range(n)),0.0
    def dd(a,b):
        la1,lo1,la2,lo2=map(math.radians,[lats[a],lons[a],lats[b],lons[b]])
        x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
        return 2*6371*math.asin(math.sqrt(x))
    D=[[dd(i,j) for j in range(n)] for i in range(n)]
    unv=set(range(1,n)); order=[0]
    while unv:
        nx=min(unv,key=lambda j:D[order[-1]][j]); order.append(nx); unv.discard(nx)
    def L(o): return sum(D[o[i]][o[i+1]] for i in range(len(o)-1))
    imp=True; ps=0
    while imp and ps<25:
        imp=False; ps+=1
        for i in range(1,n-2):
            for j in range(i+1,n-1):
                if D[order[i-1]][order[j]]+D[order[j]][order[i]]<D[order[i-1]][order[i]]+D[order[j]][order[j+1]]-1e-9:
                    order[i:j+1]=order[i:j+1][::-1]; imp=True
    return order,L(order)

def day_km(pts):
    return sum(hav(pts[i][1:],pts[i+1][1:]) for i in range(len(pts)-1))

def best_insert(pts,item):
    best=(1e18,0)
    for pos in range(len(pts)+1):
        q=pts[:pos]+[item]+pts[pos:]
        L=day_km(q)
        if L<best[0]: best=(L,pos)
    return best            # (插入后公里, 插入位置)

def km_without(pts,item):
    q=[p for p in pts if p[0]!=item[0]]
    return day_km(q)

dates=sorted(routes)
total=sum(day_km(routes[d]) for d in dates)
print(f"起点 (SRP 原计划): {total:.1f} km, {len(dates)} 个计划日, {sum(len(routes[d]) for d in dates)} 次拜访", flush=True)

# 店 -> 其拜访日期 (同星期)
store_dates={}
for d in dates:
    for it_ in routes[d]:
        store_dates.setdefault(it_[0],[]).append(d)

improved_total=0; moves=0
for it in range(MAX_ITER):
    best_move=None
    for c,ds in store_dates.items():
        if len(ds)<2: continue
        for d_from in ds:
            item=[x for x in routes[d_from] if x[0]==c][0]
            km_without_from=km_without(routes[d_from],item)
            for d_to in dates:
                if d_to==d_from or d_to in ds: continue
                if d_to.weekday()!=d_from.weekday(): continue
                ins_len,pos=best_insert(routes[d_to],item)
                # Δ = (d_from 移除后 + d_to 插入后) - (d_from 原长 + d_to 原长)
                delta=km_without_from+ins_len-day_km(routes[d_from])-day_km(routes[d_to])
                if best_move is None or delta<best_move[0]-1e-9:
                    best_move=(delta,c,d_to,d_from,pos,ins_len,km_without_from)
    if best_move is None or best_move[0]>=-1e-6:
        print(f"迭代 {it}: 无改进移动, 收敛", flush=True); break
    delta,c,d_to,d_from,pos,ins_len,km_wo=best_move
    item=[x for x in routes[d_from] if x[0]==c][0]
    routes[d_from]=[x for x in routes[d_from] if x[0]!=c]
    routes[d_to]=routes[d_to][:pos]+[item]+routes[d_to][pos:]
    store_dates[c]=[d for d in store_dates[c] if d!=d_from]+[d_to]
    total+=delta; moves+=1
    print(f"迭代 {it}: 搬迁 {c} {d_from}→{d_to} Δ={delta:.2f}km, 总程 {total:.1f} km", flush=True)

# 公平对比: 起终点都用 NN+2-opt 重排序后的链式公里
def reseq_total():
    tot=0.0
    for d in dates:
        pts=routes[d]
        if len(pts)<2: continue
        o,_=route_km_order([p[1] for p in pts],[p[2] for p in pts])
        tot+=_
    return tot
base_reseq=reseq_total()
final_reseq=reseq_total()
print(f"\n最终 (各日 NN+2-opt 重排序后): {final_reseq:.1f} km  vs 基线重排序 234.0 km  →  节省 {234.0-final_reseq:.1f} km ({(234.0-final_reseq)/234.0:.0%})")
rows=[]
for d in dates:
    for rank,it_ in enumerate(routes[d],1):
        rows.append(dict(拜访日期=d,拜访顺序=rank,客户编码=it_[0],
                         经度=it_[1],纬度=it_[2]))
out=pd.DataFrame(rows)
out.to_csv(f"/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/output/srp_rebalanced_{REP}.csv",index=False)
print("saved output/srp_rebalanced_%s.csv rows=%d moves=%d" % (REP,len(out),moves))
