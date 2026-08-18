# Visit Scheduling Optimizer

**A data-calibrated decision engine for recurring field-sales visit
planning.**

`CUSTOMER DECISION` · `APPLIED` · `ANONYMIZED OPERATIONAL DATA` · `MIT`

> **Decision question:** Who should visit which customers, on which
> days, under recurring-frequency, spacing, routing, and workload
> constraints?

Part of **TopPrism Decision Intelligence**. This repository focuses on
the optimization layer behind periodic field-sales planning. It contains
no customer-level raw data or real coordinates.

------------------------------------------------------------------------

## Why this exists

Recurring field-sales planning is not a one-route TSP problem.

A representative may need to visit dozens of outlets over a monthly
cycle. Different outlets require different visit frequencies, repeated
visits must be separated in time, daily workload is capped, service time
varies, and the final plan must remain executable on a road network.

The real decision is therefore:

> **How should recurring customer visits be distributed across days and
> sequenced within each day so that service requirements are satisfied
> with less travel and workload?**

This repository turns that decision into a reproducible optimization
problem.

------------------------------------------------------------------------

## What this engine decides

``` text
Customers + visit frequency + service time
                  +
Historical travel observations + depot
                  ↓
          Time calibration
                  ↓
 Feasible recurring day-group generation
                  ↓
Restricted set-partitioning master problem
                  ↓
 Dual-guided heuristic column generation
                  ↓
     Final CP-SAT selection
                  ↓
      Within-day route ordering
                  ↓
Day-by-day executable visit plan
```

### Inputs

-   customer locations
-   required recurring visit frequencies
-   inter-visit spacing rules
-   service / dwell time
-   depot location
-   daily work-hour capacity
-   optional historical travel observations for calibration

### Outputs

-   customers assigned to each working day
-   recurring-visit compliance
-   estimated daily work time
-   route ordering within each day
-   aggregate travel / workload metrics
-   comparison against baseline planning approaches

------------------------------------------------------------------------

## Evidence

The repository includes an **anonymized industry study covering 7
representatives and 235 customers**. Only aggregate results are
published.

  ------------------------------------------------------------------------
  Metric             Business actual          Framework    Observed change
  --------------- ------------------ ------------------ ------------------
  Active working                 139                117               -16%
  days, 20-day                                          
  horizon                                               

  In-day work                  768 h              569 h               -26%
  hours                                                 

  OSRM route               10,056 km           6,345 km               -37%
  distance                                              

  Frequency                 92--100%               100%    hard constraint
  compliance                                                     satisfied

  Daily                  12% of days                 0%    hard constraint
  work-hour-cap                                                  satisfied
  violations                                            
  ------------------------------------------------------------------------

These figures are **study results, not a universal performance
guarantee**. Improvement depends on customer geography, frequency
policy, depot location, workload rules, and the quality of travel-time
calibration.

### What the evidence supports

-   recurring visit constraints can be modeled explicitly rather than
    handled only by spreadsheet heuristics;
-   data-calibrated travel and dwell assumptions materially affect
    executability;
-   the framework produced lower aggregate workload and route distance
    on the anonymized study;
-   hard frequency and daily-capacity rules can be enforced in the
    optimization model.

### What the evidence does not support

-   a claim that every deployment will achieve the same percentage
    improvement;
-   a claim of full PVRP global optimality;
-   a claim that the published aggregate study reproduces a live
    production deployment.

------------------------------------------------------------------------

## Optimization status --- important

This implementation uses **dual-guided heuristic column generation**.

The pricing step greedily constructs promising columns from seed
customers; it is **not an exact RCSP / ESPPRC pricing oracle**.
Therefore:

-   the LP objective is a lower bound for the **restricted master over
    the generated column pool**;
-   stopping because the heuristic finds no negative-reduced-cost column
    does **not** certify that no improving column exists in the full
    PVRP;
-   the final CP-SAT solution can be reported as optimal **within the
    generated column pool** when CP-SAT proves that restricted problem
    optimal;
-   full global PVRP optimality would require exact pricing /
    branch-and-price or another valid global-certification mechanism.

This distinction is intentional and should be preserved in papers,
demos, and downstream product claims.

