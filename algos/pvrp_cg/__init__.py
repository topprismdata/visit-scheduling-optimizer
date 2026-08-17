"""
Column-generation PVRP solver with data-calibrated time matrix.

Three calibers in one file:
  1. Open route (customer-only)         — distance only
  2. Closed loop (depot round-trip)     — distance + commute
  3. Time-calibrated (workhours)        — distance × per-county rate + service time + 32 min dwell

Method: set-partitioning master + dual-guided column generation (CP-SAT for
the IP, pywraplp GLOP for the LP relaxation). Column cost is the EXACT
closed/open route cost via Held–Karp (n ≤ 9) or NN+2-opt fallback.

Public entry points:
  solve_distance_cg(n, D, depot_idx, freq, ...)   → distance caliber
  solve_time_cg(n, T, t0, svc, freq, ...)        → time-calibrated caliber
  solve_open_cg(n, D, freq, ...)                  → open route
"""
