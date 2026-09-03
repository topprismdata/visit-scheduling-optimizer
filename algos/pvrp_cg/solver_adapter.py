"""SolverAdapter — 求解器输出 → Plan vs Actual 数据契约适配器 (Phase 1, Human-led Planning)。"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Sequence

from . import solver
from .calibration import build_time_matrix
from .planning import DecisionEvidence, PlanVersion, PlannedVisit
from .policy import DEFAULT_MAX_VISITS_PER_DAY, PlanningPolicy


def _working_dates(horizon_start: date, n_slots: int) -> list[date]:
    """从 horizon_start 起取 n_slots 个工作日 (Mon-Fri), 跳过周末。"""
    result = []
    d = horizon_start
    while len(result) < n_slots:
        if d.weekday() < 5:
            result.append(d)
        d = date.fromordinal(d.toordinal() + 1)
    return result


def _build_plan_id(rep_id: str, horizon_start: date) -> str:
    return f"PLAN_{rep_id}_{horizon_start.isoformat()}"


def solve_to_plan(
    *,
    lats: Sequence[float],
    lons: Sequence[float],
    depot: tuple[float, float],
    representative_id: str = "rep",
    freq: Sequence[int] | None = None,
    svc: Sequence[float] | None = None,
    tiers: Sequence[str] | None = None,
    policy: PlanningPolicy | None = None,
    segments: Sequence[tuple[float, float, float, float, float, str]] | None = None,
    counties: Sequence[str] | None = None,
    depot_county: str | None = None,
    existing_plan: PlanVersion | None = None,
    time_limit: int = 30,
    verbose: bool = False,
    horizon_start: date | None = None,
    solver_type: str = "time",               # "time" / "distance"
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """求解器 → PlanVersion 一步完成。"""
    n = len(lats)
    svc_a = svc or ([policy.service_minutes_for_tier(t) for t in tiers]
                     if policy and policy.tier_service_minutes and tiers else [30.0] * n)
    freq_list = list(freq) if freq else [policy.frequency_rules[i] for i in range(n)] if policy else [1] * n
    days = policy.horizon_days if policy else 20
    daily_cap = policy.max_work_minutes_per_day if policy else 540.0
    hs = horizon_start or date(2026, 6, 1)

    T, t0, calib = build_time_matrix(lats, lons, depot, segments or [], counties=counties, depot_county=depot_county)
    if solver_type == "distance":
        # distance caliber: 构建距离矩阵
        from .calibration import _hav
        D_full = [[_hav(lats[i], lons[i], lats[j], lons[j]) for j in range(n + 1)]
                  for i in range(n + 1)]
        D_cust = [row[:n] for row in D_full[:n]]
        a, total, status, stats = solver.solve_distance_cg(
            n, D_cust, n, freq_list, days=days, time_limit=time_limit, verbose=verbose,
        )
    else:
        a, total, status, stats = solver.solve_time_cg(
            n, T, t0, svc_a, freq_list, days=days, daily_cap=daily_cap,
            time_limit=time_limit, verbose=verbose,
        )
    if a is None:
        a = [set() for _ in range(days)]

    new_version = (existing_plan.version + 1) if existing_plan else 1
    plan_id = _build_plan_id(representative_id, hs)
    pvid = f"{plan_id}@v{new_version}"
    run_id = f"SR_{uuid.uuid4().hex[:10]}"
    plan = PlanVersion(
        plan_id=plan_id, version=new_version,
        planning_horizon_start=hs,
        planning_horizon_end=date.fromordinal(hs.toordinal() + days - 1),
        representative_id=representative_id,
        policy_version="v1.0",
        solver_run_id=run_id, status="draft",
        created_at=datetime.now(timezone.utc),
    )
    wd = _working_dates(hs, max(days, 28))
    visits = []
    vi = 0
    for di, ds in enumerate(a):
        if not ds or di >= len(wd):
            continue
        ad = wd[di] if di < len(wd) else hs
        for seq, ci in enumerate(sorted(ds)):
            vi += 1
            visits.append(PlannedVisit(
                plan_version_id=pvid, visit_id=f"V_{pvid}_{vi}",
                customer_id=str(ci), planned_date=ad, sequence=seq + 1,
                estimated_service_minutes=svc_a[ci] if svc_a else 0.0,
            ))
    evidence = DecisionEvidence(
        solver_run_id=run_id, policy_version="v1.0",
        input_version=f"n{n}",
        optimality_scope="restricted_column_pool",
        status=status, n_columns=stats.get("n_columns", 0),
        n_constraints=n * days,
        warnings=(calib.get("warn", ""),) if calib.get("warn") else (),
    )
    return plan, visits, evidence


def adapt_solution(
    assigns: list[set[int]] | None,
    total: float,
    status: str,
    stats: dict,
    policy: PlanningPolicy,
    n_customers: int,
    svc: Sequence[float] | None = None,
    representative_id: str = "rep",
    existing_plan: PlanVersion | None = None,
    horizon_start: date | None = None,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """求解器输出 → 数据契约 (不重新求解)。"""
    nv = (existing_plan.version + 1) if existing_plan else 1
    hs = horizon_start or date(2026, 6, 1)
    days = policy.horizon_days
    pid = _build_plan_id(representative_id, hs)
    pvid = f"{pid}@v{nv}"
    run_id = f"AD_{uuid.uuid4().hex[:10]}"
    plan = PlanVersion(
        plan_id=pid, version=nv,
        planning_horizon_start=hs,
        planning_horizon_end=date.fromordinal(hs.toordinal() + days - 1),
        representative_id=representative_id,
        policy_version="v1.0", solver_run_id=run_id,
        status="draft", created_at=datetime.now(timezone.utc),
    )
    svc_a = svc or [30.0] * n_customers
    wd = _working_dates(hs, max(days, 28))
    visits = []
    vi = 0
    if assigns:
        for di, ds in enumerate(assigns):
            if not ds or di >= len(wd):
                continue
            ad = wd[di]
            for seq, ci in enumerate(sorted(ds)):
                vi += 1
                visits.append(PlannedVisit(
                    plan_version_id=pvid, visit_id=f"V_{pvid}_{vi}",
                    customer_id=str(ci), planned_date=ad, sequence=seq + 1,
                    estimated_service_minutes=svc_a[ci],
                ))
    evidence = DecisionEvidence(
        solver_run_id=run_id, policy_version="v1.0",
        input_version=f"adapt_n{n_customers}",
        optimality_scope="restricted_column_pool",
        status=status, n_columns=stats.get("n_columns", 0),
        n_constraints=n_customers * days,
    )
    return plan, visits, evidence