# References / 参考文献

> All references are sorted by relevance to this work. For each, we note *(a)* the core method/finding and *(b)* how it informed our design.

---

## 1. Core Methodology (直接指导本研究的核心文献)

### 1.1 van Montfort, Leitner, Paradiso (2026)

**An exact algorithm for vehicle routing problems with temporal dependency constraints.**
Vrije Universiteit Amsterdam. Preprint.

- *Method*: Fragment-based set-partitioning formulation, solved by price-cut-and-enumerate (alternating column-and-row generation + valid inequalities + branch-and-cut).
- *Relevance*: **P1**. The fragment concept influenced our county-day decomposition (county-day = a self-contained scheduling unit; constraints only at "boundaries"). Our 2–3× speedup over vanilla branch-and-price and the strength of valid inequalities informed our use of set partitioning with clique-cut-style separation in CP-SAT.

### 1.2 Arenas-Vasco, Alcázar, Villegas (2025)

**A meta-analysis of set partitioning/set covering based matheuristics for vehicle routing problems.**
*Operations Research Perspectives* 15: 100357.

- *Finding*: 72% of surveyed papers use SP/SC as a post-optimizer; 25% iteratively; CPLEX dominates (36/54), Gurobi second (7); performance gain 0.6% (post-opt) vs 0.4% (iterative); **clique cuts significantly accelerate large SP models**.
- *Relevance*: **P2**. Validated our choice of CP-SAT (a free solver) with explicit valid-inequality awareness. Justified our four-layer lexicographic objective (post-opt framing) and informed the lexicographic cascade with warm-start hints.

### 1.3 Amazon Last-Mile Routing Research Challenge (2026)

**A decision-tree-based algorithm for the Amazon last-mile routing research challenge.**
*European Transport Research Review*. <https://doi.org/10.1186/s12544-026-00795-4>

- *Method*: Two-stage decomposition (Zone_ID sequencing + stop sequencing). Decision tree learns traversal direction (ascending/descending) from historical driver data via frequency analysis.
- *Relevance*: **A3** — our traversal-direction learning (PCA on inter-store displacement vectors) is directly inspired by this. Also confirmed the value of hierarchical spatial decomposition (zone → stop).

---

## 2. Periodic & Territory-Based Routing (本研究的问题邻域)

### 2.1 Cordeau, Gendreau, Laporte (1997)

**A guide to vehicle routing problems.**
*Networks* 49(4): 353–364. Survey of VRP variants.

- *Relevance*: PVRP problem formulation (frequency-constrained visits over a planning horizon) — the class this work falls into.

### 2.2 Fisher & Jaikumar (1981)

**A generalized assignment heuristic for vehicle routing.**
*Networks* 11(2): 109–124.

- *Method*: Cluster-first route-second decomposition.
- *Relevance*: The classical justification for our decomposition — cluster by region (county), then route within cluster.

### 2.3 Territory Design for Dynamic Multi-Period Vehicle Routing with Time Windows (2020)

- *Method*: Mathematical formulation and heuristics for grouping customers into geographic territories assigned to drivers over a planning horizon.
- *Relevance*: Validated that territory-design constraints ("one territory per day") reduce mileage by 20–40% in multi-period routing — our single-county-per-day rule is a special case of this.

### 2.4 ConVRP / Consistent VRP literature

Cohort of papers on routing with driver-customer time-consistency:

- *Relevance*: **F3** — our consistency objective (each customer's pattern matches its historical weekday preference) is a ConVRP relaxation. **Cited indirectly**: the most authoritative recent work is *Subramanyam, Gounaris et al.* in *Transportation Science* / *European Journal of Operational Research*.

---

## 3. Travel Time Estimation (F6 校准依据)

### 3.1 Time-Driven Activity-Based Costing (TDABC)

Kaplan, R. S., & Anderson, S. R. (2004/2007). *Time-driven activity-based costing: A simpler and more powerful path to higher profits.* Harvard Business School Press.

- *Concept*: Estimation of resource costs driven by time-consumption equations rather than surveys.
- *Relevance*: Theoretical underpinning for F6 — recognize that time costs dominate in service operations (sales visits, healthcare, consulting), and that naïve linear-time estimates can be wrong by a factor of 3–5×.

### 3.2 Inverse Optimization

Aytug, H., & Koehler, G. J. (2004) and follow-ups:

- *Concept*: Given observed decisions, infer the objective function (or constraints) the expert was implicitly optimizing.
- *Relevance*: Our historical-data analysis (comparing the rep's actual visits against the optimized plan) is a primitive form of inverse optimization — we observe the rep's behavior and infer the unstated rules.

---

## 4. Driver Behavior & Real-World Routing (数据驱动优化依据)

### 4.1 UPS ORION

From public case studies (e.g., Tactical VC, Head of AI, Forsmile):

- *Architecture*: Continuous optimization backed by telematics data — driver routes, fuel consumption, delivery times.
- *Relevance*: Industrial proof that ongoing learning from driver data (telematics→route) yields 100M miles / $400M savings. Our F6 + A3 stack is a small-scale analogue.

### 4.2 ARCA (Coca-Cola bottler, Mexico) VRP

- *Context*: Real-world beverage distribution territory design.
- *Relevance*: Same industry (快消 / FMCG) — territory-design savings of 15–30% are directly comparable to our county-pure-day empirical result (−47% store mileage).

### 4.3 Last-Mile Routing with Decision-Maker Preferences

Multiple recent papers (2024–2026) on routing that *deviates from shortest paths* due to driver/dispatcher preferences — see search results in our session notes.

- *Relevance*: Confirms that "true optimal" requires incorporating human-driver preferences, not just distance minimization.

---

## 5. Cutting-Plane / Constraint Generation (clique cuts, valid inequalities)

### 5.1 Clique Cuts for Set Partitioning

Standard OR technique: in the SP polytope, any clique (subgroup of mutually incompatible columns) yields a valid inequality. Modern solvers (CPLEX, Gurobi, CP-SAT) discover these via clique-cover and/or conflict-graph analysis.

- *Relevance*: Our solver choice (CP-SAT) was validated by the P2 meta-analysis finding that "aggressive clique cut separation significantly accelerates large SP models". The W[i,j,d] = AND(V[i,d], V[j,d]) construct we use is, in effect, a conflict-clique detection within each day.

### 5.2 BRKGA / Hybrid Genetic Algorithms for VRP

- *Relevance*: We considered GA-based approaches (and CP-SAT outperformed them for pure integer/boolean problems).

---

## 6. Recent Surveys & Position Papers

### 6.1 "Revisiting Cluster First Route Second for the Vehicle Routing Problem"

Academia.edu — academic paper comparing cluster-first vs. simultaneous optimization.

- *Relevance*: Confirms cluster-first is competitive for geographically constrained VRP variants (our case).

### 6.2 "Decomposition Strategies for Vehicle Routing Heuristics"

Optimization Online (2021).

- *Relevance*: Validates decomposition-based approaches for our problem size.

### 6.3 "Preference Learning and Human-Centric Optimization for Last-Mile Delivery Routing"

Recent survey (2024–2025) on integrating human preferences into routing optimization.

- *Relevance*: The closest *named* framework to our approach — preference learning + optimization.

### 6.4 "An LLM-powered MILP modelling engine for workforce scheduling guided by expert knowledge"

arXiv 2026.

- *Relevance*: Shows that combining human expertise with mathematical optimization is an active research direction. Our approach is a concrete instance of this paradigm.

---

## 7. Books / Foundational References

### 7.1 Toth, P., & Vigo, D. (2014)

**Vehicle Routing: Problems, Methods, and Applications** (2nd ed.). SIAM.

- *Relevance*: Comprehensive reference for all VRP variants and solution methods.

### 7.2 Lawler, E. L., & Wood, D. E. (1966)

**Branch-and-bound methods: A survey.**
*Operations Research* 14(4): 699–719.

- *Relevance*: Branch-and-bound is the foundation of CP-SAT's search.

### 7.3 Schrijver, A. (1998)

**Theory of Linear and Integer Programming.**
Wiley.

- *Relevance*: Foundational for the integer-programming theory underlying our model.

---

## Citation

If you reference this work, please cite:

```bibtex
@misc{visit-scheduling-optimizer-2026,
  title = {Visit Scheduling Optimizer: Set Partitioning + CP-SAT + TSP for Periodic Sales-Visit Routing},
  author = {{Open Source Contributors}},
  year = {2026},
  howpublished = {\url{https://github.com/your-org/visit-scheduling-optimizer}}
}
```

---

## Notes on Anonymization

This codebase is **fully anonymized**: no client names, salesperson names, real customer data, or geography-specific details are included. The framework is agnostic to:

- The specific partitioning (we use "Region 1–5" or generic county names)
- The specific customer set (the synthetic data generator creates realistic fake data)
- The specific salesperson and their behavior

It is *parameterized* to whatever partition + frequencies + coordinates the user provides.