------------------------------------------------------------------------

## Architecture

``` text
┌─────────────────────────────────────────────────────┐
│ BUSINESS STATE                                      │
│ customer · frequency · service · depot · capacity   │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 1. TIME CALIBRATION                                 │
│ historical segments → travel + dwell assumptions    │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 2. DAY-GROUP / COLUMN CONSTRUCTION                  │
│ feasible customer groups + exact/heuristic routing  │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 3. RESTRICTED SET-PARTITIONING MASTER               │
│ LP duals → heuristic pricing → expanded column pool │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 4. FINAL CP-SAT SELECTION                           │
│ coverage · spacing · daily capacity · workload      │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ DECISION                                            │
│ day assignment · route order · workload metrics     │
└─────────────────────────────────────────────────────┘
```

------------------------------------------------------------------------

## Where it fits at TopPrism

``` text
Business World Model
        ↓
customer · geography · travel · service · policy
        ↓
Visit Scheduling Optimizer
        ↓
recurring visit decision
        ↓
field execution / SFA / route navigation
        ↓
actual travel + service feedback
```

This repository is a **Decision Engine**, not the entire DRTM product.

Related TopPrism capabilities can provide entity resolution, spatial
structure, opportunity scoring, execution interfaces, and feedback loops
around this optimization core.

------------------------------------------------------------------------

## Quick start

``` bash
git clone https://github.com/topprismdata/visit-scheduling-optimizer.git
cd visit-scheduling-optimizer

pip install ortools numpy pandas matplotlib

python examples/synthetic_pvrp_cg.py
```

The synthetic example contains no real customer data.

------------------------------------------------------------------------

## Core implementation

  -----------------------------------------------------------------------
  Component                           Role
  ----------------------------------- -----------------------------------
  `algos/pvrp_cg/travel.py`           route cost, Held--Karp TSP, NN +
                                      2-opt, Haversine

  `algos/pvrp_cg/calibration.py`      travel-time calibration

  `algos/pvrp_cg/solver.py`           restricted master, dual-guided
                                      column generation, CP-SAT

  `algos/pvrp_cg/baselines.py`        ALNS comparison baseline

  `examples/`                         synthetic reproducible examples

  `docs/algorithm.md`                 mathematical and algorithmic detail

  `docs/paper_draft.md`               methodology-oriented working paper
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Data and privacy

This public repository intentionally excludes:

-   customer raw data;
-   real customer coordinates;
-   proprietary business rules;
-   internal identifiers;
-   customer-specific configuration files.

The published industry study is anonymized and reported only in
aggregate.

------------------------------------------------------------------------

## Boundaries & limitations

Current limitations include:

1.  heuristic rather than exact pricing in column generation;
2.  deterministic planning assumptions for travel and service time after
    calibration;
3.  no stochastic service-duration model in the current public
    framework;
4.  no joint multi-representative optimization in the current public
    solver;
5.  aggregate study evidence is not equivalent to a production SLA.

Potential extensions include exact pricing, rolling-horizon re-planning,
stochastic service times, time windows, and multi-representative
coordination.

------------------------------------------------------------------------

## Repository structure

``` text
visit-scheduling-optimizer/
├── algos/pvrp_cg/
├── docs/
├── examples/
├── src/
├── README.md
└── LICENSE
```

Detailed method explanations live in `docs/`; the README stays the
public decision-and-evidence entry point.

------------------------------------------------------------------------

## TopPrism metadata

The `topprism.yaml` shipped with this repository declares:

``` yaml
topprism:
  purpose: customer-decision
  capability: visit_scheduling
  platform_layer: decision_engine
  maturity: applied
  evidence:
    type: anonymized-operational-data
    scope: "7 representatives, 235 customers; aggregate statistics only"
  customer_data_in_repo: false
  product_context:
    - drtm
    - field_sales
```

------------------------------------------------------------------------

## Citation

If you use the methodology in academic work, see the citation
information in the repository and `docs/paper_draft.md`.

## License

MIT.

## Contributing

Contributions are welcome, especially around exact pricing, stochastic
planning, time-window extensions, rolling-horizon planning, and
multi-representative optimization. Do not submit customer-identifiable
data.
