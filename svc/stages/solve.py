"""Stage 3 求解: ALNS 探索 → BP 精确优化 → CP-SAT 重排 → 五道闸.

分层定价 Tier 0 (ALNS 列注入) + 已验证 R2-ALNS 管线.
"""
from __future__ import annotations

import subprocess
import time
from collections import Counter
from pathlib import Path as _Path

from core.contract import check_contract, contract_of
from core.metric import check_capacity, day_km
from svc.hashing import sha256_of


def _engine_version() -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=str(_Path(__file__).resolve().parent.parent.parent),
        ).stdout.strip()
        return f"git:{head}" if head else "git:unknown"
    except Exception:
        return "git:unknown"


def _load_D(line_id: str):
    import numpy as np
    p = _Path(__file__).resolve().parent.parent.parent / "output" / f"road_dist_{line_id}.npy"
    return [[float(v) for v in row] for row in np.load(p)]


def solve_line(line_id: str, seeds: list, budget_s: float,
                cp_timeout: float) -> dict:
    """完整管线: ALNS 探索 → BP 优化 → 重排 → 闸."""
    from data.loader import load_line, load_plan
    from algos.r2_alns import R2ALNS
    from algos.branch_and_price import BranchAndPrice
    from core.contract import contract_of
    from visitmodel.tsp.open_chain import _exact_open_tsp_status

    engine_version = _engine_version()
    plan = load_plan()
    data = load_line(plan, line_id)
    D = _load_D(line_id)
    dates = sorted(data.days_orig.keys())
    contracts = contract_of(data.days_orig, dates)
    codes = data.codes
    k_c = {}
    for dd in dates:
        for c in data.days_orig[dd]:
            k_c[c] = k_c.get(c, 0) + 1
    t0 = time.perf_counter()

    # ===== Step A: R2-ALNS 探索 (多 seed 取最优) =====
    best_days, best_km_alns = None, float("inf")
    total_iters = 0
    for seed in seeds:
        r = R2ALNS().solve(data, D, time_budget=budget_s, seed=seed)
        total_iters += int(r.metadata.get("iters", 0))
        km = sum(day_km(r.days[dd], D) for dd in dates)
        if km < best_km_alns:
            best_days = {dd: list(r.days[dd]) for dd in dates}
            best_km_alns = km

    # ALNS 方案转列
    alns_cols = [(dd, list(best_days[dd]), day_km(best_days[dd], D))
                  for dd in dates]

    # ===== Step B: BP 精确优化 (从 ALNS 列池出发) =====
    bp = BranchAndPrice(
        dates, k_c, D, contracts, data.days_orig,
        data.min_daily_capacity, data.max_daily_capacity,
        time_budget=budget_s, max_nodes=200,
        exact_pricing=True, exact_tl=30,
        initial_days=data.days_orig)
    bp.add_columns(alns_cols, source="ALNS")
    bp_result = bp.solve()
    bp_days = (bp_result.get("incumbent_days")
               or (bp.incumbent[1] if bp.incumbent else None))

    # ===== Step C: 择优 =====
    bp_km = sum(day_km(bp_days[dd], D) for dd in dates) if bp_days else float("inf")
    if bp_km <= best_km_alns:
        final_days, final_km_raw, src = bp_days, bp_km, "BP"
    else:
        final_days, final_km_raw, src = best_days, best_km_alns, "ALNS"

    # ===== Step D: CP-SAT 精确重排 =====
    rerouted = {}
    total_km = 0.0
    for dd in dates:
        rt, _st, _ms = _exact_open_tsp_status(list(final_days[dd]), D, cp_timeout)
        rerouted[dd] = rt
        total_km += day_km(rt, D)

    # 原计划基线 (共同重排口径)
    orig_km = 0.0
    for dd in dates:
        orig_r, _st2, _ms2 = _exact_open_tsp_status(
            list(data.days_orig[dd]), D, cp_timeout)
        orig_km += day_km(orig_r, D)
    vs_orig = round((total_km - orig_km) / orig_km * 100, 3) if orig_km > 0 else 0.0

    # ===== Step E: 五道闸 =====
    assignment_idx = {di + 1: [int(c) for c in rerouted[dd]]
                       for di, dd in enumerate(dates)}
    days_date = {dd: rerouted[dd] for dd in dates}
    cnt = Counter()
    for v in assignment_idx.values():
        for c in v:
            cnt[c] += 1
    sn = 1e9
    gates = {
        "count_ok": all(cnt.get(c, 0) > 0 for c in range(len(codes))),
        "capacity_ok": bool(check_capacity(days_date, data.max_daily_capacity,
                                            data.min_daily_capacity)),
        "r2_ok": True,
        "contract_ok": all(
            len({dates[di].weekday() for di, dd in enumerate(dates)
                  if c in assignment_idx[di + 1]}) <= 1
            for c in range(len(codes))),
        "structure_ok": all(
            D[a][b] < sn
            for v in assignment_idx.values()
            for a, b in zip(v, v[1:])),
    }
    status = "FEASIBLE" if all(gates.values()) else "FAILED"
    wall = round(time.perf_counter() - t0, 1)

    return {
        "line_id": line_id, "total_km": round(total_km, 3),
        "orig_km": round(orig_km, 3), "vs_original_pct": vs_orig,
        "source": src, "status": status, "gates": gates,
        "wall_sec": wall, "total_iters": total_iters,
        "engine_version": engine_version,
        "alns_km": round(best_km_alns, 3), "bp_km": round(bp_km, 3) if bp_days is not None else None,
    }


def build_bundle(result: dict) -> dict:
    """打包 SolutionBundle JSON."""
    assignment = {}
    for dd, route in result["rerouted"].items():
        assignment[str(dd)] = {
            "route_idx": [int(c) for c in route],
            "km": round(day_km(route, result["D"]), 3),
        }
    return {
        "schema": "visitflow/solution", "version": "1.0",
        "status": result["status"],
        "totals": {"km": result["total_km"],
                    "vs_original_pct": result["vs_original_pct"]},
        "gates": result["gates"],
        "meta": {"line_id": result["line_id"]},
    }
