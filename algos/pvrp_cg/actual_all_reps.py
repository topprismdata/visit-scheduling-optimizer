# -*- coding: utf-8 -*-
"""11 业务人员实际走访 vs 计划对比 (按天, 路网距离).
每人逐日: 实际走访店(含计划外) → 实际顺序距离 vs 优化顺序距离; 计划内店同.
逐人 try/except 容错 + 每日矩阵缓存 + 增量保存."""
import pandas as pd, json, numpy as np, time, urllib.request, os, sys, traceback, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
from algos.tsp_engine import _nn2opt_open

URL = 'https://routing.openstreetmap.de/routed-bike/table/v1/driving/'
CACHE_DIR = 'output/daily_matrices'
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_matrix(codes, lons, lats):
    n = len(codes)
    D = np.full((n, n), np.nan)
    BATCH = 30
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
            for attempt in range(5):
                try:
                    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'gz-eval/1.0'}), timeout=180).read())
                    if r.get('code') == 'Ok':
                        for li, row in enumerate(r['distances']):
                            for jj, v in enumerate(row):
                                if v is not None: D[s0+li][d0+jj] = v/1000.0
                        break
                except Exception:
                    time.sleep(5)
            time.sleep(0.3)
    D = np.nan_to_num(D, nan=5.0)
    return D

# 加载
rpt = pd.read_excel('/Users/ghb/Downloads/进离店报表导出 (4).xlsx')
rpt['客户编码'] = rpt['客户编码'].astype(str)
rpt['进店时间'] = pd.to_datetime(rpt['进店时间'])
rpt['date'] = rpt['进店时间'].dt.date

plan = pd.read_excel('/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx')
plan = plan[plan['计划是否有效标识']=='有效'].copy()
plan['客户编码'] = plan['客户编码'].astype(str)

REP_LINE = {
    '冯秀珍': '冯秀珍_海珠荔湾05', '黄志成': '海珠荔湾10', '梁健满': '海珠荔湾09',
    '邝豪杰': '海珠荔湾08', '苏泳江': '海珠荔湾11', '赵成毅': '梁齐志_海珠荔湾07',
    '欧祖良': '海珠荔湾03', '梁炯棠': '海珠荔湾06', '马嘉洲': '海珠荔湾04',
    '黄宏妮': '黄宏妮_海珠荔湾02', '梁齐志': '梁齐志_海珠荔湾07',
}

all_results = []
def save_incremental():
    if all_results:
        t = pd.DataFrame(all_results)
        t.to_csv('output/actual_all_reps_daily.csv', index=False)
        json.dump(all_results, open('output/actual_all_reps_daily.json','w'), ensure_ascii=False, indent=1)

for rep, line in REP_LINE.items():
    try:
        p_stores = set(plan[plan['销售名称']==line]['客户编码'].unique())
        lj = rpt[rpt['人员名称']==rep].dropna(subset=['进店经度','进店纬度']).copy()
        if lj.empty:
            print(f"== {rep}: 无数据 ==", flush=True); continue
        print(f"== {rep} → {line} ({len(p_stores)}计划店) ==", flush=True)
        rep_rows = []
        for dd in sorted(lj['date'].unique()):
            day = lj[lj['date']==dd].sort_values('进店时间')
            actual_codes = day['客户编码'].tolist()
            seen = set(); actual_uniq = []
            for c in actual_codes:
                if c not in seen: seen.add(c); actual_uniq.append(c)
            plan_codes = [c for c in actual_uniq if c in p_stores]
            if len(actual_uniq) < 2 or len(plan_codes) < 2:
                continue
            pts = day.drop_duplicates('客户编码', keep='first').set_index('客户编码')
            lons = pts['进店经度'].astype(float).to_dict()
            lats = pts['进店纬度'].astype(float).to_dict()
            day_codes = list(seen)
            cache_path = os.path.join(CACHE_DIR, f"{rep}_{dd}.npy")
            if os.path.exists(cache_path):
                D = np.load(cache_path)
            else:
                D = fetch_matrix(day_codes, [lons[c] for c in day_codes], [lats[c] for c in day_codes])
                np.save(cache_path, D)
            idx = {c:i for i,c in enumerate(day_codes)}
            actual_seq = [idx[c] for c in actual_uniq]
            km_actual = sum(D[actual_seq[k]][actual_seq[k+1]] for k in range(len(actual_seq)-1))
            opt_seq = _nn2opt_open(actual_seq, D)
            km_opt = sum(D[opt_seq[k]][opt_seq[k+1]] for k in range(len(opt_seq)-1))
            plan_seq = [idx[c] for c in plan_codes]
            km_plan_actual = sum(D[plan_seq[k]][plan_seq[k+1]] for k in range(len(plan_seq)-1))
            plan_opt = _nn2opt_open(plan_seq, D)
            km_plan_opt = sum(D[plan_opt[k]][plan_opt[k+1]] for k in range(len(plan_opt)-1))
            rep_rows.append(dict(rep=rep, line=line, date=str(dd), wd=pd.Timestamp(dd).weekday(),
                                 n_all=len(actual_uniq), n_plan=len(plan_codes),
                                 km_actual=round(km_actual,1), km_opt=round(km_opt,1),
                                 km_plan_actual=round(km_plan_actual,1), km_plan_opt=round(km_plan_opt,1)))
        t = pd.DataFrame(rep_rows)
        if len(t):
            a1 = t.km_actual.sum(); a2 = t.km_opt.sum()
            b1 = t.km_plan_actual.sum(); b2 = t.km_plan_opt.sum()
            print(f"  {rep}: {len(t)}天 全部店 {a1:.0f}→{a2:.0f}km (-{(a1-a2)/a1:.0%}) | 计划内 {b1:.0f}→{b2:.0f}km (-{(b1-b2)/b1:.0%})", flush=True)
            all_results.extend(t.to_dict('records'))
            save_incremental()
    except Exception as e:
        print(f"== {rep}: FAILED {e} ==", flush=True)
        traceback.print_exc()
        save_incremental()

save_incremental()
if all_results:
    allt = pd.DataFrame(all_results)
    print("\n=== 全员汇总 ===")
    g = allt.groupby('rep').agg(days=('date','nunique'),
        actual_all=('km_actual','sum'), opt_all=('km_opt','sum'),
        actual_plan=('km_plan_actual','sum'), opt_plan=('km_plan_opt','sum'))
    g['sav_all%'] = (1 - g.opt_all/g.actual_all)*100
    g['sav_plan%'] = (1 - g.opt_plan/g.actual_plan)*100
    print(g.round(1).to_string())
    print(f"\n全员合计: 实际 {allt.km_actual.sum():.0f} → 优化 {allt.km_opt.sum():.0f} km (-{(1-allt.km_opt.sum()/allt.km_actual.sum()):.0%})")
    print(f"计划内合计: 实际 {allt.km_plan_actual.sum():.0f} → 优化 {allt.km_plan_opt.sum():.0f} km (-{(1-allt.km_plan_opt.sum()/allt.km_plan_actual.sum()):.0%})")
print("done")
