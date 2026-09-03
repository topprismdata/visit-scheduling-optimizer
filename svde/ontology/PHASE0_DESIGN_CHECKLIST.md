# prism-ontology Phase 0 — 独立骨架设计清单
**Document ID:** SVDE-PRISM-ONTOLOGY-PHASE0-DESIGN-V1.0
**Date:** 2026-08-24
**Status:** DESIGN ONLY (per v1.1 §9 Phase 0 — CLI/EAC skeleton, no business objects yet)
**Source Spec:** SVDE_ONTOLOGY_ENGINEERING_FRAMEWORK_COMPONENT_SPEC_v1.1

---

## 0. Phase 0 Scope Boundary

### 0.1 In Scope (this phase only)
- Module directory structure (src/prism_ontology/)
- pyproject.toml skeleton
- CLI entry point (init/ingest-source/add-claim/add-cq/validate/diagnose/gate)
- Evidence bundle loader (YAML/JSON)
- Claim registry (5 evidence levels)
- SHACL shape runner (using pyshacl)
- Governance state machine (5-state)
- Provenance writer (PROV-O compatible)
- 8+ Anti-collapse CQ tests
- GitHub Actions CI workflow (pytest + SHACL gate)

### 0.2 Out of Scope (deferred to Phase 1+)
- Sales Visit specific object definitions (deferred to v0.3 frozen ontology load)
- Capability contracts (TerritoryAlignment, PeriodicVisitPlanning, DailyRouteOptimization)
- SVDE Runtime adapter
- Real network / CP-SAT solvers
- Production deployment

---

## 1. Module Layout

```
prism-ontology/
├── pyproject.toml             (Python 3.10+, rdflib, pyshacl, owlrl, jsonschema, pytest)
├── README.md
├── src/prism_ontology/
│   ├── __init__.py
│   ├── cli.py                  (Click-based CLI: 6 subcommands)
│   ├── api.py                  (Python API for SVDE adapter)
│   ├── models.py               (Evidence, Claim, CQ, Governance dataclasses)
│   ├── evidence/
│   │   ├── __init__.py
│   │   ├── registry.py         (Evidence Bundle loader)
│   │   └── levels.py           (5-level classifier)
│   ├── requirements/
│   │   ├── __init__.py
│   │   └── cq_registry.py      (CQ + decision-level routing)
│   ├── reference/
│   │   ├── __init__.py
│   │   └── compiler.py         (RDF/OWL builder, 5-state governed)
│   ├── profiles/
│   │   └── __init__.py         (Capability profile manifests)
│   ├── compiler/
│   │   ├── __init__.py
│   │   └── operational.py      (Reference → Operational TTL + JSON Schema)
│   ├── validator/
│   │   ├── __init__.py
│   │   ├── shacl_runner.py
│   │   └── cq_runner.py
│   ├── diagnostics/
│   │   ├── __init__.py
│   │   └── intent_router.py    (5-decision-level routing)
│   ├── governance/
│   │   └── __init__.py         (5-state lifecycle: EXTRACTED→...→FROZEN→DEPRECATED)
│   ├── provenance/
│   │   └── __init__.py         (PROV-O writer)
│   └── adapters/
│       └── __init__.py         (SVDE adapter interface)
├── tests/
│   ├── test_anti_collapse.py   (8+ anti-fabrication CQ tests)
│   ├── test_governance.py      (5-state transitions)
│   ├── test_validator.py       (SHACL run)
│   └── test_provenance.py      (PROV-O output)
├── ontology-bundles/           (empty, populated in Phase 1)
└── .github/workflows/
    └── ontology-ci.yml         (pytest + SHACL gate)
```

---

## 2. CLI Subcommands (Phase 0 minimum viable)

```bash
prism-ontology init                       # create empty bundle skeleton
prism-ontology ingest-source --file <yaml> # register evidence source
prism-ontology add-claim --file <yaml>     # register a business claim
prism-ontology add-cq --file <yaml>        # register competency question
prism-ontology validate --bundle ./bundle  # run SHACL on bundle
prism-ontology diagnose --question "..."   # route to decision level
prism-ontology gate --strict               # frozen state verification
```

### Exit codes (per v1.1 §7.3)
- 0: pass
- 2: shape/data failure
- 3: ontology consistency failure
- 4: provenance/evidence gate failure
- 5: governance/GAP unapproved
- 6: compile failure

---

## 3. Anti-Collapse CQ Tests (Phase 0 minimum 8)

```python
def test_territory_alignment_not_daily_route():
def test_periodic_coverage_not_daily_route():
def test_daily_route_keeps_fixed_visit_set():
def test_locked_commitment_not_relaxable():
def test_distance_cannot_reduce_coverage():
def test_sop_not_in_sales_visit_ontology():  # GAP-6 永久关闭
def test_actual_visit_not_modify_planned_visit():
def test_customer_not_folded_into_committed_task():
```

---

## 4. CI Workflow (Phase 0 minimum)

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
      - run: prism-ontology gate --strict
```

---

## 5. Success Criteria for Phase 0 Completion

- [ ] `prism-ontology` package importable
- [ ] CLI 6 subcommands all return correct exit codes
- [ ] 8+ anti-collapse CQ tests pass
- [ ] SHACL shapes can validate dummy bundle
- [ ] Governance 5-state machine transitions are testable
- [ ] Provenance writer emits PROV-O compatible output
- [ ] CI workflow runs green
- [ ] NO `svde-bench` / `svde` / solver imports (independence requirement)

---

## 6. Forbidden Imports (Phase 0 hard rule)

```python
# FORBIDDEN in src/prism_ontology/
from svde import *                    # 禁止
from svde_bench import *              # 禁止
import ortools                        # 禁止
import solvr                          # 禁止
```

必须只用：rdflib / pyshacl / owlrl / jsonschema / click / pytest
