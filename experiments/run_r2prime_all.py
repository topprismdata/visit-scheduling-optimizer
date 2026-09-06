# -*- coding: utf-8 -*-
"""全办 R2' 终账: 每线 = weekday_lock 列生成 + 基线池列(含天然合法的原序/cpsat列) + SP(R2') 终解.
用法: python run_r2prime_all.py 02 03 04   (增量落盘 output/sp_r2prime_all.json, 可断点)"""
import sys, os, time, json, datetime as dt
sys.path.insert(0, ".")
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km
from algos.alns_v3 import ALNSv3
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, check_r2prime

LINES = sys.argv[1:] or ['02','03','04','05','06','07','08','09','10','11']
OUT_F = 'output/sp_r2prime_all.json'
BASE_F = 'output/cpsat_plan_baselines.json'
pv = load_plan()
out = json.load(open(OUT_F)) if os.path.exists(OUT_F) else {}
baseA_all = json.load(open(BASE_F)) if os.path.exists(BASE_F) else None

for lid in LINES:
    if lid in out and out[lid].get('r2_km') is not None:
        print(f"线{lid}: 已完成, 跳过", flush=True); continue
    t0 = time.time()
    d = load_line(pv, lid); D = np.load(f'output/road_dist_{lid}.npy')
    dates = list(d.dates); mn, mx = d.min_daily_capacity, d.max_daily_capacity
    baseA = baseA_all[lid] if baseA_all else None
    pool = []
    for seed in (42, 7):
        r = ALNSv3().solve(d, D, time_budget=150, seed=seed, weekday_lock=True)
        for dd in dates:
            pool.append((dd, list(r.days[dd]), round(day_km(r.days[dd], D), 3)))
    f0 = f'output/sp_pool_{lid}.json'
    if os.path.exists(f0):
        for p in json.load(open(f0)):
            pool.append((dt.date.fromisoformat(p[0]), p[1], p[2]))
    legal = dedupe_pool(pool, top_k=8, max_daily=mx, min_daily=mn)
    try:
        r = SPMatheuristic().solve(d, D, time_budget=240, pool=legal, rounds=1, sa_burst=10.0, r2_prime=True)
    except Exception as e:
        print(f"线{lid}: SP 异常 {e}", flush=True); r = None
    if r is not None and r.days:
        lens = [len(v) for v in r.days.values()]
        viol = check_r2prime(r.days)
        rec = {'baseA': baseA, 'r2_km': round(r.km, 1),
               'delta_vs_baseA_pct': round((r.km - baseA)/baseA*100, 2) if baseA else None,
               'cap_ok': bool(r.capacity_ok), 'r2_ok': len(viol) == 0, 'r2_viol_stores': len(viol),
               'day_range': [min(lens), max(lens)], 'rmp_lp': r.metadata.get('rmp_lp'),
               'pool_gap_pct': r.metadata.get('pool_gap_pct'), 'pool_cols': len(legal),
               'sec': round(time.time()-t0)}
    else:
        rec = {'baseA': baseA, 'r2_km': None, 'infeasible': True,
               'pool_cols': len(legal), 'sec': round(time.time()-t0)}
    out[lid] = rec
    json.dump(out, open(OUT_F, 'w'), ensure_ascii=False, indent=1)
    print(f"线{lid}: 基线A={baseA} | R2'-SP={rec.get('r2_km')} ({rec.get('delta_vs_baseA_pct')}%) | 分裂店={rec.get('r2_viol_stores')} | gap={rec.get('pool_gap_pct')}% | {rec['sec']}s", flush=True)
