# SVDE Reality Validation Implementation Plan (v0.4-alpha $\rightarrow$ Real Capability Benchmark)
**Document ID:** SVDE-REALITY-VALIDATION-PLAN-V1.0  
**Date:** 2026-08-24  
**Classification:** Core Engineering & Methodological Redirection Plan  
**Status:** **PLANNING & ARCHITECTURE PROPOSAL (Zero Implementation Phase)**  

---

## 1. Executive Summary & Reality Check

Following critical review of SVDE-Bench v0.4-alpha, the project officially pauses feature accumulation and initiates the **Reality Validation & De-Toying Phase**.

### 1.1 Objective Assessment of Current Baseline (v0.4-alpha)

| Capability Dimension | Current Verified State (What is Real) | Known Prototype Bottleneck (The Honest Limitation) |
| :--- | :--- | :--- |
| **1. Agent Evaluation** | 4-Tier evaluation metrics and Evaluator scoring are rigorously verified across 113 unit tests. | Baseline agents (`PureSolverAgent`, `SemanticAwareAgent`, etc.) are **behaviorally hard-coded Mock agents**, not independent black-box solvers or LLMs. |
| **2. Principle Mining** | Formal 4-stage pipeline structure, boundary checks, and MDVL gate interfaces are fully verified. | Current `principle_miner.py` relies on **keyword matching (`if "vip" in ...`) and template filling**, not true statistical/data-driven induction. |
| **3. Domain Transfer** | Multi-file schema and Pipeline reusability without tool modifications are verified. | Visit domain achieved zero-code execution by **concept downgrade / field remapping** (`req_cold` used for skills, `weight_kg` for duration), lacking true Domain Adapters. |
| **4. Benchmark Scale** | End-to-end multi-file case serialization and exact CP-SAT solving are verified. | Cases operate at **toy scale (1–3 vehicles, 2–5 orders)**, where CP-SAT solves trivially (<0.01s), evading real computational stress and trade-off noise. |

---

## 2. Target Architecture: Three-Tier Reality Redesign

```
                                  SVDE Target Architecture
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         ▼                                   ▼                                   ▼
[Module 1: Real Agent Interface]    [Module 2: Explicit Domain Adapters]  [Module 3: Scale & Data-Driven]
• Black-Box LLM Decision Agent       • DeliveryDomainAdapter               • Stress Generator (10-500 nodes)
• OR-Tools Exact Model Agent         • VisitDomainAdapter                  • Contrastive Principle Induction
• Governed Principle Runtime Agent   • Decoupled Canonical Context         • Noise & Infeasibility Injection
```

---

## 3. Four Core Engineering Workstreams

### Workstream 1: Black-Box Real Decision Agents (`agents/real/`)

Replace synthetic mock heuristics with genuine black-box reasoning engines conforming to `BaseDecisionAgent`:

1. **`LLMDecisionAgent`**:
   - Ingests structured `DecisionContext` in JSON format.
   - Prompts frontier LLM with system instructions, available vehicle/rep capacity, and customer SLA commitments.
   - Parses returned JSON routing plan and verifies if the LLM independently honors VIP commitments vs making naive proximity mistakes.
2. **`ConstrainedSolverAgent`**:
   - Formulates genuine MIP / CP-SAT mathematical models directly from `DecisionContext`.
   - Compares pure distance objective vs multi-tier weighted objective.
3. **`GovernedRuntimeAgent`**:
   - Ingests `PrincipleStore` retrieved principles as explicit invariant prompt constraints / solver bounds.

---

### Workstream 2: Explicit Domain Adapter Layer (`domains/adapters/`)

Eliminate concept remapping (`req_cold` for Specialist skills) and establish formal two-way Domain Adapters:

```python
class BaseDomainAdapter(ABC):
    @abstractmethod
    def to_canonical_context(self, case_dir: Path) -> DecisionContext:
        pass
    
    @abstractmethod
    def from_canonical_solution(self, artifact: DecisionArtifact) -> Dict[str, Any]:
        pass
```

- **`DeliveryDomainAdapter`**:
  - Vehicles $\rightarrow$ `NormalizedResource` (type: FLEET_VEHICLE, capacity: kg)
  - Orders $\rightarrow$ `NormalizedTask` (demand: kg, constraint: COLD_STORAGE)
- **`VisitDomainAdapter`**:
  - SalesReps $\rightarrow$ `NormalizedResource` (type: SALES_REP, capacity: working_minutes, skill_tier: SPECIALIST)
  - VisitDemands $\rightarrow$ `NormalizedTask` (duration: minutes, required_skill: SPECIALIST, cadence: BI_WEEKLY)

---

### Workstream 3: Scalable Synthetic Stress Benchmark (`tools/case_generator/scale_generator.py`)

Scale cases from 5-node toy problems into graduated operational stress benchmarks:

1. **Scale Hierarchy**:
   - **Small ($N=10$)**: Sanity and semantic logic debugging.
   - **Medium ($N=50$)**: Multi-vehicle combinatorial capacity contention.
   - **Large ($N=200$)**: Real-world city-scale distribution (50 vehicles, 200 orders, dense time windows).
   - **Stress ($N=500$)**: Solver timeout (>300s) and heuristic trade-off evaluation.
2. **Noise & Perturbation Generators**:
   - Stochastic travel time matrix perturbations (simulating dynamic urban traffic).
   - Unannounced mid-day order injection (testing true runtime replanning).

---

### Workstream 4: Data-Driven Principle Mining Engine v2 (`tools/case_generator/principle_miner_v2.py`)

Replace keyword if-else logic with **Contrastive Decision Trace Induction**:

```
[100+ Multi-Agent Traces] ──► [Feature Matrix Extraction] ──► [Contrastive Failure Clustering]
                                                                        │
                                                                        ▼
[Inducted Governing Invariant] ◄── [Decision Tree / Symbolic Induction] ┘
```

1. **Contrastive Failure Analysis**:
   - Compare high-scoring profiles ($\text{Semantic} = 1.0$) against failed profiles ($\text{Semantic} = 0.0$).
   - Identify decision variables with maximum mutual information with failure:
     $$I(X_{\text{action}}; Y_{\text{failure}}) \rightarrow \text{Trigger: Dropping locked task } O_i \text{ causes 100% SLA breach}$$
2. **Symbolic Invariant Induction**:
   - Automatically induce rule: `IF is_locked == True THEN assignment_priority = HIGHEST`.

---

## 4. Phased Milestone Roadmap (Sprints 5.1 to 5.4)

| Sprint | Engineering Deliverables | Acceptance Criteria |
| :--- | :--- | :--- |
| **Sprint 5.1** | `domains/adapters/` (Delivery & Visit Adapters) | Full decoupling: Visit domain uses genuine sales rep / skill fields with 0 field remapping. |
| **Sprint 5.2** | `tools/case_generator/scale_generator.py` | Generate $N=10, 50, 100$ benchmarks; measure solver solve time scaling ($t > 10\text{s}$). |
| **Sprint 5.3** | `agents/real/` (LLM & CP-SAT Black-Box Agents) | Test true LLM agent on D01–D10 and V01–V10; record real prompt failure modes. |
| **Sprint 5.4** | `tools/case_generator/principle_miner_v2.py` | Contrastive induction algorithm derives DISC-PRIN-001 from 100+ execution traces with 0 keyword rules. |

---

## 5. Summary & Immediate Next Action

The project boundary is clarified:
- **v0.4-alpha is preserved** as the verified governance scaffold (113 tests pass).
- **Sprint 5.1 will initiate the de-toying implementation** by building the explicit `DomainAdapter` architecture.
