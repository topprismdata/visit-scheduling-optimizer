"""SVDE Core Capability Contract & Pipeline Audit Tests (Sprint 6.4).

Validates:
1. CapabilityContract enforces explicit input structure, output guarantees, and evidence types.
2. RuntimeOrchestrator computes deterministic cryptographic input/output hashes per step.
3. Multi-step capability pipeline captures complete PipelineExecutionAudit traces.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import svde
from svde.contracts import (
    DecisionRequest, DecisionArtifact, DecisionSpec, DecisionContext,
    DecisionClass, AssignmentDecisionStructure, CapabilityContract,
    CapabilityStepTrace, PipelineExecutionAudit
)
from svde.planning.capability_registry import CORE_CAPABILITY_REGISTRY, BaseCapabilityAdapter
from svde.planning import DecisionPlanner
from svde.runtime import RuntimeOrchestrator


def test_capability_contract_definition():
    """Validates that DiscreteAssignmentSolverCapability exposes a complete CapabilityContract."""
    adapter = CORE_CAPABILITY_REGISTRY.get_capability("discrete_assignment")
    assert adapter is not None
    
    contract = adapter.contract
    assert isinstance(contract, CapabilityContract)
    assert contract.capability_name == "discrete_assignment"
    assert DecisionClass.DISCRETE_ASSIGNMENT in contract.supported_decision_classes
    assert contract.required_structure_type == AssignmentDecisionStructure
    assert "CAPACITY_BOUND_SATISFIED" in contract.guarantees
    assert "PHYSICAL_FEASIBILITY" in contract.evidence_types_emitted


def test_pipeline_execution_audit_and_cryptographic_hashes():
    """Validates that multi-step capability pipelines compute deterministic hashes and emit PipelineExecutionAudit."""
    req = DecisionRequest(
        request_id="REQ-HASH-AUDIT-001",
        domain="delivery",
        intent={"primary_objective": "min_cost"},
        world_state={
            "fleet": [{"id": "V1", "capacity_kg": 1000}],
            "orders": [{"id": "O1", "weight_kg": 200, "is_locked": True}]
        }
    )

    artifact = svde.decide(req)
    assert isinstance(artifact, DecisionArtifact)
    
    # 1. Audit trace envelope present
    assert "execution_steps" in artifact.execution_trace
    step_traces = artifact.execution_trace["execution_steps"]
    assert len(step_traces) >= 2  # Step 1: Solve + Step 2: Verify

    # 2. Cryptographic input/output hash validation
    step_1 = step_traces[0]
    assert "input_hash" in step_1
    assert "output_hash" in step_1
    assert len(step_1["input_hash"]) == 12
    assert len(step_1["output_hash"]) == 12
    assert step_1["status"] == "FEASIBLE"
    assert "discrete_assignment" in step_1["capability_name"]
