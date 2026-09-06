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
from algos.pvrp_cg.calibration import build_time_matrix, rate_eff
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
    # 合成校准数据: 重现旧演示的 urban≈8 / suburban≈3 min/km 密度差,
    # 通过 fit_county_rates 真实拟合 (不再硬编码) — 校准实际进入时间矩阵
    rng_cal = random.Random(SEED)
    calib_segments = []
    for _ in range(12):   # urban 短腿: ~1 km × ~8 min/km
        lat1, lon1 = lats[0] + rng_cal.uniform(-0.004, 0.004), lons[0] + rng_cal.uniform(-0.004, 0.004)
        calib_segments.append((lat1, lon1, lat1 + 0.006, lon1 + 0.008, rng_cal.uniform(7.0, 9.0), "urban"))
    for _ in range(12):   # suburban 短腿: ~1 km × ~3 min/km
        lat1, lon1 = lats[-1] + rng_cal.uniform(-0.01, 0.01), lons[-1] + rng_cal.uniform(-0.01, 0.01)
        calib_segments.append((lat1, lon1, lat1 + 0.006, lon1 + 0.008, rng_cal.uniform(2.5, 3.5), "suburban"))

    T, t0, calib_diag = build_time_matrix(
        lats, lons, DEPOT, calib_segments,
        counties=counties,
    )
    print(f"    calibration: fitted={calib_diag['counties_with_rates']}; "
          f"global-fallback legs: client {calib_diag['fallback_ratio_client_legs']:.0%} / "
          f"depot {calib_diag['fallback_ratio_depot_legs']:.0%}")
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
