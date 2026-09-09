"""Stage 3 求解: 已验证 R2-ALNS 管线.

流程 = research_matrix v1 r2_alns 引擎路径, 不改核心逻辑:
  load_line → R2ALNS(init=原计划, combo=contract) → CP-SAT 精确重排 → 五道闸
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
            cwd=str(_Path(__file__).resolve().parent.parent),
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
    """已验证管线: 返回 {dates, codes, assignment, gates, km, ...}."""
    from data.loader import load_line, load_plan
    from algos.r2_alns import R2ALNS
    from visitmodel.tsp.open_chain import _exact_open_tsp_status

    engine_version = _engine_version()
    plan = load_plan()
    data = load_line(plan, line_id)
    D = _load_D(line_id)
    dates = sorted(data.days_orig.keys())
    contracts = contract_of(data.days_orig, dates)
    codes = data.codes

    # R2-ALNS (多 seed 取最优, init = 原计划)
    best_days, best_km, best_res = None, float("inf"), None
    total_iters = 0
    for seed in seeds:
        r = R2ALNS().solve(data, D, time_budget=budget_s, seed=seed,
                            combo_mode="contract", final_reroute=False,
                            init_days=data.days_orig)
        total_iters += int(r.metadata.get("iters", 0))
        km = sum(day_km(r.days[dd], D) for dd in dates)
        if km < best_km:
            best_days = {dd: list(r.days[dd]) for dd in dates}
            best_km, best_res = km, r
    r2_ok = bool(getattr(best_res, "contract_ok", True))

    # 共同 CP-SAT 精确重排
    rerouted = {}
    alns_km = 0.0
    for dd in dates:
        route, _st, _ms = _exact_open_tsp_status(list(best_days[dd]), D, cp_timeout)
        rerouted[dd] = route
        alns_km += day_km(route, D)

    # 原计划基线 (共同重排口径)
    orig_km = 0.0
    for dd in dates:
        orig_r, _st, _ms = _exact_open_tsp_status(
            list(data.days_orig[dd]), D, cp_timeout)
        orig_km += day_km(orig_r, D)

    # 最终择优: ALNS vs 原计划, 永不劣于人类
    final_days = best_days if alns_km <= orig_km + 0.1 else data.days_orig
    final_km = min(alns_km, orig_km)

    # 五道闸
    assignment_idx = {di + 1: [int(c) for c in final_days[dd]]
                       for di, dd in enumerate(dates)}
    days_date = {dd: assignment_idx[di + 1] for di, dd in enumerate(dates)}
    cnt = Counter()
    for v in assignment_idx.values():
        for c in v:
            cnt[c] += 1
    sentinel = 1e9
    gates = {
        "count_ok": all(cnt.get(c, 0) > 0 for c in range(len(data.codes))),
        "capacity_ok": bool(check_capacity(days_date, data.max_daily_capacity,
                                            data.min_daily_capacity)),
        "r2_ok": r2_ok,
        "contract_ok": not check_contract(days_date, contracts, dates),
        "structure_ok": all(
            D[a][b] < sentinel
            for v in assignment_idx.values()
            for a, b in zip(v, v[1:])),
    }
    status = "FEASIBLE" if all(gates.values()) else "FAILED"
    vs_orig = round((final_km - orig_km) / orig_km * 100, 3) if orig_km > 0 else 0.0

    return {
        "line": data, "dates": dates, "codes": codes, "D": D,
        "final_days": final_days, "rerouted": rerouted,
        "total_km": round(final_km, 3), "orig_km": round(orig_km, 3),
        "vs_original_pct": vs_orig, "alns_km": round(alns_km, 3),
        "gates": gates, "status": status,
        "engine_version": engine_version, "total_iters": total_iters,
        "contracts": contracts,
    }


def build_bundle(result: dict, line_id: str) -> dict:
    """打包 SolutionBundle JSON."""
    data = result["line"]
    codes = result["codes"]
    dates = result["dates"]
    D = result["D"]

    assignment = {}
    for di, dd in enumerate(dates):
        route = result["rerouted"][dd]
        assignment[str(dd)] = {
            "route_idx": [int(c) for c in route],
            "route_codes": [codes[c] for c in route],
            "km": round(day_km(route, D), 3),
        }

    return {
        "schema": "visitflow/solution", "version": "1.0",
        "status": result["status"],
        "assignment": assignment,
        "totals": {"km": result["total_km"],
                    "vs_original_pct": result["vs_original_pct"],
                    "moved_stores": 0},
        "gates": result["gates"],
        "runtime": {"engine": "r2_alns",
                     "engine_version": result["engine_version"],
                     "seeds": [], "budget_s": 0,
                     "iters": result["total_iters"], "wall_sec": 0},
        "certificates": {"pool_lp": None, "certified_global_lb": None,
                          "global_gap_pct": None},
        "meta": {"line_id": line_id},
    }
