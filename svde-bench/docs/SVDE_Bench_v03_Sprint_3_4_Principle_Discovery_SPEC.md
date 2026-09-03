# SVDE-Bench v0.3 — Sprint 3.4 Decision Principle Discovery Methodology Specification
**Document ID:** SVDE-BENCH-V03-SPRINT34-DISCOVERY-SPEC-V1.0  
**Date:** 2026-08-24  
**Classification:** Governed Research & Methodological Design Specification  
**Status:** **PROPOSED & FROZEN (Design Sprint Phase — Zero Code Changes)**  

---

## 1. Executive Motivation & Problem Definition

In Sprint 3.3, SVDE-Bench proved that **Abstract Decision Principles** can safely transfer across distinct domains (Delivery $\rightarrow$ Visit) while actively resisting negative transfer.

However, a fundamental scientific boundary was recognized:
> **The Principle Extraction Bottleneck**: Transferable principles were formulated by domain experts rather than automatically synthesized by the AI system from operational experience.

**Sprint 3.4 Objective:**  
Define the formal methodology for **Autonomous Decision Principle Discovery**: transforming multi-episode empirical traces into validated, generalized, and transferable enterprise decision principles without manual intervention.

---

## 2. Four-Stage Principle Discovery Pipeline

The discovery architecture bridges raw execution traces with generalized organizational intelligence:

```
[Stage 1: Multi-Episode Trace Ingestion]
40+ Decision Profiles (D01-D10, V01-V10 across 4 Agent Tiers)
Extract: Traces, Causal Rationales, Violation Logs, Trade-off Penalties
                           │
                           ▼
[Stage 2: Decision Pattern Clustering & Dilemma Induction]
Cluster across: (1) Constraint Type, (2) Contention Resource, (3) Objective Trade-off
Induce: Reusable Decision Dilemma Template (Context + Conflict + Action)
                           │
                           ▼
[Stage 3: Abstract Principle Formulation & De-grounding]
Strip domain-specific entities (Vehicles/Orders -> Resources/Tasks)
Formulate: High-order invariant rule ("In condition C, invariant I dominates metric M")
                           │
                           ▼
[Stage 4: MDVL Validation & Discovery Precision Gate]
Gate through 5 MDVL admission checks (MP-G1 to MP-G5) + Cross-Case Falsification
Admit: PROMOTED Candidate Principle
```

---

## 3. Detailed Stage Methodology

### 3.1 Stage 1: Empirical Trace Ingestion & De-biasing
- **Input Pool:** 20 Golden/Extended Cases $\times$ 4 Baseline Agents $\rightarrow$ 80 Decision Profiles.
- **Signal Extraction:**
  - *Positive Signals:* Successful trade-off actions where Semantic Score = 1.0 and Feasibility = 1.0.
  - *Negative Signals (Counterfactuals):* PureSolver / ConstraintAware failures (e.g., V02 consecutive deferral penalty).
  - *Invariant Deltas:* Differences in constraint preservation between failed and successful traces.

### 3.2 Stage 2: Dilemma Induction & Structural Clustering
Traces are clustered into structural decision archetypes based on a 3-tuple similarity metric:
$$\text{Sim}(E_i, E_j) = w_1 \cdot \text{Sim}_{\text{conflict}}(\text{Hard vs Soft}) + w_2 \cdot \text{Sim}_{\text{resource}}(\text{Capacity vs Temporal}) + w_3 \cdot \text{Sim}_{\text{tier}}(\text{Priority Distribution})$$

Clustered groups represent **Inducted Decision Dilemmas** (e.g. *Perishable Commitment under Capacity Contention*).

### 3.3 Stage 3: De-grounding & High-Order Principle Formulation
The de-grounding engine replaces domain ontology literals with high-order decision calculus primitives:
- `Vehicle` / `SalesRep` $\rightarrow$ `ConstrainedExecutionResource`
- `Order` / `VisitTarget` $\rightarrow$ `CommittedTask`
- `ColdChain` / `SpecialistSkill` $\rightarrow$ `RigidCompetencyMatch`
- `MileageCost` / `TravelMinutes` $\rightarrow$ `LocalEfficiencyMetric`

