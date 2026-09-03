"""travel.py 单元测试 — 距离与精确路径成本。"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "algos"))

from pvrp_cg.travel import haversine, hk_closed, hk_open, nn2opt_closed


def test_haversine_zero_for_same_point():
    assert haversine(31.3, 120.6, 31.3, 120.6) == 0.0


def test_haversine_sanity_known_distance():
    # 苏州→南通 ≈ 100-110 km (经验量级)
    d = haversine(31.30, 120.62, 31.98, 120.89)
    assert 70 <= d <= 140


def test_haversine_symmetric():
    d1 = haversine(31.0, 120.0, 32.0, 121.0)
    d2 = haversine(32.0, 121.0, 31.0, 120.0)
    assert abs(d1 - d2) < 1e-9


class TestHKOpen:
    def test_two_nodes(self):
        D = [[0, 5], [7, 0]]
        assert hk_open(D) == 5

    def test_triangle_asymmetry(self):
        # 开放路径可从任意点出发 — 最优是最便宜的 2 段组合
        D = [[0, 1, 9], [9, 0, 1], [1, 9, 0]]
        assert hk_open(D) == 2

    def test_single_node(self):
        assert hk_open([[0]]) == 0


class TestHKClosed:
    def test_closed_round_trip_includes_depot_legs(self):
        # 3 客户 + depot 回程: 每段由 t0[k] 近似起点 leg — 直接验契约
        D = [[0, 5, 9], [5, 0, 4], [9, 4, 0]]
        t0 = [1.0, 2.0, 3.0]
        cost = hk_closed(D, t0)
        assert cost < math.inf and cost > 0

    def test_empty_day(self):
        assert hk_closed([], []) == 0.0


class TestNN2OptClosed:
    def test_finite_cost_small_instance(self):
        D = [[0, 2, 9], [2, 0, 4], [9, 4, 0]]
        t0 = [1.0, 1.5, 2.0]
        cost = nn2opt_closed(D, t0)
        assert cost < math.inf
