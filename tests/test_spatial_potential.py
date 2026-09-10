"""物理信息空间几何势能场 (Physics-Informed Spatial Potential Field) 单元测试 — 方案三。

验证契约: SpatialPotentialField 以总凸包面积的逐日公平份额为理想作业域,
单日分配的凸包面积超标产生平方增长势能惩罚; 长宽狭长作业域额外受罚。
核心场景: 远端孤立点混入密集组团时, 势能惩罚必须显著大于全部紧凑点分配。
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.spatial_continuous_approx import compute_convex_hull_area_km2
from core.spatial_potential import SpatialPotentialField

# WGS-84 测试坐标集: 5×5 密集组团 (苏州附近, ~1.9 km × 2.2 km) + 1 个远端孤立点 (正东 ~67 km)
CENTER_LNG, CENTER_LAT = 120.60, 31.30
_DENSE = [
    (CENTER_LNG + 0.005 * i, CENTER_LAT + 0.005 * j)
    for j in range(-2, 3)
    for i in range(-2, 3)
]
FAR_POINT = (121.30, CENTER_LAT)  # (lng, lat) 正东 ~0.71° ≈ 67 km
COORDS = _DENSE + [FAR_POINT]
DENSE_INDICES = list(range(len(_DENSE)))
FAR_INDEX = len(COORDS) - 1


def test_init_uses_convex_hull_total_area_and_ideal_share():
    total, _, _ = compute_convex_hull_area_km2(COORDS)
    field = SpatialPotentialField(COORDS, n_days=4)
    assert field.total_area_km2 == pytest.approx(total)
    assert field.ideal_day_area_km2 == pytest.approx(total / 4)


def test_far_isolated_point_penalty_dominates_dense_cluster():
    """远端孤立点放入密集组团 → 势能惩罚显著大于全部紧凑点分配。"""
    field = SpatialPotentialField(COORDS, n_days=4)
    compact = field.evaluate_day_assignment(DENSE_INDICES)
    contaminated = field.evaluate_day_assignment(DENSE_INDICES + [FAR_INDEX])
    assert compact < 1.0
    assert contaminated > 10.0
    assert contaminated > 100 * compact


def test_balanced_interleaved_partition_stays_low_potential():
    """交错 (棋盘) 均衡切分紧凑组团 → 每片均铺满组团, 势能接近零。"""
    field = SpatialPotentialField(COORDS, n_days=2)
    even = [k for k in DENSE_INDICES if ((k % 5) + (k // 5)) % 2 == 0]
    odd = [k for k in DENSE_INDICES if ((k % 5) + (k // 5)) % 2 == 1]
    assert len(even) == 13 and len(odd) == 12
    for name, piece in (("even", even), ("odd", odd)):
        penalty = field.evaluate_day_assignment(piece)
        assert penalty < 0.1, f"{name} 片势能 {penalty} 应接近零"


def test_empty_and_degenerate_assignments_have_zero_penalty():
    field = SpatialPotentialField(COORDS, n_days=4)
    assert field.evaluate_day_assignment([]) == 0.0
    assert field.evaluate_day_assignment([0, 1]) == 0.0


def test_elongated_corridor_penalized_more_than_compact_square():
    """等点数下, 东西狭长走廊 (纵横比 ~17) 的形态惩罚远大于紧凑方形。"""
    corridor = [
        (120.40 + 0.1 * i, CENTER_LAT + 0.005 * j) for i in range(5) for j in range(-2, 3)
    ]
    corridor_field = SpatialPotentialField(corridor, n_days=1)
    square_field = SpatialPotentialField(_DENSE, n_days=1)
    corridor_penalty = corridor_field.evaluate_day_assignment(list(range(len(corridor))))
    square_penalty = square_field.evaluate_day_assignment(DENSE_INDICES)
    assert corridor_penalty > 10 * square_penalty
    assert corridor_penalty > 10.0  # 纵横比 ~17 → (17-1)² 量级


def test_invalid_n_days_rejected():
    with pytest.raises(ValueError):
        SpatialPotentialField(COORDS, n_days=0)


def test_penalty_monotone_in_outlier_distance():
    """孤立点越远, 污染日势能单调不减 (物理势能随位移增长)。"""
    near_field = SpatialPotentialField(_DENSE + [(120.80, CENTER_LAT)], n_days=4)
    far_field = SpatialPotentialField(COORDS, n_days=4)
    near_penalty = near_field.evaluate_day_assignment(DENSE_INDICES + [25])
    far_penalty = far_field.evaluate_day_assignment(DENSE_INDICES + [FAR_INDEX])
    assert far_penalty > near_penalty > 0.0
    assert math.isfinite(far_penalty)
