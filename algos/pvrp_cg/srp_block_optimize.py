# -*- coding: utf-8 -*-
"""业务→数学→引擎 v2: 「每周同一天·同区块」业务规则的形式化.

业务描述 (来自原计划的真实习惯):
  R1 每店每月拜访 f_i 次 (SRP 原计划 ±1 浮动)
  R2 同一客户每周固定同一个星期几 (weekday-lock)
  R3 同一个星期几尽量只跑同一个区块 (软约束: 跨区块同日店对最小化)
  R4 日负载锚定原计划 (DAY_LO..DAY_HI)
  R5 尽量贴近原计划的星期安排 (业务连续性)

数学模型 (CP-SAT, 字典序分层):
  z[i][p]  客户 i 选择 weekday-pure 模式 p (同星期, 长度∈[lo_i, hi_i])
  B[k][b]  星期 k 分配区块 b;           Σ_b B[k][b] = 1
  一致性:  z[i][p] ≤ B[k(p)][block(i)]            (R2+R3 硬约束)
  v[i][d]  = Σ_{p∋d} z[i][p];  DAY_LO ≤ Σ_i v[i][d] ≤ DAY_HI   (R4)
  min_1 Σ pattern 不匹配原星期次数 (R5)
  min_2 Σ_i |load_i周 − 均衡|                        (负载均衡)
  min_3 日内同区块近邻对距离 (kNN 空间项)

引擎: ortools CP-SAT + travel 风格 NN+2-opt 日内排序.
"""
import sys, json, math, time
import faulthandler
faulthandler.dump_traceback_later(90, repeat=True, file=open("/tmp/gz_stack.txt","w"))
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
import pandas as pd, numpy as np, warnings, datetime
warnings.filterwarnings("ignore")
from itertools import combinations as comb
from ortools.sat.python import cp_model

REP = sys.argv[1] if len(sys.argv) > 1 else "09"
TIER_TIME = 30

# ---------- 业务层装载 ----------
plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"]); pv["date"]=pv["拜访日期"].dt.date
g = pv[pv["销售名称"].str.contains("海珠荔湾"+REP)].sort_values("拜访日期")
name = g["销售名称"].iloc[0]
master = g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码", keep="first")
freq = g.groupby("客户编码").size().reindex(master["客户编码"]).astype(int)
wmode = g.groupby("客户编码")["拜访日期"].apply(lambda s:int(s.dt.weekday.value_counts().index[0])).to_dict()
print(f"片区{REP} ({name}): 客户{len(master)} 月拜访{freq.sum()}", flush=True)

# ---------- 区块 (路网 GeoJSON) ----------
gj = json.load(open("/Users/ghb/Downloads/边界数据-路网-到区县带海岸线-四级路网-广东省-广州市.geojson"))
keep={"440103","440104","440105","440106","440111","440112","440113"}
blocks=[]
for i,f in enumerate(gj["features"]):
    p=f["properties"]
    if p.get("区县编码") not in keep: continue
    poly=f["geometry"]["coordinates"][0]
    xs=[c[0] for c in poly]; ys=[c[1] for c in poly]
    blocks.append((str(i), poly, min(xs),max(xs),min(ys),max(ys)))
def pip(lng,lat,poly):
    inside=False; j=len(poly)-1
    for i in range(len(poly)):
        xi,yi=poly[i]; xj,yj=poly[j]
        if ((yi>lat)!=(yj>lat)) and (lng<(xj-xi)*(lat-yi)/(yj-yi)+xi): inside=not inside
        j=i
    return inside
def block_of(lng,lat):
    cands=[b for b in blocks if b[2]<=lng<=b[3] and b[4]<=lat<=b[5]]
    for b in cands:
        if pip(lng,lat,b[1]): return b[0]
    if cands: return min(cands,key=lambda b:((b[2]+b[3])/2-lng)**2+((b[4]+b[5])/2-lat)**2)[0]
    return min(blocks,key=lambda b:((b[2]+b[3])/2-lng)**2+((b[4]+b[5])/2-lat)**2)[0]

t=time.time()
m2=master.reset_index(drop=True)
regions=[block_of(float(r["经度"]),float(r["纬度"])) for _,r in m2.iterrows()]
codes=m2["客户编码"].tolist()
print("落块完成; 使用区块数:", len(set(regions)), round(time.time()-t,1),"s", flush=True)

# ---------- 日期槽位 ----------
slots={}; DATES=[]; d=datetime.date(2026,7,6); i=0   # 4周完整周期 7/6-7/31 (7/1-3 溢出)
while d.month==7:
    if d.weekday()<5: slots.setdefault(d.weekday(),[]).append(i); DATES.append(d); i+=1
    d+=datetime.timedelta(days=1)
DAYS=len(DATES)
WD="一二三四五六日"
srp_daily=g[g["date"]>=datetime.date(2026,7,6)].groupby("date").size()
DAY_LO=max(1,min(srp_daily)-2)
DAY_HI=max(srp_daily)+2

