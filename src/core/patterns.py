"""Candidate weekly pattern generation.

For each customer, enumerate all valid 4-week / 5-day patterns that
satisfy their visit frequency. This is the *preprocessing* that
decouples the combinatorial structure from the solver — the solver
then just chooses amongst pre-computed candidates.

Frequency 4: 5^4 = 625 patterns (one weekday per week, all 4 weeks)
Frequency 2: 2 × 5 × 5 = 50 patterns (alternating weeks 1,3 or 2,4)
Frequency 1: 20 patterns (any single weekday)
"""

from __future__ import annotations

from core.data_structures import Customer, Pattern

DAYS_PER_WEEK = 5  # Mon .. Fri
WEEKS_PER_CYCLE = 4


def generate_patterns(customers: list[Customer]) -> list[list[Pattern]]:
    """Return one pattern list per customer, all valid for the 4-week cycle.

    Each pattern is a tuple of weekday indices (0–4) representing the
    visit-day within each constituent week. Customers must select one
    of their own patterns via the set-partitioning model.
    """
    return [_one_customer_patterns(c) for c in customers]


def _one_customer_patterns(c: Customer) -> list[Pattern]:
    """Generate valid weekday patterns for one customer."""
    if c.frequency not in (1, 2, 4):
        raise ValueError(
            f"Customer {c.code}: frequency {c.frequency} not supported "
            f"(only 1, 2, 4 are supported in the 4-week cycle)."
        )
    if c.frequency == 4:
        # One weekday per week, all 4 weeks ⇒ 5^4 = 625 patterns.
        return [
            Pattern(
                days=(w1, w2, w3, w4),
                frequency=4,
                consistency_cost=_consistency_cost(c, (w1, w2, w3, w4)),
            )
            for w1 in range(DAYS_PER_WEEK)
            for w2 in range(DAYS_PER_WEEK)
            for w3 in range(DAYS_PER_WEEK)
            for w4 in range(DAYS_PER_WEEK)
        ]
    if c.frequency == 2:
        # Alternating weeks: either weeks {0,2} or weeks {1,3}.
        return [
            Pattern(
                days=(w_a, w_b),
                frequency=2,
                consistency_cost=_consistency_cost(c, (w_a, w_b)),
            )
            for wa in (0, 2)
            for wb in (1, 3)
            for w_a in range(DAYS_PER_WEEK)
            for w_b in range(DAYS_PER_WEEK)
        ]
    # frequency == 1
    return [
        Pattern(days=(d,), frequency=1, consistency_cost=_consistency_cost(c, (d,)))
        for d in range(DAYS_PER_WEEK)
    ]


def _consistency_cost(c: Customer, weekdays: tuple[int, ...]) -> int:
    """Cost = deviation from the customer's historical weekday distribution.

    Uses only weekdays 0..4 (Mon..Fri). Lower = more consistent with
    the rep's historical visit habit. A customer with no recorded history
    pays no cost (peak = 0 → 0).
    """
    hist = c.weekday_history[:5]
    if not hist:
        return 0
    peak = max(hist)
    if peak == 0:
        return 0
    return sum((peak - hist[d]) for d in weekdays)
