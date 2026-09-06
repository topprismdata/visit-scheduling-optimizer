# -*- coding: utf-8 -*-
"""09 线两格补测 (在远端 M1 Max 运行): 并池 + 静态SP/CG 同池消融对, 3 reps 区间口径.

每 rep 构建同一合并列池 (全部主线语义合法来源):
  R2'-ALNS ×2 seeds (整店搬家) + v3 锁日版 ×1 + 反馈HGS ×1 + 基线A列
两腿消费完全相同的池:
  静态腿: sp_solve_ip(r2_prime=True) 一次解 (无对偶反馈)
  主线腿: SPMatheuristic(r2_prime=True) 对偶闭环 CG + SA 精化
差值 = CG(对偶反馈) 定价; 并池 vs 历史单源主线 (310.4/315.0) = 并池定价.
"""
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
V3_SEED = 77
HGS_SEED = 88
OUT_F = 'output/exp09_tracks.json'
PRIOR_MAINLINE = [310.4, 315.0, 315.7]   # 单源 r2_alns 历史值 (不同波次)

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


out = json.load(open(OUT_F)) if os.path.exists(OUT_F) else {'reps': []}

for rep, (s1, s2) in enumerate(REP_GROUPS):
    if any(r['rep'] == rep for r in out['reps']):
        print(f"rep{rep} 已存在, 跳过", flush=True)
        continue
    t0 = time.time()
    pool = list(base_cols)
    for s in (s1, s2):
        r = R2ALNS().solve(d, D, time_budget=150, seed=s)
        pool += r.metadata['_columns']
        print(f"  rep{rep} r2_alns s{s}: {r.km:.1f}", flush=True)
    r = ALNSv3().solve(d, D, time_budget=150, seed=V3_SEED, weekday_lock=True)
    pool += days_to_cols(r.days)
    r = HGSPVRP().solve(d, D, time_budget=150, seed=HGS_SEED)
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

    stat = {'rep': rep, 'pool_cols': len(legal), 'baseA': baseA,
            'static': None, 'cg': None}
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
                      'cg_minus_static': (None if km_s is None
                                          else round(rc.km - km_s, 2)),
                      'sec': round(t3 - t2, 1)}
    out['reps'].append(stat)
    json.dump(out, open(OUT_F, 'w'), ensure_ascii=False, indent=1)
    print(f"  rep{rep} 静态SP={stat['static'] and stat['static']['km']} "
          f"| 主线CG={stat['cg'] and stat['cg']['km']} "
          f"| 差值={stat['cg'] and stat['cg']['cg_minus_static']} "
          f"| viol={stat['cg'] and stat['cg']['viol']} | {round(t3-t0)}s", flush=True)


def band(vals):
    v = sorted(x for x in vals if x is not None)
    return None if not v else {'median': v[len(v)//2], 'min': v[0], 'max': v[-1]}


sumry = {'baseA': baseA, 'prior_mainline_band': band(PRIOR_MAINLINE),
         'merged_static_band': band([r['static']['km'] for r in out['reps'] if r['static']]),
         'merged_cg_band': band([r['cg']['km'] for r in out['reps'] if r['cg']])}
if sumry['merged_cg_band'] and sumry['merged_static_band']:
    sumry['cg_pricing'] = round(sumry['merged_static_band']['median']
                                - sumry['merged_cg_band']['median'], 2)
if sumry['merged_cg_band'] and sumry['prior_mainline_band']:
    sumry['pool_merge_pricing'] = round(sumry['prior_mainline_band']['median']
                                        - sumry['merged_cg_band']['median'], 2)
out['summary'] = sumry
json.dump(out, open(OUT_F, 'w'), ensure_ascii=False, indent=1)
print("\n=== 09 线两格补测汇总 ===")
print(f"基线A={baseA}")
for k in ('prior_mainline_band', 'merged_static_band', 'merged_cg_band'):
    print(f"  {k}: {sumry[k]}")
print(f"  CG定价(静态−CG)={sumry.get('cg_pricing')} km | 并池定价(旧中位−新中位)={sumry.get('pool_merge_pricing')} km")
print("ALL DONE")
