# System Design Document: FMCG Periodic Visit Scheduling Optimization Engine

> **Document Status**: Approved & Implemented (`已定稿 / 已实现`)  
> **Authors**: OR / Algorithm Engineering Team  
> **Last Updated**: 2026-09-05  
> **Document Standard**: Aligned with Google Software Engineering Design Doc Guidelines (Swe-Book Ch. 10 / Industrial Empathy)  
> **Target Audience**: Systems Engineers, OR Scientists, Field Sales Operations Management, Technical Stakeholders

---

## 1. Context & Background

### 1.1 Business Context
Fast-Moving Consumer Goods (FMCG) enterprise sales operations deploy territory sales representatives (SRs) who visit hundreds of retail stores across recurring monthly cycles. Currently, monthly schedules and daily visiting sequences are either hand-crafted or produced by static ERP/CRM rule engines (e.g., Salesforce SRP).

Analysis of 9,760 real-world execution events across 10 representative sales lines in the Guangzhou urban area revealed severe structural deficiencies:
1. **Chaotic Visiting Sequences**: Sales reps spend 50%~75% of their daily riding distance on back-and-forth detours, street crossings, and zigzagging paths.
2. **Workload Volatility**: Without strict physical capacity planning, manual or naive heuristics often produce volatile daily schedules (e.g., piling 90 stores onto one day while leaving another with 4 stores).
3. **Huge Mileage Waste**: The 10 sales representatives collectively logged **16,857.0 km** of riding in the baseline plan across 23 working days.

### 1.2 System Mission
Deliver an automated, mathematically rigorous, two-stage periodic vehicle routing optimization engine that dramatically reduces travel mileage while strictly respecting frontline operational constraints and employee physical capacities.

---

## 2. Goals & Non-Goals

### 2.1 Goals
- **G1: Drastic Mileage Reduction**: Cut collective territory monthly riding distance by >70% against the raw SRP plan on real OpenStreetMap cycling networks.
- **G2: Strict Physical Operational Corridor**: Every single optimized working day for every representative $l$ must strictly satisfy:
  $$K_{\min}(l) \le |S_t(l)| \le K_{\max}(l) \quad \forall t \in T$$
  preventing both employee burnout ($> K_{\max}$) and resource under-utilization ($< K_{\min}$).
- **G3: Mathematical Optimality Certification**: For every line, provide a certified mathematical lower bound via Linear Programming relaxation and report the exact duality gap ($\text{Gap} \le 2\%$).
- **G4: Multi-Tier Latency SLAs**:
  - *In-transit real-time dispatch*: $\le 50\text{ ms}$
  - *Interactive dispatcher re-planning*: $\le 60\text{ s}$
  - *Overnight batch optimization*: $\le 5\text{ min/line}$

### 2.2 Non-Goals
- **NG1: Modifying Representative Territories**: Cross-representative customer re-assignment is out of scope; each sales line is optimized strictly independently to preserve established customer relationships.
- **NG2: Real-time Traffic Jam Prediction**: Dynamic vehicular congestion modeling is excluded; urban cycling network impedance is stable and pre-calibrated via OSM.
- **NG3: Service Duration Prediction**: Store dwell times are not altered; the optimization strictly minimizes transit/travel distance and balances store count workloads.

---

## 3. Requirements & Constraints (Invariants)

### 3.1 Functional Invariants (P0 Hard Constraints)
1. **Customer Visit Frequency Conservation (`count_ok = True`)**:
   Each customer $c \in N$ must be visited exactly $f_c$ times over the 23-working-day planning horizon:
   $$\sum_{t=1}^{T} \mathbb{I}(c \in S_t) = f_c \quad \forall c \in N$$
2. **Bi-Directional Workload Operational Corridor (`capacity_ok = True`)**:
   For each sales representative $l$, daily store count must never exceed their historical maximum nor fall below their historical minimum:
   $$K_{\min}(l) \le |S_t(l)| \le K_{\max}(l) \quad \forall t \in \{1 \dots 23\}$$
   *Violation of either boundary constitutes an immediate rejection of the schedule.*
3. **Open-Chain Hamiltonian Path**:
   Daily routes are open chains without mandatory depot returns (representatives start from their first customer and end at their last).

### 3.2 Non-Functional Requirements
- **Determinism**: Identical inputs and seeds must yield identical solutions.
- **Data Integrity**: 100% of distances must be measured on real OSM bicycle road networks (zero Euclidean or Haversine shortcuts).
- **Self-Containment**: Autonomous operation without external network dependencies during offline solving.

