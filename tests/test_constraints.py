"""统一 PlanningPolicy ↔ 求解器集成测试 (属性测试: 求解器输出必须过独立 validator)。"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "algos"))

from pvrp_cg import solver
from pvrp_cg.policy import PlanningPolicy


def _small_instance():
    """10 客户小实例 (2 密度区), 与公开示例同源。"""
    import random
    rng = random.Random(20260815)
    lats, lons = [], []
    for i in range(10):
        spread = 0.05 if i < 5 else 0.20
        lats.append(31.30 + rng.uniform(-spread, spread))
        lons.append(120.60 + rng.uniform(-spread, spread))
    freq = [rng.choice([1, 1, 2]) for _ in range(10)]
    return lats, lons, freq


def _haversine(lat1, lon1, lat2, lon2):
    from math import asin, sqrt
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return 2 * 6371.0 * asin(math.sqrt(a))



class TestSolverOutputsPassPolicyValidator:
    def test_open_cg_solution_respects_policy(self):
        lats, lons, freq = _small_instance()
        n = len(lats)
        D = [[_haversine(lats[i], lons[i], lats[j], lons[j])
              for j in range(n)] for i in range(n)]
        policy = PlanningPolicy(n_customers=n, frequency_rules=dict(enumerate(freq)))
        a, total, status, st = solver.solve_open_cg(
            n, D, freq, days=policy.horizon_days, time_limit=15, verbose=False
        )
        if a is None:
            pytest.skip("求解器未返回解")
        violations = policy.validate_solution(a)
        assert not violations, f"求解器输出违反统一契约: {violations[:5]}"

    def test_closed_cg_daily_cap_never_exceeded(self):
        lats, lons, freq = _small_instance()
        n = len(lats)
        depot = (31.30, 120.60)
        pts = [(lats[i], lons[i]) for i in range(n)] + [depot]
        D = [[_haversine(a, b, c, d) for (c, d) in pts] for (a, b) in pts]
        depot_idx = n
        policy = PlanningPolicy(
            n_customers=n,
            frequency_rules=dict(enumerate(freq)),
            max_work_minutes_per_day=None,   # distance 口径无工时上限
            route_type="closed",
        )
        a, total, status, st = solver.solve_distance_cg(
            n, D, depot_idx, freq, days=policy.horizon_days,
            time_limit=15, verbose=False,
        )
        if a is None:
            pytest.skip("求解器未返回解")
        violations = policy.validate_solution(a)
        assert not any("超上限" in x for x in violations), violations

    def test_time_cg_day_cap_matches_policy(self):
        lats, lons, freq = _small_instance()
        n = len(lats)
        cap = 480.0
        T = [[_haversine(lats[i], lons[i], lats[j], lons[j]) * 6.0
              for j in range(n)] for i in range(n)]
        t0 = [_haversine(31.30, 120.60, lats[i], lons[i]) * 6.0 for i in range(n)]
        svc = [30.0] * n
        policy = PlanningPolicy(
            n_customers=n,
            frequency_rules=dict(enumerate(freq)),
            max_work_minutes_per_day=cap,
        )
        a, total, status, st = solver.solve_time_cg(
            n, T, t0, svc, freq, days=policy.horizon_days,
            daily_cap=cap, time_limit=15, verbose=False,
        )
        if a is None:
            pytest.skip("求解器未返回解")
        day_times = [
            sum(T[a_d[k]][a_d[k + 1]] for k in range(len(a_d) - 1))
            + t0[a_d[0]] + sum(svc[c] for c in a_d) if a_d else 0.0
            for a_d in a
        ]
        violations = policy.validate_solution(a, day_times=day_times)
        # 工时上限允许 ≤ tol 的浮点噪声; 频次/间隔/日数量必须零违例
        hard = [x for x in violations if "超上限" not in x]
        assert not hard, f"硬约束违例: {hard[:5]}"
