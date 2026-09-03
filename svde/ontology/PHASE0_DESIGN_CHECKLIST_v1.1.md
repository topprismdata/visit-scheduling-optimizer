# prism-ontology Phase 0 — 独立骨架设计清单 v1.1
**Document ID:** SVDE-PRISM-ONTOLOGY-PHASE0-DESIGN-CHECKLIST-V1.1
**Date:** 2026-08-24
**Status:** DESIGN ONLY (per v1.1 §9 Phase 0 — CLI/EAC skeleton, no business objects yet)
**Source Spec:** SVDE_ONTOLOGY_ENGINEERING_FRAMEWORK_COMPONENT_SPEC_v1.1
**Revision Note:** v1.0 → v1.1 incorporates 7 self-audit corrections approved by business owner:
1.埋 `ApproximationDeclaration` 接口
2.补网络访问阻断 CI 检查
3.统一文件命名
4.补全 8 个 anti-collapse CQ 文本
5.修正"5-state" → "7-state" lifecycle
6.明确 Phase 0/1/2 边界
7.补全 7 条 CI 阻断检查描述

---

## 0. Phase 0 Scope Boundary

### 0.1 In Scope (this phase only)
- 模块目录结构 (`src/prism_ontology/`)
- `pyproject.toml` skeleton
- CLI 入口（`init / ingest-source / add-claim / add-cq / validate / diagnose / gate`）
- Evidence bundle loader (YAML/JSON)
- Claim registry（5 证据等级分类）
- SHACL shape runner
- 7-state governance lifecycle implementation
- Provenance writer（PROV-O 兼容）
- 8 个 anti-collapse CQ 测试（含完整文本）
- GitHub Actions CI workflow（含 7 条阻断检查）
- **ApproximationDeclaration 接口骨架**（Phase 0 不用，Phase 1+ 必用）
- **网络访问阻断检查**（`pytest-network-blocked` 模式）

### 0.2 Out of Scope (deferred to Phase 1+)
- Sales Visit specific object definitions（v0.3 frozen 加载）
- Capability contracts (TerritoryAlignment / PeriodicVisitPlanning / DailyRouteOptimization)
- SVDE Runtime adapter
- Real network / CP-SAT solvers
- Production deployment

### 0.3 Phase Boundary Enforcement

| Item | Phase 0 | Phase 1 | Phase 2+ |
| :--- | :--- | :--- | :--- |
| Business objects | ❌ Forbidden | ✅ Allowed | ✅ Allowed |
| Capability contracts | ❌ Forbidden | ✅ Allowed | ✅ Allowed |
| Solver adapters | ❌ Forbidden | ⚠️ Adapter skeleton only | ✅ Full integration |
| Network calls | ❌ Forbidden | ❌ Forbidden (offline only) | ✅ Allowed (controlled) |
| ApproximationDeclaration | 🔧 Skeleton only | ✅ Active use | ✅ Active use |
| SHACL validation | 🔧 Skeleton + sample shapes | ✅ v0.3 shapes | ✅ Extended shapes |
| `svde` / `svde-bench` imports | ❌ STRICTLY FORBIDDEN | ❌ STRICTLY FORBIDDEN | ⚠️ Adapter only |
| 7-state lifecycle | 🔧 State machine only | ✅ Drives ontology | ✅ Drives runtime |

---

## 1. Module Layout