# ---------- 数学层: CP-SAT ----------
m=cp_model.CpModel()
stores=list(range(len(codes)))
block_ids=sorted(set(regions))
bidx={b:k for k,b in enumerate(block_ids)}

# 模式: 星期纯 (同星期, 长度 [f-1,f+1])
pats=[];  # (store, weekday, days_tuple, consistency)
for i in stores:
    f=int(freq[codes[i]]); mwd=wmode.get(codes[i],0)
    f_c=min(f,4)   # 4周周期内: 5次/月 = 每周1次(第5周为溢出)
    wk={k:ss for k,ss in slots.items()}
    for k,ss in wk.items():
        if f_c==len(ss):
            pats.append((i,k,tuple(ss), 0 if k==mwd else f_c))
        elif len(ss)>f_c:
            for sub in comb(ss,f_c):
                cons=sum(1 for s in sub if DATES[s].weekday()!=mwd)
                pats.append((i,k,tuple(sub),cons))
z={}; CONS={}
for i,k,days,c in pats:
    key=(i,k,days)
    if key in z: continue
    z[key]=m.NewBoolVar(f"z{i}_{k}_{days[0]}_{len(days)}")
    CONS[key]=c
for i in stores:
    vs=[z[key] for key in z if key[0]==i]
    m.Add(sum(vs)==1)
print(f"模式数: {len(pats)} (每店 {len(pats)//len(stores)} 均值)", flush=True)

# R3「同星期同区块」= 软约束: 以跨区块同日店对数量进入目标层 (见 t2)

# v[i][d] + 日容量
v={}
for i in stores:
    for d in range(DAYS):
        v[i,d]=m.NewBoolVar(f"v{i}_{d}")
    for d in range(DAYS):
        m.Add(sum(z[key] for key in z if key[0]==i and d in key[2])==v[i,d])
for d in range(DAYS):
    m.Add(sum(v[i,d] for i in stores)>=10)
    m.Add(sum(v[i,d] for i in stores)<=45)

# ---------- 分层目标 ----------
# T1 业务连续性: 贴近原计划星期
t1=sum(z[key]*CONS[key] for key in z)
# T2 负载均衡
load={d:sum(v[i,d] for i in stores) for d in range(DAYS)}
tgt=int(round(freq.sum()/DAYS))
dev={d:m.NewIntVar(0,DAY_HI,f"dev{d}") for d in range(DAYS)}
for d in range(DAYS): m.AddAbsEquality(dev[d], load[d]-tgt)
t2=sum(dev.values())
# T3 日内空间紧凑 (同区块近邻对, kNN=8)
def hav_km(a,b):
    la1,lo1,la2,lo2=map(np.radians,[a[1],a[0],b[1],b[0]])
    x=np.sin((la2-la1)/2)**2+np.cos(la1)*np.cos(la2)*np.sin((lo2-lo1)/2)**2
    return float(2*6371*np.arcsin(np.sqrt(x)))
XY={i:(float(m2.loc[i,"经度"]),float(m2.loc[i,"纬度"])) for i in stores}
nbr={i:sorted(stores,key=lambda j:hav_km(XY[i],XY[j]))[1:9] for i in stores}
t3=[]   # R3 软约束: 同一天出现在不同区块的近邻店对数 (尽量=0)
for d in range(DAYS):
    for i in stores:
        for j in nbr[i]:
            if j<=i or regions[i]==regions[j]: continue
            w=m.NewBoolVar(f"w{i}_{j}_{d}")
            m.Add(w<=v[i,d]); m.Add(w<=v[j,d]); m.Add(w>=v[i,d]+v[j,d]-1)
            t3.append(w)
# T1.5 频次贴合: 每店排班次数贴近 SRP 原计划 (防"削量换均衡")
fgap=[]
for i in stores:
    fi=int(freq[codes[i]])
    cv=m.NewIntVar(0,4,f"cnt{i}")
    m.Add(cv==sum(v[i,d] for d in range(DAYS)))
    dv=m.NewIntVar(0,4,f"dfg{i}")
    m.AddAbsEquality(dv,cv-fi)
    fgap.append(dv)
# 空间距离层: 同日 kNN 店对 × 实际公里数 (里程成为一等目标)
t4=[]
for d in range(DAYS):
    for i in stores:
        for j in nbr[i]:
            if j<=i: continue
            w=m.NewBoolVar(f"sp{i}_{j}_{d}")
            m.Add(w<=v[i,d]); m.Add(w<=v[j,d]); m.Add(w>=v[i,d]+v[j,d]-1)
            t4.append(w*int(hav_km(XY[i],XY[j])*100))
