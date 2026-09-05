# -*- coding: utf-8 -*-
"""全办 R2' 真终账: 每线 = 4 seed R2'-ALNS 列生成 (含终解) + SP(r2_prime) 重组.
输出 output/sp_r2_ledger_all.json (增量落盘). 用法: python run_r2_ledger.py <lines...>"""
import sys, os, time, json, datetime as dt
sys.path.insert(0, ".")
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, total_km, check_capacity
from algos.r2_alns import R2ALNS
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, check_r2prime, _wd

LINES = sys.argv[1:] or ['02','03','04','05','06','07','08','09','10','11']
OUT_F = 'output/sp_r2_ledger_all.json'
pv = load_plan()
out = json.load(open(OUT_F)) if os.path.exists(OUT_F) else {}
BASE = json.load(open('output/cpsat_plan_baselines.json'))

for lid in LINES:
    if lid in out and out[lid].get('sp_km') is not None:
        print(f"线{lid}: 已完成, 跳过", flush=True); continue
    t0 = time.time()
    d = load_line(pv, lid); D = np.load(f'output/road_dist_{lid}.npy')
    dates = list(d.dates); mn, mx = d.min_daily_capacity, d.max_daily_capacity
    orig_wd = {}
    for dd, seq in d.days_orig.items():
        for c in seq: orig_wd[c] = _wd(dd)
    pool, best = [], None
    for seed in (42, 7, 123, 2026):
        r = R2ALNS().solve(d, D, time_budget=150, seed=seed)
        pool += r.metadata['_columns']
        if best is None or r.km < best.km: best = r
    # 原计划列 (天然 R2' 合法) 也入池
    pool += [(dd, list(seq), round(day_km(seq, D), 3)) for dd, seq in d.days_orig.items()]
    legal = dedupe_pool(pool, top_k=8, max_daily=mx, min_daily=mn)
    try:
        rs = SPMatheuristic().solve(d, D, time_budget=300, pool=legal, rounds=1, sa_burst=10.0, r2_prime=True)
    except Exception as e:
        rs = None
    baseA = BASE[lid]
    if rs is not None and rs.days:
        lens = [len(v) for v in rs.days.values()]
        moved = sum(1 for c in orig_wd if len({_wd(dd) for dd, seq in rs.days.items() if c in seq}) != 1 or next(iter({_wd(dd) for dd, seq in rs.days.items() if c in seq})) != orig_wd[c])
        viol = check_r2prime(rs.days)
        rec = {'baseA': baseA, 'r2alns_km': round(best.km, 1), 'sp_km': round(rs.km, 1),
               'delta_vs_baseA_pct': round((rs.km - baseA)/baseA*100, 2),
               'cap_ok': bool(rs.capacity_ok), 'r2_viol': len(viol),
               'weekday_moved_stores': moved, 'day_range': [min(lens), max(lens)],
               'rmp_lp': rs.metadata.get('rmp_lp'), 'pool_gap_pct': rs.metadata.get('pool_gap_pct'),
               'pool_cols': len(legal), 'sec': round(time.time()-t0)}
    else:
        rec = {'baseA': baseA, 'sp_km': None, 'r2alns_km': round(best.km, 1),
               'pool_gap_pct': None, 'pool_cols': len(legal), 'sec': round(time.time()-t0)}
    out[lid] = rec
    json.dump(out, open(OUT_F, 'w'), ensure_ascii=False, indent=1)
    print(f"线{lid}: 基线A={baseA} | R2ALNS={rec.get('r2alns_km')} | SP={rec.get('sp_km')} ({rec.get('delta_vs_baseA_pct')}%) | 换店={rec.get('weekday_moved_stores')} 违R2'={rec.get('r2_viol')} | gap={rec.get('pool_gap_pct')}% | {rec['sec']}s", flush=True)
