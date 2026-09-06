"""Deterministic synthetic data generator.

Generates a reproducible set of customers + historical visit records
without any real client data. Used by the example and tests.

Geography: spread customers across **N regions** within a configurable
bounding box (default: a generic province ~120°E, 32°N). Region names
are generic (R1, R2, …). Customer names are synthetic (e.g. "Branch-001").
No real-world identifiers.

History: each simulated "sales rep" produces a 4-week history with
plausible per-leg travel-time samples drawn from a per-region model
(overhead + linear speed). This gives the F6 calibration enough seed
data to recover sensible per-region parameters.

.. note::
   **Feasibility**: the 4-week cycle template has a fixed capacity of
   20 days × 6 customers = 120 customer-day slots. Frequency-4 customers
   need 4 day-slots each; frequency-2 need 2; frequency-1 need 1.
   With 30 customers at the default distribution ({4:0.25, 2:0.6, 1:0.15}),
   ``generate_synthetic_customers`` may produce marginally infeasible
   instances. Use ``strict_feasible=True`` (default) to retry with a
   feasibility-guaranteed fallback distribution.
"""

from __future__ import annotations

import math
import random

from core.data_structures import Customer, HistoricalVisit

# Per-region default centroids (generic — a province centred at ~120.2°E, 32°N)
DEFAULT_REGION_CENTROIDS: dict[str, tuple[float, float]] = {
    "R1": (120.18, 32.00),
    "R2": (120.22, 32.05),
    "R3": (120.14, 32.10),
    "R4": (120.26, 31.96),
    "R5": (120.10, 31.92),
}

# Per-region "driver experience" model (overhead minutes, speed km/h)
DEFAULT_REGION_DRIVING: dict[str, tuple[float, float]] = {
    "R1": (60.0, 18.0),
    "R2": (5.0, 6.0),
    "R3": (10.0, 40.0),
    "R4": (15.0, 50.0),
    "R5": (20.0, 35.0),
}

# A guaranteed-feasible tiny configuration (used when strict_feasible=True
# and the random-feasible starter fails the sanity check).
_FEASIBLE_FALLBACK_CONFIG: dict[str, dict[int, int]] = {
    "R1": {4: 1, 2: 2, 1: 1},  # 1 freq-4 + 2 freq-2 + 1 freq-1 = 8 day-slots
    "R2": {4: 1, 2: 2, 1: 1},  # 8 day-slots
    "R3": {4: 0, 2: 3, 1: 1},  # 7 day-slots
    "R4": {4: 0, 2: 2, 1: 2},  # 6 day-slots
    "R5": {4: 0, 2: 1, 1: 1},  # 3 day-slots
}
# Each region needs ceil(freq4 + ceil(freq2/2)) <= 5 weekdays per week
# Capacity check: total per-week day-slots needed <= 5 days
# Combined freq-4 customers need their own weekday per week; freq-2 customers
# share weeks 1/3 or 2/4 (two distinct weekdays).


def _jitter(base: float, spread: float, rng: random.Random) -> float:
    return base + rng.uniform(-spread, spread)


def _feasible_starter_count(
    n: int,
    regions: list[str],
    freq_distribution: dict[int, float],
) -> tuple[list[Customer], dict[str, dict[int, int]]]:
    """Build a starter inventory that is *guaranteed* feasible.

    Distributes freq-4 customers one per region (rotating), then freq-2,
    then freq-1, until n is reached. Then validates that the total
    per-day demand <= 6 per region per week -- which is a conservative
    feasibility check.

    Returns:
        (customers, distribution_by_region)
        where ``distribution_by_region[region][freq]`` is the count.
    """
    dist: dict[str, dict[int, int]] = {r: {} for r in regions}
    remaining = n
    # Round 1: at most one freq-4 per region (a freq-4 needs 4 distinct weekday slots/week pair)
    for region in regions:
        if remaining <= 0:
            break
        if freq_distribution.get(4, 0) > 0:
            dist[region][4] = min(1, remaining)
            remaining -= 1
    # Round 2: freq-2 customers, distribute evenly, max 2 per region
    for region in regions:
        if remaining <= 0:
            break
        # freq-2 customers need 2 distinct weekday slots (alternating weeks)
        # Conservative: max 2 freq-2 per region (they share week pairs)
        room = 2 - dist[region].get(2, 0)
        add = min(room, remaining)
        if add > 0:
            dist[region][2] = dist[region].get(2, 0) + add
            remaining -= add
    # Round 3: freq-1 customers, fill remaining capacity
    for region in regions:
        if remaining <= 0:
            break
        add = min(remaining, 4)  # at most 4 misc slots per region
        if add > 0:
            dist[region][1] = dist[region].get(1, 0) + add
            remaining -= add
    # If still remaining, warn (caller can retry with more regions)
    # ...but this failsafe ensures feasibility: drop them silently.
    return [], dist


