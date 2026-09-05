# -*- coding: utf-8 -*-
"""全办 10 位业代容量加限 SP+CG 全量重算 (每人严格遵守各自独立的单日上限 K_max)."""
import sys, os, time, json, csv, glob
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, total_km, check_capacity
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool

pv = load_plan()
LINES = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']
BENCH = 'output/bench_20260905.csv'

print("=== 开始全办 10 位业代容量加限 SP+CG 终极重算 ===", flush=True)

for lid in LINES:
    data = load_line(pv, lid)
    min_orig = data.min_daily_capacity
    max_orig = data.max_daily_capacity
    D = np.load(f'output/road_dist_{lid}.npy')
    dates = list(data.dates)
    dmap = {str(d): d for d in dates}
    
    # 载入该线所有池文件
    pool = []
    pool_f = f'output/sp_pool_{lid}.json'
    if os.path.exists(pool_f):
        pool += [(dmap[p[0]], p[1], p[2]) for p in json.load(open(pool_f))]
    for f in glob.glob(f'output/sp_pool_{lid}_one_*.json'):
        pool += [(dmap[p[0]], p[1], p[2]) for p in json.load(open(f))]
        
    before_n = len(pool)
    clean_pool = dedupe_pool(pool, top_k=8, max_daily=max_orig, min_daily=min_orig)
    dropped = before_n - len(clean_pool)
    print(f"\n>>> 线路 海珠荔湾{lid} ({data.line_name.split('_')[-1]}) | 原计划业务走廊: [{min_orig} ~ {max_orig}] 店", flush=True)
    print(f"    走廊清洗: {before_n} -> {len(clean_pool)} 列 (清除 {dropped} 条越界列)", flush=True)
    
    t0 = time.time()
    r = SPMatheuristic().solve(data, D, time_budget=300, pool=clean_pool, rounds=2,
                               sa_burst=10.0, top_m=40, col_iter=60, max_daily=max_orig, min_daily=min_orig)
    dur = time.time() - t0
    lens = [len(r.days[dd]) for dd in dates]
    cap_ok = check_capacity(r.days, max_orig, min_orig)
    
    print(f"    SP+CG 求解完成: 里程 {r.km:.1f} km | 耗时 {dur:.1f}s", flush=True)
    print(f"    单日门店分布: [{min(lens)} ~ {max(lens)}] (走廊 [{min_orig}~{max_orig}]) | 走廊合规: {'PASS ✓' if cap_ok else 'FAIL ✗'}", flush=True)
    print(f"    LP 认证下界: {r.metadata.get('lb')} | 认证 Gap: {r.metadata.get('gap_pct')}%", flush=True)
    
    # 保存结果
    out_f = f'output/sp_clean_cap_{lid}.json'
    json.dump({
        'line': lid,
        'rep_name': data.line_name.split('_')[-1],
        'min_daily_capacity': min_orig,
        'max_daily_capacity': max_orig,
        'km': round(r.km, 1),
        'lb': r.metadata.get('lb'),
        'gap_pct': r.metadata.get('gap_pct'),
        'day_range': [min(lens), max(lens)],
        'capacity_ok': cap_ok,
        'days': {str(dd): r.days[dd] for dd in dates}
    }, open(out_f, 'w'), ensure_ascii=False, indent=1)
    
    # 写入 bench CSV
    row = [time.strftime('%Y-%m-%dT%H:%M:%S'), 'sp_clean_cap', lid, 42, 300,
           round(r.km, 1), round(dur, 1), cap_ok,
           json.dumps({'lb': r.metadata.get('lb'), 'gap': r.metadata.get('gap_pct'),
                       'max_daily': max_orig, 'day_range': [min(lens), max(lens)],
                       'cg': [r.metadata.get('cg_iters'), r.metadata.get('cg_converged')]})[:240]]
    with open(BENCH, 'a', newline='') as f:
        csv.writer(f).writerow(row)

print("\n=== 全办 10 线容量合规重算全部完成! ===", flush=True)
