# -*- coding: utf-8 -*-
"""业务人员实际走访 vs 计划对比 (按天, 路网距离).
分析1: 每天实际走访店(含计划外) → 实际顺序距离 vs 优化顺序距离
分析2: 每天计划内店 → 实际顺序距离 vs 计划顺序距离 vs 优化顺序距离
矩阵按天抓取并缓存到 output/daily_matrices/."""
import pandas as pd, json, numpy as np, time, urllib.request, os, sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
from algos.tsp_engine import _nn2opt_open

URL = 'https://routing.openstreetmap.de/routed-bike/table/v1/driving/'
CACHE_DIR = 'output/daily_matrices'
os.makedirs(CACHE_DIR, exist_ok=True)
REP = '梁健满'
LINE = '海珠荔湾09'

def fetch_matrix(codes, lons, lats):
    """抓取当天店集合的路网矩阵 (km). 分批处理 >50."""
    n = len(codes)
    D = np.full((n, n), np.nan)
    BATCH = 40
    for s0 in range(0, n, BATCH):
        s1 = min(s0+BATCH, n)
        src_idx = list(range(s0, s1))
        for d0 in range(0, n, BATCH):
            d1 = min(d0+BATCH, n)
            dst_idx = list(range(d0, d1))
            all_idx = src_idx + dst_idx
            sub_coord = ';'.join(f'{lons[i]:.6f},{lats[i]:.6f}' for i in all_idx)
            sub_src = ';'.join(str(i) for i in range(len(src_idx)))
            sub_dst = ';'.join(str(len(src_idx)+i) for i in range(len(dst_idx)))
            url = f'{URL}{sub_coord}?sources={sub_src}&destinations={sub_dst}&annotations=distance'
            for attempt in range(3):
                try:
                    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'gz-eval/1.0'}), timeout=120).read())
                    if r.get('code') == 'Ok':
                        for li, row in enumerate(r['distances']):
                            for jj, v in enumerate(row):
                                if v is not None: D[s0+li][d0+jj] = v/1000.0
                        break
                except Exception:
                    time.sleep(3)
        time.sleep(0.3)
    D = np.nan_to_num(D, nan=5.0)
    return D

# 加载数据
rpt = pd.read_excel('/Users/ghb/Downloads/进离店报表导出 (4).xlsx')
rpt['客户编码'] = rpt['客户编码'].astype(str)
rpt['进店时间'] = pd.to_datetime(rpt['进店时间'])
rpt['date'] = rpt['进店时间'].dt.date
lj = rpt[rpt['人员名称']==REP].dropna(subset=['进店经度','进店纬度']).copy()

plan = pd.read_excel('/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx')
plan = plan[plan['计划是否有效标识']=='有效'].copy()
plan['客户编码'] = plan['客户编码'].astype(str)
p09 = plan[plan['销售名称']==LINE]
p_stores = set(p09['客户编码'].unique())
p_weekday = {c: int(pd.to_datetime(p09[p09['客户编码']==c]['拜访日期']).dt.weekday.mode().iloc[0]) for c in p_stores}

results = []
for dd in sorted(lj['date'].unique()):
    day = lj[lj['date']==dd].sort_values('进店时间')
    actual_codes = day['客户编码'].tolist()
    # 去重保序
    seen = set(); actual_uniq = []
    for c in actual_codes:
        if c not in seen: seen.add(c); actual_uniq.append(c)
    plan_codes = [c for c in actual_uniq if c in p_stores]
    if len(actual_uniq) < 2 or len(plan_codes) < 2:
        continue
    pts = day.drop_duplicates('客户编码', keep='first').set_index('客户编码')
    lons = pts['进店经度'].astype(float).to_dict()
    lats = pts['进店纬度'].astype(float).to_dict()
    day_codes = list(seen)  # 当天所有店
    m = len(day_codes)
    cache_key = f"{dd}.npy"
    cache_path = os.path.join(CACHE_DIR, cache_key)
    if os.path.exists(cache_path):
        D = np.load(cache_path)
    else:
        print(f"  {dd}: 抓取 {m} 店矩阵...", flush=True)
        D = fetch_matrix(day_codes, [lons[c] for c in day_codes], [lats[c] for c in day_codes])
        np.save(cache_path, D)
        print(f"  {dd}: ✓", flush=True)
    # 计算
    idx = {c:i for i,c in enumerate(day_codes)}
    actual_seq = [idx[c] for c in actual_uniq]
    km_actual = sum(D[actual_seq[k]][actual_seq[k+1]] for k in range(len(actual_seq)-1))
    opt_seq = _nn2opt_open(actual_seq, D)
    km_opt = sum(D[opt_seq[k]][opt_seq[k+1]] for k in range(len(opt_seq)-1))
    # 计划内对比
    plan_seq = [idx[c] for c in plan_codes]
    km_plan_actual = sum(D[plan_seq[k]][plan_seq[k+1]] for k in range(len(plan_seq)-1))
    plan_opt = _nn2opt_open(plan_seq, D)
    km_plan_opt = sum(D[plan_opt[k]][plan_opt[k+1]] for k in range(len(plan_opt)-1))
    results.append(dict(date=str(dd), wd=pd.Timestamp(dd).weekday(),
                        n_all=len(actual_uniq), n_plan=len(plan_codes),
                        km_actual=round(km_actual,1), km_opt=round(km_opt,1),
                        km_plan_actual=round(km_plan_actual,1), km_plan_opt=round(km_plan_opt,1)))
    print(f"  {dd}: 全部 {len(actual_uniq)}店 实际{km_actual:.1f}→优化{km_opt:.1f} (-{(km_actual-km_opt)/km_actual:.0%}) | 计划内 {len(plan_codes)}店 实际{km_plan_actual:.1f}→优化{km_plan_opt:.1f}", flush=True)

t = pd.DataFrame(results)
print("\n=== 汇总 ===")
print(f"天数: {len(t)}")
print(f"分析1 (全部店): 实际 {t.km_actual.sum():.0f} km → 优化 {t.km_opt.sum():.0f} km (省 {t.km_actual.sum()-t.km_opt.sum():.0f} km, {(t.km_actual.sum()-t.km_opt.sum())/t.km_actual.sum():.0%})")
print(f"分析2 (计划内): 实际 {t.km_plan_actual.sum():.0f} km → 优化 {t.km_plan_opt.sum():.0f} km (省 {t.km_plan_actual.sum()-t.km_plan_opt.sum():.0f} km, {(t.km_plan_actual.sum()-t.km_plan_opt.sum())/t.km_plan_actual.sum():.0%})")
t.to_csv('output/actual_vs_plan_daily.csv', index=False)
json.dump(results, open('output/actual_vs_plan_daily.json','w'), ensure_ascii=False, indent=1)
print("saved output/actual_vs_plan_daily.csv")
