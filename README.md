# Visit Scheduling Optimizer

**A generic OR-based framework for periodic sales / service-visit scheduling.**

Set partitioning (CP-SAT) + lex-tier optimization + within-day TSP routing + data-driven calibration.

---

## Why this exists

Periodic sales-visit scheduling (think: a sales rep visiting 20–50 stores every week on a 4-week cycle, with per-customer visit frequencies) is a classic **Periodic Vehicle Routing Problem (PVRP)**. In practice it is almost always done by spreadsheet and human intuition — which leaves roughly half the potential mileage on the table, and routinely breaks frequency-compliance rules.

This repository is a **fully anonymized, framework-level** implementation of a production system that solves the problem with proper OR — set partitioning, multi-objective lexicographic optimization, TSP within each day, and data-driven calibration (travel time, traversal direction) from historical records.

---

## What it does

```
Input:  customers × coordinates × visit frequencies (4/2/1 per cycle)
        + historical visit records (for calibration)
        + depot location (for commute)

Output: a 4-week repeating schedule that
        ✓ satisfies every customer's frequency requirement
        ✓ keeps every day in a single geographic partition
        ✓ balances daily workload
        ✓ minimizes within-day driving distance
        ✓ respects historical visit-time consistency
        ✓ reports real driving time (not naïve 40km/h assumption)
        ✓ validates every constraint (no silent violations)
```

**Empirical results vs. naïve execution** (synthetic / anonymized data):

- Driving mileage: **−47%** (store-to-store)
- Total (with commute): **−21%**
- Frequency-4 weekly compliance: **12% → 100%**
- Cross-region days: **eliminated**
- Real driving time revealed: **5.3×** the naïve estimate

---

## Architecture (5 layers)

```
① Input      →  customers, visit frequencies, historical records
② Modeling   →  set-partitioning CP-SAT (z[i,p], y[c,d], v[i,d], w[i,j,d])
③ Solving    →  OR-Tools CP-SAT, lexicographic 4-tier objective
④ Routing    →  exact TSP within each day  +  A3 historical direction
                +  F6 calibrated travel-time model
⑤ Output     →  Excel schedule + map + validation report  (SHA256 signed)
```

See `docs/02-architecture.md` for the full picture.

---

## Repository layout

```
visit-scheduling-optimizer/
├── README.md                   ← you are here
├── LICENSE
├── docs/
│   ├── 01-methodology.md        ← the full optimization story (P0–P5)
│   ├── 02-architecture.md       ← the 5-layer diagram
│   ├── 03-modeling-deep-dive.md ← the math (variables, constraints, objectives)
│   ├── 04-references.md         ← the papers we cited
│   └── 05-value-framework.md    ← how to read the value
├── src/
│   ├── core/
│   │   ├── set_partition.py     ← the unified CP-SAT solver
│   │   ├── patterns.py          ← candidate-pattern generation
│   │   ├── routing.py           ← within-day TSP + A3 direction
│   │   ├── time_calibration.py  ← F6 travel-time model
│   │   ├── feedback_loop.py     ← F2 solve → route → measure → re-solve
│   │   └── validation.py        ← post-solve hard-check
│   ├── examples/
│   │   └── synthetic_example.py ← end-to-end demo on fake data
│   └── utils/
│       └── data_generator.py    ← deterministic synthetic data
├── tests/
│   └── test_solver.py           ← unit tests
└── results/
    └── anonymized_case_study.md  ← framework results on synthetic data
```

---

## Quick start

```bash
# 1. clone
git clone https://github.com/your-org/visit-scheduling-optimizer.git
cd visit-scheduling-optimizer

# 2. install (Python 3.10+, pip)
pip install ortools==9.15.6755 openpyxl==3.1.5

# 3. run the synthetic example (no client data needed)
python src/examples/synthetic_example.py

# 4. (optional) customize for your own data
from src.core.set_partition import solve_visit_schedule
from src.utils.data_generator import generate_synthetic_customers

customers = generate_synthetic_customers(n=30, regions=5, freq_dist={4:0.25, 2:0.6, 1:0.15})
result = solve_visit_schedule(customers)
```

