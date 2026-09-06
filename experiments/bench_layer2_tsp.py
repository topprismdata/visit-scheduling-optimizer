# -*- coding: utf-8 -*-
"""Layer 2 TSP 纯引擎性能-质量对决测试 (09 线真实单日数据).

对比对象:
  1. NN + 2opt (瞬时启发式: pass=0 纯NN, pass=1 快速, pass=30 充分)
  2. LKH-3 (进阶启发式: 浅搜 runs=1/1s, 均衡 runs=3/5s, 深搜 runs=10/30s)
  3. CP-SAT (精确求解器: 限时 1s, 5s, 30s, 120s 极限界)

测试规模 (09 线真实日期点集):
  - n=15: 07-01 半日抽样 (轻量作业)
  - n=23: 07-01 完整周三 (小日)
  - n=29: 07-02 完整周四 (中日)
  - n=35: 07-06 完整周一 (业务峰值满载日, K_max)
"""
import sys, os, time, json
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from data.loader import load_plan, load_line
from core.metric import day_km
from algos.tsp_engine import _nn2opt_open
from algos.lkh_engine import lkh_open_path, LKH_BIN
from ortools.sat.python import cp_model

pv = load_plan()
data = load_line(pv, '09')
D = np.load('output/road_dist_09.npy')

INSTANCES = [
    ("n=15 (半日轻量)", list(data.days_orig[data.dates[0]][:15])),
    ("n=23 (真实周三)", list(data.days_orig[data.dates[0]])),
    ("n=29 (真实周四)", list(data.days_orig[data.dates[1]])),
    ("n=35 (峰值满载)", list(data.days_orig[data.dates[3]])),
]

def solve_nn_pass(stores, D, max_pass=0):
    """NN + 指定轮数 2-opt."""
    seq = list(stores); n = len(seq)
    if n <= 3: return list(seq), 0.0
    t0 = time.perf_counter()
    unv = set(range(1, n)); out = [0]
    while unv:
        l = out[-1]; out.append(min(unv, key=lambda j: D[seq[l]][seq[j]])); unv.discard(out[-1])
    route = [seq[t] for t in out]
    if max_pass > 0:
        for _ in range(max_pass):
            imp = False
            for a in range(1, n - 2):
                for b in range(a + 1, n - 1):
                    if D[route[a-1]][route[b]] + D[route[a]][route[b+1]] < D[route[a-1]][route[a]] + D[route[b]][route[b+1]] - 1e-9:
                        route[a:b+1] = route[a:b+1][::-1]; imp = True
            if not imp: break
    dur = time.perf_counter() - t0
    return route, dur

def solve_cpsat_timed(stores, D, time_limit=30):
    """带精确计时与状态返回的 CP-SAT 求解."""
    m = len(stores)
    if m <= 3: return list(stores), 0.0, "OPTIMAL"
    n = m + 1
    t0 = time.perf_counter()
    model = cp_model.CpModel()
    arcs = []
    for i in range(m):
        for j in range(m):
            if i != j: arcs.append((i, j, model.NewBoolVar(f'x{i}_{j}')))
    for i in range(m):
        arcs.append((i, m, model.NewBoolVar(f'd{i}')))
        arcs.append((m, i, model.NewBoolVar(f'e{i}')))
    for v in range(n):
        out_v = [v_var for (i, j, v_var) in arcs if i == v]
        in_v = [v_var for (i, j, v_var) in arcs if j == v]
        model.Add(sum(out_v) == 1)
        model.Add(sum(in_v) == 1)
    x = {(i, j): v_var for (i, j, v_var) in arcs if i < n and j < n}
    obj = sum(int(round(float(D[stores[i]][stores[j]]) * 1000)) * x[(i, j)]
              for i in range(m) for j in range(m) if i != j)
    model.AddCircuit(arcs)
    model.Minimize(obj)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    st = solver.Solve(model)
    dur = time.perf_counter() - t0
    st_str = "OPTIMAL" if st == cp_model.OPTIMAL else ("FEASIBLE" if st == cp_model.FEASIBLE else "TIMEOUT")
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        tour = [m]
        for _ in range(n):
            curr = tour[-1]
            for (i, j, v_var) in arcs:
                if i == curr and solver.Value(v_var):
                    tour.append(j); break
        res = [stores[i] for i in tour if i < m]
        return res, dur, st_str
    return list(stores), dur, st_str

