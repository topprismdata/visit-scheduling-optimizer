# -*- coding: utf-8 -*-
"""全办 R2' 真终账: 每线 = 4 seed R2'-ALNS 列生成 + 基线A列 + SP(r2_prime) 重组.

修复 (2026-09-05 双机审查):
  P1 线07 SP > 基线A (结构保证被破坏): 根因 = 池只入"原始顺序"列(≠基线A的CP-SAT排序列),
     且 r2_alns 从不劣于基线时才 snapshot -> 基线A列根本没进池.
     现强制 seed 基线A (CP-SAT 逐日重排) 的列进池 => SP ≤ baseA 由构造保证.
  P2 并发写同一 ledger 文件互相覆盖: 改为每线独立文件 output/sp_r2_ledger_<lid>.json,
     汇总由 --merge 完成.

用法: python run_r2_ledger.py <lines...>   (逐线计算, 各写独立文件)
      python run_r2_ledger.py --merge       (合并全部单线文件 -> sp_r2_ledger_all.json)
"""
import sys, os, time, json, glob, datetime as dt
sys.path.insert(0, ".")
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, total_km, check_capacity
from algos.r2_alns import R2ALNS
from algos.tsp_engine import _exact_open_tsp
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, check_r2prime, _wd

ALL = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']
BASE = json.load(open('output/cpsat_plan_baselines.json'))


def merge():
    out = {}
    for f in sorted(glob.glob('output/sp_r2_ledger_??.json')):
        lid = os.path.basename(f)[len('sp_r2_ledger_'):-len('.json')]
        try:
            out[lid] = json.load(open(f))
        except Exception:
            pass
    json.dump(out, open('output/sp_r2_ledger_all.json', 'w'), ensure_ascii=False, indent=1)
    done = sorted(k for k, v in out.items() if v.get('sp_km') is not None)
    tb = sum(out[l]['baseA'] for l in done); ts = sum(out[l]['sp_km'] for l in done)
    print(f"合并 {len(done)}/10 线: {done}")
    if done:
        print(f"Σ基线A={tb:.1f} ΣSP={ts:.1f} ({(ts-tb)/tb*100:+.2f}%)")
        for l in done:
            v = out[l]
            print(f"  线{l}: {v['baseA']} -> {v['sp_km']} ({v['delta_vs_baseA_pct']}%) "
                  f"分裂{v['r2_viol']} 换店{v['weekday_moved_stores']} 单日{v['day_range']} "
                  f"cap_ok={v['cap_ok']} 结构保证={'✓' if v['sp_km'] <= v['baseA'] + 1e-6 else '✗✗'}")
    return out


if '--merge' in sys.argv:
    merge()
    raise SystemExit

LINES = sys.argv[1:] or ALL
pv = load_plan()

for lid in LINES:
    out_f = f'output/sp_r2_ledger_{lid}.json'
    t0 = time.time()
    d = load_line(pv, lid); D = np.load(f'output/road_dist_{lid}.npy')
    dates = list(d.dates); mn, mx = d.min_daily_capacity, d.max_daily_capacity
    orig_wd = {}
    for dd, seq in d.days_orig.items():
        for c in seq: orig_wd[c] = _wd(dd)

    pool = []
    # [P1] 强制基线A列入池: 原分配 + 逐日 CP-SAT 最优序 (与 cpsat_plan_baselines 完全同构)
    for dd, seq in d.days_orig.items():
        seq_opt = _exact_open_tsp(list(seq), D, time_limit=30)
        pool.append((dd, list(seq_opt), round(day_km(seq_opt, D), 3)))
    # R2'-ALNS 4 seeds 历史列池
    best = None
    for seed in (42, 7, 123, 2026):
        r = R2ALNS().solve(d, D, time_budget=150, seed=seed)
        pool += r.metadata['_columns']
        if best is None or r.km < best.km: best = r
    legal = dedupe_pool(pool, top_k=8, max_daily=mx, min_daily=mn)

    try:
        rs = SPMatheuristic().solve(d, D, time_budget=300, pool=legal, rounds=1, sa_burst=10.0, r2_prime=True)
    except Exception as e:
        print(f"线{lid}: SP 异常 {e}", flush=True); rs = None
    baseA = BASE[lid]
    if rs is not None and rs.days:
        lens = [len(v) for v in rs.days.values()]
        viol = check_r2prime(rs.days)
        cur_wd = {}
        for dd, seq in rs.days.items():
            for c in seq: cur_wd.setdefault(c, _wd(dd))
        moved = sum(1 for c, w in orig_wd.items() if cur_wd.get(c) != w)
        rec = {'line': lid, 'baseA': baseA, 'r2alns_km': round(best.km, 1), 'sp_km': round(rs.km, 1),
               'delta_vs_baseA_pct': round((rs.km - baseA) / baseA * 100, 2),
               'structure_guarantee': bool(rs.km <= baseA + 1e-6),
               'cap_ok': bool(rs.capacity_ok), 'r2_viol': len(viol),
               'weekday_moved_stores': moved, 'day_range': [min(lens), max(lens)],
               'rmp_lp': rs.metadata.get('rmp_lp'), 'pool_gap_pct': rs.metadata.get('pool_gap_pct'),
               'pool_cols': len(legal), 'sec': round(time.time() - t0)}
    else:
        rec = {'line': lid, 'baseA': baseA, 'sp_km': None, 'r2alns_km': round(best.km, 1),
               'pool_cols': len(legal), 'sec': round(time.time() - t0)}
    json.dump(rec, open(out_f, 'w'), ensure_ascii=False, indent=1)
    print(f"线{lid}: 基线A={baseA} | R2ALNS={rec.get('r2alns_km')} | SP={rec.get('sp_km')} "
          f"({rec.get('delta_vs_baseA_pct')}%) | 换店={rec.get('weekday_moved_stores')} 违R2'={rec.get('r2_viol')} "
          f"| 结构保证={'✓' if rec.get('structure_guarantee') else '✗'} | {rec['sec']}s", flush=True)
