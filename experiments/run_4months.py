# -*- coding: utf-8 -*-
"""4 个月统一优化: 10线 × 88工作日 × (baseline/nn2opt/greedy_crossday). 逐线容错."""
import pandas as pd, json, time, os, sys, traceback, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from core.base import LineData
from core.metric import day_km, total_km, check_freq
from algos.tsp_engine import _nn2opt_open
from data.road import load_cached

def load_all():
    m7 = pd.read_excel('/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx')
    m7 = m7[m7['计划是否有效标识']=='有效'].copy()
    m8 = pd.read_excel('/Users/ghb/Downloads/进离店内销售的SRP-8月拜访计划.xlsx')
    m8 = m8[m8['计划是否有效标识']=='有效'].copy()
    m9 = pd.read_excel('/Users/ghb/Downloads/进离店内销售的SRP-9&10月拜访计划.xlsx', sheet_name='Sheet1')
    for df in [m7, m8, m9]:
        df['客户编码'] = df['客户编码'].astype(str)
        df['拜访日期'] = pd.to_datetime(df['拜访日期'])
    return pd.concat([m7, m8, m9], ignore_index=True)

def greedy_crossday(days_orig, dates, D, tl=240):
    """带时间上限的贪心跨日; 每对日期只做一轮, 超时即停."""
    days = {dd: list(seq) for dd, seq in days_orig.items()}
    start = time.time(); moves = 0
    for _ in range(30):
        improved = False
        for i, dd1 in enumerate(dates):
            for dd2 in dates[i+1:]:
                if time.time() - start > tl:
                    return days, moves, time.time()-start
                s1, s2 = days[dd1], days[dd2]
                if len(s1) <= 5: continue
                for c in list(s1):
                    if c in s2: continue
                    ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
                    if len(ns1) < 2: continue
                    r1n = _nn2opt_open(ns1, D); r2n = _nn2opt_open(ns2, D)
                    r1o = _nn2opt_open(s1, D); r2o = _nn2opt_open(s2, D)
                    old = day_km(r1o, D) + day_km(r2o, D)
                    new = day_km(r1n, D) + day_km(r2n, D)
                    if new < old - 0.05:
                        days[dd1] = ns1; days[dd2] = ns2; moves += 1; improved = True
            if time.time() - start > tl:
                return days, moves, time.time()-start
        if not improved:
            break
    return days, moves, time.time()-start

allp = load_all()
allp['date'] = allp['拜访日期'].dt.date
LINES = ["02","03","04","05","06","07","08","09","10","11"]
results = []
for lid in LINES:
    try:
        g = allp[allp['销售名称'].str.contains(f"海珠荔湾{lid}")]
        if g.empty:
            print(f"线 {lid}: 空", flush=True); continue
        pts = g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码", keep="first").set_index("客户编码")
        codes = pts.index.tolist(); idx = {c:i for i,c in enumerate(codes)}
        lons = pts["经度"].astype(float).tolist(); lats = pts["纬度"].astype(float).tolist()
        dates = sorted(g["date"].unique())
        D = load_cached(lid)
        if D is None:
            print(f"线 {lid}: 无矩阵缓存", flush=True); continue
        D = D.tolist()
        days_orig = {dd: [idx[c] for c in g[g["date"]==dd].sort_values("拜访顺序")["客户编码"] if c in idx] for dd in dates}
        freq = g.groupby("客户编码").size().to_dict()
        km_b = total_km(days_orig, D)
        days_n = {dd: _nn2opt_open(seq, D) for dd, seq in days_orig.items()}
        km_n = total_km(days_n, D)
        days_g, moves, gtime = greedy_crossday(days_n, dates, D, tl=240)
        final_g = {dd: _nn2opt_open(seq, D) for dd, seq in days_g.items()}
        km_g = total_km(final_g, D)
        ok_g = check_freq(final_g, codes, freq)
        results.append(dict(line=lid, stores=len(codes), visits=len(g), days=len(dates),
                            plan=round(km_b,1), nn2opt=round(km_n,1), greedy=round(km_g,1),
                            sav_n=round((km_b-km_n)/km_b*100,1), sav_g=round((km_b-km_g)/km_b*100,1),
                            moves=moves, freq_ok=bool(ok_g), sec=round(gtime)))
        print(f"线 {lid}: 计划 {km_b:.1f} | nn2opt {km_n:.1f} (-{(km_b-km_n)/km_b:.0%}) | greedy {km_g:.1f} (-{(km_b-km_g)/km_b:.0%}) [{moves}次,{gtime:.0f}s]", flush=True)
    except Exception as e:
        print(f"线 {lid}: FAILED {e}", flush=True)
        traceback.print_exc()

t = pd.DataFrame(results)
print("\n=== 4个月总账 (路网距离) ===")
print(t[["line","stores","visits","days","plan","nn2opt","greedy","sav_n","sav_g","freq_ok"]].to_string(index=False))
print(f"\n合计: 计划 {t.plan.sum():.0f} | nn2opt {t.nn2opt.sum():.0f} (-{(t.plan.sum()-t.nn2opt.sum())/t.plan.sum():.0%}) | greedy {t.greedy.sum():.0f} (-{(t.plan.sum()-t.greedy.sum())/t.plan.sum():.0%})")
t.to_csv("output/4months_ledger.csv", index=False)
json.dump(results, open("output/4months_ledger.json","w"), ensure_ascii=False, indent=1)
print("saved output/4months_ledger.csv")
