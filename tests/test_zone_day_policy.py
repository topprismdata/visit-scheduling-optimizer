# -*- coding: utf-8 -*-
"""ZoneDayPolicy 学习管线单测 (合成数据, 无 h3 依赖)."""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestration.experience import (
    ZoneDayTemplate,
    alignment_score,
    learn_zone_day_policy,
    predict_compliance,
    wilson_lower,
)

# 合成: 线 R1 周一全在格 A, 周二全在格 B; 线 R2 均匀乱走
CELLS = {f"C{i:03d}": ("A" if i % 2 == 0 else "B") for i in range(20)}


def _actuals():
    rows = []
    # R1: 4 个周一全打 A 格店, 4 个周二全打 B 格店
    mondays = [datetime(2026, 8, 3) , datetime(2026, 8, 10), datetime(2026, 8, 17), datetime(2026, 8, 24)]
    tuesdays = [datetime(2026, 8, 4), datetime(2026, 8, 11), datetime(2026, 8, 18), datetime(2026, 8, 25)]
    a_codes = [c for c, cl in CELLS.items() if cl == "A"]
    b_codes = [c for c, cl in CELLS.items() if cl == "B"]
    for k, d in enumerate(mondays):
        for c in a_codes[:3]:
            rows.append({"salesperson_code": "R1", "call_date": d, "customer_code": c})
    for k, d in enumerate(tuesdays):
        for c in b_codes[:3]:
            rows.append({"salesperson_code": "R1", "call_date": d, "customer_code": c})
    # R2: 周一也打 B 格店 (无固定模板)
    for d in mondays + tuesdays:
        for c in (a_codes[:1] + b_codes[:1]):
            rows.append({"salesperson_code": "R2", "call_date": d, "customer_code": c})
    return pd.DataFrame(rows)


class TestLearn:
    def test_template_structure(self):
        tpl = learn_zone_day_policy(_actuals(), CELLS)
        t1 = tpl["R1"]
        assert isinstance(t1, ZoneDayTemplate)
        assert t1.top_cell[0] == "A" and t1.top_cell[1] == "B"
        assert t1.support == 24
        # Laplace: 概率和≈1, 未见格有小概率
        p0 = t1.prob[0]
        assert abs(sum(p0.values()) - 1.0) < 1e-9
        assert p0["B"] > 0 and p0["A"] > 0.9
        assert 0 < t1.confidence[0] <= 1

    def test_min_support_gate(self):
        tpl = learn_zone_day_policy(_actuals(), CELLS)
        t2 = tpl["R2"]
        # R2 每星期几样本少但 ≥3; 周三无数据 → 不出现在 top_cell
        assert 2 not in t2.top_cell and 2 not in t2.prob


class TestAlignment:
    def test_perfect_plan_scores_high(self):
        tpl = learn_zone_day_policy(_actuals(), CELLS)["R1"]
        plan = pd.DataFrame([
            {"plan_day": datetime(2026, 8, 31), "customer_code": c, "cell": "A"}  # 周一
            for c in ["C000", "C002", "C004"]
        ] + [
            {"plan_day": datetime(2026, 8, 18), "customer_code": c, "cell": "B"}  # 周二
            for c in ["C001", "C003", "C005"]
        ])
        sc = alignment_score(plan, tpl)
        assert sc["argmax"] == 1.0
        assert sc["likelihood"] > 0.8

    def test_misaligned_plan_scores_low(self):
        tpl = learn_zone_day_policy(_actuals(), CELLS)["R1"]
        plan = pd.DataFrame([
            {"plan_day": datetime(2026, 8, 31), "customer_code": c, "cell": "B"}  # 周一放 B
            for c in ["C001", "C003", "C005"]
        ])
        sc = alignment_score(plan, tpl)
        assert sc["argmax"] == 0.0
        assert sc["likelihood"] < 0.1

    def test_missing_cell_column_raises(self):
        tpl = learn_zone_day_policy(_actuals(), CELLS)["R1"]
        with pytest.raises(ValueError, match="cell"):
            alignment_score(pd.DataFrame([{"plan_day": datetime(2026, 8, 31), "customer_code": "C000"}]), tpl)


class TestCompliancePredictor:
    def test_anchors(self):
        assert predict_compliance(0.2) == 0.29
        assert predict_compliance(0.9) == 0.94
        mid = predict_compliance(0.575)
        assert 0.29 < mid < 0.94

    def test_monotonic(self):
        vals = [predict_compliance(x / 20) for x in range(21)]
        assert all(b >= a for a, b in zip(vals, vals[1:]))

    def test_nan_passthrough(self):
        assert predict_compliance(float("nan")) != predict_compliance(float("nan"))  # NaN


class TestWilson:
    def test_bounds(self):
        assert wilson_lower(100, 100) > 0.95
        assert wilson_lower(1, 2) < 0.65
        assert wilson_lower(0, 0) == 0.0
