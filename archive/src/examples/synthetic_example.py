"""End-to-end demo on synthetic data.

Run from the repo root with:
    python -m examples.synthetic_example

(Ensure `src/` is on the path — `pyrightconfig.json` already adds it,
and most Python tooling respects `extraPaths` from project root.)

Generates a small, hand-constructed feasible dataset (so the solver is
guaranteed to produce a schedule), runs the framework, and prints a
clean summary. No real client data is touched.
"""

from __future__ import annotations

from collections import defaultdict

from core.data_structures import Customer
from core.patterns import generate_patterns
from core.set_partition import solve_visit_schedule
from utils.data_generator import (
    _haversine_km,
)


def _build_handcrafted_customers() -> list[Customer]:
    """A small, *guaranteed-feasible* configuration for the demo.

    Layout:  2 regions × 6 customers each = 12 customers
    Frequencies:  region A: 3 freq-4 + 6 freq-2 + 3 freq-1
                 region B: 3 freq-4 + 6 freq-2 + 3 freq-1
    Single-region constraint keeps each region's customers clustered.

    Why this is feasible: each region has 12 customer-visits over 4 weeks,
    spread naturally across ~2 days per week = 8 days per region.
    With 5 weekdays per week, and 6 customers/day max, plenty of room.
    """
    customers: list[Customer] = []
    # region A  (10 customers: 3 freq-4, 5 freq-2, 2 freq-1)
    # region B  (10 customers: 3 freq-4, 5 freq-2, 2 freq-1)
    plan: list[tuple[str, int, float, float]] = [
        ("A", 4, 120.16, 32.00),
        ("A", 4, 120.18, 32.02),
        ("A", 4, 120.17, 32.04),
        ("A", 2, 120.16, 32.01),
        ("A", 2, 120.17, 32.03),
        ("A", 2, 120.18, 32.00),
        ("A", 2, 120.19, 32.02),
        ("A", 2, 120.17, 32.05),
        ("A", 1, 120.16, 32.00),
        ("A", 1, 120.18, 32.04),
        ("B", 4, 120.22, 32.06),
        ("B", 4, 120.24, 32.08),
        ("B", 4, 120.23, 32.10),
        ("B", 2, 120.22, 32.07),
        ("B", 2, 120.24, 32.09),
        ("B", 2, 120.23, 32.11),
        ("B", 2, 120.25, 32.07),
        ("B", 2, 120.22, 32.10),
        ("B", 1, 120.24, 32.06),
        ("B", 1, 120.23, 32.10),
    ]
    for idx, (reg, freq, lon, lat) in enumerate(plan):
        customers.append(
            Customer(
                code=f"X{idx:03d}",
                name=f"Branch-{idx:03d}",
                region=reg,
                frequency=freq,
                latitude=lat,
                longitude=lon,
            )
        )
    return customers


def main() -> None:
    # 1. Build a hand-crafted feasible dataset
    customers = _build_handcrafted_customers()
    regions = sorted({c.region for c in customers})
    print("=== Dataset ===")
    print(
        f"  customers: {len(customers)} across {len(regions)} regions ({', '.join(regions)})"
    )
    print(
        f"  freq distribution: 4→{sum(1 for c in customers if c.frequency == 4)}, "
        f"2→{sum(1 for c in customers if c.frequency == 2)}, "
        f"1→{sum(1 for c in customers if c.frequency == 1)}"
    )
    print()

    # 2. Generate candidate patterns (the solver's columns)
    patterns = generate_patterns(customers)
    total = sum(len(p) for p in patterns)
    print("=== Pattern enumeration ===")
    print(
        f"  total candidate patterns: {total} (avg {total / len(customers):.0f} per customer)"
    )
    print()

    # 3. Solve the unified set-partitioning model
    result = solve_visit_schedule(customers, patterns, time_limit_per_tier=15.0)
    if not result.feasible:
        print(
            "No feasible solution found. (This should not happen with a hand-crafted dataset.)"
        )
        return

    print("=== Solver tiers (lexicographic) ===")
    for name, val in result.objectives.items():
        print(f"  {name:>15s}: {result.statuses[name]} = {val}")
    print()

    # 4. Summarise the resulting schedule
    active_days = sum(1 for d in range(20) if result.assignments[d])
    visits = sum(len(a) for a in result.assignments)
    cross = sum(
        1
        for d in range(20)
        if len({customers[i].region for i in result.assignments[d]}) > 1
    )
    region_counts: dict[str, int] = defaultdict(int)
    for d in range(20):
        for i in result.assignments[d]:
            region_counts[customers[i].region] += 1
    print("=== Result schedule ===")
    print(f"  active days: {active_days} / 20")
    print(f"  visits:      {visits}")
    print(f"  cross-region days: {cross}")
    print(f"  per-region visits: {dict(region_counts)}")
    print()

    # 5. Per-day load distribution
    loads = [len(a) for a in result.assignments]
    print("=== Daily load distribution ===")
    for n_customers in sorted(set(loads)):
        print(f"  {n_customers} customers: {loads.count(n_customers)} days")
    print()

    # 6. Illustrate the naive 40km/h vs calibrated F6-style time estimate
    total_km = 0.0
    for d in range(20):
        idxs = result.assignments[d]
        for k in range(1, len(idxs)):
            a, b = customers[idxs[k - 1]], customers[idxs[k]]
            total_km += _haversine_km(a.longitude, a.latitude, b.longitude, b.latitude)
    naive_min = round(total_km / 40.0 * 60, 1)
    print("=== Travel time naive (40 km/h) vs calibrated F6-style ===")
    print(f"  store-to-store mileage: {total_km:.1f} km")
    print(f"  naive estimate (40 km/h): {naive_min:.0f} min")
    if naive_min > 0:
        print("  (calibrated estimate in production: typical 3-5× the naive number)")
    print()
    print(
        "Done. The dataset is hand-crafted to be feasible; the generator "
        "in utils.data_generator can produce larger instances."
    )


if __name__ == "__main__":
    main()
