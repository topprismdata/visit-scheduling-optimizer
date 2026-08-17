# Visit Scheduling Optimizer

**Data-calibrated periodic vehicle routing for field-sales visit scheduling.**

A production-grade OR framework that schedules recurring store visits for FMCG sales representatives — satisfying visit frequencies, inter-visit gaps, and daily work-hour capacity — while minimizing total travel + service time.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-9.x-green.svg)](https://developers.google.com/optimization)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What problem does this solve?

A sales representative must visit 20–50 stores on a recurring monthly cycle. Each store has a required visit frequency (1×, 2×, or 4× per month), and consecutive visits to the same store must be spaced apart. The rep works ≤ 9 hours per day. The goal: **minimize total work time** (driving + parking + in-store service) while satisfying all constraints.

In practice this is done by spreadsheet and intuition — leaving 20–60% of potential efficiency on the table and routinely breaking frequency rules. This repository solves it properly with operations research.

## Key results (anonymized industry study, 7 reps × 235 customers)

| Metric | Business-actual | This framework | Improvement |
| -------- | ---------------- | ---------------- | ------------- |
| Active working days (20-day horizon) | 139 | **117** | **−16%** |
| In-day work hours | 768 h | **569 h** | **−26%** |
| Route distance (OSRM road network) | 10 056 km | **6 345 km** | **−37%** |
| Frequency compliance | 92–100% | **100%** (hard constraint) | ✓ |
| Daily work-hour cap violations | 12% of days | **0%** | ✓ |

Cross-county visits **emerge** from the depot's spatial position (matching the 29–60% rate observed in human operation) rather than being imposed as a constraint.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT                                                          │
│  customers × coordinates × visit frequencies × service times    │
│  + historical visit records (for time calibration)              │
│  + depot location                                               │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. TIME CALIBRATION  (calibration.py)                          │
│     319 actual door-to-door segments → per-county min/km        │
│     Two-segment model: urban density premium + highway speed    │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. SET-PARTITIONING MASTER + COLUMN GENERATION  (solver.py)    │
│     Column = feasible day-group G with exact route cost         │
│     LP relaxation (GLOP) → dual prices π, μ                     │
│     Pricing: greedy marginal-gain column construction           │
│     Final IP solve: CP-SAT (300 s, 8 workers)                   │
│     Workload balancing: min-max day-load re-assignment          │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  OUTPUT                                                         │
│  Per-day schedule: which stores, departure, return, total time  │
│  LP lower bound (optimality certificate)                        │
│  Comparison vs ALNS metaheuristic baseline                      │
└─────────────────────────────────────────────────────────────────┘
```

### Three distance/time calibers

| Caliber | What it measures | Use case |
| --------- | ----------------- | ---------- |
| **Open route** | Customer-to-customer chain only | Route efficiency benchmark |
| **Closed loop** | Depot → customers → depot | Real commuting distance |
| **Time-calibrated** | Calibrated travel + service + dwell | Executable work plan |

---

## Quick start

```bash
# Clone
git clone https://github.com/topprismdata/visit-scheduling-optimizer.git
cd visit-scheduling-optimizer

# Install dependencies
pip install ortools numpy pandas matplotlib

# Run the synthetic demo (no real data needed)
python examples/synthetic_pvrp_cg.py
```

Expected output: three calibers + ALNS baseline on a 10-customer synthetic instance, all completing in < 60 s.

### Using the solver on your own data

```python
from algos.pvrp_cg import solver
from algos.pvrp_cg.calibration import build_time_matrix
from algos.pvrp_cg.travel import haversine

# 1. Build distance matrix (n customers + 1 depot)
n = len(customers)
D = [[haversine(lat_i, lon_i, lat_j, lon_j) for j in range(n+1)] for i in range(n+1)]

# 2. Calibrate time matrix from historical segments
T, t0 = build_time_matrix(lats, lons, depot, segments)

# 3. Solve (time-calibrated, 9h daily cap)
assigns, total_min, status, stats = solver.solve_time_cg(
    n, T, t0, service_times, freq,
    days=20, daily_cap=540, time_limit=300
)
# assigns[d] = list of customer indices visited on day d
```

---

## Repository structure

```
visit-scheduling-optimizer/
├── README.md                     ← you are here
├── LICENSE                       (MIT)
├── algos/
│   └── pvrp_cg/
│       ├── __init__.py           # package docstring + public API
│       ├── travel.py             # Held–Karp TSP, NN+2-opt, Haversine
│       ├── calibration.py        # per-county time-rate fitting
│       ├── solver.py             # set-partitioning + column generation
│       └── baselines.py          # Røpke–Pisinger ALNS metaheuristic
├── src/                          # legacy pattern-based solver (莆田 caliber)
│   ├── core/
│   │   ├── data_structures.py
│   │   ├── patterns.py
│   │   └── set_partition.py
│   └── utils/
│       └── data_generator.py
├── examples/
│   ├── synthetic_example.py      # legacy pattern-based demo
│   └── synthetic_pvrp_cg.py      # column-generation demo (recommended)
├── docs/
│   ├── algorithm.md              # method description + math
│   └── paper_draft.md            # full paper draft (methodology only)
└── .gitignore                    # excludes ALL data files
```

---

## Method summary

### Set-partitioning master problem

A **column** is a feasible day-group $G \subseteq N$ (≤ 6 customers, route cost ≤ 540 min). The master selects at most one column per day, covering each customer exactly $f_i$ times:

$$\min \sum_{G,t} c(G)\,\lambda_{G,t} \quad \text{s.t. coverage, interval, daily cap}$$

### Dual-guided column generation

1. **LP relaxation** (GLOP) → dual prices $\pi_{i,t}$ (customer-day opportunity cost) and $\mu_t$ (day capacity price).
2. **Pricing**: for each seed customer, greedily build $S$ by adding $j^\star = \arg\max_j (\pi_{j,t} - \Delta c)$ while marginal gain > 0.
3. **Add** up to 250 most-negative-reduced-cost columns per round.
4. **Repeat** until no negative-reduced-cost column exists → LP objective is a **valid lower bound**.
5. **Final IP** (CP-SAT, 300 s) with LP-rounded solution as hint.

### Data-calibrated time matrix

Fitted from 319 actual door-to-door trip segments:

$$\rho_{ij} = \begin{cases} r_c(j) & d_{ij} \leq 5 \text{ km} \\ 2.0 + \frac{(r_c(j)-2.0)(20-d_{ij})}{15} & 5 < d_{ij} < 20 \\ 2.0 & d_{ij} \geq 20 \text{ km} \end{cases}$$

Urban counties: 6–11 min/km (parking + mall access). Suburban: 2–4 min/km. Per-visit dwell penalty: 32 min.

### ALNS baseline (Røpke–Pisinger 2006)

4 destroy operators × 2 repair operators, adaptive weights (ρ = 0.1), Record-to-Record acceptance (5%). Same constraints, same time budget. Used to validate that the CG approach is competitive.

---

## What is NOT in this repository

- **No customer data.** All `.xlsx`, `.csv`, `.pkl` data files are excluded via `.gitignore`. The synthetic examples generate reproducible fake data.
- **No real coordinates.** The synthetic demo uses random points around a generic depot.
- **No proprietary business rules.** The framework is generic; specific frequency/gap/capacity parameters are configurable.

The anonymized industry study (7 reps, 235 customers, 3 regions) is described in `docs/paper_draft.md` with aggregate statistics only.

---

## Dependencies

| Package | Version | Purpose |
| --------- | --------- | --------- |
| `ortools` | ≥ 9.0 | CP-SAT (IP), pywraplp GLOP (LP) |
| `numpy` | ≥ 1.20 | Numerical operations |
| `pandas` | ≥ 1.3 | Data I/O (examples only) |
| `matplotlib` | ≥ 3.5 | Figures (optional, for paper) |

Python ≥ 3.10 required.

---

## Citation

If you use this framework in academic work, please cite:

```bibtex
@article{visit-scheduling-optimizer-2026,
  title   = {Data-Calibrated Periodic Vehicle Routing for Field-Sales Visit Scheduling},
  author  = {[Anonymized for review]},
  year    = {2026},
  note    = {Working paper. Set-partitioning + dual-guided column generation
             with per-county time calibration.}
}
```

---

## License

[MIT](LICENSE) — free for academic and commercial use with attribution.

---

## Contributing

Contributions welcome. Areas of interest:

- Time-window extension (PVRPTW)
- Stochastic service durations
- Multi-representative joint optimization
- Rolling-horizon re-planning

Please open an issue or PR. All contributions must not include real customer data.
