# -*- coding: utf-8 -*-
"""SRP 计划改进 (业务→数学→引擎).
业务: SRP 有效计划; 每店次数精确; 星期锁定; 日容量锚定 SRP 负载; 骑行口径后续统一.
数学: 星期锁定 ⇒ 问题按 5 个工作日解耦为独立子周期 PVRP (客户=该星期门店, 天=该星期的 4-5 个日期).
引擎: 仓库 ALNS (baselines.ALNS, Røpke-Pisinger: Shaw/worst/random/day 破坏 + 贪心/后悔-2 修复
      + 自适应权重 + RRT). 唯一适配: initial() 改为 SRP warm start. 逐星期取 min(SRP, ALNS) → 严格不劣.
"""
import sys, math, time, json, datetime
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")
from algos.pvrp_cg.baselines import ALNS
REP = sys.argv[1] if len(sys.argv)>1 else "09"
BUDGET = int(sys.argv[2]) if len(sys.argv)>2 else 45

plan=pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv=plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"]); pv["date"]=pv["拜访日期"].dt.date
g=pv[pv["销售名称"].str.contains("海珠荔湾"+REP)].sort_values("拜访顺序")
mst=g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").reset_index(drop=True)
codes=mst["客户编码"].tolist(); idx_of={c:i for i,c in enumerate(codes)}
freq=g.groupby("客户编码").size().reindex(codes).astype(int).tolist()
wmode={}
for c,s in g.groupby("客户编码")["拜访日期"]: wmode[idx_of[c]]=int(s.dt.weekday.value_counts().index[0])
LON=mst["经度"].astype(float).tolist(); LAT=mst["纬度"].astype(float).tolist()
def hav(i,j):
    la1,lo1,la2,lo2=map(math.radians,[LAT[i],LON[i],LAT[j],LON[j]])
    x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(x))
H=[[hav(i,j) for j in range(len(codes))] for i in range(len(codes))]
DATES=[]; d=datetime.date(2026,7,1)
while d.month==7:
    if d.weekday()<5: DATES.append(d)
    d+=datetime.timedelta(days=1)
by_wd={}
for i,c in enumerate(codes): by_wd.setdefault(wmode[i],[]).append(i)
srp_load=g.groupby("date").size(); CAP_HI=int(srp_load.max())+2

def route_km(seq):
    return sum(H[seq[k]][seq[k+1]] for k in range(len(seq)-1)) if len(seq)>1 else 0.0
def two_opt(seq):
    seq=list(seq)
    if len(seq)<=3: return seq,route_km(seq)
    imp=True; ps=0
    while imp and ps<30:
        imp=False; ps+=1
        for a in range(1,len(seq)-2):
            for b in range(a+1,len(seq)-1):
                if H[seq[a-1]][seq[b]]+H[seq[b]][seq[a]]<H[seq[a-1]][seq[a]]+H[seq[b]][seq[b+1]]-1e-9:
                    seq[a:b+1]=seq[a:b+1][::-1]; imp=True
    return seq,route_km(seq)

WD="一二三四五"
tot_srp=0.0; tot_new=0.0; new_plan={}
for k in sorted(by_wd):
    stores=by_wd[k]
    day_dates=[di for di,dd in enumerate(DATES) if dd.weekday()==k]
    nk=len(day_dates)
    warm={di:[] for di in range(nk)}
    # SRP 当期日集合
    for di,dd in enumerate(day_dates):
        gd=g[g["date"]==DATES[dd]]
        warm[di]=sorted(idx_of[c] for c in gd["客户编码"] if c in idx_of)
    def nn(seq):
        seq=list(seq)
        if len(seq)<=2: return seq
        out=[seq.pop(0)]; unv=set(seq)
        while unv:
            last=out[-1]
            nxt=min(unv,key=lambda j:H[last][j]); out.append(nxt); unv.discard(nxt)
        return out
    # 与 SRP 基准同法: NN 建序 + 2-opt
    warm=[two_opt(nn(warm[di]))[0] for di in range(nk)]
    f_srp=sum(route_km(r) for r in warm)
    remap={g0:i for i,g0 in enumerate(stores)}      # 全局索引→子问题索引
    subfreq=[freq[g0] for g0 in stores]
    def cost_fn(ids, _m=remap):
        seq=[stores[t] for t in ids]
        return two_opt(seq)[1]
    class Warm(ALNS):
        def initial(self):
            return [set(r) for r in warm_sub]
    warm_sub=[set(remap[x] for x in r) for r in warm]
    a=Warm(n=len(stores), freq=subfreq, days=nk, col_cost_fn=cost_fn,
           daily_cap=None, seed=42, max_per_day=CAP_HI)
    sol,bf,it_,stats=a.run(time_budget=BUDGET)
    ok=bool(stats.get("valid"))
    sol_sets=[set(s) for s in sol]
    new_routes=[sorted(stores[t] for t in s) for s in sol_sets]
    f_new=sum(two_opt(r)[1] for r in new_routes)
    if ok and f_new < f_srp-1e-9:
        chosen=new_routes; f_ch=f_new; tag="ALNS"
    else:
        chosen=warm; f_ch=f_srp; tag="SRP保底"
    tot_srp+=f_srp; tot_new+=f_ch
    for di,r in enumerate(chosen):
        new_plan[day_dates[di]]=two_opt(r)[0]
    print(f"周{WD[k]}: {len(stores)}店 {sum(subfreq)}次 SRP={f_srp:6.1f} ALNS={f_new:6.1f} valid={ok} → {tag} {f_ch:6.1f}", flush=True)
print(f"\n合计: SRP重排 {tot_srp:.1f} km → 改进后 {tot_new:.1f} km (节省 {tot_srp-tot_new:.1f} km, {(tot_srp-tot_new)/tot_srp:.1%})")
cnt=[0]*len(codes)
for r in new_plan.values():
    for i in r: cnt[i]+=1
assert cnt==freq, "次数被破坏"
rows=[]
for di,rt in sorted(new_plan.items()):
    for r_,i in enumerate(rt,1):
        rows.append(dict(拜访日期=str(DATES[di]),拜访顺序=r_,客户编码=codes[i]))
pd.DataFrame(rows).to_csv(f"output/srp_alns_{REP}.csv",index=False)
json.dump({"srp_reseq":round(tot_srp,1),"improved":round(tot_new,1),
           "saving_pct":round((tot_srp-tot_new)/tot_srp*100,1),"budget":BUDGET},
          open(f"output/srp_alns_{REP}.json","w"),ensure_ascii=False,indent=1)
print(f"saved output/srp_alns_{REP}.csv (次数逐店精确 ✓)")
