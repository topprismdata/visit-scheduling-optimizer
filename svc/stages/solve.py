"""Stage 3 求解: ProblemSpec → SolutionBundle v1 (R2-ALNS + 五道闸 + 共同重排).

口径铁律: totals.km 与 vs_original_pct 的分子分母都走共同 CP-SAT 重排
(SRP 打印序禁作分母). 内部键域 = date 对象; JSON 输出才转 ISO 字符串.
"""
from __future__ import annotations

import datetime as _dt
import subprocess
import time
from pathlib import Path as _Path

from core.base import LineData
from core.contract import check_contract, contract_of
from core.metric import check_capacity, day_km
from svc.hashing import sha256_of


def _engine_version() -> str:
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True, timeout=5,
                               cwd=str(_Path(__file__).parent)).stdout.strip()
        return f"git:{head}" if head else "git:unknown"
    except Exception:
        return "git:unknown"


def _dates_from_spec(spec: dict):
    return [_dt.date.fromisoformat(s) for s in spec["calendar"]["dates"]]


def _to_line_data(spec: dict, dates) -> LineData:
    stores = spec["stores"]
    codes = [s["code"] for s in stores]
    days_orig = {_dt.date.fromisoformat(k): list(v)
                  for k, v in spec["original_assignment"].items()}
    freq = {s["code"]: s["contract"]["required_visits"] for s in stores}
    return LineData(
        line_id=spec["line_id"], line_name=f"line{spec['line_id']}",
        codes=codes,
        lon=[s["lon"] for s in stores], lat=[s["lat"] for s in stores],
        dates=dates, days_orig=days_orig, freq=freq,
        stores=len(codes), visits=sum(freq.values()),
        min_daily_capacity=spec["corridor"]["min_daily"],
        max_daily_capacity=spec["corridor"]["max_daily"])


def _compute_gates(assignment_raw: dict, dates, spec: dict, contracts,
                    D, r2_contract_ok: bool) -> dict:
    """五道闸纯函数 (独立可测). assignment_raw: {date_obj: [idx]}.

    count_ok 语义 (R2' 本体): 每店不分裂星期几且不丢店 — 换日后 f 由合同
    派生, 月访次与原计划不同是合法的; 精确节奏由 contract 闸负责.
    """
    from collections import Counter, defaultdict
    wd_of_store, cnt = defaultdict(set), Counter()
    for dd in dates:
        for c in assignment_raw[dd]:
            wd_of_store[c].add(dd.weekday())
            cnt[c] += 1
    sentinel = spec["distance"]["unreachable_sentinel"]
    all_stores = {s["id"] for s in spec["stores"]}
    count_ok = set(wd_of_store) == all_stores and \
        all(len(wds) == 1 for wds in wd_of_store.values())
    return {
        "count_ok": count_ok,
        "capacity_ok": bool(check_capacity(
            assignment_raw, spec["corridor"]["max_daily"],
            spec["corridor"]["min_daily"])),
        "r2_ok": r2_contract_ok,   # R2ALNS combo_mode=contract 的 AlgoResult.contract_ok
        "contract_ok": not check_contract(assignment_raw, contracts, dates),
        "structure_ok": all(
            D[a][b] < sentinel
            for dd in dates
            for a, b in zip(assignment_raw[dd], assignment_raw[dd][1:])),
    }


def solve_spec(spec: dict, D, seeds: list, budget_s: float, cp_timeout: float,
                model_hash: str, engine_version: str | None = None) -> dict:
    from algos.r2_alns import R2ALNS
    from visitmodel.tsp.open_chain import _exact_open_tsp_status

    engine_version = engine_version or _engine_version()
    dates = _dates_from_spec(spec)
    date_strs = spec["calendar"]["dates"]
    t0 = time.perf_counter()

    line = _to_line_data(spec, dates)
    contracts = contract_of(line.days_orig, dates)

    best_days, best_km, best_res = None, float("inf"), None
    total_iters = 0
    for seed in seeds:
        # init_days = 原计划: 保证访次守恒 (count 闸); None 会自建日历致 ±1 漂移
        r = R2ALNS().solve(line, D, iteration_budget=int(budget_s * 600),
                            seed=seed, combo_mode="contract",
                            final_reroute=False, init_days=line.days_orig)
        total_iters += int(r.metadata.get("iters", 0))
        km = sum(day_km(r.days[dd], D) for dd in dates)
        if km < best_km:
            best_days = {dd: list(r.days[dd]) for dd in dates}
            best_km, best_res = km, r
    best_contract_ok = bool(getattr(best_res, "contract_ok", True))

    # 共同 CP-SAT 重排 (协议 §5.3)
    codes = [s["code"] for s in spec["stores"]]
    assignment_raw, total_km, moved = {}, 0.0, 0
    for di, dd in enumerate(dates):
        route, _st, _ms = _exact_open_tsp_status(list(best_days[dd]), D, cp_timeout)
        total_km += day_km(route, D)
        orig = set(spec["original_assignment"][date_strs[di]])
        moved += sum(1 for c in route if c not in orig)
        assignment_raw[dd] = [int(c) for c in route]

    gates = _compute_gates(assignment_raw, dates, spec, contracts, D,
                            best_contract_ok)
    status = "FEASIBLE" if all(gates.values()) else "FAILED"

    # 口径铁律: 分母也走共同 CP-SAT 重排 (SRP 打印序禁作分母)
    orig_km = 0.0
    for di, dd in enumerate(dates):
        orig_route, _st, _ms = _exact_open_tsp_status(
            list(spec["original_assignment"][date_strs[di]]), D, cp_timeout)
        orig_km += day_km(orig_route, D)
    vs_orig = round((total_km - orig_km) / orig_km * 100, 3) if orig_km > 0 else 0.0

    assignment = {date_strs[di]: {
        "route_idx": assignment_raw[dd],
        "route_codes": [codes[c] for c in assignment_raw[dd]],
        "km": round(day_km(assignment_raw[dd], D), 3),
    } for di, dd in enumerate(dates)}

    bundle = {
        "schema": "visitflow/solution", "version": "1.0",
        "problem_hash": sha256_of(spec),
        "model_hash": model_hash,
        "status": status,
        "assignment": assignment,
        "totals": {"km": round(total_km, 3), "vs_original_pct": vs_orig,
                    "moved_stores": moved},
        "gates": gates,
        "runtime": {"engine": "r2_alns", "engine_version": engine_version,
                     "stage_versions": {}, "seeds": list(seeds),
                     "budget_s": budget_s, "iters": total_iters,
                     "wall_sec": round(time.perf_counter() - t0, 2)},
        "certificates": {"pool_lp": None, "certified_global_lb": None,
                          "global_gap_pct": None},
        "output_hash": "PENDING",
        "meta": {},
    }
    bundle["output_hash"] = sha256_of(
        {k: v for k, v in bundle.items() if k != "output_hash"})
    return bundle
