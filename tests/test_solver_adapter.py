"""SolverAdapter 单元测试 (Phase 1)。"""

import sys
from datetime import date, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "algos"))

from pvrp_cg.planning import PlanVersion, PlannedVisit, DecisionEvidence
from pvrp_cg.policy import PlanningPolicy
from pvrp_cg.solver_adapter import adapt_solution, solve_to_plan


def _small_instance():
    import random
    rng = random.Random(20260815)
    lats, lons = [], []
    for i in range(10):
        spread = 0.05 if i < 5 else 0.20
        lats.append(31.30 + rng.uniform(-spread, spread))
        lons.append(120.60 + rng.uniform(-spread, spread))
    freq = [rng.choice([1, 1, 2]) for _ in range(10)]
    return lats, lons, freq


class TestSolveToPlan:
    def test_solve_to_plan_returns_plan_version(self):
        lats, lons, freq = _small_instance()
        policy = PlanningPolicy(n_customers=len(lats), frequency_rules=dict(enumerate(freq)))
        plan, visits, evidence = solve_to_plan(
            lats=lats, lons=lons, depot=(31.30, 120.60),
            representative_id="仁军", freq=freq, policy=policy,
            time_limit=10, verbose=False,
        )
        assert isinstance(plan, PlanVersion)
        assert plan.representative_id == "仁军"
        assert plan.status == "draft"
        assert isinstance(evidence, DecisionEvidence)

    def test_solve_to_plan_version_increments(self):
        lats, lons, freq = _small_instance()
        policy = PlanningPolicy(n_customers=len(lats), frequency_rules=dict(enumerate(freq)))
        plan1, _, _ = solve_to_plan(
            lats=lats, lons=lons, depot=(31.30, 120.60),
            representative_id="仁军", freq=freq, policy=policy,
            time_limit=10, verbose=False,
        )
        plan2, _, _ = solve_to_plan(
            lats=lats, lons=lons, depot=(31.30, 120.60),
            representative_id="仁军", freq=freq, policy=policy,
            existing_plan=plan1,
            time_limit=10, verbose=False,
        )
        assert plan2.version == plan1.version + 1

    def test_solve_to_plan_returns_valid_types(self):
        lats, lons, freq = _small_instance()
        policy = PlanningPolicy(n_customers=len(lats), frequency_rules=dict(enumerate(freq)))
        plan, visits, evidence = solve_to_plan(
            lats=lats, lons=lons, depot=(31.30, 120.60),
            representative_id="仁军", freq=freq, policy=policy,
            time_limit=15, verbose=False,
        )
        assert isinstance(plan, PlanVersion)
        assert isinstance(evidence, DecisionEvidence)
        if visits:
            assert isinstance(visits[0], PlannedVisit)


class TestAdaptSolution:
    def test_adapt_solution_returns_plan_and_visits(self):
        policy = PlanningPolicy(n_customers=5, frequency_rules=dict(enumerate([1, 1, 2, 2, 1])))
        assigns = [{0, 1}, {2, 3}, {4}, set(), set(), set(), set(), set(), set(), set(),
                   set(), set(), set(), set(), set(), set(), set(), set(), set(), set()]
        plan, visits, evidence = adapt_solution(
            assigns, 100.0, "OPTIMAL", {"n_columns": 50}, policy, 5,
            representative_id="仁军",
        )
        assert plan.status == "draft"
        assert len(visits) > 0
        assert evidence.status == "OPTIMAL"

    def test_adapt_solution_empty_assigns(self):
        policy = PlanningPolicy(n_customers=3, frequency_rules=dict(enumerate([1, 1, 1])))
        plan, visits, evidence = adapt_solution(
            None, 0.0, "INFEASIBLE", {}, policy, 3,
            representative_id="仁军",
        )
        assert len(visits) == 0
        assert evidence.status == "INFEASIBLE"
        assert plan.status == "draft"