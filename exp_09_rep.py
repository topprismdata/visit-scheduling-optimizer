# -*- coding: utf-8 -*-
"""09 线两格补测·单 rep 并行版: python exp_09_rep.py <rep_index>  (0/1/2)
输出 output/exp09_tracks_rep<N>.json; 汇总: python exp_09_rep.py --merge"""
import sys, os, time, json
from collections import Counter
sys.path.insert(0, ".")
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, check_capacity
from algos.r2_alns import R2ALNS
from algos.alns_v3 import ALNSv3
from algos.hgs_pvrp import HGSPVRP
from algos.tsp_engine import _exact_open_tsp
from algos.sp_matheuristic import (SPMatheuristic, dedupe_pool, check_r2prime,
                                   sp_solve_ip, sp_solve_lp)

REP_GROUPS = [(11, 22), (33, 44), (55, 66)]
PRIOR_MAINLINE = [310.4, 315.0, 315.7]


def run(rep):
    out_f = f'output/exp09_tracks_rep{rep}.json'
    if os.path.exists(out_f):
        print(f"rep{rep} 已存在, 跳过", flush=True)
        return
    s1, s2 = REP_GROUPS[rep]
    pv = load_plan()
    d = load_line(pv, '09'); D = np.load('output/road_dist_09.npy')
    dates = list(d.dates); mn, mx = d.min_daily_capacity, d.max_daily_capacity
    k_c = dict(Counter(c for dd in dates for c in d.days_orig[dd]))
    baseA = json.load(open('output/cpsat_plan_baselines.json'))['09']
    base_cols = []
    for dd, seq in d.days_orig.items():
        r_opt = _exact_open_tsp(list(seq), D, 30)
        base_cols.append((dd, list(r_opt), round(day_km(r_opt, D), 3)))

    def days_to_cols(days):
        return [(dd, list(s), round(day_km(s, D), 3)) for dd, s in days.items()]

    t0 = time.time()
    pool = list(base_cols)
    for s in (s1, s2):
        r = R2ALNS().solve(d, D, time_budget=150, seed=s)
        pool += r.metadata['_columns']
        print(f"  rep{rep} r2_alns s{s}: {r.km:.1f} @ {round(time.time()-t0)}s", flush=True)
    r = ALNSv3().solve(d, D, time_budget=150, seed=77 + rep, weekday_lock=True)
    pool += days_to_cols(r.days)
    r = HGSPVRP().solve(d, D, time_budget=150, seed=88 + rep)
    pool += days_to_cols(r.days)
    legal = dedupe_pool(pool, top_k=8, max_daily=mx, min_daily=mn)
    print(f"  rep{rep} 合并池 {len(legal)} 列", flush=True)

    t1 = time.time()
    km_s, days_s = sp_solve_ip(dates, k_c, legal, timeout_s=180, r2_prime=True)
    lp_s, _ = sp_solve_lp(dates, k_c, legal, r2_prime=True)
    t2 = time.time()
    rc = SPMatheuristic().solve(d, D, time_budget=360, pool=legal, rounds=1,
                                sa_burst=10.0, r2_prime=True)
    t3 = time.time()
    stat = {'rep': rep, 'pool_cols': len(legal), 'baseA': baseA, 'static': None, 'cg': None}
    if km_s is not None and days_s is not None:
        stat['static'] = {'km': round(km_s, 2),
                          'rmp_lp': round(lp_s, 2) if lp_s is not None else None,
                          'viol': len(check_r2prime(days_s)),
                          'cap_ok': bool(check_capacity(days_s, mx, mn)),
                          'sec': round(t2 - t1, 1)}
    if rc.days:
        stat['cg'] = {'km': round(rc.km, 2),
                      'rmp_lp': round(rc.metadata.get('rmp_lp') or 0, 2),
                      'pool_gap_pct': rc.metadata.get('pool_gap_pct'),
                      'viol': len(check_r2prime(rc.days)),
                      'cap_ok': bool(rc.capacity_ok),
                      'cg_minus_static': (None if km_s is None else round(rc.km - km_s, 2)),
                      'sec': round(t3 - t2, 1)}
    json.dump(stat, open(out_f, 'w'), ensure_ascii=False, indent=1)
    print(f"  rep{rep} 静态SP={stat['static'] and stat['static']['km']} "
          f"| 主线CG={stat['cg'] and stat['cg']['km']} "
          f"| 差值={stat['cg'] and stat['cg']['cg_minus_static']} | 总 {round(t3-t0)}s", flush=True)


def merge():
    reps = []
    for i in range(3):
        f = f'output/exp09_tracks_rep{i}.json'
        if os.path.exists(f):
            reps.append(json.load(open(f)))
    def band(vals):
        v = sorted(x for x in vals if x is not None)
        return None if not v else {'median': v[len(v)//2], 'min': v[0], 'max': v[-1], 'n': len(v)}
    baseA = reps[0]['baseA'] if reps else None
    pm = band(PRIOR_MAINLINE)
    sb = band([r['static']['km'] for r in reps if r.get('static')])
    cb = band([r['cg']['km'] for r in reps if r.get('cg')])
    out = {'baseA': baseA, 'reps': reps, 'prior_mainline_band': pm,
           'merged_static_band': sb, 'merged_cg_band': cb}
    if sb and cb:
        out['cg_pricing'] = round(sb['median'] - cb['median'], 2)
    if cb and pm:
        out['pool_merge_pricing'] = round(pm['median'] - cb['median'], 2)
    out['vs_baseA_delta_band'] = (None if not cb else
                                  [round((cb['max']-baseA)/baseA*100, 2),
                                   round((cb['min']-baseA)/baseA*100, 2)])
    json.dump(out, open('output/exp09_tracks_merged.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ('baseA', 'prior_mainline_band', 'merged_static_band',
                                          'merged_cg_band', 'cg_pricing', 'pool_merge_pricing',
                                          'vs_baseA_delta_band')}, ensure_ascii=False, indent=1))


if '--merge' in sys.argv:
    merge()
else:
    run(int(sys.argv[1]))
