"""物理信息空间几何势能场 (Physics-Informed Spatial Potential Field) — 方案三。

将 Layer 1 跨日分配的空间紧致性建模为势能场: 每个调度日按总凸包面积的
公平份额 (总面积 / n_days) 拥有理想作业域, 单日分配偏离该份额时产生势能惩罚。
连续近似口径沿用 Daganzo (1984) (core.spatial_continuous_approx)。

势能两项 (均无量纲, 平方增长 — 弹簧势能 U ∝ x² 的物理形态):
- 面积超标势能: U_area = (max(0, A_day − A_ideal) / A_ideal)²
  抑制"远端孤立点污染密集组团"式分配 — 跨日凸包被拉大时惩罚平方级放大;
- 长宽狭长比惩罚: U_shape = (r − 1)², r = max(dx, dy) / min(dx, dy) ≥ 1
  狭长走廊在真实路网上跨日巡回里程次优, 形态越细长惩罚越大。

该势能作为 ALNS 移动接受准则的软惩罚项, 引导日分配保持紧致组团。
"""

import math
from typing import Sequence, Tuple

from core.spatial_continuous_approx import compute_convex_hull_area_km2


class SpatialPotentialField:
    """单日空间作业域势能场。

    Attributes:
        total_area_km2: 全部门店坐标的总凸包面积 (km²)。
        ideal_day_area_km2: 单日理想作业域面积 = total_area_km2 / n_days。
    """

    def __init__(self, coords_wgs84: Sequence[Tuple[float, float]], n_days: int) -> None:
        if n_days < 1:
            raise ValueError(f"n_days 必须 ≥ 1, 收到 {n_days}")
        self.coords_wgs84 = [(float(p[0]), float(p[1])) for p in coords_wgs84]
        self.n_days = int(n_days)
        self.total_area_km2, _, _ = compute_convex_hull_area_km2(self.coords_wgs84)
        self.ideal_day_area_km2 = self.total_area_km2 / self.n_days

    def evaluate_day_assignment(self, store_indices: Sequence[int]) -> float:
        """计算单日分配的空间势能惩罚 (面积超标 + 长宽狭长, 无量纲)。

        Args:
            store_indices: 该日分配的门店在 coords_wgs84 中的下标。

        Returns:
            势能惩罚; 空分配或不足 3 点 (退化凸包) 返回 0.0。
        """
        day_coords = [self.coords_wgs84[i] for i in store_indices]
        if len(day_coords) < 3:
            return 0.0

        area_km2, dx_km, dy_km = compute_convex_hull_area_km2(day_coords)
        penalty = 0.0

        if self.ideal_day_area_km2 > 0.0:
            overshoot = max(0.0, area_km2 - self.ideal_day_area_km2)
            penalty += (overshoot / self.ideal_day_area_km2) ** 2

        short_side = min(dx_km, dy_km)
        if short_side > 1e-9:
            aspect_ratio = max(dx_km, dy_km) / short_side
            penalty += (aspect_ratio - 1.0) ** 2

        return penalty
