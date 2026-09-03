# -*- coding: utf-8 -*-
import pandas as pd, numpy as np, math, warnings
warnings.filterwarnings("ignore")
plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"]=="有效"].copy()
pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"])
g = pv[pv["销售名称"]=="海珠荔湾09"].copy()
g["date"]=g["拜访日期"].dt.date
pts = g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码").set_index("客户编码")
LON=pts["经度"].astype(float).to_dict(); LAT=pts["纬度"].astype(float).to_dict()
def dist(a,b):
    la1,lo1,la2,lo2=map(math.radians,[LAT[a],LON[a],LAT[b],LON[b]])
    x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(x))
def chain(seq): return sum(dist(seq[k],seq[k+1]) for k in range(len(seq)-1)) if len(seq)>1 else 0.0
def nn_order(cs):
    out=[cs[0]]; unv=set(cs[1:])
    while unv:
        l=out[-1]; out.append(min(unv,key=lambda j:dist(l,j))); unv.discard(out[-1])
    return out
def two_opt(seq):
    seq=list(seq); n=len(seq)
    for _ in range(30):
        imp=False
        for a in range(1,n-2):
            for b in range(a+1,n-1):
                if dist(seq[a-1],seq[b])+dist(seq[b],seq[a]) < dist(seq[a-1],seq[a])+dist(seq[b],seq[b+1]) - 1e-9:
                    seq[a:b+1]=seq[a:b+1][::-1]; imp=True
        if not imp: break
    return seq
tot_p=0.0; tot_n=0.0
WD="一二三四五"
print(f"{'日期':<12}{'星期':>4}{'店数':>4}{'原序km':>8}{'重排km':>8}")
for dd in sorted(g["date"].unique()):
    gd=g[g["date"]==dd]
    cs=sorted(set(gd["客户编码"]))
    if len(cs)<2: continue
    printed=chain(cs)
    opt=two_opt(nn_order(cs))
    kmn=chain(opt)
    tot_p+=printed; tot_n+=kmn
    wdd=pd.Timestamp(dd).weekday()
    print(f"{dd}  周{WD[wdd]}  {len(cs):>3}店  原序 {printed:6.1f}km → 重排 {kmn:6.1f}km")
print(f"\n全月: 原始 {tot_p:.1f} km → 重排 {tot_n:.1f} km ({(tot_n-tot_p)/tot_p:+.1%})")
