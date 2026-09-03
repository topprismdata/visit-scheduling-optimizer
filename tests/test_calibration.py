"""calibration.py 单元测试 — county 校准实际进入时间矩阵 (P0-1 验收)。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "algos"))

from pvrp_cg.calibration import (
    DEFAULT_GLOBAL_RATE,
    build_time_matrix,
    fit_county_rates,
    rate_eff,
)


def _segments(county: str, minutes: float, n: int = 12) -> list:
    """n 条 ~1km 同 county 腿 (分钟/公里 = minutes)。"""
    return [(31.0 + i * 1e-4, 120.0, 31.006, 120.008, minutes, county)
            for i in range(n)]


class TestFitCountyRates:
    def test_fit_returns_median_per_county(self):
        segs = _segments("urban", 8.0) + _segments("suburban", 3.0)
        rates = fit_county_rates(segs)
        assert abs(rates["urban"] - 8.0) < 0.5
        assert abs(rates["suburban"] - 3.0) < 0.5

    def test_min_samples_excludes_counties(self):
        segs = _segments("urban", 8.0, n=12) + _segments("rural", 5.0, n=3)
        rates = fit_county_rates(segs, min_samples=5)
        assert "urban" in rates
        assert "rural" not in rates


class TestBuildTimeMatrixCountyEffect:
    """P0 验收核心: 已拟合的 county rates 必须实际进入最终矩阵。"""

    SEGS = _segments("urban", 8.0) + _segments("suburban", 3.0)

    def test_same_distance_different_county_different_time(self):
        """验收标准 1: 相同行程距离、不同 county → 不同校准时间。"""
        lat = 30.0
        lon = 110.0
        # 两条同距离腿 (~1 km): dest=urban vs dest=suburban
        lats = [lat, lat]
        lons = [lon, lon + 0.01]
        T, t0, diag = build_time_matrix(
            lats, lons, (lat - 0.01, lon), self.SEGS,
            counties=["urban", "suburban"],
        )
        assert T[0][1] != T[1][0], "destination-county 校准未生效"

    def test_destination_county_semantics(self):
        """T[i][j] 使用 destination 的 county rate。"""
        # 短腿 (< kink): 时间 ≈ mpk_dest × km → 到 urban (8 min/km) 更慢
        lats = [30.0, 30.0]
        lons = [110.0, 110.01]
        T, _, _ = build_time_matrix(
            lats, lons, (29.99, 110.0), self.SEGS,
            counties=["urban", "suburban"],
        )
        # T[0][1] 到达 suburban (~3 min/km), T[1][0] 到达 urban (~8 min/km)
        assert T[0][1] < T[1][0], "destination=urban 应比 destination=suburban 慢"

    def test_fallback_marked_when_county_unfitted(self):
        """验收标准 2: county 样本不足 → 明确标记 fallback。"""
        lats = [30.0, 30.0]
        lons = [110.0, 110.01]
        T, t0, diag = build_time_matrix(
            lats, lons, (29.99, 110.0), self.SEGS,
            counties=["unheard", "unheard"],   # 该 county 无样本
        )
        assert diag["fallback_ratio_client_legs"] == 1.0
        assert diag["fallback_ratio_depot_legs"] == 1.0
        assert diag["warn"]
        # fallback 下等距双腿时间相等
        assert T[0][1] == pytest.approx(T[1][0])

    def test_fitted_rate_entered_matrix_not_fallback(self):
        """验收标准 3: fitted rate ≠ fallback 时, 矩阵使用 fitted 值。"""
        lats = [30.0, 30.0]
        lons = [110.0, 110.01]
        T, t0, diag = build_time_matrix(
            lats, lons, (29.99, 110.0), self.SEGS,
            counties=["urban", "urban"],
            fallback_rate=DEFAULT_GLOBAL_RATE,
        )
        # urban fitted ≈ 8 min/km ≠ fallback 6.0 → 短腿时间应偏离纯 fallback 计算
        km = 0.01 * 111.194  # haversine ~1.11 km
        naive_fallback = rate_eff(DEFAULT_GLOBAL_RATE, km) * km
        assert T[0][1] != pytest.approx(naive_fallback, rel=0.05)
        assert diag["fallback_ratio_client_legs"] == 0.0

    def test_depot_legs_use_customer_county(self):
        """depot legs 用各客户的 county rate (而非全局回退)。"""
        lats = [30.0, 30.0]
        lons = [110.0, 110.01]
        T, t0, diag = build_time_matrix(
            lats, lons, (29.99, 110.0), self.SEGS,
            counties=["urban", "suburban"],
        )
        assert diag["fallback_ratio_depot_legs"] == 0.0

    def test_mismatched_counties_length_raises(self):
        with pytest.raises(ValueError, match="counties 长度"):
            build_time_matrix(
                [30.0], [110.0], (29.99, 110.0), self.SEGS,
                counties=["a", "b"],
            )

    def test_backcompat_no_counties_all_fallback(self):
        """兼容旧形态: 不传 counties → 全 fallback 且 diagnostics 如实标记。"""
        lats = [30.0, 30.0]
        lons = [110.0, 110.01]
        T, t0, diag = build_time_matrix(lats, lons, (29.99, 110.0), self.SEGS)
        assert diag["fallback_ratio_client_legs"] == 1.0


class TestRateEff:
    def test_short_leg_uses_full_city_rate(self):
        assert rate_eff(8.0, 1.0) == 8.0

    def test_long_leg_converges_highway(self):
        assert rate_eff(8.0, 25.0) == 2.0

    def test_mid_leg_interpolates(self):
        mid = rate_eff(8.0, 12.5)
        assert 2.0 < mid < 8.0
