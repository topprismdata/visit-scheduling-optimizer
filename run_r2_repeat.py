# -*- coding: utf-8 -*-
"""R2' 终账重复实验协议 (评审: 单点数字不可信 -> 每线 n=3 独立重复, 报中位[范围]).

每 rep = 基线A列(强制入池) + 4×150s R2-ALNS 独立种子组列池 + SP(r2_prime) 终解.
种子组: rep1=(42,7,123,2026) rep2=(11,22,33,44) rep3=(55,66,77,88)
输出: output/sp_r2_repeat_<lid>.json {reps:[...], median, min, max, flags}
用法: python run_r2_repeat.py <lines...>
"""
import sys, os, time, json
sys.path.insert(0, ".")
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, check_capacity
from algos.r2_alns import R2ALNS
from algos.tsp_engine import _exact_open_tsp
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, check_r2prime, _wd

SEED_GROUPS = [(42, 7, 123, 2026), (11, 22, 33, 44), (55, 66, 77, 88)]
BASE = json.load(open('output/cpsat_plan_baselines.json'))
pv = load_plan()

for lid in sys.argv[1:]:
    out_f = f'output/sp_r2_repeat_{lid}.json'
    if os.path.exists(out_f) and len(json.load(open(out_f)).get('reps', [])) == len(SEED_GROUPS):
        print(f"线{lid}: 重复实验已完成, 跳过", flush=True)
        continue
    d = load_line(pv, lid); D = np.load(f'output/road_dist_{lid}.npy')
    dates = list(d.dates); mn, mx = d.min_daily_capacity, d.max_daily_capacity
    base_cols = []
    for dd, seq in d.days_orig.items():
        seq_opt = _exact_open_tsp(list(seq), D, time_limit=30)
        base_cols.append((dd, list(seq_opt), round(day_km(seq_opt, D), 3)))
    recs = []
    for rep, seeds in enumerate(SEED_GROUPS):
        t0 = time.time()
        pool = list(base_cols)
        for s in seeds:
            r = R2ALNS().solve(d, D, time_budget=150, seed=s)
            pool += r.metadata['_columns']
        legal = dedupe_pool(pool, top_k=8, max_daily=mx, min_daily=mn)
        rs = SPMatheuristic().solve(d, D, time_budget=300, pool=legal, rounds=1, sa_burst=10.0, r2_prime=True)
        viol = len(check_r2prime(rs.days))
        cap_ok = bool(check_capacity(rs.days, mx, mn))
        recs.append({'rep': rep, 'seeds': list(seeds), 'km': round(rs.km, 2),
                     'r2_viol': viol, 'cap_ok': cap_ok,
                     'pool_gap_pct': rs.metadata.get('pool_gap_pct'), 'sec': round(time.time()-t0)})
        print(f"  线{lid} rep{rep}: {rs.km:.2f} km (viol={viol} cap={cap_ok}) {recs[-1]['sec']}s", flush=True)
    kms = sorted(x['km'] for x in recs)
    med = kms[len(kms)//2]
    baseA = BASE[lid]
    out = {'line': lid, 'baseA': baseA, 'reps': recs,
           'median': med, 'min': kms[0], 'max': kms[-1],
           'median_delta_pct': round((med - baseA)/baseA*100, 2),
           'band_delta_pct': [round((kms[-1]-baseA)/baseA*100, 2), round((kms[0]-baseA)/baseA*100, 2)],
           'all_r2_ok': all(x['r2_viol'] == 0 for x in recs), 'all_cap_ok': all(x['cap_ok'] for x in recs)}
    json.dump(out, open(out_f, 'w'), ensure_ascii=False, indent=1)
    print(f"线{lid} 终: median={med} [{kms[0]}~{kms[-1]}] baseA={baseA} ({out['median_delta_pct']}%)", flush=True)
