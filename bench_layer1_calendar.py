# -*- coding: utf-8 -*-
"""Layer 1 月度排日历 性能-质量帕累托矩阵测试 (09 线真实全月数据, 严格单日 <= 35 店).

测试矩阵:
  - 算法: ALNS v3 (容量加限), HGS-PVRP (容量加限), SP+CG (合规列池集合划分)
  - 时间档位: 30s (快速预览), 60s (敏捷调试), 300s (标准交付 5min), 900s (深度排产 15min)
  - 统计指标: 全月里程 km, 节省率, 单日店数范围 [min, max], 变异系数 CV, 认证 Gap, capacity_ok
"""
import sys, os, time, json
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km, total_km, check_capacity
from algos.alns_v3 import ALNSv3
from algos.hgs_pvrp import HGSPVRP
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool

pv = load_plan(); data = load_line(pv, '09')
D = np.load('output/road_dist_09.npy')
dates = list(data.dates)
max_daily = data.max_daily_capacity  # 严格 35 店
SRP_BASE_KM = 1116.0

# 原始计划分布
orig_lens = [len(data.days_orig[dd]) for dd in dates]
orig_cv = round(float(np.std(orig_lens) / np.mean(orig_lens)), 3)
print(f"=== Layer 1 月度排日历性能-质量矩阵测试 (09线, 单日严格 <= {max_daily} 店) ===", flush=True)
print(f"SRP 原始计划: {SRP_BASE_KM} km | 单日 [{min(orig_lens)}~{max(orig_lens)}] | CV={orig_cv}", flush=True)

# 载入合规路线池 (严格 <= 35 店)
pool = []
dmap = {str(d): d for d in dates}
if os.path.exists('output/sp_pool_09.json'):
    pool += [(dmap[p[0]], p[1], p[2]) for p in json.load(open('output/sp_pool_09.json'))]
import glob
for f in glob.glob('output/sp_pool_09_one_*.json'):
    pool += [(dmap[p[0]], p[1], p[2]) for p in json.load(open(f))]
legal_pool = dedupe_pool(pool, max_daily=max_daily)
print(f"路线池容量门禁: {len(pool)} -> {len(legal_pool)} 合规列 (100% <= {max_daily} 店)\n", flush=True)

TIME_TIERS = [30, 60, 300]  # 快速/敏捷/标准档 (900s 已由深波浪实测数据对齐)
matrix_results = []

def eval_solution(name, tier_s, r, lb=None, gap=None):
    lens = [len(r.days[dd]) for dd in dates]
    cv = round(float(np.std(lens) / np.mean(lens)), 3)
    cap_ok = max(lens) <= max_daily
    pct_save = round((SRP_BASE_KM - r.km) / SRP_BASE_KM * 100, 1)
    res = {
        "algo": name,
        "budget_s": tier_s,
        "km": round(r.km, 1),
        "pct_save": pct_save,
        "day_min": min(lens),
        "day_max": max(lens),
        "cv": cv,
        "cap_ok": cap_ok,
        "lb": round(lb, 1) if lb else None,
        "gap_pct": gap,
        "elapsed": round(r.elapsed, 1) if hasattr(r, 'elapsed') else tier_s
    }
    matrix_results.append(res)
    gap_str = f"| gap: {gap}%" if gap is not None else ""
    cap_str = "PASS ✓" if cap_ok else "FAIL ✗"
    print(f"  {name:<16} [{tier_s:>3}s] | {r.km:>6.1f} km (-{pct_save:>4.1f}%) | 单日 [{min(lens):>2}~{max(lens):>2}] | CV: {cv:.3f} | 容量: {cap_str} {gap_str}", flush=True)
    return res

for budget in TIME_TIERS:
    print(f"\n>>> 时间预算档位: {budget} 秒", flush=True)
    
    # 1. ALNS v3 (容量加限)
    t0 = time.time()
    r_v3 = ALNSv3().solve(data, D, time_budget=budget, seed=42)
    r_v3.elapsed = time.time() - t0
    eval_solution("ALNS v3 (容量加限)", budget, r_v3)
    
    # 2. HGS-PVRP (容量加限)
    t0 = time.time()
    r_hgs = HGSPVRP().solve(data, D, time_budget=budget, seed=42)
    r_hgs.elapsed = time.time() - t0
    eval_solution("HGS-PVRP (容量加限)", budget, r_hgs)
    
    # 3. SP + CG (合规列池)
    t0 = time.time()
    r_sp = SPMatheuristic().solve(data, D, time_budget=budget, pool=legal_pool, rounds=1,
                                  top_m=40, col_iter=60, max_daily=max_daily)
    r_sp.elapsed = time.time() - t0
    eval_solution("SP+CG (合规列池)", budget, r_sp,
                  lb=r_sp.metadata.get('lb'), gap=r_sp.metadata.get('gap_pct'))

json.dump(matrix_results, open("output/layer1_calendar_benchmark.json", "w"), ensure_ascii=False, indent=2)
print("\n=== Layer 1 帕累托矩阵测试完成! 结果保存在 output/layer1_calendar_benchmark.json ===", flush=True)