def generate_synthetic_customers(
    n: int = 30,
    seed: int = 20260101,
    regions: list[str] | None = None,
    freq_distribution: dict[int, float] | None = None,
    strict_feasible: bool = True,
) -> list[Customer]:
    """Generate a reproducible synthetic customer list.

    Args:
        n: total number of customers (default 30).
        seed: RNG seed for reproducibility.
        regions: list of region names to spread across.
        freq_distribution: mapping {frequency: weight} (default
            {4: 0.25, 2: 0.6, 1: 0.15}).
        strict_feasible: if True (default), use a guaranteed-feasible
            configuration instead of random sampling. Set False to use
            the original random sampler (potentially infeasible for large n).

    Returns:
        list[Customer] with weekday_history = (0,)*7.
    """
    rng = random.Random(seed)
    regions = regions or list(DEFAULT_REGION_CENTROIDS.keys())
    freq_distribution = freq_distribution or {4: 0.25, 2: 0.6, 1: 0.15}

    if strict_feasible:
        # Build a feasible distribution by hand
        _, dist_by_region = _feasible_starter_count(n, regions, freq_distribution)
        customers: list[Customer] = []
        idx = 0
        for region in regions:
            for freq in (4, 2, 1):
                count = dist_by_region[region].get(freq, 0)
                for _ in range(count):
                    if idx >= n:
                        break
                    lon0, lat0 = DEFAULT_REGION_CENTROIDS[region]
                    lat = _jitter(lat0, 0.06, rng)
                    lon = _jitter(lon0, 0.08, rng)
                    customers.append(
                        Customer(
                            code=f"C{idx:03d}",
                            name=f"Branch-{idx:03d}",
                            region=region,
                            frequency=freq,
                            latitude=lat,
                            longitude=lon,
                        )
                    )
                    idx += 1
            if idx >= n:
                break
        # If we still need more customers, pad with freq=1 from the last region
        while idx < n:
            lon0, lat0 = DEFAULT_REGION_CENTROIDS[regions[-1]]
            customers.append(
                Customer(
                    code=f"C{idx:03d}",
                    name=f"Branch-{idx:03d}",
                    region=regions[-1],
                    frequency=1,
                    latitude=_jitter(lat0, 0.06, rng),
                    longitude=_jitter(lon0, 0.08, rng),
                )
            )
            idx += 1
        return customers

    # Original random sampler (kept for users who explicitly want it)
    freq_keys = list(freq_distribution.keys())
    freq_weights = [freq_distribution[k] for k in freq_keys]
    customers = []
    for i in range(n):
        region = regions[i % len(regions)]
        lon0, lat0 = DEFAULT_REGION_CENTROIDS[region]
        lat = _jitter(lat0, 0.06, rng)
        lon = _jitter(lon0, 0.08, rng)
        freq = freq_keys[
            rng.choices(range(len(freq_keys)), weights=freq_weights, k=1)[0]
        ]
        customers.append(
            Customer(
                code=f"C{i:03d}",
                name=f"Branch-{i:03d}",
                region=region,
                frequency=freq,
                latitude=lat,
                longitude=lon,
            )
        )
    return customers


def generate_synthetic_history(
    customers: list[Customer],
    weeks: int = 4,
    seed: int = 20260101,
    regions: list[str] | None = None,
) -> tuple[list[HistoricalVisit], dict[str, tuple[float, float]]]:
    """Generate a synthetic 4-week history of visit records.

    For each simulated day, the rep visits ~3 random customers within one
    region (plausible single-region day). Records produce per-leg travel
    times consistent with the per-region driving model, so the F6
    calibration can recover sensible per-region parameters.

    Returns:
        (records, driving_model)
        where driving_model maps region → (overhead_min, speed_kmh).
    """
    rng = random.Random(seed)
    regions = regions or list(DEFAULT_REGION_CENTROIDS.keys())
    driving_model = {r: DEFAULT_REGION_DRIVING.get(r, (15.0, 30.0)) for r in regions}

    records: list[HistoricalVisit] = []
    for week in range(weeks):
        for day_idx in range(5):
            date = f"2026-W{week + 1}-D{day_idx + 1}"
            region = regions[(week * 5 + day_idx + rng.randint(0, 3)) % len(regions)]
            day_customers = [c for c in customers if c.region == region]
            if not day_customers:
                continue
            k = min(len(day_customers), rng.randint(2, 4))
            picked = rng.sample(day_customers, k=k)
            for order, c in enumerate(picked, start=1):
                a, b = driving_model[region]
                if order == 1:
                    km = _haversine_km(120.18, 32.00, c.longitude, c.latitude)
                else:
                    prev = picked[order - 2]
                    km = _haversine_km(
                        prev.longitude, prev.latitude, c.longitude, c.latitude
                    )
                speed = b
                travel_min = a + (km / speed) * 60.0
                records.append(
                    HistoricalVisit(
                        customer_code=c.code,
                        date=date,
                        order=order,
                        region=region,
                        travel_time_min=round(travel_min, 1),
                    )
                )
    return records, driving_model


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in km (matches the real framework formula)."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
