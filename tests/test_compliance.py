# -*- coding: utf-8 -*-
"""义务合规率 KPI 单测 (v0.4 §10.1: 适配的正确指标)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestration.experience.compliance import line_kpi, phase_hit, store_compliance


class TestStoreCompliance:
    def test_full_compliance(self):
        assert store_compliance({"A": 2, "B": 2}, {"A": 2, "B": 2}) == 1.0

    def test_missing_store_penalized(self):
        # B 完全没访: (2/2 + 0/2)/2
        assert store_compliance({"A": 2, "B": 2}, {"A": 2}) == 0.5

    def test_overvisit_capped(self):
        # 超访不加分: min(5,2)/2 = 1.0
        assert store_compliance({"A": 2}, {"A": 5}) == 1.0

    def test_zero_plan_excluded(self):
        assert store_compliance({"A": 0, "B": 2}, {"B": 2}) == 1.0

    def test_partial_multi_visit(self):
        # 计划月访 4, 实际 3 → 0.75
        assert store_compliance({"A": 4}, {"A": 3}) == 0.75


class TestPhaseHit:
    def test_phase_preserved(self):
        assert phase_hit({"A": 1}, {"A": [1, 3]}) == 1.0

    def test_phase_violated(self):
        # 计划奇周, 实际只在偶周
        assert phase_hit({"A": 1}, {"A": [2, 4]}) == 0.0

    def test_never_visited(self):
        # A 计划奇周, 从未到访 → 不合规
        assert phase_hit({"A": 1}, {}) == 0.0

    def test_even_phase_is_real_obligation(self):
        # 相位 0 = 偶周, 同样是义务 (actual_phases 值域 {0,1})
        assert phase_hit({"B": 0}, {"B": [0]}) == 1.0
        assert phase_hit({"B": 0}, {"B": [1]}) == 0.0


class TestLineKpi:
    def test_aggregate(self):
        k = line_kpi({"A": 2, "B": 2}, {"A": 3, "B": 1}, {"A": 1, "B": 2},
                     {"A": [1], "B": [1]})
        assert abs(k["compliance"] - 0.75) < 1e-9   # (2/2 + 1/2)/2
        assert abs(k["visit_rate"] - 0.75) < 1e-9   # min 合计 3 / 计划 4
        assert k["phase"] == 0.5                    # A 奇周命中, B 计划偶周实际奇周