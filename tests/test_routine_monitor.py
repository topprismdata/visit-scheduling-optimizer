# -*- coding: utf-8 -*-
"""隐约束监控 (变点检测 / elicitation 条件化) 单测."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestration.experience.routine_monitor import (
    ElicitationEvent,
    apply_elicitation,
    detect_change_points,
    reset_prior_on_change_point,
)


class TestChangePoints:
    def test_stable_no_spike(self):
        assert detect_change_points([0.5, 0.5, 0.5, 0.5]) == []

    def test_spike_detected(self):
        # W3 隐约束变化 (周会改日) → loss 突刺
        assert detect_change_points([0.5, 0.5, 2.5, 0.6]) == [2]

    def test_min_weeks_guard(self):
        assert detect_change_points([0.1, 5.0, 0.5], min_weeks=2) == []


class TestElicitation:
    def test_no_answer_noop(self):
        a, lam = apply_elicitation({"A": 5.0, "B": 1.0}, 0.9,
                                   ElicitationEvent("L", "meeting_day", 2, None))
        assert a == {"A": 5.0, "B": 1.0} and lam == 0.9

    def test_answer_sharpens_and_slows_decay(self):
        a, lam = apply_elicitation({"A": 5.0, "B": 1.0}, 0.9,
                                   ElicitationEvent("L", "meeting_day", 2, "Tuesday"))
        assert a["A"] == 10.0 and a["B"] == 1.0
        assert lam == 0.95

    def test_reset_on_change_point(self):
        city = {"A": 1.0, "B": 1.0}
        assert reset_prior_on_change_point(city, {"A": 9.0}, 2, [2]) == city
        assert reset_prior_on_change_point(city, {"A": 9.0}, 3, [2]) == {"A": 9.0}