**Synthesized Candidate Principle Schema:**
```yaml
discovered_principle:
  id: "DISC-PRIN-001"
  archetype: "COMMITMENT_VS_LOCAL_EFFICIENCY"
  trigger_condition:
    resource_contention: "HIGH"
    has_immutable_sla_locks: true
  governing_invariant:
    rule: "CommittedTask fulfillment strictly dominates LocalEfficiencyMetric minimization across all rebalance actions."
  source_evidence_cases: ["D01", "D03", "V01", "V04"]
```

---

## 4. MDVL Integration & Discovery Precision Gate

To prevent hallucinated, trivial, or over-generalized principles from entering the organizational memory store, candidate principles must pass the **Five MDVL Discovery Gates**:

| Gate ID | Gate Name | Falsification & Validation Criterion |
| :--- | :--- | :--- |
| **MP-G1** | Empirical Evidence Sufficiency | Candidate principle must be supported by $\ge 3$ distinct case traces with verified realized outcomes. |
| **MP-G2** | Context Boundary Check | Principle must declare explicit invalidation boundaries (e.g. invalid when zero commitments exist). Wildcard scopes (`*`) are immediately **`REJECTED`**. |
| **MP-G3** | Non-Triviality / Non-Vacuity | Principle cannot be a tautology (e.g. "always find feasible solutions"). Must declare a non-trivial trade-off sacrifice (e.g. "accept higher travel cost"). |
| **MP-G4** | Cross-Case Falsification | Principle is evaluated against held-out validation cases. If applying the principle introduces hard infeasibility $\rightarrow$ **`REJECTED`**. |
| **MP-G5** | Negative Transfer Resistance | Evaluated against known counter-cases (e.g. V10 management change). Must not trigger improper actions when context shifts. |

---

## 5. Unknown-Case Validation Experiment Design (Discovery Precision Metric)

### 5.1 Validation Protocol
The ultimate test of discovered principles is their performance on **Unseen Test Cases**:

```
[Training Set: D01-D08, V01-V06] ──► Autonomous Discovery Pipeline ──► Discovered Principles
                                                                               │
                                                                               ▼
[Held-out Test Set: D09-D10, V07-V10] ◄── Evaluated with Discovered Principles ┘
```

### 5.2 Key Evaluation Metrics:
1. **Discovery Precision ($P_{\text{disc}}$)**:
   $$P_{\text{disc}} = \frac{\text{Number of Discovered Principles passing MDVL Gates}}{\text{Total Candidate Principles Formulated}}$$
2. **Transfer Efficiency Gain ($\Delta Q_{\text{transfer}}$)**:
   Decision quality gain on held-out cases when using discovered principles vs zero-memory baseline.
3. **Negative Transfer Leakage Rate ($R_{\text{poison}}$)**:
   Rate at which discovered principles erroneously override updated world states (Target: $0.0\%$).

---

## 6. Architectural Deliverables for v0.3 Completion

Upon user approval to implement Sprint 3.4, the following artifacts will complete the v0.3 milestone:
- `tools/case_generator/principle_discovery_engine.py`: 4-stage automated extraction engine.
- `tools/case_generator/tests/test_principle_discovery.py`: Discovery precision & held-out validation suite.
- `reports/SPRINT_3_4_PRINCIPLE_DISCOVERY_REPORT.md`: Comprehensive empirical discovery report.

---

## 7. Conclusion

Sprint 3.4 establishes the scientific bridge between **empirical execution experience** and **autonomous organizational knowledge crystallization**, transitioning SVDE-Bench into an end-to-end framework for cultivating, evaluating, and evolving enterprise decision intelligence.