---

## Why this is a framework, not a deployment

This repo contains **no client-specific data**:

- No salesperson names, store names, addresses, or real coordinates
- No real historical visit records
- No proprietary business rules

It is a **generic framework**. To deploy on your own data:

1. Format your customers as `list[Customer]` with `code, name, region, frequency, latitude, longitude`
2. Format your historical records as `list[HistoricalVisit]` with `customer, date, order, travel_time_min, was_in_region`
3. Plug into `solve_visit_schedule(...)`
4. The framework handles the rest (pattern generation, constraint building, solving, TSP routing, validation)

---

## Method/algorithm overview

The optimization is **four layers of lexicographic objectives**:

1. **shortfall** — minimize days with <3 visits (compliance ⊤)
2. **load_balance** — minimize daily visit-count deviation (equity)
3. **spatial** — minimize within-day pairwise distance spread (route awareness)
4. **consistency** — minimize deviation from historical weekday patterns (relationship)

Each layer is locked at its proven optimum before the next is optimized. The solver is **OR-Tools CP-SAT** (free, multi-threaded, native boolean/CP support). See `docs/03-modeling-deep-dive.md` for the full set-partitioning formulation.

The within-day routing is **exact TSP** (brute-force for ≤6 customers/day) plus **A3 historical direction learning** (PCA on consecutive-visit displacement vectors). The travel-time model is **F6 calibrated** per-region (linear regression: `minutes = a + b × km`, where a is the per-leg parking/walking overhead and b is the inverse effective speed).

---

## Results (synthetic case, 30 customers × 5 regions)

| Metric | Naïve execution | This framework | Improvement |
| --- | ---: | ---: | --- |
| Cross-region days | 8 | 0 | **eliminated** |
| Frequency-4 weekly compliance | 12.5% | 100% | +87.5pp |
| Store-to-store mileage | 630.7 km | 333.8 km | **−47%** |
| Commute (depot round trips) | 1,244 km | 1,143 km | −8% |
| Total mileage (incl. commute) | 1,875 km | 1,477 km | **−21%** |
| Per-visit mileage | 8.9 km | 4.5 km | **−50%** |
| Real driving time revealed | — | 5.3× the naïve estimate | +new visibility |

(These are framework results on synthetic data; real-deployment numbers depend on the customer's own geography, customer set, and historical quality.)

---

## Tech stack

- **Python 3.10+**
- **OR-Tools 9.15** (CP-SAT engine) — *free, open-source, optimality-provable*
- **openpyxl** — Excel I/O
- **scipy** (optional) — for A3 direction learning
- **folium** (optional) — for the interactive real-map view

No paid dependencies. No Gurobi. No commercial solver.

---

## What this repo is NOT

- **Not** a deployment package. The code is research-grade, not production-hardened. But it's a working framework.
- **Not** a UI / dashboard. Output is Excel + Markdown + (optional) HTML map.
- **Not** a competitor to Salesforce / SFA tools. We solve the *routing* problem of a sales rep; we don't do CRM.

---

## License

MIT. See `LICENSE`.

---

## References

See `docs/04-references.md` for the full academic bibliography, including:

- van Montfort et al. (2026) — fragment-based exact solver
- Arenas-Vasco et al. (2025) — set-partitioning matheuristics meta-analysis
- Amazon Last-Mile Routing Research Challenge (2026) — driver-preference learning
- TDABC (Kaplan & Anderson) — time-driven cost
- ConVRP / Consistent VRP literature
- PVRP / territory design literature

---

## Contributing

This is methodology, not a product. PRs welcome for:

- Algorithmic improvements (e.g., better linearization, different objective formulations)
- New benchmark / synthetic examples
- Documentation translations
- Bug reports in the synthetic example

See `docs/01-methodology.md` for the evolution of the optimization choices.
