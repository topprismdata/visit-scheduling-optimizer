# Algorithm: Data-Calibrated PVRP via Set-Partitioning + Column Generation

## 1. Problem formulation

Given $n$ customers, a planning horizon of $T$ days, and a depot:

- Customer $i$ requires $f_i$ visits ($f_i \in \{1,\dots,6\}$)
- Consecutive visits to customer $i$ must be ≥ $\Delta_i = \lfloor T/(f_i+1) \rfloor$ days apart
- Each day visits ≤ 6 customers (count cap) and ≤ 540 minutes (time cap)
- Objective: minimize total work time = travel + parking/dwell + in-store service

## 2. Column definition

A **column** is a feasible day-group $G \subseteq \{1,\dots,n\}$ with:

- $|G| \leq 6$
- Route cost $c(G) \leq 540$ minutes

The route cost is computed **exactly** via Held–Karp dynamic programming (for $|G| \leq 9$) or NN+2-opt heuristic (for larger groups, ≤ 0.5% gap).

## 3. Master problem (set partitioning)

$$\min \sum_{G \in \mathcal{P}} \sum_{t=0}^{T-1} c(G) \cdot \lambda_{G,t}$$

subject to:

- **One column per day**: $\sum_G \lambda_{G,t} \leq 1 \quad \forall t$
- **Coverage**: $\sum_{G \ni i} \sum_t \lambda_{G,t} = f_i \quad \forall i$
- **Interval**: encoded via auxiliary $x_{i,t} = \sum_{G \ni i} \lambda_{G,t}$ with pairwise OR-clauses
- **Daily time cap**: $\sum_G c(G) \cdot \lambda_{G,t} \leq 540 \quad \forall t$
- $\lambda_{G,t} \in \{0,1\}$

## 4. Column generation loop

### 4.1 LP relaxation

Solve the master with continuous $\lambda \in [0,1]$ using GLOP. Extract dual variables:

- $\pi_{i,t}$: opportunity cost of covering customer $i$ on day $t$
- $\mu_t$: capacity price of day $t$

### 4.2 Pricing subproblem

For each (day $t$, seed customer $s$):

1. Start with $S = \{s\}$
2. Greedily add $j^\star = \arg\max_j \bigl(\pi_{j,t} - [c(S \cup \{j\}) - c(S)]\bigr)$
3. Stop when marginal gain ≤ $10^{-6}$ or $|S| = 6$
4. Compute reduced cost: $\bar{c}(S,t) = c(S) - \sum_{i \in S} \pi_{i,t} - \mu_t$
5. If $\bar{c} < 0$, add column to pool

### 4.3 Convergence

Repeat until no negative-reduced-cost column exists. At convergence, the LP objective is a **valid lower bound** on the IP optimum.

### 4.4 Final IP solve

CP-SAT with:

- Full column pool (typically 1000–2000 columns)
- Solution hint from LP-rounded assignment
- Time limit: 300 s, 8 workers

## 5. Time calibration

### 5.1 Data extraction

From historical visit records, extract consecutive-customer segments:
$$\Delta t_{\text{obs}} = (\text{next entry time}) - (\text{prev entry time}) - (\text{prev service duration})$$

### 5.2 Per-county fitting

For each county $c$ with ≥ 5 observations:
$$r_c = \text{median}\left(\frac{\Delta t_{\text{obs}}}{d_{\text{OSRM}}}\right)$$

### 5.3 Two-segment model

$$\rho(d) = \begin{cases}
r_c & d \leq 5 \text{ km (urban: parking dominates)} \\
2.0 + \frac{(r_c - 2.0)(20 - d)}{15} & 5 < d < 20 \text{ km (transition)} \\
2.0 & d \geq 20 \text{ km (highway: steady speed)}
\end{cases}$$

This prevents the model from "exploding" on long inter-county legs while preserving the urban density premium.

### 5.4 Column cost (time caliber)
$$c(G) = T_{\text{route}}(G \cup \{\text{depot}\}) + \sum_{i \in G} d_i + 32 \cdot |G|$$

where $T_{\text{route}}$ is the exact closed-route time, $d_i$ is the in-store service duration, and 32 min is the per-visit dwell penalty (parking + building access).

## 6. Workload balancing (post-processing)

After the CG-MIP produces a route-optimal schedule, a second small MIP re-assigns day-groups to days (preserving coverage and interval constraints) to minimize $\max_t c(G_t)$.

This implements the Nekooghadirli et al. (2022) result: for horizons ≥ 5 days, workload equity and route optimality are jointly achievable.

## 7. ALNS baseline (Røpke–Pisinger 2006)

