"""L6 Projection → Solver 集成适配器 (集成契约 v1.0)。

将 svde PlannerStateProjection 的输出转换为 pvrp_cg 求解器的输入参数，
并可回转求解器输出为 PlanVersion + PlannedVisit[] + DecisionEvidence。

设计文档: svde/docs/L6_SOLVER_INTEGRATION_CONTRACT.md
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from pvrp_cg.planning import DecisionEvidence, PlanVersion, PlannedVisit
from pvrp_cg.policy import PlanningPolicy


# ============================================================================
# 适配结果 (frozen, 可审计)
# ============================================================================
@dataclass(frozen=True)
class ProjectionToSolverInput:
    projection_id: str
    target_rep_id: str
    n_customers: int
    travel_cost_matrix: tuple[tuple[float, ...], ...]
    service_times: tuple[float, ...]
    freq: tuple[int, ...]
    horizon_days: int
    locked_visits: tuple[tuple[int, int], ...]
    policy: PlanningPolicy


def adapt_projection(
    projection,
    freq: Sequence[int] | None = None,
    locked_visits: set[tuple[int, int]] | None = None,
    **policy_overrides,
) -> ProjectionToSolverInput:
    """PlannerStateProjection → ProjectionToSolverInput。

    Args:
        projection: L6 编译的投影。
        freq: 显式频次列表 (None = 从 candidate_pattern_space 推导)。
        locked_visits: 已锁定 (customer_idx, day_idx) 集合。
        **policy_overrides: 覆盖 PlanningPolicy 默认值。

    Returns:
        ProjectionToSolverInput (frozen)。
    """
    n = len(projection.nodes)
    T = [list(row) for row in projection.travel_cost_matrix]
    svc = list(projection.service_duration_vector)

    if freq is not None:
        derived_freq = list(freq)
    else:
        derived_freq = _derive_freq_from_patterns(projection.candidate_pattern_space, n)

    locked = tuple(sorted(locked_visits)) if locked_visits else ()

    policy_kwargs = {
        "n_customers": n,
        "frequency_rules": dict(enumerate(derived_freq)),
        "horizon_days": projection.time_slots_count if hasattr(projection, "time_slots_count") else 20,
        "max_visits_per_day": projection.daily_stop_capacity,
        "max_work_minutes_per_day": float(projection.daily_workload_budget_min),
    }
    policy_kwargs.update(policy_overrides)
    policy = PlanningPolicy(**policy_kwargs)

    lv: list[tuple[int, int]] = []
    for (cust_key, day_key), nodes in projection.locked_commitments_mask.items():
        cust_idx = _node_to_index(cust_key, n)
        if cust_idx is not None:
            for d in nodes:
                lv.append((cust_idx, d))

    return ProjectionToSolverInput(
        projection_id=projection.projection_id,
        target_rep_id=projection.target_rep_id,
        n_customers=n,
        travel_cost_matrix=tuple(tuple(row) for row in T),
        service_times=tuple(svc),
        freq=tuple(derived_freq),
        horizon_days=policy.horizon_days,
        locked_visits=lv,
        policy=policy,
    )


def _derive_freq_from_patterns(pattern_space, n: int) -> list[int]:
    """从 candidate_pattern_space 推导每个客户的目标月频次。"""
    result = [1] * n  # 最小值
    for key, patterns in pattern_space.items():
        idx = _node_to_index(key, n)
        if idx is not None and patterns:
            max_len = max(len(p) for p in patterns) if isinstance(patterns[0], list) else 1
            result[idx] = max(result[idx], max_len)
    return result


def _node_to_index(key, n: int):
    """从 node_matrix_index 键或整数推导索引。"""
    if isinstance(key, int) and 0 <= key < n:
        return key
    # 字符串形式 "C-XXX" 或数字字符串
    try:
        iv = int(str(key).lstrip("C").lstrip("0") or "0")
        if 0 <= iv < n:
            return iv
    except ValueError:
        pass
    return None


def adapt_solution(
    proj_input: ProjectionToSolverInput,
    assigns: list[set[int]] | None,
    total: float,
    status: str,
    stats: dict,
    representative_id: str | None = None,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """求解器输出 → PlanVersion + PlannedVisit[] + DecisionEvidence。"""
    nv = 1
    hs = date(2026, 6, 1)
    days = proj_input.horizon_days
    rep = representative_id or proj_input.target_rep_id
    plan_id = f"PLAN_{rep}_{hs.isoformat()}"
    pvid = f"{plan_id}@v{nv}"
    run_id = f"L6_{uuid.uuid4().hex[:10]}"

    plan = PlanVersion(
        plan_id=plan_id, version=nv,
        planning_horizon_start=hs,
        planning_horizon_end=date.fromordinal(hs.toordinal() + days - 1),
        representative_id=rep,
        policy_version=f"POLICY@{proj_input.projection_id}",
        solver_run_id=run_id, status="draft",
        created_at=datetime.now(),
    )

    visits = []
    vi = 0
    if assigns:
        for di, ds in enumerate(assigns):
            if not ds or di >= days:
                continue
            ad = date.fromordinal(hs.toordinal() + di)
            for seq, ci in enumerate(sorted(ds)):
                vi += 1
                visits.append(PlannedVisit(
                    plan_version_id=pvid, visit_id=f"V_{pvid}_{vi}",
                    customer_id=str(ci), planned_date=ad, sequence=seq + 1,
                    estimated_service_minutes=proj_input.service_times[ci] if ci < len(proj_input.service_times) else 0.0,
                ))

    evidence = DecisionEvidence(
        solver_run_id=run_id,
        policy_version=f"POLICY@{proj_input.projection_id}",
        input_version=proj_input.projection_id,
        optimality_scope="restricted_column_pool",
        status=status,
        n_columns=stats.get("n_columns", 0),
        n_constraints=nv * days,
    )
    return plan, visits, evidence