```
prism-ontology/
├── pyproject.toml              (Python 3.10+, rdflib, pyshacl, owlrl, jsonschema, click, pytest, pytest-network-blocked)
├── README.md
├── src/prism_ontology/
│   ├── __init__.py
│   ├── cli.py                   (Click-based CLI: 6 subcommands)
│   ├── api.py                   (Python API for SVDE adapter)
│   ├── models.py                (Evidence, Claim, CQ, Governance dataclasses)
│   ├── approximation/
│   │   ├── __init__.py
│   │   └── declaration.py       (ApproximationDeclaration interface skeleton)
│   ├── evidence/
│   │   ├── __init__.py
│   │   ├── registry.py          (Evidence Bundle loader)
│   │   └── levels.py            (5-level classifier: PRODUCT_FACT / DOMAIN_PRACTICE / MATHEMATICAL_THEORY / EMPIRICAL_EVIDENCE / DESIGN_INFERENCE)
│   ├── requirements/
│   │   ├── __init__.py
│   │   └── cq_registry.py       (CQ + decision-level routing)
│   ├── reference/
│   │   ├── __init__.py
│   │   └── compiler.py          (RDF/OWL builder, 7-state governed)
│   ├── profiles/
│   │   └── __init__.py          (Capability profile manifests)
│   ├── compiler/
│   │   ├── __init__.py
│   │   └── operational.py       (Reference → Operational TTL + JSON Schema)
│   ├── validator/
│   │   ├── __init__.py
│   │   ├── shacl_runner.py
│   │   └── cq_runner.py
│   ├── diagnostics/
│   │   ├── __init__.py
│   │   └── intent_router.py     (5-decision-level routing)
│   ├── governance/
│   │   ├── __init__.py
│   │   └── lifecycle.py         (7-state: EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN → DEPRECATED)
│   ├── provenance/
│   │   └── __init__.py          (PROV-O writer)
│   └── adapters/
│       └── __init__.py          (SVDE adapter interface)
├── tests/
│   ├── test_anti_collapse.py    (8 anti-fabrication CQ tests with full text — see §3)
│   ├── test_governance.py       (7-state transitions)
│   ├── test_validator.py        (SHACL run)
│   ├── test_approximation.py    (ApproximationDeclaration contract)
│   └── test_provenance.py       (PROV-O output)
├── ontology-bundles/            (empty, populated in Phase 1)
└── .github/workflows/
    └── ontology-ci.yml          (pytest + SHACL + 7 blocking checks — see §5)
```

---

## 2. CLI Subcommands (Phase 0 minimum viable)

```bash
prism-ontology init                            # create empty bundle skeleton
prism-ontology ingest-source --file <yaml>    # register evidence source
prism-ontology add-claim --file <yaml>        # register a business claim
prism-ontology add-cq --file <yaml>           # register competency question
prism-ontology validate --bundle ./bundle     # run SHACL on bundle
prism-ontology diagnose --question "..."      # route to decision level
prism-ontology gate --strict                  # frozen state verification
```

### Exit codes (per v1.1 §7.3)
- 0: pass
- 2: data/shape failure
- 3: ontology consistency failure
- 4: provenance/evidence gate failure
- 5: governance/GAP unapproved
- 6: compile failure

---

## 3. Anti-Collapse CQ Tests (8 with full text)

```python
# tests/test_anti_collapse.py

def test_territory_alignment_not_daily_route():
    """CQ-T1: 用户问"客户被分错了代表" → 必须分类为 TERRITORY_ALIGNMENT，不能误判为 DAILY_ROUTE_SEQUENCING。"""

def test_periodic_coverage_not_daily_route():
    """CQ-T2: 用户问"四周拜访频次不均匀" → 必须分类为 PERIODIC_COVERAGE，不能误判为单日路线。"""

def test_daily_route_keeps_fixed_visit_set():
    """CQ-T3: 单日路线能力接收的 Plan 必须是固定的 PlannedVisit 集合，能力不得擅自增减客户。"""

def test_locked_commitment_not_relaxable():
    """CQ-T4: 任何 Capability 不得通过牺牲 LOCKED 承诺来换取距离下降。DistanceMinimization.mustNotOverride(CommitmentLock) 必须机器验证。"""

def test_distance_cannot_reduce_coverage():
    """CQ-T5: 当距离下降导致覆盖率（频率/承诺）下降时，DistanceMinimization.subordinateTo(CoverageCompliance) 必须机器验证。"""

def test_sop_not_in_sales_visit_ontology():
    """CQ-T6 (GAP-6 永久关闭): 销售拜访本体不引入 SOPPolicy / CustomerSOPBinding / CustomerOpRequirement 任何 SOP 对象。"""

def test_actual_visit_not_modify_planned_visit():
    """CQ-T7: ActualVisit 不得回写覆盖 PlannedVisit 状态；滚动重排须新建 PlannedVisit 实例而非修改原计划。"""

def test_customer_not_folded_into_committed_task():
    """CQ-T8 (回归测试): Customer 永远不得被映射为 COMMITTED_TASK；Domain Adapter 折叠度报告须为 0。"""
```

---

## 4. Governance 7-State Lifecycle (v1.1 §8)