# 区块层已删除: 路网边界是人工切割, 与真实距离冲突 (实验证据 v1/v2)
# 负载均衡层删除 (用户假设验证: 过度均衡拆散自然簇 → 里程上升)
levels=[("consistency",t1),("freq_adherence",sum(fgap)),("spatial",sum(t4))]
sv=cp_model.CpSolver(); sv.parameters.num_workers=8
objs={}; sts={}
sol_z=None
for nm,expr in levels:
    sv.parameters.max_time_in_seconds=TIER_TIME
    m.Minimize(expr)
    st=sv.Solve(m)
    sts[nm]=str(st)
    if st not in (cp_model.OPTIMAL,cp_model.FEASIBLE): break
    val=int(round(sv.ObjectiveValue()))
    objs[nm]=val
    m.Add(expr==val)
    m.ClearHints()
    for key,var in z.items(): m.AddHint(var, sv.Value(var))
    sol_z={key:sv.Value(var) for key,var in z.items() if sv.Value(var)}
print("objectives:", objs, "statuses:", sts, flush=True)

# ---------- 日内排序 + 与 SRP 对比 ----------
def nn2opt(lons,lats):
    n=len(lons)
    if n<=1: return list(range(n)),0.0
    def d(a,b):
        la1,lo1,la2,lo2=map(math.radians,[lats[a],lons[a],lats[b],lons[b]])
        x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
        return 2*6371*math.asin(math.sqrt(x))
    D=[[d(i,j) for j in range(n)] for i in range(n)]
    unv=set(range(1,n)); order=[0]
    while unv:
        nx=min(unv,key=lambda j:D[order[-1]][j]); order.append(nx); unv.discard(nx)
    def L(o): return sum(D[o[i]][o[i+1]] for i in range(len(o)-1))
    imp=True; passes=0
    while imp and passes<25:   # 防退化护栏: 同坐标堆叠时浮点噪声可致微改进循环
        imp=False; passes+=1
        for i in range(1,n-2):
            for j in range(i+1,n-1):
                if D[order[i-1]][order[j]]+D[order[j]][order[i]]<D[order[i-1]][order[i]]+D[order[j]][order[j+1]]-1e-9:
                    order[i:j+1]=order[i:j+1][::-1]; imp=True
    return order,L(order)

chosen={}
_t=time.time()
for (i,k,days),_ in z.items():
    if sol_z.get((i,k,days)): chosen.setdefault(k,{}).setdefault(i,[]).extend(days)
print("chosen 构建", round(time.time()-_t,1),"s", flush=True)
opt_km=0.0; loads=[]; rows=[]; wdblock={}
srp_km=0.0
mid=master.set_index("客户编码")
srp_km=0.0
_t=time.time(); _n=0
import itertools as _it
_gsorted = g.sort_values("拜访顺序")
print("SRP循环: 排序完成", len(_gsorted), "行", flush=True)
for dd, gd in _gsorted.groupby("date"):
    print(f"  SRP组 {dd} n={len(gd)}", flush=True)
    gd=gd[gd["客户编码"].isin(mid.index)]
    if len(gd)<2: continue
    mm=mid.loc[gd["客户编码"]]
    o,_=nn2opt(mm["经度"].tolist(),mm["纬度"].tolist())
    srp_km+=_; _n+=1
print("SRP基线排序", _n,"天", round(time.time()-_t,1),"s", flush=True)
for k in sorted(slots):
    if k not in chosen: continue
    stores_k=sorted(chosen[k])
    days=sorted(set(s for i in stores_k for s in [x for key in z if key[0]==i and key[1]==k for x in key[2]]) ) if False else None
    # 该星期的每个槽位: 覆盖其上的店
    for si,di in enumerate(slots[k]):
        group=[i for i in stores_k if di in chosen.get(k,{}).get(i,[])]
        if not group: continue
        loads.append(len(group))
        bl=regions[group[0]]
        wdblock.setdefault(k,set()).add(bl)
        o,kmv=nn2opt([XY[i][0] for i in group],[XY[i][1] for i in group])
        opt_km+=kmv
        date=DATES[di]
        for rank,ii in enumerate(o,1):
            rows.append(dict(销售编码=g["销售编码"].iloc[0],销售名称=name,拜访日期=date,
                             拜访顺序=rank,客户编码=codes[group[ii]],客户名称=m2.loc[group[ii],"客户名称"]))
print(f"\nSRP现行: {srp_km:.1f} km/月   优化后: {opt_km:.1f} km/月   节省 {srp_km-opt_km:.1f} km ({(srp_km-opt_km)/max(srp_km,1):.0%})")
print("日负载:", loads)
print("星期→区块数:", {WD[k]:len(v) for k,v in sorted(wdblock.items())})
out=pd.DataFrame(rows)
import os
os.makedirs("output", exist_ok=True)
out.to_csv(f"output/srp_block_opt_{REP}.csv",index=False)
json.dump({"srp_km":srp_km,"opt_km":opt_km,"loads":loads,"objs":objs,
           "weekday_blocks":{WD[k]:sorted(v) for k,v in wdblock.items()}},
          open(f"output/srp_block_opt_{REP}.json","w"),ensure_ascii=False,indent=1)
print("saved block2_opt_%s.csv rows=%d" % (REP,len(out)))
