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

Same constraints, same time budget as CG.

## 8. Complexity and scalability

| Component | Complexity | Practical limit |
|-----------|-----------|-----------------|
| Held–Karp (per column) | $O(2^n \cdot n^2)$ | $n \leq 9$ exact |
| LP relaxation (GLOP) | Polynomial | 10 000+ columns |
| Pricing (per round) | $O(n \cdot T \cdot K)$ | $K$ = neighbor depth |
| Final IP (CP-SAT) | NP-hard | 2000 columns, 300 s |

For the studied instances (32–36 customers, 20 days), total solve time is 2–8 minutes per person.

## 9. Optimality certificates

- **Open route**: 6/7 instances achieve LP bound = IP solution (global optimum over column pool)
- **Closed loop**: 3/7 OPTIMAL, 4/7 FEASIBLE with gap 0.6–4.2% from LP bound
- **Time caliber**: all instances FEASIBLE within 540-min cap; balance re-assignment reduces max load by 0–80 min

## 10. References

- Rothenbächer, A. (2017). Branch-and-Price-and-Cut for the PVRP with Flexible Schedule Structures. *JGU Mainz*.
- Pirkwieser, S. & Raidl, G. (2009). Column Generation for PVRPTW. *TU Wien*.
- Røpke, S. & Pisinger, D. (2006). An Adaptive Large Neighborhood Search Heuristic for PDPTW. *Transportation Science*.
- Nekooghadirli, N. et al. (2022). Workload Equity in Multi-Period VRP. *arXiv:2206.14596*.
- Dalla Chiara, G. & Goodchild, A. (2020). Do Commercial Vehicles Cruise for Parking? *Transport Policy*.
- Ríos-Mercado, R. & López-Pérez, J. (2011). Commercial Territory Design with Realignment. *UANL*.
