# -*- coding: utf-8 -*-
"""bp_grasp_validation — GRASP 定价接入后的全量 B&P 生产验证.

对照: research_matrix/v1 的 bp_solo 基线 (96046c5 时代, CP-SAT 兜底).
验收点: 09 线 CG 不再停滞后的改善; 其余线无回退; 诚实状态签发.
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
from algos.tsp_engine import _exact_open_tsp_status
from core.metric import day_km
from core.contract import contract_of
from data.loader import load_line, load_plan

SCHEMA = "bp_grasp_validation/v1"
OUT_DIR = ROOT / "output" / "bp_grasp_validation" / "v1"

# research_matrix/v1 bp_solo 基线 (总池 IP, 共同 CP-SAT 排序后)
BP_SOLO_BASELINE = {
    "02": 263.284, "03": 220.789, "04": 261.775, "05": 388.792, "06": 157.882,
    "07": 371.821, "08": 806.96, "09": 326.612, "10": 386.316, "11": 959.99,
}


def run_line(line_id, time_budget):
    plan = load_plan()
    data = load_line(plan, line_id)
    D = [[float(v) for v in row] for row in np.load(ROOT / "output" / f"road_dist_{line_id}.npy")]
    dates = sorted(data.days_orig.keys())
    contracts = contract_of(data.days_orig, dates)
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    bp = BranchAndPrice(dates, k_c, D, contracts, data.days_orig,
                        data.min_daily_capacity, data.max_daily_capacity,
                        time_budget=time_budget, max_nodes=20000,
                        exact_pricing=True, exact_tl=1.0, initial_days=None)
    t0 = time.perf_counter()
    res = bp.solve()
    wall = time.perf_counter() - t0
    # 与 research_matrix/v1 同口径: incumbent days 过共同 CP-SAT 排序后再评价
    days = res.get("incumbent_days") or (bp.incumbent[1] if bp.incumbent else None)
    km = None
    if days:
        km = 0.0
        for dd in dates:
            route, _st, _ms = _exact_open_tsp_status(list(days[dd]), D, 30)
            km += day_km(route, D)
        km = round(km, 3)
    base = BP_SOLO_BASELINE[line_id]
    return {
        "schema": SCHEMA, "line": line_id, "km": round(km, 3) if km else None,
        "baseline_bp_solo": base,
        "delta_pct": round((km - base) / base * 100, 3) if km else None,
        "status": res["status"], "wall_sec": round(wall, 1),
        "cg_iters": bp.cg_iters_total, "pool": len(bp.pool),
        "stalled": bp.pricing_stalled,
        "converge": f"{bp.converge_proven}/{bp.converge_attempts}",
        "warm_cols": bp.warm_start_columns,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", default="02,03,04,05,06,07,08,09,10,11")
    ap.add_argument("--time-budget", type=float, default=600.0)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for lid in args.lines.split(","):
        t0 = time.perf_counter()
        r = run_line(lid, args.time_budget)
        (OUT_DIR / f"{lid}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
        print(f"[{lid}] km={r['km']} base={r['baseline_bp_solo']} delta={r['delta_pct']}% "
              f"status={r['status']} cg={r['cg_iters']} pool={r['pool']} "
              f"stalled={r['stalled']} wall={r['wall_sec']}s", flush=True)


if __name__ == "__main__":
    main()
