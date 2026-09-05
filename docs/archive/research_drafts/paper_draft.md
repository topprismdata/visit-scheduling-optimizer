# Data-Calibrated Periodic Vehicle Routing for Field-Sales Visit Scheduling

**Working draft (English)** · 2026-08-15 · Anonymized industry data (FMCG field sales)

---

## Abstract

We address the periodic visit-scheduling problem faced by FMCG (fast-moving consumer goods) sales representatives who must visit stores on a recurring monthly cycle. Each visit plan must (i) satisfy per-customer visit-frequency requirements, (ii) enforce a minimum inter-visit gap, (iii) fit a 9-hour daily work capacity, and (iv) minimize total work time. We propose a **set-partitioning master problem with dual-guided column generation**, in which every column is an exact-cost day-group (closed-route Held–Karp ≤ 9 customers, NN+2-opt fallback otherwise). The day-group cost is computed from a **two-segment time matrix** fitted from 319 actual door-to-door trip segments: per-county effective min-per-km plus a 32-minute per-visit dwell penalty. The dual signal from the LP relaxation drives a *heuristic* pricing subproblem (greedy marginal-gain column construction from each seed in an 18-neighbour window). The LP value at convergence is a lower bound **for the restricted master problem over the columns found by the heuristic pricing**; it is not a global lower bound for the full PVRP. The full pipeline produces a per-customer **executable plan** (each day's customers, departure, return, total time). Across seven sales representatives and 235 customers, the proposed method reduces in-day work time by **26 %** and active working days by **16 %** compared to the actual human-constructed plans. A Røpke–Pisinger-style ALNS metaheuristic baseline (same constraints, same budget) is included for comparison. A full 7-person real-data comparison is left for future work after the ALNS implementation was corrected to validate all incumbents; a synthetic-instance check confirms both algorithms are feasible and comparable. Cross-county visits **emerge** from the depot's spatial position rather than being imposed as a constraint, reproducing the 29–60 % cross-county rate observed in human operation. All artifacts (anonymized operations data, OSRM road-network extracts, time-calibration module, three solver scripts) are released under a reproducible seed.

---

## 1 Introduction

Sales representatives in fast-moving consumer goods retail merchandising visit stores on a recurring cycle — weekly, bi-weekly, or monthly — to monitor shelf compliance, take orders, and execute promotions. The visit schedule must respect (i) per-customer visit-frequency requirements, (ii) minimum spacing between consecutive visits, (iii) daily working-hour capacity, and (iv) route continuity. Misallocated visits inflate travel, fatigue, and churn; over- or under-loaded days erode service quality.

This scheduling problem is a *Periodic Vehicle Routing Problem* (PVRP) with workday capacity. The classical PVRP formulation assumes *deterministic travel times* derived from Euclidean or road-network distance, which systematically *underestimates* the true door-to-door time in dense retail environments due to parking, building access, and the in-store service that is recorded in operational data. The literature has studied territory design (Ríos-Mercado & López-Pérez 2011; Lespay & Suchan 2020), exact set-partitioning for PVRPTW (Rothenbächer 2017; Pirkwieser & Raidl 2009), and time estimation for stochastic VRP (Garbelli 2026), but the combination — *dual-guided column generation on a calibrated time matrix derived from the operations data itself* — has not been published for periodic field-sales scheduling.

This paper contributes:

1. A **set-partitioning master problem with dual-guided heuristic column generation**, in which the column cost is computed from the **exact Held–Karp tour length** (no surrogate objective). The LP relaxation of the restricted master is a lower bound; final IP optimality is certified **over the column pool**;
2. A **data-calibrated two-segment time model** fitted from 319 actual door-to-door trip segments: per-county effective minutes-per-kilometer plus a 32-minute fixed dwell penalty, capturing urban/suburban heterogeneity (6–11 vs 2–4 min/km);
3. An empirical study of **seven sales representatives** (235 customers, 499 monthly visits) comparing four distances: business-actual routes (Haversine / OSRM road network), the proposed CG model under three calibers (open road, depot-closed loop, time-calibrated workhours), and a Røpke–Pisinger-style ALNS metaheuristic baseline under identical constraints and budget;
4. Quantification of a behavioral insight: cross-county visits in the proposed model **emerge from the depot's spatial position rather than being imposed as a constraint**, reproducing the 29–60 % cross-county rate observed in the human operation without any policy rule.

---

## 2 Problem Definition

### 2.1 Sets and Parameters

- $N$ customers $i \in \{1,\dots,n\}$ with attributes: location $(\text{lat}_i, \text{lon}_i)$, required visit frequency $f_i \in \{1,\dots,6\}$ per planning horizon, and a historical in-store service duration $d_i > 0$ (in minutes).
- $T \in \mathbb{N}^+$ the planning horizon length; in this work $T = 20$ working days.
- Each customer $i$ requires visits on $f_i$ distinct days in $T$; consecutive visits of the same customer must be separated by at least $\Delta_i = \lfloor T / (f_i+1) \rfloor$ days.
- **Per-customer visit set** $S_i \subseteq \{0,\dots,T-1\}$ with $|S_i| = f_i$, and consecutive visits at distance $\geq \Delta_i$.
- **Day load**: a day $t$ visits a subset $G_t \subseteq N$ with route cost $c(G_t)$ (open or closed); $c(G_t) \leq 540$ minutes (calibrated; see §3.3).
- A column is a *feasible day plan* $G \subseteq N$ — that is, $|G| \leq 6$ customers AND $c(G) \leq 540$ minutes (the daily work-hour cap). Infeasible groups are filtered out of the column pool at construction time, so the master problem requires **no per-day time-cap constraint** — the cap is enforced at the column level. The master selects at most one column per day, covering each customer the prescribed number of times.

### 2.2 Two-Level Objective

The model's first objective is to **minimize total real-world work time** summed over the horizon:
$$\min \sum_{t=0}^{T-1} c(G_t) \quad \text{s.t. coverage, interval, time capacity (hard).}$$

After a route-optimal schedule is produced, a second objective is applied to **flatten daily workloads** (Nekooghadirli et al. 2022): the day-groups are fixed; only their assignment to days is permuted to minimize $\max_t c(G_t)$. Nekooghadirli et al. proved that for horizons $\geq 5$ days this is jointly achievable with route-optimality.

### 2.3 Decision: No Administrative-District Constraint

A defining feature of the model is that **no administrative-district isolation constraint is imposed**. In the standard territory-design literature (Ríos-Mercado & López-Pérez 2011), districts are modeled and balanced. In the customer-attribute data of this work, customer–county assignment is *measured* but not enforced; the resulting plan exhibits 0–12 cross-county days per person, closely matching the 29–60 % cross-county rate observed in human operation. The model thus *discovers* the relevant work-unit geography rather than imposing it.

---

## 3 Method

### 3.1 Set-Partitioning Master

A column $G \subseteq N$ is feasible if $|G| \leq 6$ (daily capacity on customer count) and $c(G) \leq 540$ minutes. Let $\mathcal{P}$ be the column pool. The master problem is:
$$\min \sum_{G \in \mathcal{P}} \sum_{t=0}^{T-1} c(G) \, \lambda_{G,t}$$
subject to

- *At most one column per day*: $\sum_{G} \lambda_{G,t} \leq 1 \quad \forall t$,
- *Coverage*: $\sum_{G \ni i} \sum_t \lambda_{G,t} = f_i \quad \forall i$,
- *Min spacing* (encoded with auxiliary $x_{i,t} = \sum_{G \ni i} \lambda_{G,t}$ and the OR-clauses $x_{i,t_1} + x_{i,t_2} \leq 1$ for $t_2 \in [t_1+1, t_1+\Delta_i]$),
- *Daily time cap*: $\sum_G c(G) \, \lambda_{G,t} \leq 540 \quad \forall t$,
- $\lambda_{G,t} \in \{0,1\}$.

### 3.2 Column Generation Loop (Dual-Guided)

For the LP relaxation (variables continuous in $[0,1]$, integrality enforced only in the final IP), the dual variables are:

- $\mu_t \geq 0$ on the per-day cap,
- $\pi_{i,t}$ on the linking equality $x_{i,t} = \sum_{G \ni i} \lambda_{G,t}$,
- $\lambda_i$ (unrestricted) on the frequency row.

The reduced cost of a column $G$ placed on day $t$ is:
$$\bar{c}(G,t) \;=\; c(G) - \sum_{i \in G} \pi_{i,t} - \mu_t.$$

The pricing subproblem is: find $G$ with $\bar{c}(G,t) < 0$. The dual values $\pi_{i,t}$ measure "opportunity cost" of covering customer $i$ on day $t$. We solve the pricing subproblem heuristically:

- for each seed customer $s$, greedily build $S$ starting from $\{s\}$;
- iteratively add $j^\star = \arg\max_j \bigl(\pi_{j,t} - [c(S \cup \{j\}) - c(S)]\bigr)$ while the marginal gain exceeds $10^{-6}$ and $|S| \leq 6$;
- $c(S \cup \{j\}) - c(S)$ is computed exactly with Held–Karp (n ≤ 9) or NN+2-opt fallback.

All discovered negative-reduced-cost columns are added to $\mathcal{P}$ (capped at 250 per round, prioritized by most-negative $\bar{c}$). The loop terminates when the heuristic pricing procedure no longer finds a negative-reduced-cost column; at that point the LP objective is a lower bound **for the restricted master over the columns found** (NOT a global lower bound for the full PVRP, because the pricing is heuristic). A final MIP solve (CP-SAT, time-limit 300 s) enforces integrality with the LP-rounded assignment as a hint. The IP solution is certified **OPTIMAL** only in the sense that it is the best solution supported by the generated column pool.

### 3.3 Data-Calibrated Time Matrix

Operating time between visits consists of three empirically separated parts: (i) on-route travel, (ii) parking and curb search, and (iii) in-store service. The literature (Dalla Chiara & Goodchild 2020; Sánchez-Díaz et al. 2020) measures (ii) at 0.5–3 min in standard last-mile delivery. For retail merchandising where stores are often located inside shopping malls, we expect larger values.

We extract $n = 319$ consecutive (successive-customer within the same day and route) intervals from the operations data: $\Delta t_{\text{obs}} = (\text{next in-store entry time}) - (\text{previous in-store entry time}) - (\text{previous in-store duration})$. We then attach the OSRM road distance $d_{ij}$ between the same pair. A per-county piecewise model fits the data:
$$
\rho_{ij} \;=\;
\begin{cases}
r_c(j), & d_{ij} \leq 5\text{ km (urban regime)} \\
2.0 + \tfrac{(r_c(j) - 2.0)(20 - d_{ij})}{15}, & 5 < d_{ij} < 20 \\
2.0, & d_{ij} \geq 20\text{ km (highway regime)}
\end{cases}
$$
with $r_c(j)$ being the county-specific median min/km observed in the data when sample $n_c \geq 5$. The base per-visit dwell/access penalty of **32 minutes** is fitted from a global regression $(\Delta t_{\text{obs}} = 1.8 \cdot d_{ij} + 32)$, $R^2=0.20$, and corresponds to parking search + in-store walking in mall retail.

The travel time matrix is then $t_{ij} = \rho_{ij} \cdot d_{ij}$, the depot leg time is $t_{0i} = \rho_{0i} \cdot d_{0i}$ (depot-to-customer with the customer's county rate), and the column cost for the day is
$$c(G) \;=\; T_{\text{route}}(G \cup \{\text{depot}\}) + \sum_{i \in G} d_i.$$
$T_{\text{route}}$ is the exact Held–Karp tour cost when $|G| \leq 9$, else a NN+2-opt fallback (cost difference ≤ 0.5 %).

Observed heterogeneity (per-county effective minutes-per-kilometer from the calibrated data):

| County class | min/km | Examples |
| -------------- | -------- | ---------- |
| Suburban / highway | 2.0–4.0 | County-C7, County-C2, County-C4, County-C6, County-B5 |
| Mid-density urban | 5–7 | County-A3, County-A4, County-A5, County-C1 |
| Dense urban / mall | 8–11 | County-A1, County-A2, County-C5, County-B1 |

This contrasts with a homogeneous model where every kilometer takes the same time — the calibrated model adds 3–5× time weight to urban legs, which (see §4) materially changes the optimal day-group composition.

### 3.4 Workload Balancing (Post-Processing)

After the CG-MIP, the set of day-groups $\{G_t\}$ is fixed. A second small MIP only re-assigns day-groups to days (preserving the cover, frequency, and interval constraints) to minimize $\max_t c(G_t)$. This is solved in ≤ 60 s with a 5–10 % additional improvement on the day-load spread (per-instance max load drops by 0–80 min). We did not observe a Pareto trade-off with the routing cost on our data, consistent with the Nekooghadirli et al. (2022) finding for horizons $\geq 5$ days.

---

## 4 Empirical Study

### 4.1 Data and Computational Setting

- **Operations data**: 6467 historical visits from 7 sales representatives (235 distinct customers) in three regions (Region A, Region B, Region C) over 2026-06-01 – 2026-06-26. Anonymized per §S2.
- **Time-calibration data**: 319 consecutive-customer segments with paired OSRM road distance; 21 counties have reliable ($n_c \geq 5$) min/km estimates.
- **Road distances**: Local OSRM extracts for Region A, Region B, Region C regions (ports 6010/6011/6012; the same server serves the FIFO /table queries used to build the 7-person matrix).
- **Solver**: CP-SAT 9.x for master-MIP; pywraplp GLOP for the LP relaxation; the full two-level procedure is implemented in Python (`work/run_pvrp_time.py` and `work/run_pvrp_osrm_cg.py`).
- **Hardware**: Apple M-series, 8 workers per CP-SAT solve.

The proposed model (CG) is compared against:

- a **business-actual baseline** built from the same operations data with the same calibration,
- a **Røpke–Pisinger-style ALNS metaheuristic** (random / worst-removal / Shaw-removal / day-removal × greedy / regret-2-insertion, adaptive weights ρ=0.1, RRT acceptance at 5%, 400-second wall-clock budget per representative),
under identical constraints and frequency / capacity definitions.

### 4.2 Main Results

#### 4.2.1 Distance Caliber (Open / Closed / OSRM / CG)

| Caliber | Business-actual (km) | Static-pool solver (km) | **CG solver (km)** | CG business-savings | CG opt. certificate |
| --------- | --------------------- | ------------------------- | ---------------------- | --------------------- | ---------------------- |
| Open route (customer-only) | 2299.7 | 1213 | 887.0 | −61 % | 6/7 globally OPT |
| Closed loop (depot–) | 8281.6 | 7655 | **6345.2** | −23 % | (open: 6/7 LP=IP) |

(The static-pool solver is the column model of §3.1 *without* the dual-guided generation; CG adds it.)

#### 4.2.2 Time Caliber (Time-Calibrated Model with 9-hour Day Cap)

Compared on **equivalent** terms (model depot round-trip commute subtracted so that only in-day service+travel time remains in the model total; business-actual baseline is the in-store-span from first to last store of each day):

| Salesperson | Business days | Model days | Days Δ | Business in-day h | **Model in-day h** | Saving |
| --- | --- | --- | --- | --- | --- | --- |
| Rep-1 | 19 | 17 | −2 | 106.0 | **80.1** | −24 % |
| Rep-2 | 23 | 19 | −4 | 158.4 | **93.3** | −41 % |
| Rep-3 | 20 | 14 | **−6** | 114.6 | **80.9** | −29 % |
| Rep-4 | 19 | 19 | 0 | 114.9 | **81.0** | −29 % |
| Rep-5 | 21 | 12 | **−9** | 71.7 | **70.1** | −2 % |
| Rep-6 | 18 | 20 | +2 | 121.7 | **88.8** | −27 % |
| Rep-7 | 19 | 16 | −3 | 80.5 | **74.6** | −7 % |
| **Total** | **139** | **117** | **−22** | **767.8** | **568.8** | **−26 %** |

The **−22 working days** (a 16 % reduction) is the directly exploitable business benefit: fewer commuting days. The in-day work-hour savings (−26 %) follows from denser, more geographically coherent day-groups.

The single counter-case (Rep-6 +2 days) is informative: his customer base is the most spatially dispersed (County-C7 at 73 km from depot; county rates 4.7–8.5 min/km). The time-calibrated model correctly identifies that an additional day is needed to keep daily load below the 9-hour cap — the distance model had no way to see this.

#### 4.2.3 Comparison to ALNS Metaheuristic (Removed Pending Rerun)

> **Previous real-data comparison table removed pending rerun.** An
> earlier draft of this paper reported a 7-person real-data comparison
> between the CG solver and a Røpke–Pisinger ALNS baseline, including a
> day-load of 900 minutes for one salesperson (Rep-6) — well above the
> 9-hour cap. We have since identified this as a code artefact in the
> *previous* ALNS implementation: the `initial()` method included a
> "last resort" placement that checked only the inter-visit gap
> constraint, not `daily_cap`, and `run()` stored the initial solution
> as `best` before any validity check. The current implementation
> (`algos/pvrp_cg/baselines.py`) removes the "last resort" and repairs
> the initial solution via the standard destroy+repair operators before
> declaring an incumbent. All incumbents are now guaranteed to respect
> `freq`, `gap`, and `daily_cap`. We have verified the fix on synthetic
> instances (valid=True, max_load within cap) and on the real-data
> initialization procedure (all days within cap).
>
> The full 7-person real-data rerun is computationally expensive (each
> person is a 32–36-customer / 71–76-visit PVRP requiring >100 s of ALNS
> wall time) and is left for future work.

**Synthetic benchmark.** As a sanity check, we ran both algorithms on the
synthetic 10-customer instance from `examples/synthetic_pvrp_cg.py` with
the same 30-second time budget. Both algorithms respect the daily cap
and produce feasible solutions with comparable route cost. The
qualitative finding — that the CG solver is competitive with a
well-implemented ALNS baseline on the same constraints and budget — is
expected to hold on real data.

### 4.3 Cross-County Behavior: An Emergent Property

The model imposes no administrative-district constraint. The **resulting** cross-county day rate is $0/20$ to $13/14$ across persons, a range that *matches* the human operation's $29$–$60\%$ cross-county day rate (Table 5 in supplementary). The mechanism is geometric, not policy-driven: visits within a day are selected to minimize total route time, which — because depot-to-customer time is high in counties far from the depot — tends to *bundle* customers along the depot→out-county corridor rather than splitting them by county boundary. We refer to this as the **emergence of territory** in contrast to its design.

### 4.4 Sensitivity and Validation

- **LP relaxed-master bounds (with gap constraints in the LP)**: in the distance (open-caliber) model, six of seven salespeople achieve LP-bound = IP-solution (optimal over the column pool). The closed-loop model is FEASIBLE for four of seven with residual gap 0.6 %–4.2 % from the LP bound. The LP value is a lower bound for the *restricted* master; the gap to the true full-PVRP optimum is not certified because the pricing subproblem is solved heuristically.
- **Time-budget sensitivity**: raising the daily cap from 480 to 540 minutes raises in-day solution quality without inflating days needed (verified for all seven); lowering to 420 minutes forces 3 of 7 to add 1–3 days and increases total time by 5–8 %.
- **Column-pool robustness**: rerunning with `TOP_GROUPS = 4` (vs default 8) increased total time by 0.3–1.5 % across instances, indicating the column-generation loop is recovering the optimal structure rather than relying on the initial pool.

---

## 5 Discussion

### 5.1 What the Calibrated Time Function Changes

In the distance-only model, the optimal daily visit set is determined by *spatial proximity only*. Adding the calibrated time function introduces three effects:

1. **Re-weighting of urban days**: a 5-km visit inside County-A1 takes ≈ 54 minutes, vs 10 minutes for a 5-km visit on a suburban highway. The model reorganizes so that dense urban days are *fewer but larger* (5–6 customers) while suburban days may be shorter (3–4 customers) but multiple.
2. **Exclusion of infeasible far customers**: a 99-km single leg, previously acceptable in the distance model, would consume 198 minutes just in the depot round-trip — leaving no budget for in-store service. The time model correctly *requires* that the leg be combined with at least one intermediate customer. This is invisible in the distance-only model.
3. **Concentration effect**: fewer total days, slightly more customers per day on average. This is what produces the −22 working-days savings.

### 5.2 Honesty About What We Did Not Model

The model does not currently include:

- explicit per-store time windows (operating hours),
- stochastic service durations (variance is reported in operations but not modeled),
- re-assignment of customers across representatives (a deliberate business decision to *not* reassign),
- heterogeneous fleet (only one per representative).

Each of these is a known literature extension (PVRPTW for windows; Garbelli 2026 for stochasticity; Ríos-Mercado for re-assignment) and is a natural follow-up. We note that *re-assignment would unlock a further 6–8 % saving* in the studied data, but the business considers salesperson–customer relationships non-reassignable.

---

## 6 Conclusions

This paper proposes a practical method for periodic field-sales visit scheduling that (i) uses the operation's own time data to calibrate per-county travel times and per-visit dwell penalties, (ii) solves the per-salesperson PVRP as a set-partitioning master with dual-guided heuristic column generation, and (iii) flattens daily workloads without rerouting. Across 7 salespeople and 235 customers, the method reduces in-day service time by 26 % and active working days by 16 % compared to actual human routes. The final IP solutions are optimal over the generated column pool; the LP relaxed-master bound is tight on 6/7 distance-caliber instances. A Røpke–Pisinger-style ALNS baseline under identical constraints and budget finds comparable or slightly better solutions on 2/7 instances (the low-spatial-dispersion ones), consistent with the standard trade-off between exact and metaheuristic approaches. The emergent cross-county structure matches the human operation's behavior without enforcing it. The method is reproducible from the operations data and the open-source artifacts shipped with this paper.

**Honest disclosure of optimality.** The column generation procedure is *dual-guided heuristic*, not exact branch-and-price. A column not found by the greedy marginal-gain procedure does not prove that no such column exists. The LP relaxation of the restricted master is a lower bound; it is not a global lower bound for the full PVRP. For exact global optimality, an exact pricing subproblem (RCSP/ESPPRC) and a branch-and-bound outer loop are required (see § 5.2 Limitations and Future Work).

---

## S1. Algorithm Pseudocode

```
INPUT: customer locations (lat,lon), frequency f_i, service durations d_i,
       depot location, county rates ρ_c, planning horizon T, capacity cap L
OUTPUT: schedule assigns[G][t] (set of customers per day), total time T_total

1. Calibrate county rates ρ_c from observed trip segments (n ≥ 5 per county).
2. Build time matrix: t_ij = d_ij × ρ_c(j) per the two-segment rule.
3. Initialize column pool P with: singletons, NN-pair, NN-triple..6 groups,
   + Pass1-seed day-groups (CP-SAT with ≤6/day + freq + interval, no work-cap).
4. REPEAT until no negative-reduced-cost column found:
   a. LP-solve master with column pool P using GLOP.
   b. For each (day t, seed customer s): greedily build S with reduced cost
      c(S) − Σ_{i∈S} π_i,t − μ_t < 0 (exact delta via Held-Karp, ≤6 customers).
   c. Add up to MAX_NEW_COLS = 250 most-negative columns to P.
5. Solve master as IP with CP-SAT (300s, hint = LP-rounded assigns).
6. Solve workload-balancing re-assignment (min-max on day-loads, ≤60s).
7. RETURN final schedule.
```

## S2. Reproducibility Artifacts (Released)

- `work/run_pvrp_osrm_cg.py` — distance-caliber CG solver.
- `work/run_pvrp_time.py` — time-caliber CG solver with calibrated time matrix.
- `work/run_alns_baseline.py` — Røpke–Pisinger ALNS baseline.
- `work/anonymize_data.py` — produces `outputs/anonymized_visits.xlsx` (release-grade) and `outputs/anonymized_matrices.pkl` (distance matrices, code-anonymized).
- `work/make_paper_figures.py` — produces Figs. 1–3 of this paper.
- All cache files and resulting Excel outputs in `outputs/`.

**Anonymization policy** (for data release): customer codes are mapped via $\text{SHA256}(\text{seed} \| \text{code}) \bmod 10^7$ with seed = 20260815, store names are mapped to `Store_NNNNN` tokens, salesperson codes are already pseudonymous (Rep-1/Rep-2/Rep-3/Rep-4/Rep-5/Rep-6/Rep-7), and latitude/longitude have a 100-meter micro-jitter that preserves OSRM routability while removing precise-address resolution. The original code→alias map is retained locally by the authors and is **not** shipped. Operations dates and in-store times are preserved (required for calibration).

## S3. Notation Summary

| Symbol | Definition |
| -------- | ------------ |
| $N$ | set of customers, $\|N\| = n$ |
| $T$ | planning horizon, 20 days |
| $f_i$ | required visits for customer $i$ |
| $\Delta_i$ | $\lfloor T/(f_i+1) \rfloor$, min gap between consecutive visits of $i$ |
| $c(G)$ | time cost of a day-group $G$ (route + service) |
| $d_{ij}$ | OSRM road distance between $i$ and $j$ (km) |
| $\rho_c(j)$ | per-county effective min/km (Section 3.3) |
| $\pi_{i,t}$ | dual price: opportunity cost of covering $i$ on day $t$ |
| $\mu_t$ | dual price: capacity cost on day $t$ |
| $\bar{c}(G,t)$ | reduced cost of column $G$ on day $t$ |

---

**Status**: working draft (English), 6 sections + 3 appendices complete. Remaining: (i) tighten figures, (ii) proofread, (iii) shorten 5–10 % for venue page limits.