For comparison, we implement:
- **Destroy**: random / worst-cost / Shaw (neighborhood) / whole-day removal
- **Repair**: greedy insertion / regret-2 insertion
- **Adaptive weights**: $\rho = 0.1$, score = {3: new best, 2: improved, 1: accepted}
- **Acceptance**: Record-to-Record Travel, threshold = 5%

Same constraints (freq, gap, daily cap) and same wall-clock budget as the CG solver. The ALNS main loop only accepts candidate solutions that pass `valid()`, and the initial solution is repaired (via greedy / regret-2 re-insertion) before being used as the incumbent. An infeasible initial that cannot be repaired within the repair budget is reported with `valid=False` rather than as the best.

## 8. Complexity and scalability

| Component | Complexity | Practical limit |
|-----------|-----------|-----------------|
| Held–Karp (per column) | $O(2^n \cdot n^2)$ | $n \leq 9$ exact |
| LP relaxation (GLOP) | Polynomial | 10 000+ columns |
| Pricing (per round) | $O(n \cdot T \cdot K)$ | $K$ = neighbor depth |
| Final IP (CP-SAT) | NP-hard | 2000 columns, 300 s |

For the studied instances (32–36 customers, 20 days), total solve time is 2–8 minutes per person.

## 9. Optimality: what is and is not certified

The final CP-SAT IP solution is certified **OPTIMAL** in the sense that
it is the best solution supported by the **column pool** found by the
dual-guided heuristic pricing. This is *not* a proof of global optimality
of the full PVRP, because:

1. **Pricing is heuristic**, not exact. A negative-reduced-cost column
   that the greedy marginal-gain procedure fails to discover does
   not prove that no such column exists. The column pool is constructed
   by NN-seeded top-K enumeration plus greedy pricing, not by solving
   the exact pricing subproblem (which would be an RCSP/ESPPRC).
2. **The LP relaxation is a lower bound only for the restricted master.**
   The LP solved in step 2a of the algorithm includes the column-restricted
   master with all linear constraints (one-column-per-day, coverage,
   linking, inter-visit gap). Its objective is therefore a lower bound
   for the *restricted* master. With heuristic pricing this is *not*
   a global lower bound for the full PVRP.

Reported numbers (anonymized 7-rep study, OSRM road network):
- **Open route**: 6/7 instances achieve LP bound = IP solution (optimal over
  the column pool; *not* certified as a global PVRP bound)
- **Closed loop**: 3/7 OPTIMAL, 4/7 FEASIBLE with residual gap 0.6–4.2%
  from the restricted-master LP
- **Time caliber**: all instances FEASIBLE within the 540-min cap;
  balance re-assignment reduces max daily load by 0–80 min

## 10. Limitations and natural follow-ups

1. **Exact pricing (RCSP/ESPPRC).** The current pricing is a greedy
   marginal-gain procedure. An exact pricing subproblem that finds
   *all* negative-reduced-cost columns (or proves none exist) is the
   missing piece for true branch-and-price. This is the single largest
   gap to a provably-optimal solver.
2. **Branch-and-bound outer loop.** Even with exact pricing, integer
   decisions on customer-day coverage may require a search tree.
3. **Stochastic service durations.** A distribution over $d_i$ (e.g.
   sub-Gaussian residuals) could be incorporated via scenario-based
   re-optimization (Nekooghadirli 2022).
4. **Rolling-horizon re-planning.** The current implementation plans a
   single 20-day horizon; a rolling-horizon feedback loop would close
   the gap to a production scheduling engine.
5. **Multi-representative joint optimization.** The current solver
   optimizes each representative independently. A joint formulation
   with shared capacity (e.g. fleet constraints) would unlock further
   savings — but at the cost of violating the current one-rep-per-customer
   customer-relationship preservation.

## 11. References

- Rothenbächer, A. (2017). Branch-and-Price-and-Cut for the PVRP with Flexible Schedule Structures. *JGU Mainz*.
- Pirkwieser, S. & Raidl, G. (2009). Column Generation for PVRPTW. *TU Wien*.
- Røpke, S. & Pisinger, D. (2006). An Adaptive Large Neighborhood Search Heuristic for PDPTW. *Transportation Science*.
- Nekooghadirli, N. et al. (2022). Workload Equity in Multi-Period VRP. *arXiv:2206.14596*.
- Dalla Chiara, G. & Goodchild, A. (2020). Do Commercial Vehicles Cruise for Parking? *Transport Policy*.
- Ríos-Mercado, R. & López-Pérez, J. (2011). Commercial Territory Design with Realignment. *UANL*.
