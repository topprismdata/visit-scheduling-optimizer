# SVDE Core Framework — System Implementation Specification (v1.0)
**Document ID:** SVDE-CORE-SYSTEM-SPEC-V1.0  
**Date:** 2026-08-24  
**Classification:** Canonical Engineering Specification & Architecture Freeze  
**Status:** **APPROVED, AUDITED & FROZEN (Sprint 6.4 Baseline)**  

---

## 1. Framework Philosophy & Core Position

The **Semantic Validated Decision Engine (SVDE)** is an **Enterprise Decision Intelligence Operating System (Decision OS)**:

```
[What SVDE is NOT]                    [What SVDE IS]
• NOT a monolithic OR solver          • A Declarative Decision Compiler
• NOT a generic Agent chat workflow   • An Extensible Capability Pipeline Router
• NOT a domain-specific dispatch app  • An Independent 3-Tier Feasibility Auditor
                                      • A Governed Decision Knowledge & Lifecycle Memory
```

### The Core Architectural Axiom:
$$\text{DecisionRequest} \xrightarrow[\text{DomainAdapter}]{\text{Compile}} \text{DecisionSpec} \xrightarrow[\text{CapabilityRouting}]{\text{Plan}} \text{DecisionPlan} \xrightarrow[\text{PipelineExec}]{\text{Runtime}} \text{DecisionResult} \xrightarrow[\text{3D Audit}]{\text{Audit}} \text{DecisionArtifact}$$

---

## 2. Real Runtime Architecture & Execution Pipeline

```
                                [External Caller / API Client]
                                              │
                                              ▼
                                 svde.decide(DecisionRequest)
                                              │
         ┌────────────────────────────────────┼────────────────────────────────────┐
         │                                    │                                    │
         ▼                                    ▼                                    ▼
[1. DecisionCompiler]                [2. Runtime Principles]             [3. DecisionPlanner]
• DomainAdapter Normalization        • Declarative Trigger Eval           • Structural Capability Match
• Extracts Invariants & Prefs        • Boundary Filtering (MP-G2/G5)      • Builds Ordered Pipeline
• Emits DecisionSpec                 • Produces Active/Rejected List      • Emits DecisionPlan
         │                                    │                                    │
         └────────────────────────────────────┴────────────────────────────────────┘
                                              │
                                              ▼
                                   [4. RuntimeOrchestrator]
                                   • Sequential Multi-Step Execution
                                   • Dynamic Capability Ingestion
                                   • Cryptographic Input/Output Hashing
                                   • Emits DecisionResult & Audit Trail
                                              │
                                              ▼
                                     [5. DecisionAuditor]
                                     • Physical Feasibility Verification
                                     • Business Commitment Verification
                                     • Declarative Competency Compliance
                                     • Assembles Segregated Evidence
                                              │
                                              ▼
                                      [DecisionArtifact]
```

---

## 3. Contract Specification & Data Primitives

### 3.1 `DecisionRequest` (`svde/contracts/__init__.py`)
- `request_id`: `str` — Unique tracking identifier.
- `domain`: `str` — Domain namespace key for adapter routing.
- `intent`: `Dict[str, Any]` — Business intent and objective priorities.
- `world_state`: `Dict[str, Any]` — Raw, un-normalized domain state.
- `semantic_contract`: `Dict[str, Any]` — Contractual SLAs and invariants.
- `runtime_context`: `Optional[Dict[str, Any]]` — Dynamic disturbance state.

### 3.2 First-Class Decision Structures (`svde/contracts/decision_structures.py`)
- **`AssignmentDecisionStructure`**: Discrete resource-to-task allocation modeling ($resources, tasks, contention, commitments$).
- **`RoutingDecisionStructure`**: Sequential network routing modeling ($nodes, edge\_matrix, depot\_ids, time\_windows, sequence\_locks$).

### 3.3 `DecisionSpec` (`svde/contracts/__init__.py`)
- `spec_id`: `str` — Compiled specification ID.
- `decision_class`: `DecisionClass` — Primary problem classification.
- `decision_structure`: `BaseDecisionStructure` — First-class typed structure.
- `required_capabilities`: `List[str]` — Required solver capabilities.
- `hard_invariants`, `soft_preferences`: Extracted rule lists.
- `governing_principles`: Promoted principles active for this episode.

### 3.4 `DecisionPlan` (`svde/contracts/__init__.py`)
- `plan_id`: `str` — Plan tracking ID.
- `steps`: `List[CapabilityStep]` — Ordered capability execution pipeline.
- `selected_engine`: `str` — Primary capability solver identifier.
- `engine_config`: `Dict[str, Any]` — Execution parameters and governing principles.

### 3.5 `DecisionEvidence` (`svde/contracts/__init__.py`)
- `physical`: `PhysicalFeasibilityEvidence` — Capacity limits & active resources ($solution\_feasible$).
- `business`: `BusinessFeasibilityEvidence` — SLA commitments & non-negotiable drops ($decision\_feasible$).
- `semantic`: `SemanticComplianceEvidence` — Declarative competency & compartment match ($semantic\_compliance$).
- `activated_principles`, `rejected_principles`: Explainability records.

