"""
Time-matrix calibration from historical visit data.

Given a list of (from_lat, from_lon, to_lat, to_lon, observed_minutes) tuples
(door-to-door time = next-entry − prev-entry − prev-service), fit a per-county
piecewise model:

    rate_eff(mpk_c, km) = mpk_c                       if km ≤ 5
                         2.0 + (mpk_c − 2.0)(20−km)/15   if 5 < km < 20
                         2.0                          if km ≥ 20

where mpk_c is the county-specific median min-per-km (only counties with
n ≥ 5 observations are used; others fall back to a global default).

The two-segment form preserves the urban density premium (mall/curb-search
overhead dominates short legs) and converges to a fixed highway speed
(≈ 30 km/h) on long legs — preventing the calendar-time model from
"exploding" on long inter-county legs.

Public entry point:
  build_time_matrix(lats, lons, dep_latlons, segments, fallback_rate=6.0,
                    counties=None, depot_county=None)
    -> (T, t0, diagnostics)

counties 传入后 destination-county 校准才生效; 省略时全部回退全局 rate
(diagnostics.fallback_ratio_client_legs == 1.0)。
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

LONG_RATE = 2.0  # min/km on long legs (≈ 30 km/h steady-state)
SHORT_KINK = 5.0  # km at which the city-rate stops fully applying
LONG_KINK = 20.0  # km at which the highway-rate fully takes over
DEFAULT_GLOBAL_RATE = 6.0  # min/km fallback for counties with < 5 samples


def _hav(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def rate_eff(mpk: float, km: float) -> float:
    if km <= SHORT_KINK:
        return mpk
    if km >= LONG_KINK:
        return LONG_RATE
    return LONG_RATE + (mpk - LONG_RATE) * (LONG_KINK - km) / (LONG_KINK - SHORT_KINK)


def fit_county_rates(
    segments: Sequence[tuple[float, float, float, float, float, str]],
    min_samples: int = 5,
) -> dict[str, float]:
    """Fit per-county min/km from observed (from_lat, from_lon, to_lat, to_lon,
    obs_min, county) segments.

    Only counties with at least `min_samples` observations are returned; others
    fall back to ``DEFAULT_GLOBAL_RATE`` at call time.
    """
    by_county: dict[str, list[float]] = defaultdict(list)
    for lat1, lon1, lat2, lon2, obs, county in segments:
        km = _hav(lat1, lon1, lat2, lon2)
        if km < 0.5:
            continue
        by_county[county].append(obs / km)
    return {
        c: float(sorted(v)[len(v) // 2])
        for c, v in by_county.items()
        if len(v) >= min_samples
    }


def build_time_matrix(
    lats: Sequence[float],
    lons: Sequence[float],
    dep_latlons: tuple[float, float],
    segments: Sequence[tuple[float, float, float, float, float, str]],
    fallback_rate: float = DEFAULT_GLOBAL_RATE,
    counties: Sequence[str] | None = None,
    depot_county: str | None = None,
) -> tuple[list[list[float]], list[float], dict]:
    """Build a calibrated time matrix T, depot legs t0, and diagnostics.

    Args:
        lats/lons: 客户坐标。
        dep_latlons: (depot_lat, depot_lon)。
        segments: 历史行程 (from_lat, from_lon, to_lat, to_lon, obs_min, county)。
        fallback_rate: county 样本不足/未匹配时的全局回退 min/km。
        counties: 客户所属 county (len == len(lats)); None = 全部使用 fallback
            (兼容旧调用形态, 但 diagnostics 将标记 fallback_ratio = 1.0)。
        depot_county: depot 所属 county; None = 回退 fallback_rate 或首个客户 county。

    Returns:
        T  : n×n 校准时间矩阵 (分钟), T[i][j] = rate_eff(mpk_dest, km) × km —
             采用 **destination county** (到达端密度主导城市拥堵 premium)。
        t0 : depot→客户 leg 时间 (分钟), 使用各客户的 county rate。
        diagnostics: {rates_fitted, n_customers_with_county, fallback_ratio_client_legs,
                      fallback_ratio_depot_legs, warn}
    """
    rates = fit_county_rates(segments)
    n = len(lats)
    dep_lat, dep_lon = dep_latlons

    if counties is not None and len(counties) != n:
        raise ValueError(f"counties 长度 {len(counties)} != 客户数 {n}")

    def _mpk_for(county: str | None) -> tuple[float, bool]:
        if county is not None and county in rates:
            return rates[county], True
        return fallback_rate, False

    cust_county = list(counties) if counties is not None else [None] * n

    T = [[0.0] * n for _ in range(n)]
    fb_client = 0
    total_client = 0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            km = _hav(lats[i], lons[i], lats[j], lons[j])
            mpk, fitted = _mpk_for(cust_county[j])
            total_client += 1
            if not fitted:
                fb_client += 1
            T[i][j] = rate_eff(mpk, km) * km

    # depot legs: 显式 depot_county, 否则尝试首个客户 county (同区常见), 否则 fallback
    leg_county = depot_county if depot_county is not None else (cust_county[0] if n else None)
    t0 = []
    fb_depot = 0
    for i in range(n):
        mpk, fitted = _mpk_for(leg_county)
        if not fitted:
            fb_depot += 1
        km = _hav(dep_lat, dep_lon, lats[i], lons[i])
        t0.append(rate_eff(mpk, km) * km)

    diagnostics = {
        "rates_fitted": dict(rates),
        "counties_with_rates": sorted(rates),
        "fallback_ratio_client_legs": (fb_client / total_client) if total_client else 0.0,
        "fallback_ratio_depot_legs": (fb_depot / n) if n else 0.0,
        "warn": (
            f"{fb_client}/{total_client} client legs 与 {fb_depot}/{n} depot legs "
            f"使用了全局回退 {fallback_rate} min/km"
            if (fb_client or fb_depot)
            else ""
        ),
    }
    return T, t0, diagnostics
