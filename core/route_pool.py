# -*- coding: utf-8 -*-
"""RoutePool: 全局路线池. 多算法产出 → 统一收集 → SP 重组合."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import List, Tuple, Optional, Dict, Set
from core.metric import day_km


@dataclass(frozen=True, order=True)
class Route:
    """一条日路线 (不可变, 用于池中去重)."""
    date: date
    stores: Tuple[int, ...]  # store indices in order
    cost: float = 0.0
    algo: str = ""

    def __post_init__(self):
        if not self.cost:
            object.__setattr__(self, 'cost', 0.0)


class RoutePool:
    """全局路线池. 收集/去重/注入/SP 输入."""

    def __init__(self):
        self._routes: Dict[date, Dict[Tuple[int, ...], Route]] = {}

    def add(self, route: Route):
        if route.date not in self._routes:
            self._routes[route.date] = {}
        key = route.stores
        # keep lowest cost for identical route
        if key not in self._routes[route.date] or route.cost < self._routes[route.date][key].cost:
            self._routes[route.date][key] = route

    def add_from_algo(self, days: dict, D: List[List[float]], algo_name: str = ""):
        """Add all routes from an algorithm's output."""
        for dd, seq in days.items():
            km = day_km(seq, D)
            self.add(Route(date=dd, stores=tuple(seq), cost=km, algo=algo_name))

    def inject(self, date: date, stores: List[int], cost: float, algo: str = "injected"):
        """Inject a route manually (e.g., human plan, external solver)."""
        self.add(Route(date=date, stores=tuple(stores), cost=cost, algo=algo))

    def get_routes(self, date: date) -> List[Route]:
        """Get all routes for a date."""
        return list(self._routes.get(date, {}).values())

    def get_all_dates(self) -> List[date]:
        return sorted(self._routes.keys())

    def best_for_date(self, date: date) -> Optional[Route]:
        """Return lowest-cost route for a date."""
        routes = self.get_routes(date)
        return min(routes, key=lambda r: r.cost) if routes else None

    def best_for_all(self) -> Dict[date, Route]:
        """For each date, pick the cheapest route (no coverage check)."""
        return {dd: self.best_for_date(dd) for dd in self.get_all_dates()}

    def stats(self) -> dict:
        total = sum(len(v) for v in self._routes.values())
        dates = len(self._routes)
        # source algo breakdown
        from collections import Counter
        src = Counter()
        for dd, routes in self._routes.items():
            for r in routes.values():
                if r.algo:
                    src[r.algo] += 1
        return {"total_routes": total, "dates": dates, "sources": dict(src)}

    def sp_input(self) -> tuple:
        """Return (dates, routes_per_date, route_cost_map) for Set Partitioning."""
        dates = self.get_all_dates()
        by_date = {dd: self.get_routes(dd) for dd in dates}
        return dates, by_date
