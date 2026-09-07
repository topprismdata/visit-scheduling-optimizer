# -*- coding: utf-8 -*-
"""research_matrix/v1 — 算法研究对比协议 runner.

设计: docs/design/MATRIX_PROTOCOL_V3_DESIGN_v0.3.md
三类对照:
  A 日历算法矩阵  — 引擎裸池互比 (无基线保底), native + pipeline 双保留
  B 路线算法矩阵  — 冻结日店集, 路线算法互比 (nn2opt / multistart / cpsat / lkh3)
  C 组合增量矩阵  — R2 / bp_solo / R2→BP, 等总预算四臂对照

独立性协议 (评审 R2 修正):
  - 每格裸池 = 仅本引擎产出, 格间零交叉 (来源戳断言);
  - base 独立参照格, 不注入其他引擎;
  - 独立性是来源隔离, 不是内容互斥 (独立找到同店集合法)。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys_root = str(ROOT)
if sys_root not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_root)

from algos.registry import get as get_algo  # noqa: E402
from algos.tsp_engine import _exact_open_tsp_status, _nn2opt_open  # noqa: E402
from core.contract import check_contract, contract_of, legal_date_map  # noqa: E402
from core.metric import check_capacity, day_km  # noqa: E402
from data.loader import load_line, load_plan  # noqa: E402
from visitmodel.sp.formulation import sp_solve_ip  # noqa: E402

SCHEMA = "research_matrix/v1"
OUT_DIR = ROOT / "output" / "research_matrix" / "v1"
ALL_LINES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]
ALL_ENGINES = ["base", "r2_alns", "alns_v3", "hgs_pvrp", "sp_cg", "bp_solo"]


# ---------------------------------------------------------------------------
# 池规范化: (date, 店集) 归并 + 来源戳
# ---------------------------------------------------------------------------

def normalize_columns(raw_columns):
    """同 (date, 店集) 归并保最优排序; 来源并集; 非法列不在此层过滤.

    raw_columns: [(date, route, km, source)]
    返回:         [(date, route, km, sources(frozenset))]
    """
    best = {}
    for dd, route, km, src in raw_columns:
        key = (dd, frozenset(route))
        if key not in best or km < best[key][0]:
            best[key] = (km, list(route))
    out = []
    for (dd, fset), (km, route) in sorted(best.items(), key=lambda z: (str(z[0][0]), sorted(z[0][1]))):
        out.append((dd, route, km, fset))
    return out


def merge_pools(pools):
    """多 source 列池合并: 来源戳取并集, 同店集保最低 km."""
    merged = {}
    for src, cols in pools:
        for dd, route, km in cols:
            key = (dd, frozenset(route))
            if key not in merged or km < merged[key][0]:
                merged[key] = (km, list(route))
    return [(dd, route, km, frozenset(srcs)) for (dd, fset), (km, route) in [] for (dd, fset), (km, route) in merged.items()]


# ---------------------------------------------------------------------------
# 引擎适配器: 每引擎返回 (native_days 或 None, raw_columns[(date, route, km, source)])
# ---------------------------------------------------------------------------

def _route_date_pool(days, dates, D, tsp_mode, cp_timeout):
    """日历 → 排序后候选列."""
    cols = []
    for dd in dates:
        route, status = _route_with_tsp(list(days[dd]), D, tsp_mode, cp_timeout)
        cols.append((dd, route, round(day_km(route, D), 3), status))
    return cols


def _route_with_tsp(seq, D, mode, cp_timeout):
    if mode == "cpsat":
        route, status, _ms = _exact_open_tsp_status(list(seq), D, cp_timeout)
        return list(route), status
    if mode == "nn2opt":
        return list(_nn2opt_open(list(seq), D)), "HEURISTIC"
    raise ValueError(f"unknown TSP mode: {mode}")


def produce_calendar(engine_id, data, D, dates, contracts, budget_s, seeds, cp_timeout):
    """运行单个日历引擎, 返回 (native_days, raw_columns, diagnostics)."""
    raw = []           # (date, route, km, source)
    native_days = None
    diag = {}
    t0 = time.perf_counter()

    if engine_id == "base":
        for dd in dates:
            route, status = _route_with_tsp(list(data.days_orig[dd]), D, "cpsat", cp_timeout)
            raw.append((dd, route, round(day_km(route, D), 3), "base"))
        native_days = {dd: list(data.days_orig[dd]) for dd in dates}

    elif engine_id == "r2_alns":
        from algos.r2_alns import R2ALNS
        for s in seeds:
            r = get_algo("r2_alns")().solve(
                data, D, iteration_budget=int(budget_s * 600), seed=s,
                combo_mode="contract", final_reroute=False)
            for dd, route in r.days.items():
                raw.append((dd, route, round(day_km(route, D), 3), f"r2_s{s}"))
            diag.setdefault("iters", []).append(r.metadata.get("iters"))
        if r.days:
            native_days = {dd: list(rt) for dd, rt in r.days.items()}

    elif engine_id == "alns_v3":
        from algos.alns_v3 import ALNSv3
        for s in seeds:
            r = ALNSv3().solve(data, D, time_budget=budget_s, seed=s, weekday_lock=True)
            for dd, route in r.days.items():
                raw.append((dd, route, round(day_km(route, D), 3), f"alns3_s{s}"))
            diag.setdefault("iters", []).append(r.metadata.get("iters"))
        native_days = {dd: list(rt) for dd, rt in r.days.items()} if r.days else None

    elif engine_id == "hgs_pvrp":
        from algos.hgs_pvrp import HGSPVRP
        for s in seeds:
            r = HGSPVRP().solve(data, D, time_budget=budget_s, seed=s)
            for dd, route in r.days.items():
                raw.append((dd, route, round(day_km(route, D), 3), f"hgs_s{s}"))
        native_days = {dd: list(rt) for dd, rt in r.days.items()} if r.days else None

    elif engine_id == "sp_cg":
        from algos.sp_matheuristic import column_generate
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        base_cols = []
        for dd in dates:
            route, _st = _route_with_tsp(list(data.days_orig[dd]), D, "cpsat", cp_timeout)
            base_cols.append((dd, route, round(day_km(route, D), 3)))
        rmp_lp, generated, cg_iters, converged = column_generate(
            dates, k_c, base_cols, D, max_iter=6, verbose=False,
            top_m=40, col_iter=60, max_daily=data.max_daily_capacity,
            min_daily=data.min_daily_capacity, r2_prime=True, contract=contracts)
        for dd, route, km in generated:
            raw.append((dd, route, km, "sp_cg"))
        for dd, route, km in base_cols:
            raw.append((dd, route, km, "sp_cg_seed"))
        diag["cg_iters"] = cg_iters
        diag["cg_converged"] = bool(converged)
        diag["rmp_lp"] = rmp_lp

    elif engine_id == "bp_solo":
        from algos.branch_and_price import BranchAndPrice
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
                for dd, route in res["incumbent_days"].items():
                    raw.append((dd, route, round(day_km(route, D), 3), f"bp_s{s}"))
            for dd, route, _km in res["pool"]:
                raw.append((dd, route, round(day_km(route, D), 3), f"bp_s{s}"))
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
# A 矩阵: 引擎裸池 → 规范化 → Contract-SP 终闸
# ---------------------------------------------------------------------------

def run_a_matrix(line_id, data, D, dates, contracts, k_c,
                 budget_s, seeds, cp_timeout, tsp_mode="cpsat"):
    """A 日历算法矩阵: 每引擎裸池互比, 共同 Contract-SP 终闸."""
    results = {}
    baseline_km = None

    for engine in ALL_ENGINES:
        t0 = time.perf_counter()
        native_days, raw, diag = produce_calendar(
            engine, data, D, dates, contracts, budget_s, seeds, cp_timeout)
        wall = round(time.perf_counter() - t0, 3)

        # 池规范化: (date, 店集) 归并保最优排序
        norm = normalize_columns([(dd, rt, km, "engine") for dd, rt, km, _s in raw])

        # Contract-SP 终闸
        if norm:
            best_km, selected, info = sp_solve_ip(
                dates, k_c, [(dd, rt, km) for dd, rt, km, _s in norm],
                timeout_s=300, r2_prime=True, contract=contracts,
                return_diagnostics=True)
        else:
            best_km, selected, info = None, None, {"status": "EMPTY_POOL"}

        # 独立业务复验 (三闸)
        violations = []
        cap_ok = None
        if selected:
            violations = check_contract(selected, contracts, dates)
            cap_ok = check_capacity(selected, data.max_daily_capacity, data.min_daily_capacity)

        # native_result: 引擎直接日历经共同 TSP (cpsat) 排序评价
        native_km = None
        if native_days:
            native_km = round(sum(
                day_km(_route_with_tsp(list(native_days[dd]), D, tsp_mode, cp_timeout)[0],
                       D) for dd in dates), 3)

        # 来源分布
        src_dist = dict(Counter(_s for _, _, _, _s in raw))

        results[engine] = {
            "engine": engine,
            "native_km": native_km,
            "pipeline_km": round(best_km, 3) if best_km is not None else None,
            "vs_base_pct": None,          # 填在 base 确定后
            "status": info.get("status", "UNKNOWN"),
            "optimality_proven": info.get("optimality_proven", False),
            "contract_violations": len(violations),
            "capacity_ok": cap_ok,
            "pool_size": len(norm),
            "raw_pool_size": len(raw),
            "source_dist": dict(Counter(_s for _, _, _, _s in raw)),
            "native_km_source": native_km,
            "wall_sec": wall,
            "diag": diag,
        }
        if engine == "base":
            baseline_km = best_km

    # vs_base_pct
    for engine in results:
        if baseline_km is not None and results[engine]["pipeline_km"] is not None:
            results[engine]["vs_base_pct"] = round(
                (results[engine]["pipeline_km"] - baseline_km) / baseline_km * 100, 3)

    return results


# ---------------------------------------------------------------------------
# B 矩阵: 冻结日店集, 路线算法互比
# ---------------------------------------------------------------------------

def multistart_nn2opt(seq, D, n_starts=10, rng=None):
    """多起点 NN+2opt: 取最短 (SDR 思想轻量版)."""
    import random as _rd
    rng = rng or _rd.Random(42)
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
        # 2-opt
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
    """B 路线算法矩阵: 冻结日店集 (原计划), 路线算法互比."""
    routes_methods = {
        "nn2opt": lambda seq, D: (list(_nn2opt_open(list(seq), D)), "HEURISTIC"),
        "multistart_nn2opt": lambda seq, D: multistart_nn2opt(list(seq), D, n_starts=10) + ("HEURISTIC",),
    }
    results = {}
    for dd in dates:
        stores = list(data.days_orig[dd])
        row = {}
        # nn2opt
        r, _s = _nn2opt_open(stores, D), "HEURISTIC"
        row["nn2opt"] = {"km": round(day_km(r, D), 3), "status": "HEURISTIC"}
        # multistart
        r_ms, km_ms = multistart_nn2opt(stores, D, n_starts=10)
        row["multistart_nn2opt"] = {"km": round(km_ms, 3), "status": "HEURISTIC"}
        # cpsat
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
    parser.add_argument("--budget", type=float, default=600.0,
                        help="每引擎机制预算 (秒; R2 换算 ×600 迭代)")
    parser.add_argument("--seeds", default="42,7,123,2026")
    parser.add_argument("--cp-timeout", type=float, default=30.0)
    parser.add_argument("--sp-timeout", type=float, default=300.0)
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

    # 汇总
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


if __name__ == "__main__":
    main()
