# -*- coding: utf-8 -*-
"""SP matheuristic 对照实验 (论文 [META]/[ESF] 驱动, 基准 = alns_v3). 支持任意线路.

用法:
  python run_sp_experiment.py --line 09 --phase pool          # 池生成 (增量断点)
  python run_sp_experiment.py --line 09 --one alns_v3:51:900:deep1   # 单跑 (并行无锁)
  python run_sp_experiment.py --line 09 --phase sp            # SP+CG + 报告
"""
import sys, os, time, json, csv, datetime, glob, random
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, total_km
import algos.impl, algos.alns_v3, algos.hgs_pvrp, algos.sp_matheuristic  # noqa: 注册
from algos.registry import get as get_algorithm

args = sys.argv[1:]
LINE = args[args.index('--line') + 1] if '--line' in args else '09'
PHASE = args[args.index('--phase') + 1] if '--phase' in args else 'all'
ONE = args[args.index('--one') + 1].split(':') if '--one' in args else None  # name:seed:budget:tag
POOL_F = f'output/sp_pool_{LINE}.json'
RUNS_F = f'output/sp_runs_{LINE}.json'
BENCH = 'output/bench_20260905.csv'

pv = load_plan()
data = load_line(pv, LINE)
D = np.load(f'output/road_dist_{LINE}.npy')
dates = list(data.dates)

# v3 基线: 仅 09 有 300s 档三种子实测; 其他线用池内 v3 run 对比
V3_BASE = {42: 266.8, 7: 263.6, 2026: 263.3} if LINE == '09' else None

def log(msg):
    print(msg, flush=True)

def save_pool(pool):
    json.dump([[str(dd), r, km] for dd, r, km in pool], open(POOL_F, 'w'))

def load_pool():
    if not os.path.exists(POOL_F):
        return []
    dmap = {str(d): d for d in dates}
    return [(dmap[p[0]], p[1], p[2]) for p in json.load(open(POOL_F))]

def load_runs_manifest():
    if os.path.exists(RUNS_F):
        return json.load(open(RUNS_F))
    return {}

def save_runs_manifest(m):
    json.dump(m, open(RUNS_F, 'w'), ensure_ascii=False, indent=1)

def add_run(pool, name, days):
    km = 0.0
    for dd in dates:
        r = list(days[dd])
        km += day_km(r, D)
        pool.append((dd, r, round(day_km(r, D), 3)))
    log(f"  [{name}] 总里程 {km:.1f} km, 路线 {len(dates)} 条入池 (池={len(pool)})")
    return round(km, 1)

if ONE:
    # 单跑模式: 并行无锁, 各自落盘
    name, seed, budget, tag = ONE[0], int(ONE[1]), int(ONE[2]), ONE[3]
    cls = get_algorithm(name)
    t1 = time.time()
    r = cls().solve(data, D, time_budget=budget, seed=seed)
    km = round(sum(day_km(r.days[dd], D) for dd in dates), 1)
    json.dump([[str(dd), list(r.days[dd]), round(day_km(r.days[dd], D), 3)] for dd in dates],
              open(f'output/sp_pool_{LINE}_one_{tag}.json', 'w'))
    json.dump({'tag': tag, 'name': name, 'seed': seed, 'budget': budget, 'km': km},
              open(f'output/sp_one_km_{LINE}_{tag}.json', 'w'), ensure_ascii=False)
    sys.exit(0)

