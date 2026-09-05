# -*- coding: utf-8 -*-
"""全办 R2' 终账: 每线 = weekday_lock 列生成 (4x120s) + 基线池列 + SP(R2') 终解.
输出 output/sp_r2prime_all.json: 每线 基线A vs R2'-SP + 合规校验 + 池内差距."""
import sys, os, time, json, glob, datetime as dt
sys.path.insert(0, ".")
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, check_capacity
from algos.alns_v3 import ALNSv3
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, check_r2prime

pv = load_plan()
LINES = ['02','03','04','05','06','07','08','09','10','11']
out = {}
for lid in LINES:
    t0 = time.time()
    d = load_line(pv, lid); D = np.load(f'output/road_dist_{lid}.npy')
    dates = list(d.dates); mn, mx = d.min_daily_capacity, d.max_daily_capacity
    baseA = round(sum(day_km(_r, D) for _r in [d.days_orig[k] for k in dates]), 1)  # 近似: 原序
    # 基线A = 原分配 + CP-SAT 排序: 从 cpsat_plan_baselines.json 读
    baseA = json.load(open('output/cpsat_plan_baselines.json'))[lid]
    # 1) 锁定列生成
    pool = []
    for seed in (42, 7, 123, 2026):
        r = ALNSv3().solve(d, D, time_budget=120, seed=seed, weekday_lock=True)
        for dd in dates:
            pool.append((dd, list(r.days[dd]), round(day_km(r.days[dd], D), 3)))
    # 2) 基线池里的 R2'-合法列 (原计划列/cpsat列天然合法)
    f0 = f'output/sp_pool_{lid}.json'
    if os.path.exists(f0):
        for p in json.load(open(f0)):
            pool.append((dt.date.fromisoformat(p[0]), p[1], p[2]))
    legal = dedupe_pool(pool, top_k=8, max_daily=mx, min_daily=mn)
    # 3) R2' SP 终解
    r = SPMatheuristic().solve(d, D, time_budget=300, pool=legal, rounds=2, sa_burst=10.0, r2_prime=True)
    lens = [len(v) for v in r.days.values()] if r.days else []
    viol = check_r2prime(r.days) if r.days else list(range(10**9))
    out[lid] = {'baseA': baseA, 'r2_km': round(r.km, 1) if r.days else None,
                'delta_vs_baseA_pct': round((r.km - baseA)/baseA*100, 2) if r.days else None,
                'cap_ok': bool(r.capacity_ok), 'r2_ok': len(viol) == 0, 'r2_viol_stores': len(viol),
                'day_range': [min(lens), max(lens)] if lens else None,
                'rmp_lp': r.metadata.get('rmp_lp'), 'pool_gap_pct': r.metadata.get('pool_gap_pct'),
                'pool_cols': len(legal), 'sec': round(time.time()-t0)}
    print(f"线{lid}: 基线A={baseA} | R2'-SP={out[lid]['r2_km']} ({out[lid]['delta_vs_baseA_pct']}%) | 分裂店={out[lid]['r2_viol_stores']} | gap={out[lid]['pool_gap_pct']}%", flush=True)
    json.dump(out, open('output/sp_r2prime_all.json','w'), ensure_ascii=False, indent=1)
print("ALL DONE")
