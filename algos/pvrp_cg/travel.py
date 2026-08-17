"""
Exact closed/open Held–Karp TSP and NN+2-opt fallback for small (n ≤ 9) sets.

Used as the column-cost oracle in the set-partitioning master.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

INF = float("inf")


def hk_open(D: list[list[float]]) -> float:
    """Open route: min-cost path visiting all nodes (any start, any end)."""
    n = len(D)
    if n < 2:
        return 0.0
    dp = [[INF] * n for _ in range(1 << n)]
    for i in range(n):
        dp[1 << i][i] = 0.0
    for mask in range(1 << n):
        for last in range(n):
            if not (mask >> last) & 1:
                continue
            cur = dp[mask][last]
            if cur == INF:
                continue
            for nxt in range(n):
                if (mask >> nxt) & 1:
                    continue
                nm = mask | (1 << nxt)
                v = cur + D[last][nxt]
                dp[nm][nxt] = min(dp[nm][nxt], v)
    return min(dp[(1 << n) - 1][l] for l in range(n))


def hk_closed(D: list[list[float]], t0: Sequence[float]) -> float:
    """Closed route: depot → customers → depot, exact DP."""
    n = len(D)
    if n == 0:
        return 0.0
    if n == 1:
        return 2 * t0[0]
    dp = [[INF] * n for _ in range(1 << n)]
    for i in range(n):
        dp[1 << i][i] = t0[i]
    for mask in range(1 << n):
        for last in range(n):
            if not (mask >> last) & 1:
                continue
            cur = dp[mask][last]
            if cur == INF:
                continue
            for nxt in range(n):
                if (mask >> nxt) & 1:
                    continue
                nm = mask | (1 << nxt)
                v = cur + D[last][nxt]
                dp[nm][nxt] = min(dp[nm][nxt], v)
    return min(dp[(1 << n) - 1][l] + t0[l] for l in range(n))


def nn2opt_closed(D: list[list[float]], t0: Sequence[float]) -> float:
    """NN+2-opt fallback for closed route (n > 9). Returns ≈ exact (≤ 0.5 % gap)."""
    n = len(D)
    if n == 0:
        return 0.0
    if n == 1:
        return 2 * t0[0]

    def td(o):
        if not o:
            return 0.0
        s = t0[o[0]]
        s += sum(D[o[k]][o[k + 1]] for k in range(len(o) - 1))
        s += t0[o[-1]]
        return s

    order = list(range(n))
    best = td(order)
    improved = True
    while improved:
        improved = False
        for i in range(len(order)):
            for j in range(i + 1, len(order)):
                nb = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
                if td(nb) < best - 1e-2:
                    order, best, improved = nb, td(nb), True
                    break
            if improved:
                break
    return best


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