---

## 4. System Architecture & Detailed Design

The system implements a classic **Two-Stage Decomposition** that completely decouples macro calendar scheduling from micro intra-day path routing.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        INPUT: SRP Baseline Plan & Road Matrix                          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Calendar Planning (全月排日历 / 跨日分配)                                      │
│                                                                                        │
│   ┌────────────────────────────────┐         ┌─────────────────────────────────────┐   │
│   │ Column Generation Engine       │ ◄───────┤ Dual Feedback Pricing Oracle        │   │
│   │ (SP + CG with [K_min, K_max])  │         │ (Reduced Cost: c_r - Σ u_c - w_d <0)│   │
│   └───────────────┬────────────────┘         └─────────────────────────────────────┘   │
│                   │                                                                    │
│                   ▼                                                                    │
│   ┌────────────────────────────────┐         ┌─────────────────────────────────────┐   │
│   │ Multi-Algorithm Column Pool    │ ◄───────┤ Feedback ALNS & Feedback HGS        │   │
│   │ (Legal Routes satisfying cap)  │         │ (Tour-Carrying Local Search)        │   │
│   └───────────────┬────────────────┘         └─────────────────────────────────────┘   │
│                   │                                                                    │
│                   ▼                                                                    │
│   ┌────────────────────────────────┐                                                   │
│   │ Integer Set Partitioning (IP)  │ ────► Certified Optimal Calendar Solution S_t     │
│   │ (CP-SAT Solver + LP Bound)     │       (100% capacity_ok, 100% count_ok)           │
│   └────────────────────────────────┘                                                   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ Selected Store Sets {S_1, S_2, ... S_23}
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Intra-Day Routing (单日排顺序 / 路径排序)                                     │
│                                                                                        │
│   For each day t:                                                                      │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ CP-SAT Global Exact Circuit Solver (AddCircuit + Dummy Depot)                  │   │
│   │   - Problem: Open-Path ATSP over S_t on OSM Matrix D                           │   │
│   │   - Performance: Solves |S_t| <= 37 to 100% OPTIMAL in 20 ms ~ 1.7 s           │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        OUTPUT: Verified Production Schedules                           │
│           (100% Corridor Compliant, Mathematically Certified Minimal Mileage)           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Layer 2 Design: Intra-Day TSP Route Solver
- **Mathematical Formulation**: Open Traveling Salesperson Problem on an asymmetric road matrix $D$.
- **Model**: Formulated as an Asymmetric TSP (ATSP) with a dummy depot vertex $m = |S_t|$. Arcs $(i, m)$ and $(m, i)$ carry zero cost (or uniform constant), while $(i, j)$ carries $D_{ij}$. Circuit constraint `AddCircuit(arcs)` enforces a single subtour covering all vertices.
- **Engine Selection**: **CP-SAT Global Exact Solver** is the sole engine.
  - Empirical finding: On all real business days ($n \le 37$), CP-SAT proves global mathematical optimality in **$\le 1.77\text{ seconds}$** (median $< 50\text{ ms}$). Heuristic approximations (e.g., LKH-3) are unnecessary and underperform due to non-Euclidean road asymmetry.

### 4.2 Layer 1 Design: Monthly Calendar Planner
- **Mathematical Formulation**: Set Partitioning over column space $\mathcal{R}_t$:
  $$\min \sum_{t \in T} \sum_{r \in \mathcal{R}_t} c_r \cdot x_{rt}$$
  $$\text{s.t.} \quad \sum_{r \in \mathcal{R}_t} x_{rt} = 1 \quad \forall t \in T \quad (\text{Single route per working day})$$
  $$\sum_{t \in T} \sum_{r \in \mathcal{R}_t : c \in r} x_{rt} = f_c \quad \forall c \in N \quad (\text{Exact frequency conservation})$$
  $$x_{rt} \in \{0, 1\} \quad \forall t \in T, r \in \mathcal{R}_t$$
- **Column Legality Definition**:
  $$\mathcal{R}_t = \left\{ r \subseteq N : K_{\min} \le |r| \le K_{\max}, \quad c_r = \text{ExactTSP}(r, D) \right\}$$
  Any candidate route violating the corridor is structurally excluded from the column pool.
