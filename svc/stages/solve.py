"""Stage 3 求解: 频次需求 → SolutionBundle v1.

流程:
  Step A  频次需求 -> 初始日分配 (负载均衡铺排, 确定性, 保证走廊可行)
  Step B  R2-ALNS 以初始排期为起点做全局优化 (次数守恒的合同同构移动:
          pattern/相位/星期几 = 决策变量, 历史计划不限死规划空间)
  Step C  共同 CP-SAT 重排 (协议 §5.3) + 五道闸

口径铁律: totals.km 与 vs_original_pct 的分子分母均走共同 CP-SAT 重排.
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


def _window_visits(freq: dict, n_days: int) -> int:
    """该频次在 n_days 窗口内的总拜访次数 (visits = 每周期次数)."""
    return max(1, round(freq["visits"] * n_days / freq["horizon"]))


def _to_line_data(spec: dict, dates, init_days_idx: dict,
                   target: dict) -> LineData:
    """LineData 的 days_orig/freq 均以初始铺排为准 (ALNS 次数守恒的锚)."""
    stores = spec["stores"]
    codes = [s["code"] for s in stores]
    days_orig = {_dt.date(2000, 1, 1) + _dt.timedelta(days=int(k) - 1): list(v)
                  for k, v in init_days_idx.items()}
    freq = {s["code"]: len(target[s["id"]]) for s in stores}
    return LineData(
        line_id=spec["line_id"], line_name=f"line{spec['line_id']}",
        codes=codes,
        lon=[s["lon"] for s in stores], lat=[s["lat"] for s in stores],
        dates=dates, days_orig=days_orig, freq=freq,
        stores=len(codes), visits=sum(freq.values()),
        min_daily_capacity=spec["corridor"]["min_daily"],
        max_daily_capacity=spec["corridor"]["max_daily"])


def _spread(spec: dict, n_days: int):
    """Step A: 频次需求 -> 初始日分配 (负载均衡贪心, 确定性).

    每店: 目标次数 = window_visits(频次); 相位候选 = 周期内每个可能的
    起始位; 选"窗口内最大日负载"最小的相位. 返回 {store_id: [day,...]}.
    """
    load = {di: 0 for di in range(1, n_days + 1)}
    order = sorted(spec["stores"], key=lambda s: (-s["frequency"]["visits"],
                                                   s["id"]))
    target = {}
    for s in order:
        sid = s["id"]
        f = s["frequency"]
        visits_target = _window_visits(f, n_days)
        if f.get("ambiguous"):
            # 节奏断裂店: 保留原拜访日 (只承诺不丢店)
            days = [day for day in range(1, n_days + 1)
                     if sid in spec["original_assignment_idx"].get(str(day), [])]
            target[sid] = days
            for d in days:
                load[d] += 1
            continue
        cand = []
        for phase in range(1, n_days + 1):
            days = list(range(phase, n_days + 1, f["horizon"]))
            if len(days) != visits_target:
                continue
            mx = max(load[d] for d in days)
            cand.append((mx, sum(load[d] for d in days), days))
        if not cand:
            days = [min(n_days, int(i * n_days / visits_target) + 1)
                     for i in range(visits_target)]
            cand = [(max(load[d] for d in days),
                     sum(load[d] for d in days), days)]
        _mx, _sm, days = min(cand)
        target[sid] = days
        for d in days:
            load[d] += 1
    return target, load


def _compute_gates(assignment_raw: dict, n_days: int, spec: dict,
                    D, r2_contract_ok: bool) -> dict:
    """五道闸纯函数 (独立可测). assignment_raw: {day_idx(int): [idx]}.

    count_ok (频次承诺): 每店不丢店, 窗口内总次数 == 频次要求
    (visits × 窗口期数, 尾窗四舍五入), 且同一 horizon 窗口内不重复拜访.
    """
    from collections import Counter
    freq = {s["id"]: s["frequency"] for s in spec["stores"]}
    cnt = Counter()
    per_window = Counter()
    for dd in sorted(assignment_raw):
        for c in assignment_raw[dd]:
            cnt[c] += 1
            f = freq[c]
            per_window[(c, (dd - 1) // f["horizon"])] += 1
    sentinel = spec["distance"]["unreachable_sentinel"]
    count_ok = True
    for sid, f in freq.items():
        expected = max(1, round(f["visits"] * n_days / f["horizon"]))
        if cnt[sid] != expected:
            count_ok = False   # 访次 != 频次要求
            break
        if any(c2 > 1 for (s2, _w), c2 in per_window.items() if s2 == sid):
            count_ok = False   # 同一周期窗口内 >1 次, 违反间隔承诺
            break
    days_date = {_dt.date(2000, 1, 1) + _dt.timedelta(days=int(k) - 1): v
                  for k, v in assignment_raw.items()}
    return {
        "count_ok": count_ok,
        "capacity_ok": bool(check_capacity(
            days_date, spec["corridor"]["max_daily"],
            spec["corridor"]["min_daily"])),
        "r2_ok": r2_contract_ok,   # R2ALNS combo_mode=contract 的 AlgoResult.contract_ok
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

    # Step A: 频次 -> 初始铺排
    target, load = _spread(spec, n_days)
    init_days_idx = {di: target[di] for di in range(1, n_days + 1)}
    line = _to_line_data(spec, dates, init_days_idx, target)
    init_days = {_dt.date(2000, 1, 1) + _dt.timedelta(days=int(k) - 1): list(v)
                  for k, v in init_days_idx.items()}

    # Step B: R2-ALNS 规划 (pattern/相位/星期几 = 决策变量; 次数守恒)
    best_days, best_km, best_res = None, float("inf"), None
    total_iters = 0
    for seed in seeds:
        r = R2ALNS().solve(line, D, iteration_budget=int(budget_s * 600),
                            seed=seed, combo_mode="contract",
                            final_reroute=False, init_days=init_days)
        total_iters += int(r.metadata.get("iters", 0))
        km = sum(day_km(r.days[dd], D) for dd in dates)
        if km < best_km:
            best_days = {dd: list(r.days[dd]) for dd in dates}
            best_km, best_res = km, r
    best_contract_ok = bool(getattr(best_res, "contract_ok", True))

    # Step C: 共同 CP-SAT 重排 (协议 §5.3)
    codes = [s["code"] for s in spec["stores"]]
    assignment_raw, total_km, moved = {}, 0.0, 0
    for di, dd in enumerate(dates):
        route, _st, _ms = _exact_open_tsp_status(list(best_days[dd]), D, cp_timeout)
        total_km += day_km(route, D)
        orig = set(spec["original_assignment_idx"].get(str(di + 1), []))
        moved += sum(1 for c in route if c not in orig)
        assignment_raw[di + 1] = [int(c) for c in route]

    gates = _compute_gates(assignment_raw, n_days, spec, D, best_contract_ok)
    status = "FEASIBLE" if all(gates.values()) else "FAILED"

    # 口径铁律: 分母也走共同 CP-SAT 重排 (SRP 打印序禁作分母)
    orig_km = 0.0
    for day_key in day_keys:
        orig = spec["original_assignment_idx"].get(str(day_key), [])
        orig_route, _st, _ms = _exact_open_tsp_status(list(orig), D, cp_timeout)
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