if PHASE in ('pool', 'all'):
    pool = load_pool()
    manifest = load_runs_manifest()
    t0 = time.time()
    RUNS = ([('alns_v3', dict(time_budget=150, seed=s), f'alns_v3/s{s}/150s') for s in (1, 2, 3, 4)]
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
        manifest[tag] = {'name': name, 'km': km, **kw}
        save_pool(pool)
        save_runs_manifest(manifest)
        open(done_marker, 'w').write(f"{km}")
        log(f"  耗时 {time.time()-t1:.0f}s | 累计 {time.time()-t0:.0f}s")
    log(f"=== 线{LINE} 池生成完成: {len(pool)} 列, {time.time()-t0:.0f}s ===")

if PHASE in ('sp', 'all'):
    pool = load_pool()
    manifest = load_runs_manifest()
    dmap = {str(d): d for d in dates}
    for f in glob.glob(f'output/sp_pool_{LINE}_one_*.json'):
        pool += [(dmap[p[0]], p[1], p[2]) for p in json.load(open(f))]
    for f in glob.glob(f'output/sp_one_km_{LINE}_*.json'):
        d = json.load(open(f))
        if not isinstance(d, dict):
            continue  # 旧版错位文件 (内容为路线), 已迁移至 sp_pool 文件
        manifest[d['tag']] = {'name': d['name'], 'km': d['km'],
                              'time_budget': d['budget'], 'seed': d['seed']}
    save_runs_manifest(manifest)
    from algos.sp_matheuristic import SPMatheuristic, dedupe_pool
    max_daily = getattr(data, 'max_daily_capacity', 0) or max(len(v) for v in data.days_orig.values())
    pool = dedupe_pool(pool, top_k=8, max_daily=max_daily)
    log(f"线{LINE} 池容量过滤后(<= {max_daily}店) {len(pool)} 列")
    t0 = time.time()
    r = SPMatheuristic().solve(data, D, time_budget=1800, pool=pool, rounds=3, sa_burst=15.0, max_daily=max_daily)
    lens = [len(r.days[dd]) for dd in dates]
    cap_ok = getattr(r, 'capacity_ok', True) and max(lens) <= max_daily
    row = [datetime.datetime.now().isoformat(timespec='seconds'), 'sp_matheuristic', LINE, 42, 1800,
           round(r.km, 1), round(time.time() - t0, 1), cap_ok,
           json.dumps({'lb': r.metadata.get('lb'), 'gap': r.metadata.get('gap_pct'),
                       'max_daily': max_daily, 'day_range': [min(lens), max(lens)],
                       'cg': [r.metadata.get('cg_iters'), r.metadata.get('cg_converged')],
                       'hist': r.metadata.get('history')})[:240]]
    with open(BENCH, 'a', newline='') as f:
        csv.writer(f).writerow(row)

    v3_kms = [v['km'] for t, v in manifest.items() if t.startswith('alns_v3')]
    v3_best = min(v3_kms) if v3_kms else None
    v3_mean = round(sum(v3_kms) / len(v3_kms), 1) if v3_kms else None
    all_best = min([v['km'] for v in manifest.values()] or [r.km])
    log(f"\n=== 线{LINE} SP vs v3 基线 ===")
    log(f"v3 runs: {sorted(v3_kms) if v3_kms else '无'} | 最优 {v3_best} | 均值 {v3_mean}")
    log(f"SP+CG   : {r.km:.1f} | 单日分布 [{min(lens)}~{max(lens)}] (上限 {max_daily}) | 认证 gap {r.metadata.get('gap_pct')}% | capacity_ok={cap_ok}")
    if v3_best:
        log(f"vs v3 最优: {(r.km - v3_best) / v3_best * 100:+.2f}% | vs v3 均值: {(r.km - v3_mean) / v3_mean * 100:+.2f}%")
    log(f"vs 池内最佳单解: {(r.km - all_best) / all_best * 100:+.2f}% (池内最佳 {all_best})")

if PHASE in ('intensify', 'all'):
    # 绝对能力强化: SP 现行解 -> 逐日 LKH 升级 -> SA 变体列 -> 激进定价 SP+CG
    import glob as _glob
    from algos.lkh_engine import lkh_open_path
    from algos.hgs_pvrp import _sa_improve
    from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, sp_solve_ip
    pool = load_pool()
    manifest = load_runs_manifest()
    dmap = {str(d): d for d in dates}
    for f in _glob.glob(f'output/sp_pool_{LINE}_one_*.json'):
        pool += [(dmap[p[0]], p[1], p[2]) for p in json.load(open(f))]
    pool = dedupe_pool(pool, top_k=8)
    t0 = time.time()
    r0 = SPMatheuristic().solve(data, D, time_budget=240,
                                pool=[(dd, r, km) for dd, r, km in pool],
                                rounds=0, top_m=80, col_iter=120)
    incumbent = r0.days
    log(f"[intensify/{LINE}] 现行解 {r0.km:.1f} km, 开始 LKH 日级升级")
    from algos.tsp_engine import _exact_open_tsp
    for dd in dates:
        base = incumbent[dd]
        if len(base) <= 3:
            continue
        km_base = day_km(base, D)
        best_route, how = list(base), '保留'
        if len(base) <= 45:
            # 小中规模日: CP-SAT 精确解 -> 最优性证明 (先确认最优)
            try:
                ex = _exact_open_tsp(list(base), D, time_limit=120)
                km_ex = day_km(ex, D)
                if km_ex < km_base - 1e-6:
                    best_route, how = list(ex), 'CP-SAT最优'
                    km_base = km_ex
            except Exception as e:
                log(f"  CP-SAT {str(dd)} 异常({str(e)[:30]})")
        else:
            # 百店日: LKH 长跑确认 (先给足时间, 性能后调)
            try:
                lk = lkh_open_path(list(base), D, runs=10, max_trials=10000, time_limit=240)
                km_lk = day_km(lk, D)
                if km_lk < km_base - 1e-6:
                    best_route, how = list(lk), 'LKH'
                    km_base = km_lk
            except Exception as e:
                log(f"  LKH {str(dd)} 异常({str(e)[:30]})")
        log(f"  {str(dd)} n={len(incumbent[dd])}: {how} | {day_km(incumbent[dd], D):.2f} -> {day_km(best_route, D):.2f}")
        pool.append((dd, list(best_route), round(day_km(best_route, D), 3)))
    rng = random.Random(777)
    for bi in range(4):
        child = {dd: list(incumbent[dd]) for dd in dates}
        _sa_improve(child, D, dates, rng, time.time() + 45, hot=0.12)
        for dd in dates:
            pool.append((dd, list(child[dd]), round(day_km(child[dd], D), 3)))
        log(f"  SA 变体 {bi+1}/4: {total_km(child, D):.1f} km")
    pool = dedupe_pool(pool, top_k=8)
    log(f"强化池 {len(pool)} 列, 开始终解 SP+CG")
    r = SPMatheuristic().solve(data, D, time_budget=1200, pool=pool, rounds=3,
                               sa_burst=15.0, top_m=80, col_iter=120)
    row = [datetime.datetime.now().isoformat(timespec='seconds'), 'sp_intensify', LINE, 777, 1200,
           round(r.km, 1), round(time.time() - t0, 1), True,
           json.dumps({'lb': r.metadata.get('lb'), 'gap': r.metadata.get('gap_pct'),
                       'hist': r.metadata.get('history')})[:220]]
    with open(BENCH, 'a', newline='') as f:
        csv.writer(f).writerow(row)
    json.dump({'line': LINE, 'km': round(r.km, 1), 'lb': r.metadata.get('lb'),
               'gap_pct': r.metadata.get('gap_pct'),
               'days': {str(dd): r.days[dd] for dd in dates}},
              open(f'output/sp_intensified_{LINE}.json', 'w'), ensure_ascii=False, indent=1)
    v3_kms = [v['km'] for t, v in manifest.items() if v.get('name') == 'alns_v3' and v.get('km')]
    v3_best = min(v3_kms) if v3_kms else None
    log(f"\n=== 线{LINE} 强化终解 ===")
    log(f"SP+CG 强化: {r.km:.1f} | LP 下界 {r.metadata.get('lb')} | 认证 gap {r.metadata.get('gap_pct')}%")
    if v3_best:
        log(f"vs v3 最优: {(r.km - v3_best) / v3_best * 100:+.2f}% (v3 最优 {v3_best})")