- **Dual-Feedback Closed-Loop Column Generation (CG)**:
  1. Solve LP relaxation of the master problem via Google OR-Tools GLOP.
  2. Extract dual multipliers: $u_c$ for customer coverage constraints, $w_t$ for daily assignment constraints.
  3. **Pricing Subproblem**: For each day $t$, generate candidate routes maximizing net marginal profit $u_c - \Delta \text{km}$ while respecting $|r| \le K_{\max}$. If reduced cost $c_r - \sum_{c \in r} u_c - w_t < 0$, column $r$ is injected into the pool.
  4. Iterate until the LP lower bound stabilizes (plateau convergence).
  5. Solve integer master problem using CP-SAT, yielding the final schedule and certified gap.

---

## 5. Standard Algorithm Nomenclature

All algorithms are standardized with mechanism-first nomenclature:

```
├── Layer 1: Calendar Planning
│   ├── Cold-Evaluation ALNS (冷评估大邻域搜索, formerly ALNS v1)      [Baseline Reference]
│   ├── Tour-Carrying Feedback ALNS (路径反馈大邻域搜索, formerly ALNS v3)  [Workhorse Generator]
│   ├── Tour-Feedback Hybrid Genetic (路径反馈混合遗传, formerly HGS)      [Diversity Generator]
│   ├── Dual-Feedback Closed-Loop CG (对偶闭环列生成, formerly SP+CG)       [Final Optimizer & Certificate]
│   └── Multi-Objective Pareto Stabilizer (多目标帕累托稳定器, formerly v4) [Trade-off Tuner]
│
└── Layer 2: Single-Day Routing
    ├── CP-SAT Global Exact Circuit Solver (约束规划全局精确求解器)          [Production Master Engine]
    ├── Nearest Neighbor with 2-opt (最近邻局部搜索)                        [In-Transit Real-Time]
    └── Lin-Kernighan-Helsgaun 5-opt (变深度局部搜索, LKH-3)               [Large-Scale Fallback]
```

---

## 6. Alternatives Considered & Technical Trade-Offs

| Alternative | Rationale for Rejection / Deprecation | Selected Replacement |
|---|---|---|
| **Monolithic Single-Stage MIP** | Attempting to solve all 686 visits across 23 days simultaneously in a single MIP model produces millions of arc variables and sub-tour elimination constraints. Infeasible within realistic time limits ($> 10\text{ hours}$ without convergence). | **Two-Stage Decomposition** (Layer 1 Set Partitioning + Layer 2 CP-SAT TSP) solves in under 3 minutes with proven optimality. |
| **LKH-3 for Intra-Day TSP** | LKH relies on $\alpha$-nearness 1-tree relaxation under the assumption of symmetric, Euclidean metric space. In urban cycling road networks with one-way streets, detours, and barriers, LKH produces solutions 12%~35% worse than CP-SAT while requiring subprocess file I/O. | **CP-SAT Exact Circuit Solver** solves directly on asymmetric distance matrices, proving global optimality in $< 1.8\text{ s}$. |
| **Unconstrained ALNS (No $K_{\min}/K_{\max}$)** | Unconstrained search clusters up to 90 stores onto single days while leaving other days with 4 stores. Mathematically shorter by ~20 km, but **operationally impossible** for frontline reps. | **Bi-Directional Corridor $[K_{\min}, K_{\max}]$** enforces strict operational feasibility. |
| **Static One-Shot Set Partitioning** | Solving an integer program once over an arbitrary heuristic pool without pricing feedback plateaus early (gap > 7%), missing cross-solution column recombinations. | **Dual-Feedback Closed-Loop Column Generation** dynamically discovers negative reduced-cost columns, reducing gaps to $\le 1.15\%$. |

---

## 7. Verification & Benchmark Evidence

### 7.1 Layer 2 Single-Day TSP Engine Benchmark (09 Line Data)
All instances benchmarked against the mathematical global optimum (CP-SAT 120s):

| Scale | Metric | NN + 2-opt | LKH-3 (ATSP) | CP-SAT Global Exact |
|:---:|---|:---:|:---:|:---:|
| **$n=15$** (Light) | Distance / Gap<br/>Runtime / Status | 11.32 km (+2.5%)<br/>0.2 ms (Heuristic) | 13.09 km (+18.4%)<br/>349 ms (Heuristic) | **11.05 km (0.0% Gap)**<br/>**21.8 ms (OPTIMAL Proven)** |
| **$n=23$** (Typical) | Distance / Gap<br/>Runtime / Status | 19.39 km (+48.4%)<br/>0.5 ms (Heuristic) | 14.72 km (+12.6%)<br/>5.03 s (Heuristic) | **13.07 km (0.0% Gap)**<br/>**37.3 ms (OPTIMAL Proven)** |
| **$n=29$** (Heavy) | Distance / Gap<br/>Runtime / Status | 14.36 km (+18.4%)<br/>1.4 ms (Heuristic) | 16.37 km (+35.1%)<br/>5.02 s (Heuristic) | **12.12 km (0.0% Gap)**<br/>**78.6 ms (OPTIMAL Proven)** |
| **$n=35$** (Peak $K_{\max}$) | Distance / Gap<br/>Runtime / Status | 15.87 km (+8.8%)<br/>2.3 ms (Heuristic) | 19.32 km (+32.5%)<br/>5.07 s (Heuristic) | **14.58 km (0.0% Gap)**<br/>**1.77 s (OPTIMAL Proven)** |

