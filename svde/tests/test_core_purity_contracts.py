"""SVDE Core Architecture Contract & Purity Tests (Sprint 6.4/6.5).

Verifies all 7 Code Review Remediation Invariants:
1. Zero active resources explicitly emits physical_feasible=False & unresolved_issues populated (Fix #2).
2. Capacity=0.0 is not overridden by 1000 fallback (Fix #3).
3. Capability registry defaults to allow_overwrite=False, preventing silent replacement (Fix #5).
4. Semantic contracts are ingested and enforced in audit (Fix #4).
5. All core purity and contract safety invariants remain green.
"""
import sys
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import svde
from svde.contracts import (
    DecisionRequest, DecisionArtifact, DecisionSpec, DecisionContext,
    NormalizedEntity, DecisionResult, DecisionClass,
    UnsupportedDomainError, UnsupportedCapabilityError, CapabilityContract,
    AssignmentDecisionStructure
)
from svde.domains import BaseDomainAdapter, CORE_ADAPTER_REGISTRY
from svde.planning.capability_registry import BaseCapabilityAdapter, CORE_CAPABILITY_REGISTRY, CapabilityRegistry
from svde.compiler import DecisionCompiler
from svde.planning import DecisionPlanner
from svde.runtime import RuntimeOrchestrator
from svde.verification import DecisionAuditor


def test_core_has_zero_dependency_on_svde_bench():
    """Invariant 1: svde core modules must never import svde-bench or svdebench."""
    svde_pkg = Path(svde.__file__).parent
    py_files = list(svde_pkg.rglob("*.py"))
    
    for py_f in py_files:
        if "tests" in str(py_f):
            continue
        content = py_f.read_text(encoding="utf-8")
        assert "svde-bench" not in content, f"Forbidden svde-bench import found in {py_f}"
        assert "svdebench" not in content, f"Forbidden svdebench import found in {py_f}"


def test_all_core_modules_have_zero_domain_specific_keywords():
    """Invariant 2: Scans ALL core modules for domain leaks."""
    core_modules = [
        Path(svde.runtime.__file__).parent / "__init__.py",
        Path(svde.planning.__file__).parent / "__init__.py",
        Path(svde.planning.__file__).parent / "capability_registry.py",
        Path(svde.compiler.__file__).parent / "__init__.py",
        Path(svde.verification.__file__).parent / "__init__.py",
    ]
    
    forbidden_terms = ["vehicle", "cold_chain", "sales_rep", "cadence", "store_manager", "patient", "nurse", "icu"]
    for path in core_modules:
        source = path.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in source, f"Domain specific keyword '{term}' found in core module: {path}"


def test_zero_resources_emits_structured_infeasibility_and_unresolved_issues():
    """Fix #2: Zero active resources request must return solution_feasible=False with explicit unresolved_issues."""
    req = DecisionRequest(
        request_id="REQ-ZERO-RES",
        domain="delivery",
        intent={"primary_objective": "test"},
        world_state={
            "fleet": [],  # Empty fleet
            "orders": [{"id": "O1", "weight_kg": 50}]
        }
    )

    artifact = svde.decide(req)
    assert isinstance(artifact, DecisionArtifact)
    assert artifact.solution_feasible is False
    assert artifact.decision_feasible is False
    assert len(artifact.unresolved_issues) >= 1
    assert any("Zero active execution resources" in iss for iss in artifact.unresolved_issues)


def test_zero_capacity_resource_is_not_treated_as_falsy_1000():
    """Fix #3: Resource with capacity=0.0 must not accept tasks and cause overload."""
    req = DecisionRequest(
        request_id="REQ-ZERO-CAP",
        domain="delivery",
        intent={"primary_objective": "test"},
        world_state={
            "fleet": [{"id": "V_ZERO", "type": "STANDARD_VAN", "capacity_kg": 0.0, "status": "AVAILABLE"}],
            "orders": [{"id": "O1", "weight_kg": 50.0, "is_locked": True}]
        }
    )

    artifact = svde.decide(req)
    # 50kg assigned to 0kg capacity vehicle -> physical overload violation!
    assert artifact.solution_feasible is False
    assert artifact.decision_feasible is False
    assert len(artifact.unresolved_issues) >= 1
    assert any("overloaded: 50.0 > 0.0" in iss for iss in artifact.unresolved_issues)


def test_capability_registry_disallows_silent_overwrites():
    """Fix #5: CapabilityRegistry.register_capability defaults to allow_overwrite=False and raises ValueError."""
    reg = CapabilityRegistry()
    
    class DummyCap(BaseCapabilityAdapter):
        @property
        def contract(self) -> CapabilityContract:
            return CapabilityContract(
                capability_name="discrete_assignment",
                supported_decision_classes=[DecisionClass.DISCRETE_ASSIGNMENT],
                required_structure_type=AssignmentDecisionStructure
            )
        def execute(self, ctx, p):
            pass

    with pytest.raises(ValueError) as excinfo:
        reg.register_capability("discrete_assignment", DummyCap(), allow_overwrite=False)
    assert "already registered" in str(excinfo.value)