### 3.6 `DecisionArtifact` (`svde/contracts/__init__.py`)
- Complete external delivery envelope containing decision payload, the 3 independent feasibility verdicts, segregated evidence, execution trace with cryptographic hashes, and unresolved issue strings.

---

## 4. Capability Extension Guide (How to Add Capabilities)

To integrate a new computational solver or reasoning model (e.g. Genetic Algorithm, PyVRP, or LLM Reasoner):

### Step 1: Implement `BaseCapabilityAdapter`
```python
from svde.planning.capability_registry import BaseCapabilityAdapter
from svde.contracts import CapabilityContract, DecisionClass, DecisionContext, DecisionResult, RoutingDecisionStructure

class PyVRPOptimizerCapability(BaseCapabilityAdapter):
    @property
    def contract(self) -> CapabilityContract:
        return CapabilityContract(
            capability_name="pyvrp_optimizer",
            supported_decision_classes=[DecisionClass.SEQUENTIAL_ROUTING],
            required_structure_type=RoutingDecisionStructure,
            guarantees=["TIME_WINDOWS_SATISFIED", "EUCLIDEAN_OPTIMAL"],
            evidence_types_emitted=["PHYSICAL_FEASIBILITY"]
        )

    def execute(self, context: DecisionContext, parameters: dict) -> DecisionResult:
        # 1. Ingest context.structure (RoutingDecisionStructure)
        # 2. Solve via PyVRP / Newton heuristics
        # 3. Return DecisionResult
        return DecisionResult(...)
```

### Step 2: Register into `CORE_CAPABILITY_REGISTRY`
```python
from svde.planning.capability_registry import CORE_CAPABILITY_REGISTRY

CORE_CAPABILITY_REGISTRY.register_capability("pyvrp_optimizer", PyVRPOptimizerCapability())
```
*Zero Core edits required. Planner automatically routes routing requests to the registered capability.*

---

## 5. Domain Extension Guide (How to Add Business Domains)

To integrate a new enterprise domain (e.g. Warehouse Slotting, Channel Quota Allocation, or Hospital Bed Management):

### Step 1: Implement `BaseDomainAdapter`
```python
from svde.domains import BaseDomainAdapter
from svde.contracts import DecisionRequest, DecisionContext, NormalizedEntity, DecisionClass

class WarehouseSlottingAdapter(BaseDomainAdapter):
    @property
    def domain_name(self) -> str:
        return "warehouse_slotting"

    def to_decision_context(self, request: DecisionRequest) -> DecisionContext:
        # Ingest warehouse world_state (Locations, SKUs, Movement Rates)
        # Emit canonical DecisionContext with SPATIAL_SLOTTING decision class
        return DecisionContext(
            request_id=request.request_id,
            domain=self.domain_name,
            primary_objective="minimize_travel_and_congestion",
            decision_classes=[DecisionClass.SPATIAL_SLOTTING],
            entities=[...],
        )
```

### Step 2: Register into `CORE_ADAPTER_REGISTRY`
```python
from svde.domains import CORE_ADAPTER_REGISTRY

CORE_ADAPTER_REGISTRY.register_adapter(WarehouseSlottingAdapter())
```
*Zero Core edits required. Calling `svde.decide(DecisionRequest(domain="warehouse_slotting", ...))` executes immediately.*

---

## 6. Testing & Engineering Verification Stratum

| Test Stratum | Focus | Test File & Suite | Count | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 0: Invariant Purity** | Zero Bench imports, Zero domain keywords in Core | `svde/tests/test_core_purity_contracts.py` | 5 tests | **PASS** ✅ |
| **Layer 1: Contract Safety** | Fail-closed resolution, 3-tier feasibility orthogonality | `svde/tests/test_core_purity_contracts.py` | 6 tests | **PASS** ✅ |
| **Layer 2: Core Execution** | End-to-end `svde.decide()` for Delivery, Visit, Overload | `svde/tests/test_core_engine.py` | 3 tests | **PASS** ✅ |
| **Layer 3: Structure & Pipeline** | Routing structure, multi-step pipeline & audit hashes | `svde/tests/test_decision_structures_composition.py` | 4 tests | **PASS** ✅ |
| **Layer 4: Capability Contracts**| Formal capability input/output and hash trace verification| `svde/tests/test_capability_contracts_audit.py` | 2 tests | **PASS** ✅ |
| **Layer 5: Benchmark Suite** | Multi-domain stress & decision intelligence validation | `svde-bench/` full regression test suite | 121 tests | **PASS** ✅ |

---

## 7. Conclusion & Governance Freeze

SVDE Core Framework v1.0 is **OFFICIALLY FROZEN** across its contracts, compiler, planning, runtime, verification, memory, and adapter layers. Total verified test count: **18 Core Tests + 121 Bench Tests = 139 Tests (100% PASS)**.