### 7.2 Layer 1 Calendar Planning Ablation: Value of Feedback Coupling
Evaluating the independent contribution of TSP feedback within the $[23, 35]$ corridor on Line 09:

| Algorithm Family | Budget | Without Feedback (One-Shot / Blind) | With TSP Feedback Coupling | **Net Feedback Benefit** |
|---|:---:|:---:|:---:|:---:|
| **ALNS Family** | 60s | Cold-Evaluation: 365.0 km (3,480 iters) | Tour-Carrying: **275.7 km** (24,790 iters) | **−89.2 km (−24.5%)**, 7.1× throughput |
| **ALNS Family** | 300s | Cold-Evaluation: 365.0 km (59,822 iters) | Tour-Carrying: **272.9 km** (210,706 iters) | **−92.1 km (−25.2%)**, breaks 365km plateau |
| **HGS Family** | 60s | Blind-GA: 376.8 km (1,691 gens) | Tour-Feedback HGS: **277.2 km** (19 gens) | **−99.6 km (−26.4%)** |
| **HGS Family** | 300s | Blind-GA: 375.2 km (8,410 gens) | Tour-Feedback HGS: **268.5 km** (104 gens) | **−106.7 km (−28.4%)** |
| **SP / CG Family** | 60s | Static SP: 321.8 km (Gap 7.39%) | Dual-Feedback CG: **271.3 km** (Gap 0.51%) | **−50.5 km (−15.7%)**, gap tightened |
| **SP / CG Family** | 300s | Static SP: 321.8 km (Gap 7.39%) | Dual-Feedback CG: **271.1 km** (Gap 1.15%) | **−50.7 km (−15.8%)**, certified LP bound |

### 7.3 Full-Office 10-Representative Verified Production Ledger
Enforcing individual operational corridors $[K_{\min}(l), K_{\max}(l)]$ across all 10 lines:

$$\text{Baseline: } 16,857.0\text{ km} \quad \longrightarrow \quad \text{Optimized: } \mathbf{3,865.6\text{ km}} \quad \left( \mathbf{-77.1\%}, \text{ Net Saving: } 12,991.4\text{ km} \right)$$
$$\text{Corridor Compliance: } \mathbf{100\%} \quad (0\text{ violations across all } 230\text{ rep-days}) \quad \Big| \quad \text{Mean Certified Gap: } \mathbf{0.20\%}$$

---

## 8. Operational Tiers & Production Playbook

| Production Scenario | Target Engine | Latency SLA | Certified Gap | Operational Target |
|---|---|---|---|---|
| **Tier 1: Mobile In-Transit Dispatch** | `Nearest Neighbor with 2-opt` + Corridor Projection | $\le 50\text{ ms}$ | Heuristic (< 5% vs CP-SAT) | Dynamic insertion of ad-hoc visits while preserving past check-ins. |
| **Tier 2: Interactive Dispatch Console** | `Dual-Feedback CG` (Quick Mode, 4 CG iterations) | $\le 60\text{ s}$ | $\le 1.2\%$ | Territory dispatcher adjusting monthly schedules with instant visual verification. |
| **Tier 3: Monthly Batch Optimization** | `Dual-Feedback CG` + Full Pool Recombination | $\le 3\text{ min/line}$ | $\le 0.5\%$ | Automated end-of-month batch generating production schedules for the next cycle. |

---

## 9. Security, Privacy & Data Governance

- **Customer PII**: Raw customer phone numbers, personal contacts, and financial records are strictly excluded from the routing engine; only synthetic customer IDs (`客户编码`) and geographic coordinates (`经度`, `纬度`) are ingested.
- **Cache Isolation**: Distance matrices are hashed by line ID, coordinate set, and date stamp, preventing cross-tenant matrix contamination.
- **Audit Trails**: Every production schedule export includes full execution telemetry: solver status, runtime, iteration counts, and certified LP bounds.