```python
# src/prism_ontology/governance/lifecycle.py

class LifecycleState(str, Enum):
    EXTRACTED = "EXTRACTED"                       # 从资料/对话初步识别
    EVIDENCE_PENDING = "EVIDENCE_PENDING"         # 等待精确来源/章节/页码
    CANDIDATE = "CANDIDATE"                       # 证据齐备，待评审
    DOMAIN_REVIEW = "DOMAIN_REVIEW"               # 架构/域专家审查
    BUSINESS_APPROVED = "BUSINESS_APPROVED"       # 业务方签字
    FROZEN = "FROZEN"                             # 不可变
    DEPRECATED = "DEPRECATED"                     # 软下线
    RETIRED = "RETIRED"                           # 硬下线
```

Transitions:
```
EXTRACTED → EVIDENCE_PENDING
EVIDENCE_PENDING → CANDIDATE
CANDIDATE → DOMAIN_REVIEW
DOMAIN_REVIEW → BUSINESS_APPROVED
BUSINESS_APPROVED → FROZEN
FROZEN → DEPRECATED  (only via OntologyChangeRequest)
DEPRECATED → RETIRED  (only via OntologyChangeRequest)
```

> ❌ Cannot skip states. ❌ Cannot regress (e.g., FROZEN → CANDIDATE).

---

## 5. CI Workflow with 7 Blocking Checks (v1.1 §7.4)

```yaml
# .github/workflows/ontology-ci.yml
name: ontology-ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v
      - run: prism-ontology validate --bundle ./ontology-bundles
      - run: prism-ontology gate --strict
      # --- 7 Blocking Checks (per v1.1 §7.4) ---
      - name: "Check 1: FROZEN objects must have source provenance"
        run: |
          if ! pytest tests/test_governance.py -v -k "test_frozen_requires_source"; then exit 1; fi
      - name: "Check 2: SHACL must pass on any committed bundle"
        run: |
          if ! prism-ontology validate --bundle ./ontology-bundles; then exit 1; fi
      - name: "Check 3: GAP must be approved before any frozen object change"
        run: |
          python -m prism_ontology.ci.gap_gate
      - name: "Check 4: Algorithm concepts must not appear in business ontology"
        run: |
          if ! pytest tests/test_anti_collapse.py -v -k "test_sop_not_in_sales_visit_ontology or test_customer_not_folded"; then exit 1; fi
      - name: "Check 5: Diagnostic must route to correct decision level"
        run: |
          if ! pytest tests/test_anti_collapse.py -v -k "test_territory_alignment_not_daily_route or test_periodic_coverage_not_daily_route"; then exit 1; fi
      - name: "Check 6: Unimplemented capabilities must not be marked available"
        run: |
          python -m prism_ontology.ci.capability_honesty_gate
      - name: "Check 7: Breaking changes must include migration note"
        run: |
          python -m prism_ontology.ci.breaking_change_migration_gate
      # --- Network Access Blocking (v1.1 §9 independence requirement) ---
      - name: "Check: No network access during test run"
        run: |
          pytest tests/ -v --disable-network
```

---

## 6. ApproximationDeclaration Interface (Phase 0 skeleton)

```python
# src/prism_ontology/approximation/declaration.py

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ApproximationDeclaration:
    """
    Per v1.1 §6.1 rule 5: 所有近似必须有显式 ApproximationDeclaration。
    Phase 0 only implements the contract; Phase 1+ fills the fields.
    """
    name: str                              # "default_capacity_per_km", "big_m_penalty_estimate"
    approximation_type: str               # "DEFAULT_VALUE" | "BIG_M_PENALTY" | "TOLERANCE_EPSILON"
    source_evidence_id: str              # Must link to a Claim
    justification: str                    # "Why this approximation is acceptable"
    error_bound_pct: float = 0.0         # 0.0 = exact, e.g., 0.05 = ±5%
    applicable_scope: str = ""           # "assignment / routing / simulation"
    deprecated_after: str = ""           # ISO 8601 date or empty
    notes: str = ""

    def to_prov_o(self) -> Dict[str, Any]:
        """Emit PROV-O compatible provenance for this approximation."""
        return {
            "prov:type": "prism:ApproximationDeclaration",
            "prov:name": self.name,
            "approximation_type": self.approximation_type,
            "source_evidence": self.source_evidence_id,
            "error_bound_pct": self.error_bound_pct,
        }
```

