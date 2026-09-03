# -*- coding: utf-8 -*-
"""SRP 拜访计划优化 — 全部基于 OSM 骑行路网距离.
① 重排每日顺序: 店→日不变, 仅 TSP 优化日内顺序.
② 重新安排拜访: 允许跨日移动店, 月总次数不变, 每日顺序最优."""
import pandas as pd, numpy as np, math, json, time, warnings
warnings.filterwarnings("ignore")

# ---------- 数据 ----------
plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"]=="有效"].copy(); pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"])
g = pv[pv["销售名称"]=="海珠荔湾09"].copy(); g["date"]=g["拜访日期"].dt.date
pts = g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").set_index("客户编码")
codes = pts.index.tolist(); idx={c:i for i,c in enumerate(codes)}
n=len(codes); DATES=sorted(g["date"].unique())

# ---------- 路网距离矩阵 ----------
D = np.load("output/road_dist_09.npy")
print(f"{n} 店, 路网距离矩阵 {D.shape}, 填充率 {(~np.isnan(D)).mean():.0%}")
D = np.nan_to_num(D, nan=D.max()*0.5)

def day_km(seq):
    if len(seq)<2: return 0.0
    return float(sum(D[seq[k]][seq[k+1]] for k in range(len(seq)-1)))

def nn2opt(seq):
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

# ---------- 原始计划 ----------
days_orig = {dd: sorted([idx[c] for c in g[g["date"]==dd]["客户编码"] if c in idx]) for dd in DATES}
# 按计划原顺序(不重排)
days_orig_seq = {dd: [idx[c] for c in g[g["date"]==dd].sort_values("拜访顺序")["客户编码"] if c in idx] for dd in DATES}
total_orig = sum(day_km(days_orig_seq[dd]) for dd in DATES)

# ---------- ① 重排顺序 ----------
days_1 = {dd: nn2opt(days_orig[dd]) for dd in DATES}
total_1 = sum(day_km(days_1[dd]) for dd in DATES)

print(f"\n原始计划:  {total_orig:.1f} km")
print(f"①顺序重排: {total_1:.1f} km  (-{(total_orig-total_1)/total_orig:.0%})")

# ---------- ② 重新安排拜访 ----------
days_2 = {dd: list(days_1[dd]) for dd in DATES}
moves = 0
start = time.time()
for round_num in range(50):
    improved = False
    for dd1 in DATES:
        for dd2 in DATES:
            if dd1 == dd2: continue
            s1 = days_2[dd1]; s2 = days_2[dd2]
            if len(s1) <= 5: continue
            for c in list(s1):
                if c in s2: continue
                ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
                if len(ns1) < 2: continue
                r1o = nn2opt(s1); r2o = nn2opt(s2)
                r1n = nn2opt(ns1); r2n = nn2opt(ns2)
                old = day_km(r1o) + day_km(r2o)
                new = day_km(r1n) + day_km(r2n)
                if new < old - 0.05:
                    days_2[dd1] = r1n; days_2[dd2] = r2n
                    moves += 1; improved = True
            if time.time() - start > 180: break
    if not improved or time.time() - start > 180: break

total_2 = sum(day_km(days_2[dd]) for dd in DATES)

# 次数校验
freq_orig = g.groupby("客户编码").size().to_dict()
cnt2 = {}
for dd in DATES:
    for c in days_2[dd]:
        cnt2[codes[c]] = cnt2.get(codes[c], 0) + 1
ok = all(cnt2.get(c,0) == freq_orig.get(c,0) for c in freq_orig)

print(f"\n②重新安排: {total_2:.1f} km  (vs ① {total_1:.1f} km, 差 {total_1-total_2:+.1f} km)")
print(f"  跨日移动: {moves} 次")
print(f"  每店总次数: {'✓ 一致' if ok else '✗ 不一致!'}")
print(f"\n== 最终对比 (全部路网距离) ==")
print(f"  原始计划:   {total_orig:.1f} km")
print(f"  ①顺序重排:  {total_1:.1f} km  (-{(total_orig-total_1)/total_orig:.0%})")
print(f"  ②重新安排:  {total_2:.1f} km  (-{(total_orig-total_2)/total_orig:.0%})")

rows = []
for dd in DATES:
    seq = days_2[dd]
    for rank, c in enumerate(seq, 1):
        rows.append(dict(拜访日期=str(dd), 拜访顺序=rank, 客户编码=codes[c]))
pd.DataFrame(rows).to_csv("output/opt2_road_09.csv", index=False)
json.dump({"orig": round(total_orig,1), "opt1": round(total_1,1), "opt2": round(total_2,1), "moves": moves},
          open("output/opt2_road_09.json", "w"))
print("saved output/opt2_road_09.csv")
