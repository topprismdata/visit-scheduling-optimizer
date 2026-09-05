# -*- coding: utf-8 -*-
"""SP matheuristic 对照实验 (论文 [META]/[ESF] 驱动, 基准 = alns_v3).

Phase pool  : 多算法/多种子生成路线池 (增量落盘, 可断点)
Phase sp    : SP 精确重组 + 迭代精化 -> 对照 v3 基线出报告
--one name:seed:budget:tag : 单跑模式, 各自落盘 output/sp_pool_09_one_<tag>.json (并行无锁)
"""
import sys, os, time, json, csv, datetime, glob
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km
import algos.impl, algos.alns_v3, algos.hgs_pvrp, algos.sp_matheuristic  # noqa: 注册
from algos.registry import get as get_algorithm

args = sys.argv[1:]
PHASE = args[args.index('--phase') + 1] if '--phase' in args else 'all'
ONE = args[args.index('--one') + 1].split(':') if '--one' in args else None  # name:seed:budget:tag
POOL_F = 'output/sp_pool_09.json'
BENCH = 'output/bench_20260905.csv'

pv = load_plan()
data = load_line(pv, '09')
D = np.load('output/road_dist_09.npy')
dates = list(data.dates)

# v3 基线 (2026-09-05 三种子 300s 实测, output/bench_20260905.csv)
V3_BASE = {42: 266.8, 7: 263.6, 2026: 263.3}

def log(msg):
    print(msg, flush=True)

def save_pool(pool):
    json.dump([[str(dd), r, km] for dd, r, km in pool], open(POOL_F, 'w'))

def load_pool():
    if not os.path.exists(POOL_F):
        return []
    dmap = {str(d): d for d in dates}
    return [(dmap[p[0]], p[1], p[2]) for p in json.load(open(POOL_F))]

def add_run(pool, name, days):
    km = 0.0
    for dd in dates:
        r = list(days[dd])
        km += day_km(r, D)
        pool.append((dd, r, round(day_km(r, D), 3)))
    log(f"  [{name}] 总里程 {km:.1f} km, 路线 {len(dates)} 条入池 (池={len(pool)})")
    return km

if ONE:
    # 单跑模式: 并行无锁, 各自落盘
    name, seed, budget, tag = ONE[0], int(ONE[1]), int(ONE[2]), ONE[3]
    cls = get_algorithm(name)
    t1 = time.time()
    r = cls().solve(data, D, time_budget=budget, seed=seed)
    json.dump([[str(dd), list(r.days[dd]), round(day_km(r.days[dd], D), 3)] for dd in dates],
              open(f'output/sp_pool_09_one_{tag}.json', 'w'))
    log(f"[one/{tag}] {name} seed={seed} budget={budget}s -> "
        f"{sum(day_km(r.days[dd], D) for dd in dates):.1f} km, 耗时 {time.time()-t1:.0f}s")
    sys.exit(0)

if PHASE in ('pool', 'all'):
    pool = load_pool()
    t0 = time.time()
    RUNS = ([('alns_v3', dict(time_budget=150, seed=s), f'alns_v3/s{s}/150s') for s in (1, 2, 3, 4, 5, 6, 7, 8)]
          + [('hgs_pvrp', dict(time_budget=150, seed=s), f'hgs_pvrp/s{s}/150s') for s in (11, 12)]
          + [('greedy_crossday', dict(time_budget=300), 'greedy/s42/300s')]
          + [('nn2opt', dict(time_budget=60), 'nn2opt/s42')]
          + [('cpsat_route', dict(time_budget=60), 'cpsat/s42')])
    for name, kw, tag in RUNS:
        done_marker = POOL_F + f'.{tag.replace("/", "_")}.done'
        if os.path.exists(done_marker):
            log(f"  [skip] {tag} 已完成")
            continue
        cls = get_algorithm(name)
        t1 = time.time()
        r = cls().solve(data, D, **kw)
        km = add_run(pool, tag, r.days)
        save_pool(pool)
        open(done_marker, 'w').write(f"{km}")
        log(f"  耗时 {time.time()-t1:.0f}s | 累计 {time.time()-t0:.0f}s")
    log(f"=== 池生成完成: {len(pool)} 列, {time.time()-t0:.0f}s ===")

if PHASE in ('sp', 'all'):
    pool = load_pool()
    dmap = {str(d): d for d in dates}
    for f in glob.glob('output/sp_pool_09_one_*.json'):
        pool += [(dmap[p[0]], p[1], p[2]) for p in json.load(open(f))]
    from algos.sp_matheuristic import SPMatheuristic, dedupe_pool
    pool = dedupe_pool(pool, top_k=8)
    log(f"池去重后 {len(pool)} 列 (含深度波浪)")
    t0 = time.time()
    r = SPMatheuristic().solve(data, D, time_budget=1800, pool=pool, rounds=4, sa_burst=20.0)
    row = [datetime.datetime.now().isoformat(timespec='seconds'), 'sp_matheuristic', '09', 42, 1800,
           round(r.km, 1), round(time.time() - t0, 1), True,
           json.dumps({'lb': r.metadata.get('lb'), 'gap': r.metadata.get('gap_pct'),
                       'hist': r.metadata.get('history')})[:200]]
    with open(BENCH, 'a', newline='') as f:
        csv.writer(f).writerow(row)

    v3_best = min(V3_BASE.values()); v3_mean = sum(V3_BASE.values()) / len(V3_BASE)
    log("\n=== SP Matheuristic vs v3 基线 (09 线) ===")
    log(f"v3 三种子@300s : {sorted(V3_BASE.values())} | 最优 {v3_best} | 均值 {v3_mean:.1f}")
    log(f"SP (论文驱动)  : {r.km:.1f} | LP 下界 {r.metadata.get('lb')} | 池内 gap {r.metadata.get('gap_pct')}%")
    log(f"vs v3 最优     : {(r.km - v3_best) / v3_best * 100:+.2f}%")
    log(f"vs v3 均值     : {(r.km - v3_mean) / v3_mean * 100:+.2f}%")