def solve_lkh_timed(stores, D, runs=3, max_trials=1000, time_limit=5):
    """带高精度计时的 LKH-3."""
    t0 = time.perf_counter()
    res = lkh_open_path(stores, D, runs=runs, max_trials=max_trials, time_limit=time_limit)
    dur = time.perf_counter() - t0
    return res, dur

results = []
print("=== 开始 Layer 2 单日 TSP 纯引擎性能-质量对决测试 ===", flush=True)

for label, stores in INSTANCES:
    n = len(stores)
    print(f"\n>>> 测试规模: {label} (n={n})", flush=True)
    
    # 0. 先跑 CP-SAT 120s 获取该实例的数学全局最优作为基准锚点
    opt_route, opt_dur, opt_st = solve_cpsat_timed(stores, D, time_limit=120)
    opt_km = day_km(opt_route, D)
    print(f"  [锚点] CP-SAT 120s: {opt_km:.3f} km | 耗时 {opt_dur*1000:.1f} ms | 状态 {opt_st}", flush=True)

    CONFIGS = [
        # (大类, 档位名称, 函数回调)
        ("NN+2opt", "纯NN (0-pass)", lambda: solve_nn_pass(stores, D, max_pass=0) + ("HEURISTIC",)),
        ("NN+2opt", "快速 2-opt (1-pass)", lambda: solve_nn_pass(stores, D, max_pass=1) + ("HEURISTIC",)),
        ("NN+2opt", "充分 2-opt (30-pass)", lambda: solve_nn_pass(stores, D, max_pass=30) + ("HEURISTIC",)),
        ("LKH-3",   "极速档 (runs=1, 1s)", lambda: solve_lkh_timed(stores, D, runs=1, max_trials=200, time_limit=1) + ("HEURISTIC",)),
        ("LKH-3",   "标准档 (runs=5, 5s)", lambda: solve_lkh_timed(stores, D, runs=5, max_trials=2000, time_limit=5) + ("HEURISTIC",)),
        ("LKH-3",   "充分档 (runs=10, 20s)", lambda: solve_lkh_timed(stores, D, runs=10, max_trials=10000, time_limit=20) + ("HEURISTIC",)),
        ("CP-SAT",  "瞬时档 (限时 0.2s)", lambda: solve_cpsat_timed(stores, D, time_limit=0.2)),
        ("CP-SAT",  "交互档 (限时 1.0s)", lambda: solve_cpsat_timed(stores, D, time_limit=1.0)),
        ("CP-SAT",  "标准档 (限时 5.0s)", lambda: solve_cpsat_timed(stores, D, time_limit=5.0)),
        ("CP-SAT",  "充分档 (限时 30.0s)", lambda: solve_cpsat_timed(stores, D, time_limit=30.0)),
    ]

    for algo, tier, fn in CONFIGS:
        route, dur, st = fn()
        km = day_km(route, D)
        gap = round((km - opt_km) / opt_km * 100, 2)
        dur_str = f"{dur*1000:.1f} ms" if dur < 1.0 else f"{dur:.2f} s"
        print(f"  {algo:<8} | {tier:<20} | 里程: {km:.3f} km | Gap: {gap:>+6.2f}% | 耗时: {dur_str:>9} | {st}", flush=True)
        results.append({
            "scale": label,
            "n": n,
            "algo": algo,
            "tier": tier,
            "km": round(km, 3),
            "opt_km": round(opt_km, 3),
            "gap_pct": gap,
            "dur_sec": round(dur, 4),
            "status": st
        })

json.dump(results, open("output/layer2_tsp_benchmark.json", "w"), ensure_ascii=False, indent=2)
print("\n=== Layer 2 TSP 纯引擎对决测试完成! 结果已保存至 output/layer2_tsp_benchmark.json ===", flush=True)
