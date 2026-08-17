"""Data structures for the visit scheduling framework.

Authoritative types. All other modules import from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Customer:
    """A customer location with periodic visit frequency.

    Attributes:
        code:       stable identifier (e.g. "S001")
        name:       display name (generic; no real client data)
        region:     geographic partition label (e.g. "R1" … "R5").
                    Within ``solve_visit_schedule``, this becomes the
                    "single region per day" hard constraint.
        frequency:  visits per 4-week cycle: 1, 2, or 4.
        latitude:   decimal degrees
        longitude:  decimal degrees
        weekday_history: tuple of length 7 = [#visits-on-Mon, …, #visits-on-Sun]
                   estimated from historical records; used by the consistency
                   objective. Optional.
    """

    code: str
    name: str
    region: str
    frequency: int
    latitude: float
    longitude: float
    weekday_history: tuple[int, int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0, 0)


@dataclass(frozen=True)
class HistoricalVisit:
    """One row of historical visit records.

    Attributes:
        customer_code:  which customer was visited
        date:            iso date string (e.g. "2026-06-02")
        order:           1..N visit order within the day (1-indexed)
        region:          region the visit occurred in
        travel_time_min: minutes spent on the leg to THIS customer
                         (either from base for the first of the day, or
                         from the previous customer).
    """

    customer_code: str
    date: str
    order: int
    region: str
    travel_time_min: float | None = None


@dataclass(frozen=True)
class Pattern:
    """A candidate weekly visit pattern for one customer.

    For frequency=4: 4-tuple of weekday indices (one per week, Mon=0..Fri=4).
    For frequency=2: 2-tuple of weekday indices (weeks 1,3 or 2,4).
    For frequency=1: 1-tuple of weekday index.
    """

    days: tuple[int, ...]
    frequency: int = 0
    consistency_cost: int = 0  # lower = closer to historical weekday habit


@dataclass
class SolveResult:
    """Output of :func:`set_partition.solve_visit_schedule`."""

    assignments: list[list[int]] = field(default_factory=list)
    regions: list[str | None] = field(default_factory=list)
    objectives: dict[str, int] = field(default_factory=dict)
    statuses: dict[str, str] = field(default_factory=dict)
    feasible: bool = True
