# -*- coding: utf-8 -*-
"""Run the calendar/TSP matrix with Contract-SP as the hard gate.

Calendar modes:
  - alns_v3: path-feedback ALNS candidate schedules;
  - hgs_pvrp: path-feedback HGS candidate schedules;
  - sp_cg: contract-native column-generation candidate pool;
  - bp: contract-native branch-and-price candidate pool;
  - r2_alns: contract-native R2' multi-seed candidate columns.

TSP modes are:
  - nn2opt: NN + 2-opt;
  - lkh3: LKH-3 ATSP open path;
  - cpsat: CP-SAT exact open path.

Every cell is solved by the same Contract-SP integer master
(r2_prime=True, contract=contracts). Calendar generators provide candidate
columns; Contract-SP is the only accepted final decision. Seeded modes use
the union of per-seed columns; deterministic modes run once. The selected TSP
mode controls all columns handed to Contract-SP.

Usage:
  .venv/bin/python experiments/run_contract_matrix.py --lines 09
  .venv/bin/python experiments/run_contract_matrix.py --lines 02 03 ... 11
  .venv/bin/python experiments/run_contract_matrix.py --merge
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from data.loader import load_line, load_plan  # noqa: E402
from algos.alns_v3 import ALNSv3  # noqa: E402
from algos.hgs_pvrp import HGSPVRP  # noqa: E402
from algos.lkh_engine import LKH_BIN, lkh_open_path  # noqa: E402
from algos.branch_and_price import BranchAndPrice  # noqa: E402
from algos.r2_alns import R2ALNS  # noqa: E402
from algos.sp_matheuristic import (  # noqa: E402
    _contract_pool_filter, column_generate,
    dedupe_pool,
)
from algos.tsp_engine import _exact_open_tsp_status, _nn2opt_open  # noqa: E402
from core.contract import check_contract, contract_of, legal_date_map  # noqa: E402
from core.metric import check_capacity, day_km  # noqa: E402
from visitmodel.sp.formulation import sp_solve_ip  # noqa: E402

ALL_LINES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]
ALLOC_MODES = ("alns_v3", "hgs_pvrp", "sp_cg", "bp", "r2_alns")
TSP_MODES = ("nn2opt", "lkh3", "cpsat")
MATRIX_DIR = ROOT / "output" / "contract_matrix_4x3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lines", nargs="+", choices=ALL_LINES, default=None)
    parser.add_argument("--alloc-budget", type=float, default=60.0)
    parser.add_argument("--sp-timeout", type=float, default=300.0)
    parser.add_argument("--cp-timeout", type=float, default=30.0)
    parser.add_argument("--lkh-timeout", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", default=None,
                        help="逗号分隔多 seed (覆盖 --seed): 池 = 各 seed 生成列并集")
    parser.add_argument("--cells", nargs="+", default=None,
                        help="cell names such as alns_v3+nn2opt")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--merge", action="store_true")
    return parser.parse_args()


def cell_name(alloc: str, tsp: str) -> str:
    return f"{alloc}+{tsp}"


def route_with_tsp(seq: list[int], D: np.ndarray, mode: str, args: argparse.Namespace):
    """Return (route, status) and leave timing to the caller."""
    if mode == "nn2opt":
        return list(_nn2opt_open(list(seq), D)), "HEURISTIC"
    if mode == "lkh3":
        if shutil.which(LKH_BIN) is None and not os.path.exists(LKH_BIN):
            return list(_nn2opt_open(list(seq), D)), "LKH_FALLBACK_NN2OPT"
        return list(lkh_open_path(list(seq), D, runs=10, max_trials=5000,
                                  cand=20, time_limit=args.lkh_timeout)), "HEURISTIC"
    if mode == "cpsat":
        route, status, _elapsed_ms = _exact_open_tsp_status(
            list(seq), D, time_limit=args.cp_timeout
        )
        return list(route), status
    raise ValueError(f"unknown TSP mode: {mode}")


def route_schedule(schedule: dict, dates: list, D: np.ndarray, mode: str,
                   args: argparse.Namespace):
    routed = {}
    status_counts = Counter()
    t0 = time.perf_counter()
    for dd in dates:
        route, status = route_with_tsp(list(schedule[dd]), D, mode, args)
        routed[dd] = route
        status_counts[status] += 1
    return routed, status_counts, time.perf_counter() - t0


def base_schedule(data, D: np.ndarray, tsp_mode: str, args: argparse.Namespace):
    return schedule_pool(data.days_orig, list(data.dates), D, tsp_mode, args)


def schedule_pool(schedule: dict, dates: list, D: np.ndarray, tsp_mode: str,
                  args: argparse.Namespace):
    routed, statuses, elapsed = route_schedule(schedule, dates, D, tsp_mode, args)
    return [(dd, routed[dd], round(day_km(routed[dd], D), 3)) for dd in dates], statuses, elapsed


def allocation_schedule(mode: str, data, D: np.ndarray, dates: list,
                        contracts: dict, tsp_mode: str, args: argparse.Namespace,
                        seed: int):
    """Build candidate columns for one calendar mode + one seed + one TSP mode."""
    t0 = time.perf_counter()
    metadata = {"mode": mode, "tsp_mode": tsp_mode, "seed": seed}
    if mode == "alns_v3":
        result = ALNSv3().solve(
            data, D, time_budget=args.alloc_budget, seed=seed,
        )
        raw = result.days
        metadata.update(result.metadata or {})
        metadata["raw_km_nn_internal"] = float(result.km)
        pool, statuses, tsp_sec = schedule_pool(raw, dates, D, tsp_mode, args)
        metadata["generator_sec"] = time.perf_counter() - t0
        return pool, statuses, tsp_sec, metadata

    if mode == "hgs_pvrp":
        result = HGSPVRP().solve(
            data, D, time_budget=args.alloc_budget, seed=seed,
        )
        raw = result.days
        metadata.update(result.metadata or {})
        metadata["raw_km_nn_internal"] = float(result.km)
        pool, statuses, tsp_sec = schedule_pool(raw, dates, D, tsp_mode, args)
        metadata["generator_sec"] = time.perf_counter() - t0
        return pool, statuses, tsp_sec, metadata

    if mode == "sp_cg":
        # Start from the original assignment, routed by the selected TSP.
        base_pool, statuses, tsp_sec = base_schedule(data, D, tsp_mode, args)
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        max_daily = data.max_daily_capacity
        min_daily = data.min_daily_capacity
        rmp_lp, generated, cg_iters, converged = column_generate(
            dates,
            k_c,
            base_pool,
            D,
            max_iter=6,
            verbose=False,
            top_m=40,
            col_iter=60,
            max_daily=max_daily,
            min_daily=min_daily,
            r2_prime=True,
            contract=contracts,
        )
        # Pricing uses insertion order internally. Re-route every generated
        # column so the TSP factor remains the cost actually passed to SP.
        rerouted = []
        reroute_t0 = time.perf_counter()
        for dd, route, _km in generated:
            new_route, status = route_with_tsp(list(route), D, tsp_mode, args)
            rerouted.append((dd, new_route, round(day_km(new_route, D), 3)))
            statuses[status] += 1
        tsp_sec += time.perf_counter() - reroute_t0
        metadata.update({
            "cg_iters": cg_iters,
            "cg_converged": bool(converged),
            "cg_rmp_lp": rmp_lp,
            "generator_sec": time.perf_counter() - t0,
        })
        return rerouted, statuses, tsp_sec, metadata

    if mode == "bp":
        # Branch-and-Price: 合同原生树搜索 (树内插入序代价, raw 口径).
        # B&P 自带可行 incumbent (原计划保底), 列池含树内全部生成列;
        # TSP 因子与其它日历模式同口径: 产出列重排计价后交 Contract-SP 终闸.
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        statuses = Counter()
        engine = BranchAndPrice(
            dates, k_c, D, contracts, data.days_orig,
            data.min_daily_capacity, data.max_daily_capacity,
            time_budget=args.alloc_budget, max_nodes=20000,
            exact_pricing=True, exact_tl=1.0,
        )
        res_bp = engine.solve()
        rerouted = []
        tsp_sec = 0.0
        reroute_t0 = time.perf_counter()
        for dd, route, _km in res_bp["pool"]:
            new_route, status = route_with_tsp(list(route), D, tsp_mode, args)
            rerouted.append((dd, new_route, round(day_km(new_route, D), 3)))
            statuses[status] += 1
        tsp_sec += time.perf_counter() - reroute_t0
        metadata.update({
            "bp_status": res_bp["status"],
            "bp_incumbent_km_internal": res_bp["incumbent_km"],
            "bp_root_lb": res_bp["root_lb"],
            "bp_nodes": res_bp["nodes"],
            "bp_cg_iters": res_bp["cg_iters"],
            "bp_converge_attempts": res_bp["converge_attempts"],
            "bp_converge_proven": res_bp["converge_proven"],
            "bp_propagate_prunes": res_bp["propagate_prunes"],
            "generator_sec": time.perf_counter() - t0,
        })
        return rerouted, statuses, tsp_sec, metadata
    if mode == "r2_alns":
        # 合同化 R2'-ALNS: 终局日程按 TSP 模式重排入池 (与台账 _columns 同构).
        result = R2ALNS().solve(
            data, D, time_budget=args.alloc_budget, seed=seed,
            combo_mode="contract",
        )
        metadata.update({k: v for k, v in (result.metadata or {}).items() if k != "_columns"})
        metadata["raw_km_internal"] = float(result.km)
        pool, statuses, tsp_sec = schedule_pool(result.days, dates, D, tsp_mode, args)
        metadata["generator_sec"] = time.perf_counter() - t0
        return pool, statuses, tsp_sec, metadata
    raise ValueError(f"unknown allocation mode: {mode}")

def run_cell(line_id: str, alloc_mode: str, tsp_mode: str,
             args: argparse.Namespace, plan: dict):
    data = load_line(plan, line_id)
    D = np.load(ROOT / f"output/road_dist_{line_id}.npy")
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    legal = legal_date_map(contracts, dates)
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    max_daily = data.max_daily_capacity
    min_daily = data.min_daily_capacity

    t0 = time.perf_counter()
    base_pool, base_status, base_tsp_sec = base_schedule(data, D, tsp_mode, args)
    seeds = ([int(s) for s in str(args.seeds).split(",") if s.strip()]
             if getattr(args, "seeds", None) else [args.seed])
    if alloc_mode in ("sp_cg", "bp"):
        seeds = seeds[:1]   # 确定性引擎: 多 seed 同解, 只跑一次
    generated_pool, gen_status, gen_tsp_sec = [], Counter(), 0.0
    seed_meta = []
    for sd in seeds:
        pool_s, status_s, tsp_s, meta_s = allocation_schedule(
            alloc_mode, data, D, dates, contracts, tsp_mode, args, sd
        )
        generated_pool += pool_s
        gen_status.update(status_s)
        gen_tsp_sec += tsp_s
        seed_meta.append({k: meta_s[k] for k in meta_s if k not in ("mode", "tsp_mode")})
    gen_meta = {"mode": alloc_mode, "tsp_mode": tsp_mode, "seeds": seeds, "per_seed": seed_meta}
    raw_pool = base_pool + generated_pool
    pool_after_capacity = dedupe_pool(
        raw_pool, max_daily=max_daily, min_daily=min_daily, top_k=8
    )
    contract_pool, dropped = _contract_pool_filter(pool_after_capacity, legal)
    # Contract-SP is the common, hard final gate for every cell.
    sp_t0 = time.perf_counter()
    best_km, selected = sp_solve_ip(
        dates,
        k_c,
        contract_pool,
        timeout_s=args.sp_timeout,
        r2_prime=True,
        contract=contracts,
    )
    sp_sec = time.perf_counter() - sp_t0

    if selected:
        contract_viol = check_contract(selected, contracts, dates)
        cap_ok = check_capacity(selected, max_daily, min_daily)
        selected_km = sum(day_km(selected[dd], D) for dd in dates)
        selected_counts = [len(selected[dd]) for dd in dates]
        result_status = "OK"
    else:
        contract_viol = ["SP_INFEASIBLE"]
        cap_ok = False
        selected_km = None
        selected_counts = []
        result_status = "INFEASIBLE"

    result = {
        "schema": "contract_matrix_cell/v1",
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "line": line_id,
        "allocation_mode": alloc_mode,
        "tsp_mode": tsp_mode,
        "cell": cell_name(alloc_mode, tsp_mode),
        "contract_sp": {
            "required": True,
            "r2_prime": True,
            "solver": "sp_solve_ip",
            "status": result_status,
        },
        "budgets": {
            "allocation_sec": args.alloc_budget,
            "sp_timeout_sec": args.sp_timeout,
            "cp_timeout_sec": args.cp_timeout,
            "lkh_timeout_sec": args.lkh_timeout,
            "seed": args.seed,
        },
        "baseline_a_km": None,
        "sp_km": round(float(best_km), 3) if best_km is not None else None,
        "sp_km_recomputed": round(float(selected_km), 3) if selected_km is not None else None,
        "delta_vs_baseline_pct": None,
        "capacity_ok": bool(cap_ok),
        "contract_violations": len(contract_viol),
        "contract_violation_ids": contract_viol[:20],
        "day_count_range": [min(selected_counts), max(selected_counts)] if selected_counts else None,
        "raw_pool_count": len(raw_pool),
        "capacity_pool_count": len(pool_after_capacity),
        "contract_pool_count": len(contract_pool),
        "contract_pool_dropped": int(dropped),
        "tsp": {
            "base_status_counts": dict(base_status),
            "generated_status_counts": dict(gen_status),
            "base_sec": round(base_tsp_sec, 6),
            "generated_sec": round(gen_tsp_sec, 6),
            "total_route_sec": round(base_tsp_sec + gen_tsp_sec, 6),
        },
        "allocation": gen_meta,
        "elapsed_sec": None,
    }
    baseline_path = ROOT / "output" / "cpsat_plan_baselines.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))[line_id]
    result["baseline_a_km"] = float(baseline)
    if best_km is not None:
        result["delta_vs_baseline_pct"] = round((best_km - baseline) / baseline * 100, 3)
    result["elapsed_sec"] = round(time.perf_counter() - t0, 3)

    out_dir = MATRIX_DIR / alloc_mode / tsp_mode
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{line_id}.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def merge_outputs():
    cells = {}
    for alloc in ALLOC_MODES:
        for tsp in TSP_MODES:
            for path in sorted((MATRIX_DIR / alloc / tsp).glob("??.json")):
                result = json.loads(path.read_text(encoding="utf-8"))
                cells.setdefault(result["cell"], {})[result["line"]] = result
    (MATRIX_DIR / "cells.json").write_text(
        json.dumps(cells, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = []
    for cell in sorted(cells):
        rows = list(cells[cell].values())
        ok_rows = [r for r in rows if r["sp_km"] is not None]
        summary.append({
            "cell": cell,
            "lines": len(rows),
            "ok": len(ok_rows),
            "total_sp_km": round(sum(r["sp_km"] for r in ok_rows), 3),
            "total_baseline_a_km": round(sum(r["baseline_a_km"] for r in ok_rows), 3),
            "delta_pct": round(
                (sum(r["sp_km"] for r in ok_rows) - sum(r["baseline_a_km"] for r in ok_rows))
                / sum(r["baseline_a_km"] for r in ok_rows) * 100, 3
            ) if ok_rows else None,
            "mean_elapsed_sec": round(sum(r["elapsed_sec"] for r in rows) / len(rows), 3) if rows else None,
            "mean_tsp_sec": round(sum(r["tsp"]["total_route_sec"] for r in rows) / len(rows), 3) if rows else None,
            "mean_contract_pool_dropped": round(sum(r["contract_pool_dropped"] for r in rows) / len(rows), 3) if rows else None,
            "contract_violations": sum(r["contract_violations"] for r in rows),
            "capacity_failures": sum(not r["capacity_ok"] for r in rows),
        })
    (MATRIX_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    args = parse_args()
    MATRIX_DIR.mkdir(parents=True, exist_ok=True)
    if args.merge:
        for row in merge_outputs():
            print(json.dumps(row, ensure_ascii=False))
        return 0

    selected_cells = set(args.cells or [cell_name(a, t) for a in ALLOC_MODES for t in TSP_MODES])
    expected = {cell_name(a, t) for a in ALLOC_MODES for t in TSP_MODES}
    unknown = selected_cells - expected
    if unknown:
        raise SystemExit(f"unknown cells: {sorted(unknown)}")
    plan = load_plan()
    lines = args.lines or ALL_LINES
    for alloc in ALLOC_MODES:
        for tsp in TSP_MODES:
            if cell_name(alloc, tsp) not in selected_cells:
                continue
            for line_id in lines:
                out_file = MATRIX_DIR / alloc / tsp / f"{line_id}.json"
                if out_file.exists() and not args.force:
                    print(f"SKIP {cell_name(alloc, tsp)} line={line_id} existing={out_file}", flush=True)
                    continue
                result = run_cell(line_id, alloc, tsp, args, plan)
                print(
                    f"{result['cell']} line={line_id} "
                    f"sp={result['sp_km']} baseline={result['baseline_a_km']} "
                    f"delta={result['delta_vs_baseline_pct']}% "
                    f"pool={result['contract_pool_count']} dropped={result['contract_pool_dropped']} "
                    f"contract_viol={result['contract_violations']} "
                    f"elapsed={result['elapsed_sec']}s",
                    flush=True,
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
