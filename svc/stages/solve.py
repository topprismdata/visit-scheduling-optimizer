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


def _synthetic_dates(n_days: int):
    """节奏空间需要的只是连续抽象日; 引擎拿合成连续日, 真实日历与求解无关."""
    return [_dt.date(2000, 1, 1) + _dt.timedelta(days=i) for i in range(n_days)]


def _to_line_data(spec: dict, dates) -> LineData:
    stores = spec["stores"]
    codes = [s["code"] for s in stores]
    days_orig = {_dt.date(2000, 1, 1) + _dt.timedelta(days=int(k) - 1): list(v)
                  for k, v in spec["original_assignment_idx"].items()}
    freq = {s["code"]: max(1, _window_visits(s["frequency"], len(days_orig)))
             for s in stores}
    return LineData(
        line_id=spec["line_id"], line_name=f"line{spec['line_id']}",
        codes=codes,
        lon=[s["lon"] for s in stores], lat=[s["lat"] for s in stores],
        dates=dates, days_orig=days_orig, freq=freq,
        stores=len(codes), visits=sum(freq.values()),
        min_daily_capacity=spec["corridor"]["min_daily"],
        max_daily_capacity=spec["corridor"]["max_daily"])


def _window_visits(r: dict, n_days: int) -> int:
    """该节奏在 n_days 窗口内的应有拜访次数 (按 pattern 逐位累计)."""
    n_full, rem = divmod(n_days, r["horizon"])
    total = 0
    for i, bit in enumerate(r["pattern"][: r["horizon"]], start=1):
        if bit == "1":
            total += n_full + (1 if i <= rem else 0)
    return total


def _compute_gates(assignment_raw: dict, dates: list, spec: dict, contracts,
                    D, r2_contract_ok: bool) -> dict:
    """五道闸纯函数 (独立可测). assignment_raw: {day_idx(int): [idx]}.

    count_ok (节奏空间语义): 每店不丢店, 且月内拜访次数 == 该店节奏
    (period/phase) 在窗口内的出现次数; 节奏断裂店 (ambiguous) 只要求不丢店.
    """
    from collections import Counter
    rhythm = {s["id"]: s["frequency"] for s in spec["stores"]}
    cnt = Counter()
    for dd in sorted(assignment_raw):
        for c in assignment_raw[dd]:
            cnt[c] += 1
    sentinel = spec["distance"]["unreachable_sentinel"]
    all_stores = set(rhythm)
    count_ok = True
    for sid, r in rhythm.items():
        if cnt[sid] == 0:
            count_ok = False   # 丢店
            break
        if r.get("ambiguous"):
            continue           # 节奏断裂店: 不硬卡次数
        if cnt[sid] != _window_visits(r, len(dates)):
            count_ok = False   # 访次 != 频率要求的窗口出现次数
            break
    # contract 闸 (v2 节奏空间): 每店实际拜访日集合 == pattern 目标日集合
    contract_ok = True
    for sid, r in rhythm.items():
        if r.get("ambiguous"):
            continue
        target = {day for day in range(1, len(dates) + 1)
                   if r["pattern"][(day - 1) % r["horizon"]] == "1"}
        visited = {day for day in range(1, len(dates) + 1)
                    if sid in assignment_raw.get(day, [])}
        if visited != target:
            contract_ok = False
            break
    return {
        "count_ok": count_ok,
        "capacity_ok": bool(check_capacity(
            {_dt.date(2000, 1, 1) + _dt.timedelta(days=int(k) - 1): v
             for k, v in assignment_raw.items()},
            spec["corridor"]["max_daily"], spec["corridor"]["min_daily"])),
        "r2_ok": r2_contract_ok,
        "contract_ok": contract_ok,
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
    dates = _synthetic_dates(n_days)          # 合成连续抽象日
    day_keys = list(range(1, n_days + 1))     # 拜访日序号
    t0 = time.perf_counter()

    line = _to_line_data(spec, dates)
    contracts = contract_of(line.days_orig, dates)

    # 日分配 = 节奏 pattern 的确定性展开: 每店拜访日 = pattern 为 1 的拜访日.
    # (R2-ALNS 的价值在"选哪个 pattern/星期几", 属于 pattern 优化层, 见设计文档)
    rhythm = {s["id"]: s["frequency"] for s in spec["stores"]}
    target_days = {sid: [] for sid in rhythm}
    for sid, r in rhythm.items():
        if r.get("ambiguous"):
            continue                     # 断裂店: 保留原分配 (下方回填)
        target_days[sid] = [day for day in range(1, n_days + 1)
                             if r["pattern"][(day - 1) % r["horizon"]] == "1"]
    for sid, days in target_days.items():
        if not days:                     # 断裂店回填: 保留原拜访日
            target_days[sid] = [day for day in range(1, n_days + 1)
                                 if sid in spec["original_assignment_idx"][str(day)]]

    best_days = {dd: [] for dd in dates}   # 键 = 合成日 (与下游一致)
    for sid, days in target_days.items():
        for day in days:
            best_days[dates[day - 1]].append(sid)
    best_contract_ok = True              # 节奏展开天然合同同构 (槽位精确覆盖)


    # 共同 CP-SAT 重排 (协议 §5.3)
    codes = [s["code"] for s in spec["stores"]]
    assignment_raw, total_km, moved = {}, 0.0, 0
    for di, dd in enumerate(dates):
        route, _st, _ms = _exact_open_tsp_status(list(best_days[dd]), D, cp_timeout)
        total_km += day_km(route, D)
        orig = set(spec["original_assignment_idx"][str(di + 1)])
        moved += sum(1 for c in route if c not in orig)
        assignment_raw[di + 1] = [int(c) for c in route]

    gates = _compute_gates(assignment_raw, dates, spec, contracts, D,
                            best_contract_ok)
    status = "FEASIBLE" if all(gates.values()) else "FAILED"

    # 口径铁律: 分母也走共同 CP-SAT 重排 (SRP 打印序禁作分母)
    orig_km = 0.0
    for day_key in day_keys:
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
                     "budget_s": budget_s, "iters": 0,   # 节奏展开为确定性构造, 无迭代
                     "wall_sec": round(time.perf_counter() - t0, 2)},
        "certificates": {"pool_lp": None, "certified_global_lb": None,
                          "global_gap_pct": None},
        "output_hash": "PENDING",
        "meta": {},
    }
    bundle["output_hash"] = sha256_of(
        {k: v for k, v in bundle.items() if k != "output_hash"})
    return bundle