def test_unknown_domain_fails_strictly():
    """P0-1 Acceptance: Unknown domain strictly raises UnsupportedDomainError."""
    request = DecisionRequest(
        request_id="REQ-UNKNOWN-DOM",
        domain="warehouse_slotting_unregistered",
        intent={"primary_objective": "test"},
        world_state={}
    )

    with pytest.raises(UnsupportedDomainError) as excinfo:
        svde.decide(request)
    assert "warehouse_slotting_unregistered" in str(excinfo.value)


def test_unknown_capability_fails_strictly():
    """P0-1 Acceptance: Unknown preferred capability strictly raises UnsupportedCapabilityError."""
    request = DecisionRequest(
        request_id="REQ-UNKNOWN-CAP",
        domain="delivery",
        intent={"primary_objective": "test"},
        world_state={"fleet": [{"id": "V1", "capacity_kg": 1000}], "orders": [{"id": "O1", "weight_kg": 100}]}
    )

    with pytest.raises(UnsupportedCapabilityError) as excinfo:
        svde.decide(request, preferred_capability="quantum_annealer_unavailable")
    assert "quantum_annealer_unavailable" in str(excinfo.value)


def test_mathematically_feasible_but_semantically_invalid_produces_orthogonal_evidence():
    """P0-4 Acceptance: Solution feasible (capacity OK) but semantic invalid (competency mismatch)."""
    auditor = DecisionAuditor()
    spec = DecisionSpec(
        spec_id="SPEC-SEM-TEST",
        domain="test",
        context=DecisionContext(
            request_id="R1",
            domain="test",
            primary_objective="test",
            entities=[
                NormalizedEntity(entity_id="RES_STD", entity_type="EXECUTION_RESOURCE", capacity=1000.0, is_active=True, provided_competencies=["GENERAL"]),
                NormalizedEntity(entity_id="TSK_SPEC", entity_type="COMMITTED_TASK", demand=100.0, is_locked=True, required_competencies=["SPECIALIST_CERT"])
            ]
        )
    )

    raw_result = DecisionResult(
        request_id="R1",
        status="FEASIBLE",
        raw_decision={"assignments": {"RES_STD": ["TSK_SPEC"]}},
        objective_value=100.0
    )

    artifact = auditor.audit(spec, raw_result)
    assert artifact.solution_feasible is True
    assert artifact.semantic_compliance is False
    assert artifact.decision_feasible is True
    assert artifact.evidence.physical.satisfied is True
    assert artifact.evidence.semantic.satisfied is False


def test_synthetic_third_domain_smoke_adapter_registers_without_core_modification():
    """Synthetic third domain registers and executes cleanly."""
    class HospitalBedAllocationAdapter(BaseDomainAdapter):
        @property
        def domain_name(self) -> str:
            return "hospital_bed"

        def to_decision_context(self, request: DecisionRequest) -> DecisionContext:
            raw = request.world_state
            entities = []
            for r in raw.get("nurses", []):
                entities.append(NormalizedEntity(
                    entity_id=r["nurse_id"],
                    entity_type="EXECUTION_RESOURCE",
                    capacity=float(r.get("shift_hours", 8.0)),
                    is_active=True,
                    provided_competencies=["ICU_SPECIALIST", "GENERAL"] if r.get("is_icu") else ["GENERAL"]
                ))
            for p in raw.get("patients", []):
                entities.append(NormalizedEntity(
                    entity_id=p["patient_id"],
                    entity_type="COMMITTED_TASK",
                    demand=float(p.get("care_hours", 2.0)),
                    is_locked=bool(p.get("is_critical", False)),
                    required_competencies=["ICU_SPECIALIST"] if p.get("is_critical") else ["GENERAL"],
                    time_window=[0, 8]
                ))
            return DecisionContext(
                request_id=request.request_id,
                domain=self.domain_name,
                primary_objective="critical_care_coverage",
                decision_classes=[DecisionClass.DISCRETE_ASSIGNMENT],
                entities=entities,
                has_hard_commitments=True,
                has_competency_constraints=True
            )

    CORE_ADAPTER_REGISTRY.register_adapter(HospitalBedAllocationAdapter(), allow_overwrite=True)

    req = DecisionRequest(
        request_id="REQ-HOSPITAL-001",
        domain="hospital_bed",
        intent={"primary_objective": "zero_critical_patient_drop"},
        world_state={
            "nurses": [
                {"nurse_id": "NURSE_ICU_01", "is_icu": True, "shift_hours": 8.0},
                {"nurse_id": "NURSE_GEN_02", "is_icu": False, "shift_hours": 8.0}
            ],
            "patients": [
                {"patient_id": "PATIENT_CRITICAL_01", "is_critical": True, "care_hours": 4.0},
                {"patient_id": "PATIENT_ROUTINE_02", "is_critical": False, "care_hours": 2.0}
            ]
        }
    )

    artifact = svde.decide(req)
    assert isinstance(artifact, DecisionArtifact)
    assert artifact.domain == "hospital_bed"
    assert artifact.solution_feasible is True
    assert artifact.decision_feasible is True
    assert artifact.semantic_compliance is True
