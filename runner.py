# -*- coding: utf-8 -*-
"""Runner: 多算法流水线. 路线生成 → 池 → SP 重组合 → 精确闭锁.
python runner.py --mode fast|standard|deep|all
python runner.py --algos baseline,nn2opt --lines 09
"""
import pandas as pd, json, time, os, sys
from data.loader import load_plan, load_line, ALL_LINE_IDS
from data.road import load_cached, save_cached, fetch_matrix
from algos.registry import get, list_all
from core.metric import check_freq
from core.route_pool import RoutePool, Route, day_km

import algos.impl  # triggers @register
import algos.sdr_exact  # triggers @register

MODES = {
    "fast":     {"baseline": 10, "nn2opt": 10, "greedy_crossday": 180},
    "standard": {"baseline": 10, "nn2opt": 10, "greedy_crossday": 180,
                 "cpsat_route": 300, "alns": 300},
    "deep":     {"baseline": 10, "nn2opt": 10, "greedy_crossday": 180,
                 "cpsat_route": 300, "alns": 300, "ensemble_sp": 300, "sdr_exact": 600},
    "all":      {"baseline": 10, "nn2opt": 10, "greedy_crossday": 180,
                 "cpsat_route": 300, "alns": 300, "ensemble_sp": 300,
                 "sdr_exact": 600, "lkh_route": 300},
}
GENERATORS = ["baseline", "nn2opt", "greedy_crossday", "cpsat_route", "alns"]


def run_pipeline_line(data, D, budgets, algo_names):
    """Pipeline: 路线生成 → 池 → SP 重组合.
    Returns list of {line, algo, km, ...} results.
    """
    pool = RoutePool()
    results = []
    best_days = None
    best_km = float('inf')
    names = algo_names or list(budgets.keys())
    gen_names = [a for a in GENERATORS if a in names]
    # Phase 1: Route generators → fill pool
    for name in gen_names:
        if name not in budgets: continue
        try:
            algo = get(name)()
            t0 = time.time()
            result = algo.solve(data, D, time_budget=budgets[name])
            result.elapsed = time.time() - t0
            result.count_ok = check_freq(result.days, data.codes, data.freq)
            results.append(dict(line=data.line_id, algo=name, km=round(result.km, 1),
                                moves=result.moves, count_ok=bool(result.count_ok),
                                sec=round(result.elapsed, 1), phase="gen"))
            print(f"  {name}: {result.km:.1f} km [{result.moves}] 校验{'✓' if result.count_ok else '✗'}", flush=True)
            # 跟踪最优解用于 warm start
            if name not in ['baseline', 'nn2opt']:
                if 'best_days' not in dir() or result.km < best_km:
                    best_days = result.days
                    best_km = result.km
            # 注入路线池
            pool.add_from_algo(result.days, D, name)
            # 同时注入所有生成器的子路线 (TSP 优化后的)
            for dd, seq in result.days.items():
                pool.add(Route(date=dd, stores=tuple(seq), cost=day_km(seq, D), algo=name))
        except Exception as e:
            print(f"  [{name}] FAILED: {e}", flush=True)
    # Phase 2: Ensemble SP over pool
    if "ensemble_sp" in names:
        try:
            t0 = time.time()
            es = get("ensemble_sp")()
            result = es.solve(data, D, time_budget=budgets["ensemble_sp"], pool=pool)
            result.elapsed = time.time() - t0
            result.count_ok = check_freq(result.days, data.codes, data.freq)
            results.append(dict(line=data.line_id, algo="ensemble_sp", km=round(result.km, 1),
                                moves=0, count_ok=bool(result.count_ok),
                                sec=round(result.elapsed, 1), phase="ensemble"))
            print(f"  ensemble_sp: {result.km:.1f} km (pool={pool.stats()['total_routes']}) 校验{'✓' if result.count_ok else '✗'}", flush=True)
        except Exception as e:
            print(f"  [ensemble_sp] FAILED: {e}", flush=True)
    # Phase 3: SDR exact over pool
    if "sdr_exact" in names:
        try:
            t0 = time.time()
            sdr = get("sdr_exact")()
            result = sdr.solve(data, D, time_budget=budgets["sdr_exact"], pool=pool, warm_start=best_days if 'best_days' in dir() else None)
            result.elapsed = time.time() - t0
            result.count_ok = check_freq(result.days, data.codes, data.freq)
            results.append(dict(line=data.line_id, algo="sdr_exact", km=round(result.km, 1),
                                moves=0, count_ok=bool(result.count_ok),
                                sec=round(result.elapsed, 1), phase="sdr"))
            meta = result.metadata or {}
            print(f"  sdr_exact: {result.km:.1f} km (pool={pool.stats()['total_routes']}, gap={meta.get('gap','?')}) 校验{'✓' if result.count_ok else '✗'}", flush=True)
        except Exception as e:
            print(f"  [sdr_exact] FAILED: {e}", flush=True)
    return results


def run_lines(line_ids=None, mode="standard", out="output/ledger.csv"):
    pv = load_plan()
    line_ids = line_ids or ALL_LINE_IDS
    budgets = MODES.get(mode, MODES["standard"])
    summary = []
    for lid in line_ids:
        data = load_line(pv, lid)
        print(f"== 线 {lid} ({data.line_name}): {data.stores}店/{data.visits}次 ==", flush=True)
        D = load_cached(lid)
        if D is None:
            print(f"  获取路网矩阵 {data.stores}x{data.stores} ...", flush=True)
            t0 = time.time(); D = fetch_matrix(data.codes, data.lon, data.lat)
            save_cached(lid, D, data.codes)
            print(f"  矩阵 {time.time()-t0:.0f}s", flush=True)
        D = D.tolist()
        res = run_pipeline_line(data, D, budgets, list(budgets.keys()))
        summary.extend(res)
    t = pd.DataFrame(summary)
    os.makedirs(os.path.dirname(out) if os.path.dirname(out) else ".", exist_ok=True)
    t.to_csv(out, index=False)
    json.dump(summary, open(out.replace(".csv", ".json"), "w"), ensure_ascii=False, indent=1)
    piv = t[t.phase != "ensemble"].pivot_table(index="line", columns="algo", values="km")
    print("\n=== 总账 (km) ===")
    print(piv.to_string())
    if "ensemble_sp" in t["algo"].values:
        print("\n=== Ensemble SP ===")
        print(t[t["algo"] == "ensemble_sp"][["line", "km", "sec"]].to_string(index=False))
    print("\n=== 全办合计 ===")
    for a in t["algo"].unique():
        km_sum = t[t["algo"] == a]["km"].sum()
        print(f"  {a}: {km_sum:.1f} km")
    return t


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="standard")
    ap.add_argument("--algos")
    ap.add_argument("--lines")
    ap.add_argument("--out", default="output/ledger_standard.csv")
    a = ap.parse_args()
    run_lines(line_ids=a.lines.split(",") if a.lines else None,
              mode=a.mode, out=a.out)
