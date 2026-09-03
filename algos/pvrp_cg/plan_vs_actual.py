"""Plan vs Actual 指标计算 (Phase 1, Task 7) — 基于数据契约生成可审计汇报指标。

所有指标至少来源可追溯：输入、策略、求解版本三重锚定。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from .planning import ActualVisit, DecisionEvidence, PlanVersion, PlannedVisit


@dataclass(frozen=True)
class PlanVsActualMetrics:
    """Plan vs Actual 对比指标的单一输出结构 (frozen)。

    核心指标:
        - coverage_rate: 计划覆盖率
        - completion_rate: 实际完成率
        - on_plan_completion: 计划内完成数
        - ad_hoc: 临时追加数
        - cancelled: 取消数
        - rescheduled: 改期数
        - frequency_compliance_rate: 频次合规率
        - route_deviation_km: 路线偏差
        - travel_time_deviation_min: 预计 vs 实际旅行时间偏差
        - service_time_deviation_min: 预计 vs 实际服务时间偏差
        - manual_override_rate: 人工调整率
        - deviation_reasons: 偏差原因分布
    """
    period_label: str
    representative_id: str
    plan_version: str
    policy_version: str
    solver_run_id: str

    # 覆盖率
    n_planned_visits: int = 0
    n_actual_visits: int = 0
    n_planned_customers: int = 0
    n_actual_customers: int = 0
    coverage_rate: float = 0.0      # n_planned_customers / n_actual_customers

    # 完成率
    n_completed: int = 0
    n_on_plan: int = 0
    n_ad_hoc: int = 0
    n_cancelled: int = 0
    n_rescheduled: int = 0
    n_missed: int = 0
    completion_rate: float = 0.0    # n_completed / n_planned_visits

    # 频次合规
    frequency_compliance_rate: float = 0.0

    # 偏差
    travel_time_deviation_min: float = 0.0
    service_time_deviation_min: float = 0.0
    route_deviation_km: float = 0.0

    # 人工调整
    n_overrides: int = 0
    manual_override_rate: float = 0.0

    # 偏差原因分布
    deviation_reasons: dict[str, int] = field(default_factory=dict)

    notes: tuple[str, ...] = ()


def compute_plan_vs_actual(
    plan: PlanVersion,
    planned: list[PlannedVisit],
    actual: list[ActualVisit],
    evidence: DecisionEvidence | None = None,
    overrides: list | None = None,
) -> PlanVsActualMetrics:
    """计算 Plan vs Actual 全量指标。

    输入:
        plan: 计划版本
        planned: 该计划版本下的所有计划拜访
        actual: 该代表该周期内的所有实际拜访
        evidence: 可选的求解证据
        overrides: 可选的人工调整记录
    """
    n_planned = len(planned)
    n_actual = len(actual)

    planned_customers = {v.customer_id for v in planned}
    actual_customers = {v.customer_id for v in actual}

    # 计划完成率
    planned_visit_ids = {v.visit_id for v in planned}
    actual_plan_ids = {v.planned_visit_id for v in actual if v.planned_visit_id}

    on_plan = len(actual_plan_ids & planned_visit_ids)
    ad_hoc = n_actual - on_plan

    completed = sum(1 for v in actual if v.outcome_code == "COMPLETED")
    cancelled = sum(1 for v in planned if v.visit_id not in actual_plan_ids)
    missed = n_planned - on_plan - cancelled

    # 频次合规
    freq_actual = Counter(v.customer_id for v in actual)
    freq_planned = Counter(v.customer_id for v in planned)
    freq_compliant = sum(
        1 for c in planned_customers if freq_actual.get(c, 0) == freq_planned.get(c, 0)
    )
    freq_compliance = (
        freq_compliant / len(planned_customers) if planned_customers else 1.0
    )

    # 偏差
    travel_dev = 0.0
    service_dev = 0.0
    matched = 0
    for a in actual:
        if a.planned_visit_id and a.planned_visit_id in planned_visit_ids:
            p = next((v for v in planned if v.visit_id == a.planned_visit_id), None)
            if p:
                travel_dev += abs(a.actual_travel_minutes - p.estimated_travel_minutes)
                service_dev += abs(a.service_minutes - p.estimated_service_minutes)
                matched += 1
    t_dev = travel_dev / matched if matched else 0.0
    s_dev = service_dev / matched if matched else 0.0

    # 人工调整
    n_overrides = len(overrides) if overrides else 0

    # 偏差原因
    reasons: dict[str, int] = {}
    for a in actual:
        if a.outcome_code != "COMPLETED":
            reasons[a.outcome_code] = reasons.get(a.outcome_code, 0) + 1

    return PlanVsActualMetrics(
        period_label=f"{plan.planning_horizon_start}~{plan.planning_horizon_end}",
        representative_id=plan.representative_id,
        plan_version=f"{plan.plan_id}@v{plan.version}",
        policy_version=plan.policy_version,
        solver_run_id=plan.solver_run_id or "",
        n_planned_visits=n_planned,
        n_actual_visits=n_actual,
        n_planned_customers=len(planned_customers),
        n_actual_customers=len(actual_customers),
        coverage_rate=len(planned_customers & actual_customers) / max(len(actual_customers), 1),
        n_completed=completed,
        n_on_plan=on_plan,
        n_ad_hoc=ad_hoc,
        n_cancelled=cancelled,
        n_rescheduled=0,
        n_missed=missed,
        completion_rate=completed / n_planned if n_planned else 0.0,
        frequency_compliance_rate=freq_compliance,
        travel_time_deviation_min=t_dev,
        service_time_deviation_min=s_dev,
        n_overrides=n_overrides,
        manual_override_rate=n_overrides / n_planned if n_planned else 0.0,
        deviation_reasons=dict(reasons),
    )