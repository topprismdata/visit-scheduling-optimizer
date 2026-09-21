"""Stage 3 求解: ALNS 探索 → BP 精确优化 → CP-SAT 重排 → 五道闸.

分层定价 Tier 0 (ALNS 列注入) + 已验证 R2-ALNS 管线.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path as _Path

from core.metric import day_km
from orchestration.adapter import compile_line_spec
from orchestration.episode import emit_episode, episode_hash
from visit_math_api import SolverConfig as _SolverCfg, SolveResult as _SolveRes
from visitmodel import MathCompiler, MathValidator
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
    from visitmodel.tsp.open_chain import _exact_open_tsp_status

    engine_version = _engine_version()
    plan = load_plan()
    data = load_line(plan, line_id)
    D = _load_D(line_id)
    dates = sorted(data.days_orig.keys())

    # L1 零例外闸 + 语义规格: 合同/义务/走廊的所有权在这里 (Phase B/D1 迁移点)
    spec = compile_line_spec(data)
    inst = MathCompiler().compile(spec)
    code2idx = {c: i for i, c in enumerate(data.codes)}
    contracts = {}   # {store_idx: ("W",None) | ("B",phi)} — 由语义规格派生, 不再调 contract_of
    k_c = {}         # 义务 = |legal_dates|, 零例外闸下与原计划拜访次数逐店相等
    for c in spec.contracts:
        i = code2idx[c.customer_code]
        contracts[i] = ("W", None) if c.contract_type.value == "W" else ("B", c.phase)
        k_c[i] = c.obligation
    codes = data.codes
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

    # ALNS 方案转列 (注入 BP 池前过合同合法性 — ALNS 本体无合同耦合, 产出可能跨相位)
    legal_idx = {code2idx[c.customer_code]: frozenset(c.legal_dates) for c in spec.contracts}

    def _route_legal(dd, route):
        return all(dd in legal_idx.get(i, frozenset()) for i in route)

    def _days_legal(days):
        return all(_route_legal(dd, seq) for dd, seq in days.items())

    alns_cols = [(dd, list(best_days[dd]), day_km(best_days[dd], D))
                  for dd in dates if _route_legal(dd, best_days[dd])]

    # ===== Step B: BP 精确优化 (从 ALNS 合法列池出发) =====
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

    # ===== Step C: 择优 (合法性优先, 再比里程 — 违约解不得因更短而入选) =====
    bp_km = sum(day_km(bp_days[dd], D) for dd in dates) if bp_days else float("inf")
    alns_km_full = best_km_alns
    alns_ok = _days_legal(best_days)
    if bp_days is not None and (not alns_ok or bp_km <= best_km_alns):
        final_days, final_km_raw, src = bp_days, bp_km, "BP"
    else:
        final_days, final_km_raw, src = best_days, alns_km_full, "ALNS"

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

    # ===== Step E: 五道闸 (义务/走廊/合法日期由 L2 MathValidator 独立裁定 — L3 不自证) =====
    assignment_idx = {di + 1: [int(c) for c in rerouted[dd]]
                       for di, dd in enumerate(dates)}
    days_date = {dd: rerouted[dd] for dd in dates}
    report = MathValidator().validate(
        inst, {dd: tuple(codes[i] for i in rerouted[dd]) for dd in dates})
    viol_ids = {v.constraint_id for v in report.violations}
    sn = 1e9
    gates = {
        "count_ok": "C1_OBLIGATION" not in viol_ids,
        "capacity_ok": not any(v.startswith("C2_") for v in viol_ids),
        "r2_ok": "C3_ELIGIBILITY" not in viol_ids,
        "contract_ok": not ({"C1_OBLIGATION", "C3_ELIGIBILITY"} & viol_ids),
        "structure_ok": all(
            D[a][b] < sn
            for v in assignment_idx.values()
            for a, b in zip(v, v[1:])),
    }
    if not report.ok:
        gates["violations"] = [f"{v.constraint_id}: {v.detail}" for v in report.violations[:10]]
    status = "FEASIBLE" if all(gates.values()) else "FAILED"

    # ===== Layer Escalation (v0.2 §6.2): 违例沿 SourceMap 升级, L3 不自裁决 =====
    escalation_note = None
    if status != "FEASIBLE":
        from orchestration import Level, escalate
        esc = escalate(inst, _SolveRes(status=status, assignments={}, objective_vector=(),
                                       termination_reason="gates_failed"), report)
        escalation_note = {"level": esc.level.value, "action": esc.action,
                           "rules": list(esc.violated_rule_ids)}

    # ===== 决策留痕 (G4): 结果与产生它的规格/实例/参数绑定入账 =====
    solve_result = _SolveRes(
        status=status,
        assignments={dd: tuple(codes[i] for i in rerouted[dd]) for dd in dates},
        objective_vector=(round(total_km, 3),),
        termination_reason=f"src={src}",
        instance_hash=dict(inst.metadata).get("content_hash", ""),
    )
    episode = emit_episode(
        spec, inst, solve_result,
        _SolverCfg(backend="r2alns+bp+cpsat", time_limit_s=float(budget_s),
                   seed=int(seeds[0]) if seeds else 0),
        solver_version=engine_version,
    )
    wall = round(time.perf_counter() - t0, 1)

    return {
        "line_id": line_id, "total_km": round(total_km, 3),
        "orig_km": round(orig_km, 3), "vs_original_pct": vs_orig,
        "source": src, "status": status, "gates": gates,
        "episode_id": episode.episode_id, "episode_hash": episode_hash(episode),
        "escalation": escalation_note,
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
