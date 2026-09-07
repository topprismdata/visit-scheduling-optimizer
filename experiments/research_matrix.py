# -*- coding: utf-8 -*-
"""research_matrix/v1 — 算法研究对比协议 runner (A 日历 / B 路线).

设计: docs/design/MATRIX_PROTOCOL_V3_DESIGN_v0.3.md
核心规则: 全部引擎产出过共同 CP-SAT 排序后评价与入池 (§5.3)。
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algos.branch_and_price import BranchAndPrice
from algos.hgs_pvrp import HGSPVRP
from algos.r2_alns import R2ALNS
from algos.sp_matheuristic import column_generate
from algos.tsp_engine import _exact_open_tsp_status, _nn2opt_open
from core.contract import check_contract, contract_of
from core.metric import check_capacity, day_km
from data.loader import load_line, load_plan
from visitmodel.sp.formulation import sp_solve_ip

SCHEMA = "research_matrix/v1"
OUT_DIR = ROOT / "output" / "research_matrix" / "v1"
ALL_LINES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]
ALL_ENGINES = ["base", "r2_alns", "alns_v3", "hgs_pvrp", "sp_cg", "bp_solo"]

# ---------------------------------------------------------------------------
# 共同 TSP 排序
# ---------------------------------------------------------------------------

def _cpsat_route(seq, D, timeout):
    route, status, _ms = _exact_open_tsp_status(list(seq), D, timeout)
    return list(route), status


# ---------------------------------------------------------------------------
# 引擎适配器: 产出 (native_days, raw_columns[(date, route, km, source)])
# 全部产出必须经共同 CP-SAT 排序后再评价 (协议 §5.3)
# ---------------------------------------------------------------------------

def produce_calendar(engine_id, data, D, dates, contracts, budget_s, seeds, cp_timeout):
    raw = []
    native_days = None
    diag = {}
    t0 = time.perf_counter()

    if engine_id == "base":
        for dd in dates:
            route, _st = _cpsat_route(list(data.days_orig[dd]), D, cp_timeout)
            km = round(day_km(route, D), 3)
            raw.append((dd, route, km, "base"))
        native_days = {dd: list(data.days_orig[dd]) for dd in dates}

    elif engine_id == "r2_alns":
        from algos.r2_alns import R2ALNS as _R2
        for s in seeds:
            r = _R2().solve(data, D, iteration_budget=int(budget_s * 600), seed=s,
                            combo_mode="contract", final_reroute=False)
            for dd in dates:
                route, _st = _cpsat_route(list(r.days[dd]), D, cp_timeout)
                raw.append((dd, route, round(day_km(route, D), 3), f"r2_s{s}"))
            diag.setdefault("iters", []).append(r.metadata.get("iters"))
        native_days = {dd: list(rt) for dd, rt in r.days.items()}

    elif engine_id == "alns_v3":
        from algos.alns_v3 import ALNSv3
        for s in seeds:
            r = ALNSv3().solve(data, D, time_budget=budget_s, seed=s, weekday_lock=True)
            for dd in dates:
                route, _st = _cpsat_route(list(r.days[dd]), D, cp_timeout)
                raw.append((dd, route, round(day_km(route, D), 3), f"alns3_s{s}"))
            diag.setdefault("iters", []).append(r.metadata.get("iters"))
        native_days = {dd: list(rt) for dd, rt in r.days.items()}

    elif engine_id == "hgs_pvrp":
        from algos.hgs_pvrp import HGSPVRP
        for s in seeds:
            r = HGSPVRP().solve(data, D, time_budget=budget_s, seed=s)
            for dd in dates:
                route, _st = _cpsat_route(list(r.days[dd]), D, cp_timeout)
                raw.append((dd, route, round(day_km(route, D), 3), f"hgs_s{s}"))
        native_days = {dd: list(rt) for dd, rt in r.days.items()}

    elif engine_id == "sp_cg":
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        base_cols = []
        for dd in dates:
            route, _st = _cpsat_route(list(data.days_orig[dd]), D, cp_timeout)
            base_cols.append((dd, route, round(day_km(route, D), 3)))
        rmp_lp, generated, cg_iters, converged = column_generate(
            dates, k_c, base_cols, D, max_iter=6, verbose=False,
            top_m=40, col_iter=60, max_daily=data.max_daily_capacity,
            min_daily=data.min_daily_capacity, r2_prime=True, contract=contracts)
        for dd, route, km in generated:
            route2, _st = _cpsat_route(list(route), D, cp_timeout)
            raw.append((dd, route2, round(day_km(route2, D), 3), "sp_cg"))
        for dd, route, km in base_cols:
            route2, _st = _cpsat_route(list(route), D, cp_timeout)
            raw.append((dd, route2, round(day_km(route2, D), 3), "sp_cg_seed"))
        diag["cg_iters"] = cg_iters
        diag["cg_converged"] = bool(converged)
        diag["rmp_lp"] = rmp_lp

    elif engine_id == "bp_solo":
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        for s in seeds:
            eng = BranchAndPrice(
                dates, k_c, D, contracts, data.days_orig,
                data.min_daily_capacity, data.max_daily_capacity,
                time_budget=budget_s, max_nodes=20000,
                exact_pricing=True, exact_tl=1.0,
                initial_days=None, initial_pool=None)
            res = eng.solve()
            if res["incumbent_days"]:
                for dd in dates:
                    route, _st = _cpsat_route(list(res["incumbent_days"][dd]), D, cp_timeout)
                    raw.append((dd, route, round(day_km(route, D), 3), f"bp_s{s}"))
            for dd, route, _km in res["pool"]:
                route2, _st = _cpsat_route(list(route), D, cp_timeout)
                raw.append((dd, route2, round(day_km(route2, D), 3), f"bp_s{s}"))
            diag.setdefault("bp_status", []).append(res["status"])
            diag.setdefault("bp_nodes", []).append(res["nodes"])
            diag.setdefault("root_lb", []).append(res.get("root_lb"))
        if res["incumbent_days"]:
            native_days = {dd: list(rt) for dd, rt in res["incumbent_days"].items()}

    else:
        raise ValueError(f"unknown engine: {engine_id}")

    diag["wall_sec"] = round(time.perf_counter() - t0, 3)
    return native_days, raw, diag


# ---------------------------------------------------------------------------
# 池规范化 + 终闸
# ---------------------------------------------------------------------------

def normalize_columns(raw_columns):
    """同 (date, 店集) 归并保最优排序."""
    best = {}
    for dd, route, km in raw_columns:
        key = (dd, frozenset(route))
        if key not in best or km < best[key][0]:
            best[key] = (km, list(route))
    return [(dd, rt, km) for (dd, fs), (km, rt) in sorted(best.items(), key=lambda z: str(z[0][0]))]


def run_a_matrix(line_id, data, D, dates, contracts, k_c,
                 budget_s, seeds, cp_timeout):
    results = {}
    baseline_km = None

    for engine in ALL_ENGINES:
        t0 = time.perf_counter()
        native_days, raw, diag = produce_calendar(
            engine, data, D, dates, contracts, budget_s, seeds, cp_timeout)
        wall = round(time.perf_counter() - t0, 3)

        norm = normalize_columns([(dd, rt, km) for dd, rt, km, _s in raw])

        if norm:
            best_km, selected, info = sp_solve_ip(
                dates, k_c, [(dd, rt, km) for dd, rt, km in norm],
                timeout_s=300, r2_prime=True, contract=contracts,
                return_diagnostics=True)
        else:
            best_km, selected, info = None, None, {"status": "EMPTY_POOL"}

        violations = []
        cap_ok = None
        if selected:
            violations = check_contract(selected, contracts, dates)
            cap_ok = check_capacity(selected, data.max_daily_capacity, data.min_daily_capacity)

        native_km = None
        if native_days:
            native_km = round(sum(
                day_km(_cpsat_route(list(native_days[dd]), D, cp_timeout)[0], D)
                for dd in dates), 3)

        src_dist = dict(Counter(_s for _, _, _, _s in raw))

        results[engine] = {
            "engine": engine,
            "native_km": native_km,
            "pipeline_km": round(best_km, 3) if best_km is not None else None,
            "vs_base_pct": None,
            "status": info.get("status", "UNKNOWN"),
            "optimality_proven": info.get("optimality_proven", False),
            "contract_violations": len(violations),
            "capacity_ok": cap_ok,
            "pool_size": len(norm),
            "raw_pool_size": len(raw),
            "source_dist": src_dist,
            "wall_sec": wall,
            "diag": diag,
        }
        if engine == "base":
            baseline_km = best_km

    for engine in results:
        if baseline_km is not None and results[engine]["pipeline_km"] is not None:
            results[engine]["vs_base_pct"] = round(
                (results[engine]["pipeline_km"] - baseline_km) / baseline_km * 100, 3)

    return results


# ---------------------------------------------------------------------------
# B 矩阵: 冻结日店集, 路线算法互比
# ---------------------------------------------------------------------------

def multistart_nn2opt(seq, D, n_starts=10, seed=42):
    import random
    rng = random.Random(seed)
    best_route, best_km = None, float("inf")
    for _ in range(n_starts):
        start = rng.choice(seq)
        route = [start]
        unused = set(seq) - {start}
        while unused:
            cur = route[-1]
            nxt = min(unused, key=lambda j: D[cur][j])
            route.append(nxt)
            unused.discard(nxt)
        improved = True
        while improved:
            improved = False
            n = len(route)
            for a in range(1, n - 1):
                for b in range(a + 1, n):
                    old = D[route[a-1]][route[a]] + (D[route[b]][route[b+1]] if b < n-1 else 0)
                    new = D[route[a-1]][route[b]] + (D[route[a]][route[b+1]] if b < n-1 else 0)
                    if new < old - 1e-9:
                        route[a:b+1] = route[a:b+1][::-1]
                        improved = True
        km = sum(D[route[k]][route[k+1]] for k in range(len(route) - 1))
        if km < best_km:
            best_km = km
            best_route = list(route)
    return best_route, best_km


def run_b_matrix(line_id, data, D, dates, cp_timeout):
    results = {}
    for dd in dates:
        stores = list(data.days_orig[dd])
        row = {}
        r, _s = _nn2opt_open(stores, D), "HEURISTIC"
        row["nn2opt"] = {"km": round(day_km(r, D), 3), "status": "HEURISTIC"}
        r_ms, km_ms = multistart_nn2opt(stores, D, n_starts=10)
        row["multistart_nn2opt"] = {"km": round(km_ms, 3), "status": "HEURISTIC"}
        r_cpsat, status, _ms = _exact_open_tsp_status(stores, D, cp_timeout)
        row["cpsat"] = {"km": round(day_km(r_cpsat, D), 3), "status": status}
        results[str(dd)] = row
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lines", nargs="+", default=ALL_LINES)
    parser.add_argument("--budget", type=float, default=600.0)
    parser.add_argument("--seeds", default="42,7,123,2026")
    parser.add_argument("--cp-timeout", type=float, default=30.0)
    args = parser.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    plan = load_plan()
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}
    for line_id in args.lines:
        print(f"=== A 矩阵: 线 {line_id} ===", flush=True)
        data = load_line(plan, line_id)
        D = np.load(ROOT / "output" / f"road_dist_{line_id}.npy")
        dates = list(data.dates)
        contracts = contract_of(data.days_orig, dates)
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))

        a_results = run_a_matrix(
            line_id, data, D, dates, contracts, k_c,
            budget_s=args.budget, seeds=seeds, cp_timeout=args.cp_timeout)

        b_results = run_b_matrix(line_id, data, D, dates, args.cp_timeout)

        line_out = {
            "schema": SCHEMA,
            "line": line_id,
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "budget_sec": args.budget,
            "seeds": seeds,
            "a_matrix": a_results,
            "b_matrix": b_results,
        }
        fp = out_dir / f"{line_id}.json"
        fp.write_text(json.dumps(line_out, ensure_ascii=False, indent=2, default=str),
                      encoding="utf-8")
        print(f"  落盘 {fp}", flush=True)
        all_results[line_id] = a_results

    summary = {}
    for line_id, a in all_results.items():
        for engine, r in a.items():
            summary.setdefault(engine, {})[line_id] = {
                "pipeline_km": r["pipeline_km"],
                "native_km": r["native_km"],
                "vs_base_pct": r["vs_base_pct"],
                "wall_sec": r["wall_sec"],
            }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"汇总已写 {out_dir / 'summary.json'}")


import datetime as dt

if __name__ == "__main__":
    main()
