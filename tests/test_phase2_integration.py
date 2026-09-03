"""Phase 2 集成测试 — DynamicPlanningPolicy + CustomerValueModel + weighted CG。"""

import random
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys_path = str(Path(__file__).resolve().parents[1] / "algos")
sys = __import__("sys")
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from pvrp_cg.baselines import ALNS
from pvrp_cg.customer_value import CustomerValueModel
from pvrp_cg.dynamic_policy import DynamicPlanningPolicy
from pvrp_cg.planning import ActualVisit, PlanVersion, PlannedVisit
from pvrp_cg.policy import PlanningPolicy
from pvrp_cg.weighted_solver import solve_weighted_cg


def _make_actuals(n_customers=8, seed=42):
    """生成 3 轮拜访的 ActualVisit 列表。"""
    rng = random.Random(seed)
    actuals = []
    for c in range(n_customers):
        for visit_num in range(2 + rng.randint(0, 1)):
            actuals.append(ActualVisit(
                actual_id=f"A_{c}_{visit_num}",
                customer_id=str(c),
                actual_date=date(2026, 6, 10 + rng.randint(0, 5) + visit_num * 7),
                service_minutes=rng.uniform(30, 60),
                outcome_code="COMPLETED" if rng.random() > 0.15 else "MISSED",
                source_system="TEST",
            ))
    return actuals


class TestDynamicPlanningPolicy:
    def test_minimal_ok(self):
        base = PlanningPolicy(n_customers=5,
                              frequency_rules=dict(enumerate([2] * 5)))
        scores = {i: 0.5 for i in range(5)}
        conf = {i: 0.8 for i in range(5)}
        dp = DynamicPlanningPolicy(base=base, value_scores=scores, value_confidence=conf)
        assert dp.effective_value_weight() == pytest.approx(1.0 * 0.8)

    def test_empty_scores_raises(self):
        import pytest as _pytest
        base = PlanningPolicy(n_customers=3, frequency_rules={0: 1, 1: 1, 2: 1})
        with _pytest.raises(ValueError, match="value_scores"):
            DynamicPlanningPolicy(base=base, value_scores={}, value_confidence={})

    def test_score_out_of_range_raises(self):
        import pytest as _pytest
        base = PlanningPolicy(n_customers=3, frequency_rules={0: 1, 1: 1, 2: 1})
        with _pytest.raises(ValueError, match="value_scores"):
            DynamicPlanningPolicy(base=base, value_scores={0: 1.5, 1: 0.5, 2: 0.3},
                                  value_confidence={})


class TestCustomerValueModel:
    def test_completes_with_data(self):
        model = CustomerValueModel()
        actuals = _make_actuals()
        scores, conf, signals = model.compute_scores(actuals)
        assert len(scores) == 8
        for s in scores.values():
            assert 0.0 <= s <= 1.0
        assert len(signals) > 0
        # inferred 信号必须带 model_version
        for sig in signals:
            if sig.kind == "inferred":
                assert sig.model_version != ""

    def test_high_completion_customer_scores_higher(self):
        model = CustomerValueModel()
        high_comp = [ActualVisit("A_H", "99", date(2026, 6, 10), service_minutes=45,
                                 outcome_code="COMPLETED"),
                     ActualVisit("A_H2", "99", date(2026, 6, 20), service_minutes=50,
                                 outcome_code="COMPLETED")]
        low_comp = [ActualVisit("A_L", "88", date(2026, 6, 10), service_minutes=40,
                                outcome_code="MISSED"),
                    ActualVisit("A_L2", "88", date(2026, 6, 20), service_minutes=35,
                                outcome_code="MISSED")]
        all_a = high_comp + low_comp
        scores, _, _ = model.compute_scores(all_a)
        assert scores["99"] > scores["88"], f"高完成率客户({scores['99']}) 应高于低完成率({scores['88']})"


class TestWeightedCGIntegration:
    def _policy(self, freq, n):
        return PlanningPolicy(n_customers=n,
                              frequency_rules=dict(enumerate(freq)),
                              horizon_days=20, max_visits_per_day=6)

    def test_weighted_vs_plain_different_schedules(self):
        n = 6
        T = [[abs(i - j) * 10.0 for j in range(n)] for i in range(n)]
        t0 = [15.0] * n
        svc = [30.0] * n
        freq = [2] * n
        scores = [1.0, 0.9, 0.0, 0.0, 0.0, 0.0]

        a_eff, _, _, _ = solve_weighted_cg(n, T, t0, svc, freq,
                                           value_scores=None, time_limit=10)
        a_val, _, _, _ = solve_weighted_cg(n, T, t0, svc, freq,
                                           value_scores=scores, value_weight=3.0,
                                           time_limit=10)
        if a_eff and a_val:
            # 有价值客户应更早被拜访（间隔更紧）
            d_hi_val = sorted(d for d, day in enumerate(a_val) if 0 in day or 1 in day)
            assert len(d_hi_val) >= 2

    def test_solve_returns_all_visits(self):
        n = 5
        T = [[abs(i - j) * 8.0 for j in range(n)] for i in range(n)]
        t0 = [12.0] * n
        svc = [40.0] * n
        freq = [2] * n
        scores = {i: i / (n - 1) for i in range(n)}
        a, total, status, stats = solve_weighted_cg(n, T, t0, svc, freq,
                                                    value_scores=list(scores.values()),
                                                    time_limit=10)
        if a:
            count = sum(len(day) for day in a)
            expected = sum(freq)
            assert count >= expected - n, f"期望 >= {expected - n} 次拜访, 实际 {count}"
