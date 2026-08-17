"""End-to-end demo of the column-generation PVRP on SYNTHETIC data.

Run from the repo root:
    python -m examples.synthetic_pvrp_cg

Generates a small reproducible instance (no real client data), runs all
three calibers (open / closed / time-calibrated) plus the ALNS baseline,
and prints a comparison table. This is the recommended first thing to run
after cloning.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.pvrp_cg import baselines, solver
from algos.pvrp_cg.calibration import rate_eff
from algos.pvrp_cg.travel import haversine

SEED = 20260815
N_CUSTOMERS = 10
DAYS = 20
DEPOT = (31.30, 120.60)  # synthetic depot


def make_instance():
    """Synthetic customers spread around the depot with two density zones."""
    rng = random.Random(SEED)
    lats, lons, counties, svc = [], [], [], []
    for i in range(N_CUSTOMERS):
        if i < N_CUSTOMERS // 2:
            # dense urban zone: close to depot, high service time
            lat = DEPOT[0] + rng.uniform(-0.06, 0.06)
            lon = DEPOT[1] + rng.uniform(-0.06, 0.06)
            counties.append("urban")
            svc.append(rng.uniform(40, 70))
        else:
            # suburban zone: farther, lower service time
            lat = DEPOT[0] + rng.uniform(-0.25, 0.25)
            lon = DEPOT[1] + rng.uniform(-0.25, 0.25)
            counties.append("suburban")
            svc.append(rng.uniform(25, 45))
        lats.append(lat)
        lons.append(lon)
    # frequencies: mix of 1/2/3
    freq = [rng.choice([1, 1, 2, 2, 3]) for _ in range(N_CUSTOMERS)]
    return lats, lons, counties, svc, freq


def build_matrices(lats, lons):
    """Haversine distance matrix + depot legs (km)."""
    n = len(lats)
    D = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(n):
            D[i][j] = haversine(lats[i], lons[i], lats[j], lons[j])
        D[i][n] = haversine(lats[i], lons[i], DEPOT[0], DEPOT[1])
        D[n][i] = D[i][n]
    return D


def build_time_matrix(D, counties, svc):
    """Calibrated time matrix: per-county rate × distance + service time."""
    n = len(counties)
    rates = {"urban": 8.0, "suburban": 3.0}  # min/km
    T = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            km = D[i][j]
            T[i][j] = rate_eff(rates[counties[j]], km) * km
    t0 = [rate_eff(rates[counties[i]], D[i][n]) * D[i][n] for i in range(n)]
    return T, t0


def main():
    print("=" * 70)
    print("Synthetic PVRP-CG demo  (no real client data)")
    print("=" * 70)
    lats, lons, counties, svc, freq = make_instance()
    D_full = build_matrices(lats, lons)
    n = N_CUSTOMERS
    D_cust = [row[:n] for row in D_full[:n]]
    depot_idx = n
    print(f"Customers: {n}, total visits: {sum(freq)}, horizon: {DAYS} days")
    print(f"Frequency mix: { {f: freq.count(f) for f in sorted(set(freq))} }")

    # --- Caliber 1: open route ---
    print("\n[1] Open route (customer chain only)")
    a, t, s, st = solver.solve_open_cg(
        n, D_cust, freq, days=DAYS, time_limit=20, verbose=False
    )
    print(f"    total = {t:.1f} km, status = {s}, columns = {st['n_columns']}")

    # --- Caliber 2: closed loop (depot round-trip) ---
    print("\n[2] Closed loop (depot round-trip, distance)")
    a, t, s, st = solver.solve_distance_cg(
        n, D_full, depot_idx, freq, days=DAYS, time_limit=20, verbose=False
    )
    print(f"    total = {t:.1f} km, status = {s}, columns = {st['n_columns']}")

    # --- Caliber 3: time-calibrated ---
    print("\n[3] Time-calibrated (workhours, 9h cap)")
    T, t0 = build_time_matrix(D_full, counties, svc)
    a, t, s, st = solver.solve_time_cg(
        n, T, t0, svc, freq, days=DAYS, daily_cap=540, time_limit=20, verbose=False
    )
    active = sum(1 for d in a if d) if a else 0
    print(
        f"    total = {t:.0f} min ({t / 60:.1f} h), status = {s}, "
        f"active days = {active}, balanced = {st.get('balanced')}"
    )
    if a:
        loads = st.get("loads", [])
        if loads:
            print(f"    day loads: min {min(loads):.0f}, max {max(loads):.0f} min")

    # --- ALNS baseline ---
    print("\n[4] ALNS baseline (same constraints, 30 s budget)")
    t0_legs = [D_full[depot_idx][i] for i in range(n)]
    alns = baselines.ALNS(
        n,
        freq,
        days=DAYS,
        col_cost_fn=lambda ids: solver._col_cost_closed(D_cust, t0_legs, ids),
        daily_cap=None,
    )
    b, bf, it, ast = alns.run(time_budget=15)
    print(
        f"    total = {bf:.1f} km, iterations = {it}, "
        f"max day load = {ast['max_load']:.0f} visits"
    )

    print("\n" + "=" * 70)
    print("Done. All three calibers + ALNS baseline ran on synthetic data.")
    print("=" * 70)


if __name__ == "__main__":
    main()