> **Phase 0 scope**: Interface + PROV-O emitter only. No field values used yet.  
> **Phase 1+ scope**: Capability adapters must populate `ApproximationDeclaration` for any non-exact computation.

---

## 7. Forbidden Imports (Phase 0 hard rule)

```python
# FORBIDDEN in src/prism_ontology/
from svde import *                    # 禁止
from svde_bench import *              # 禁止
import ortools                        # 禁止
import solvr                          # 禁止
import requests                       # 禁止（Phase 0 必须离线）
import urllib.request                 # 禁止（同上）
```

Allowed dependencies:
- `rdflib` — RDF/OWL graph I/O
- `pyshacl` — SHACL validation
- `owlrl` — optional lightweight rule materialization
- `jsonschema` — runtime contract validation
- `click` — CLI framework
- `pytest`, `pytest-network-blocked` — testing

---

## 8. Success Criteria for Phase 0 Completion

- [ ] `prism-ontology` package importable
- [ ] CLI 6 subcommands all return correct exit codes (0/2/3/4/5/6)
- [ ] 8 anti-collapse CQ tests pass (with full CQ text from §3)
- [ ] SHACL shapes can validate dummy bundle
- [ ] Governance 7-state machine transitions are testable
- [ ] Provenance writer emits PROV-O compatible output
- [ ] `ApproximationDeclaration` interface is importable
- [ ] CI workflow runs green with all 7 blocking checks
- [ ] Network access blocked during test run
- [ ] NO `svde-bench` / `svde` / solver imports (independence requirement)
- [ ] NO `FROZEN` claims without source provenance

---

## 9. Risk Register (Phase 0 self-audit)

| Risk | Mitigation | Status |
| :--- | :--- | :--- |
| Skipped lifecycle state transition | Governance 7-state machine with unit tests | Mitigated |
| Unsubstantiated frozen claim | Check 1: source provenance required | Mitigated |
| Algorithm concept → business object | Check 4 + 8 anti-collapse CQs | Mitigated |
| Unintended network access | Check 7 + `pytest-network-blocked` | Mitigated |
| Wrong decision level routing | Check 5 + 8 anti-collapse CQs | Mitigated |
| Unimplemented capability marked available | Check 6: capability honesty gate | Mitigated |
| Breaking change without migration | Check 7: breaking change migration gate | Mitigated |
| Approximation without declaration | ApproximationDeclaration contract (Phase 0 skeleton) | Mitigated (interface only in Phase 0) |

---

## 10. Self-Audit Trail (v1.0 → v1.1)

| Round | Issue | Resolution |
| :--- | :--- | :--- |
| v1.0 | `ApproximationDeclaration` not implemented (v1.1 §6.1 rule 5) | Skeleton added (§6) |
| v1.0 | No network access blocking in CI (v1.1 §9 independence) | `pytest-network-blocked` check added (§5) |
| v1.0 | Filename / title mismatch | Unified to "PHASE0_DESIGN_CHECKLIST_v1.1" |
| v1.0 | 8 anti-collapse CQs only listed as names | Full CQ text written (§3) |
| v1.0 | "5-state" incorrect (v1.1 has 7 states) | Corrected to 7-state (§4) |
| v1.0 | Phase 0/1/2 boundaries not explicit | Boundary table added (§0.3) |
| v1.0 | 7 CI blocking checks only summarized | Each check now explicit (§5) |

---

## 11. Next Step (Phase 0 → Phase 1 Handoff)

When Phase 0 success criteria (all 11 items in §8) are green:

1. Phase 1 starts: load `SVDE_SALES_VISIT_ONTOLOGY_DESIGN_v0.3.md` into `prism-ontology` reference layer
2. Generate Operational contract + SHACL shapes from reference
3. `DomainAdapter` reads operational contract (no business logic in adapter)
4. Capability contracts (`TerritoryAlignment` / `PeriodicVisitPlanning` / `DailyRouteOptimization`) loaded into profile registry
5. SVDE adapter calls `prism-ontology` for decision-level routing

---

## 12. Archival

- `archival_path`: `prism-ontology/provenance/phase0-design-checklist-v1.1.ttl`
- `design_state`: `EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN`
- `approved_by`: Business Owner + Project Architect
- `approval_date`: 2026-08-24
