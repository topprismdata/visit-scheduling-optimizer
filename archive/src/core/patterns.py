"""Candidate weekly pattern generation.

For each customer, enumerate all valid 4-week / 5-day patterns that
satisfy their visit frequency. Each pattern uses ABSOLUTE day indices
(0-19 for a 4-week cycle) — NOT weekday indices.
This is the *preprocessing* that decouples the combinatorial
structure from the solver.

Week index → absolute day:  week * 5 + weekday
  week 0 (Mon-Fri): days 0-4
  week 1 (Mon-Fri): days 5-9
  week 2 (Mon-Fri): days 10-14
  week 3 (Mon-Fri): days 15-19

Frequency 4: 5^4 = 625 patterns (one weekday per week, all 4 weeks)
Frequency 2: 50 patterns       (alternating 2 weeks, 2 weekdays)
Frequency 1: 20 patterns       (any single weekday)
"""

from __future__ import annotations

from itertools import product

from core.data_structures import Customer, Pattern

DAYS_PER_WEEK = 5  # Mon .. Fri
WEEKS_PER_CYCLE = 4  # default; callers should pass `weeks` to generate_patterns


def _weekday_to_abs(week: int, weekday: int) -> int:
    """Map (week, weekday) → absolute day index (0-based)."""
    return week * DAYS_PER_WEEK + weekday


def generate_patterns(
    customers: list[Customer],
    weeks: int = WEEKS_PER_CYCLE,
) -> list[list[Pattern]]:
    """Return one pattern list per customer, all valid for the n-week cycle.

    Each pattern is a tuple of ABSOLUTE day indices (0 to weeks*5-1).
    Customers must select one of their own patterns via the
    set-partitioning model.
    """
    return [_one_customer_patterns(c, weeks) for c in customers]


def _one_customer_patterns(c: Customer, weeks: int = WEEKS_PER_CYCLE) -> list[Pattern]:
    """Generate valid absolute-day patterns for one customer."""
    if c.frequency not in (1, 2, 4):
        raise ValueError(
            f"Customer {c.code}: frequency {c.frequency} not supported "
            f"(only 1, 2, 4 are supported in the {weeks}-week cycle)."
        )
    if c.frequency == 4:
        # One weekday per week, all `weeks` weeks must be visited.
        # Select which weekday (0-4) for each of the `weeks` weeks.
        patterns: list[Pattern] = []
        for weekdays in product(range(DAYS_PER_WEEK), repeat=weeks):
            abs_days = tuple(_weekday_to_abs(w, d) for w, d in enumerate(weekdays))
            patterns.append(
                Pattern(
                    days=abs_days,
                    frequency=4,
                    consistency_cost=_consistency_cost(c, weekdays),
                )
            )
        return patterns

    if c.frequency == 2:
        # Two visits at least 14 calendar days apart.
        # Working day d maps to calendar offset = (d//5)*7 + (d%5).
        # 14 calendar days = 2 full weeks. Check actual calendar gap per pair.
        patterns = []
        min_calendar_gap = 14
        for d1 in range(weeks * DAYS_PER_WEEK):
            for d2 in range(d1 + 1, weeks * DAYS_PER_WEEK):
                cal_gap = (d2 // 5) * 7 + (d2 % 5) - ((d1 // 5) * 7 + (d1 % 5))
                if cal_gap < min_calendar_gap:
                    continue
                patterns.append(
                    Pattern(
                        days=(d1, d2),
                        frequency=2,
                        consistency_cost=_consistency_cost(
                            c, (d1 % DAYS_PER_WEEK, d2 % DAYS_PER_WEEK)
                        ),
                    )
                )
        return patterns

    # frequency == 1: visit exactly once, on any weekday in any week.
    patterns = []
    for w in range(weeks):
        for d in range(DAYS_PER_WEEK):
            abs_day = _weekday_to_abs(w, d)
            patterns.append(
                Pattern(
                    days=(abs_day,),
                    frequency=1,
                    consistency_cost=_consistency_cost(c, (d,)),
                )
            )
    return patterns


def _consistency_cost(c: Customer, weekdays: tuple[int, ...]) -> int:
    """Cost = deviation from the customer's historical weekday distribution.

    Uses only weekdays 0..4 (Mon..Fri). Lower = more consistent with
    the rep's historical visit habit. A customer with no recorded history
    pays no cost (peak = 0 → 0).
    """
    hist = c.weekday_history[:DAYS_PER_WEEK]
    if not hist:
        return 0
    peak = max(hist)
    if peak == 0:
        return 0
    return sum((peak - hist[d]) for d in weekdays)
