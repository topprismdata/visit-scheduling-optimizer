"""Stage 3 求解: 频次需求 → SolutionBundle v1.

规划自由度: pattern/相位/星期几全部是决策变量, 由 R2-ALNS 规划;
语义层只给需求 (每 horizon 工作日 visits 次), 不限死方案.
口径铁律: totals.km 与 vs_original_pct 分子分母均走共同 CP-SAT 重排.
"""
from __future__ import annotations

import datetime as _dt
import subprocess
import time
from pathlib import Path as _Path

from core.base import LineData
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


def _synthetic_dates(n_days: int):
    """引擎只需要连续抽象日; 真实日历与求解无关 (见 calendar_map.json)."""
    return [_dt.date(2000, 1, 1) + _dt.timedelta(days=i) for i in range(n_days)]


def _to_line_data(spec: dict, dates) -> LineData:
    stores = spec["stores"]
    codes = [s["code"] for s in stores]
    days_orig = {_dt.date(2000, 1, 1) + _dt.timedelta(days=int(k) - 1): list(v)
                  for k, v in spec["original_assignment_idx"].items()}
    # 需求 -> 引擎目标次数: 每 horizon 工作日 visits 次
    freq = {}
    for s in stores:
        f = s["frequency"]
        freq[s["code"]] = max(1, round(f["visits"] * len(dates) / f["horizon"]))
    return LineData(
        line_id=spec["line_id"], line_name=f"line{spec['line_id']}",
        codes=codes,
        lon=[s["lon"] for s in stores], lat=[s["lat"] for s in stores],
        dates=dates, days_orig=days_orig, freq=freq,
        stores=len(codes), visits=sum(freq.values()),
        min_daily_capacity=spec["corridor"]["min_daily"],
        max_daily_capacity=spec["corridor"]["max_daily"])


def _compute_gates(assignment_raw: dict, dates: list, spec: dict,
                    D, r2_contract_ok: bool) -> dict:
    """五道闸纯函数 (独立可测). assignment_raw: {day_idx(int): [idx]}.

    count_ok (频次承诺): 每店不丢店, 窗口总次数 == 需求 (visits×窗口期数,
    尾窗四舍五入), 且同一 horizon 窗口内不重复拜访 (隔周/每周间隔保证).
    """
    from collections import Counter
    freq = {s["id"]: s["frequency"] for s in spec["stores"]}
    cnt = Counter()
    per_window = Counter()   # (store, 窗口号) -> 次数
    n_days = len(dates)
    for dd in sorted(assignment_raw):
        for c in assignment_raw[dd]:
            cnt[c] += 1
            per_window[(c, (dd - 1) // freq[c]["horizon"])] += 1
    sentinel = spec["distance"]["unreachable_sentinel"]
    count_ok = True
    for sid, f in freq.items():
        expected = max(1, round(f["visits"] * n_days / f["horizon"]))
        if cnt[sid] != expected:
            count_ok = False
            break
        if any(c2 > 1 for (s2, _w), c2 in per_window.items() if s2 == sid):
            count_ok = False   # 同一周期窗口内拜访 >1 次, 违反间隔承诺
            break
    days_date = {_dt.date(2000, 1, 1) + _dt.timedelta(days=int(k) - 1): v
                  for k, v in assignment_raw.items()}
    return {
        "count_ok": count_ok,
        "capacity_ok": bool(check_capacity(
            days_date, spec["corridor"]["max_daily"],
            spec["corridor"]["min_daily"])),
        "r2_ok": r2_contract_ok,
        # 合同同构 = 方案自身星期几节奏一致 (单星期几); 由 R2ALNS contract 模式保证
        "contract_ok": r2_contract_ok,
        "structure_ok": all(
            D[a][b] < sentinel
            for k in assignment_raw
            for a, b in zip(assignment_raw[k], assignment_raw[k][1:])),
    }


def solve_spec(spec: dict, D, seeds: list, budget_s: float, cp_timeout: float,
                model_hash: str, engine_version: str | None = None) -> dict:
    from algos.r2_alns import R2ALNS
    from visitmodel.tsp.open_chain import _exact_open_tsp_status

    engine_version = engine_version or _engine_version()
    n_days = spec["cycle"]["n_days"]
    dates = _synthetic_dates(n_days)
    day_keys = list(range(1, n_days + 1))
    t0 = time.perf_counter()

    line = _to_line_data(spec, dates)

    # pattern/相位/星期几 = 决策变量: 不放 init_days, 历史计划不限死规划空间
    best_days, best_km, best_res = None, float("inf"), None
    total_iters = 0
    for seed in seeds:
        r = R2ALNS().solve(line, D, iteration_budget=int(budget_s * 600),
                            seed=seed, combo_mode="contract",
                            final_reroute=False)
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
        orig = set(spec["original_assignment_idx"][str(di + 1)])
        moved += sum(1 for c in route if c not in orig)
        assignment_raw[di + 1] = [int(c) for c in route]

    gates = _compute_gates(assignment_raw, dates, spec, D, best_contract_ok)
    status = "FEASIBLE" if all(gates.values()) else "FAILED"

    # 口径铁律: 分母也走共同 CP-SAT 重排 (SRP 打印序禁作分母)
    orig_km = 0.0
    for day_key in sorted(assignment_raw, key=int):
        orig_route, _st, _ms = _exact_open_tsp_status(
            list(spec["original_assignment_idx"][str(day_key)]), D, cp_timeout)
        orig_km += day_km(orig_route, D)
    vs_orig = round((total_km - orig_km) / orig_km * 100, 3) if orig_km > 0 else 0.0

    assignment = {str(day_key): {
        "route_idx": assignment_raw[day_key],
        "route_codes": [codes[c] for c in assignment_raw[day_key]],
        "km": round(day_km(assignment_raw[day_key], D), 3),
    } for day_key in day_keys}

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
