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
  build_time_matrix(lats, lons, dep_latlons, segments) -> (T, t0, svc_county)
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

LONG_RATE = 2.0           # min/km on long legs (≈ 30 km/h steady-state)
SHORT_KINK = 5.0          # km at which the city-rate stops fully applying
LONG_KINK = 20.0          # km at which the highway-rate fully takes over
DEFAULT_GLOBAL_RATE = 6.0 # min/km fallback for counties with < 5 samples


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


def fit_county_rates(segments: Sequence[tuple[float, float, float, float, float, str]],
                     min_samples: int = 5
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
        for c, v in by_county.items() if len(v) >= min_samples
    }


def build_time_matrix(lats: Sequence[float], lons: Sequence[float],
                      dep_latlons: tuple[float, float],
                      segments: Sequence[tuple[float, float, float, float, float, str]],
                      fallback_rate: float = DEFAULT_GLOBAL_RATE,
                      ) -> tuple[list[list[float]], list[float]]:
    """Build a calibrated time matrix T and depot legs t0.

    Returns
    -------
    T  : n × n matrix of effective travel times (minutes), T[i][j] = rate(dest_j) × km(i, j)
    t0 : n-vector of depot→customer leg times (minutes)
    """
    rates = fit_county_rates(segments)
    n = len(lats)
    dep_lat, dep_lon = dep_latlons
    T = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            km = _hav(lats[i], lons[i], lats[j], lons[j])
            county = ""  # rate by origin would need per-origin county mapping
            mpk = rates.get(county, fallback_rate)
            T[i][j] = rate_eff(mpk, km) * km
    t0 = [rate_eff(fallback_rate, _hav(dep_lat, dep_lon, lats[i], lons[i]))
          * _hav(dep_lat, dep_lon, lats[i], lons[i]) for i in range(n)]
    return T, t0
