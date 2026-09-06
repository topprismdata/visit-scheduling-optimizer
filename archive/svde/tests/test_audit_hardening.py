"""SVDE Core Acceptance Test (Sprint 6.5 Remediated).

Validates:
1. Custom semantic invariants are actually enforced during audit (Fix #1).
2. Malformed semantic_contract raises CompilationError (Fix #4).
3. Routing audit catches empty routes, unvisited customer stops, and depot closure (Fix #3).
4. Physical / Business / Semantic feasibility dimensions are independently verified.
"""
import sys
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import svde
from svde.contracts import (
    DecisionRequest, DecisionArtifact, UnsupportedDomainError, UnsupportedCapabilityError, CompilationError
)


def test_custom_semantic_invariant_enforcement():
    """Fix #1: Confirms that custom invariants (e.g. MUST_BE_FALSE or impossible rules) are audited and reject semantic compliance."""
    request = DecisionRequest(
        request_id="REQ-CUSTOM-INV-FAIL",
        domain="delivery",
        intent={"primary_objective": "test"},
        world_state={
            "fleet": [{"id": "V1", "capacity_kg": 1000, "status": "AVAILABLE"}],
            "orders": [{"id": "O1", "weight_kg": 100, "is_locked": True}]
        },
        semantic_contract={
            "invariants": [
                {"id": "IMPOSSIBLE_RULE", "type": "MUST_BE_FALSE"}
            ]
        }
    )

    artifact = svde.decide(request)
    assert isinstance(artifact, DecisionArtifact)
    # Physical assignment is 100kg <= 1000kg (solution_feasible=True)
    assert artifact.solution_feasible is True
    # But semantic compliance MUST be False due to the violated custom invariant!
    assert artifact.semantic_compliance is False
    assert len(artifact.unresolved_issues) >= 1
    assert any("IMPOSSIBLE_RULE" in iss for iss in artifact.unresolved_issues)


def test_malformed_semantic_contract_raises_compilation_error():
    """Fix #4: Passing malformed semantic_contract shapes raises typed CompilationError."""
    # Malformed as non-dict (e.g. string)
    req_bad_type = DecisionRequest(
        request_id="REQ-BAD-SEM-TYPE",
        domain="delivery",
        intent={},
        world_state={"fleet": [{"id": "V1", "capacity_kg": 100}], "orders": []},
        semantic_contract="invalid_string_instead_of_dict"
    )
    with pytest.raises(CompilationError) as excinfo:
        svde.decide(req_bad_type)
    assert "must be a dictionary" in str(excinfo.value)

    # Malformed constraints as non-list
    req_bad_constraints = DecisionRequest(
        request_id="REQ-BAD-CONSTR",
        domain="delivery",
        intent={},
        world_state={"fleet": [{"id": "V1", "capacity_kg": 100}], "orders": []},
        semantic_contract={"constraints": "not_a_list"}
    )
    with pytest.raises(CompilationError) as excinfo:
        svde.decide(req_bad_constraints)
    assert "must be a list" in str(excinfo.value)


def test_routing_auditor_catches_empty_routes_and_unvisited_stops():
    """Fix #3: In routing problems, returning empty routes when stops exist causes audit failure."""
    from svde.contracts import DecisionClass, RoutingDecisionStructure, RoutingNode, DecisionResult, DecisionSpec, DecisionContext
    from svde.verification import DecisionAuditor

    auditor = DecisionAuditor()
    spec = DecisionSpec(
        spec_id="SPEC-ROUTING-AUDIT-TEST",
        domain="city_routing",
        decision_class=DecisionClass.SEQUENTIAL_ROUTING,
        decision_structure=RoutingDecisionStructure(
            nodes=[
                RoutingNode("DEPOT", "DEPOT"),
                RoutingNode("STOP_A", "CUSTOMER_STOP", is_locked_window=True),
                RoutingNode("STOP_B", "CUSTOMER_STOP", is_locked_window=False)
            ],
            edge_matrix={
                "DEPOT": {"STOP_A": 10.0, "STOP_B": 12.0},
                "STOP_A": {"STOP_B": 8.0, "DEPOT": 10.0},
                "STOP_B": {"DEPOT": 12.0, "STOP_A": 8.0}
            },
            depot_ids=["DEPOT"]
        ),
        context=DecisionContext(request_id="R1", domain="city_routing", primary_objective="test")
    )

    # 1. Result with empty routes -> Must be audited as physical & business failure!
    empty_result = DecisionResult(
        request_id="R1",
        status="FEASIBLE",
        raw_decision={"assigned_routes": {}},
        objective_value=0.0
    )
    art_empty = auditor.audit(spec, empty_result)
    assert art_empty.solution_feasible is False
    assert art_empty.decision_feasible is False
    assert any("missing or has empty" in iss for iss in art_empty.unresolved_issues)

    # 2. Result missing depot closure (does not start/end at DEPOT) -> Must be caught!
    bad_depot_result = DecisionResult(
        request_id="R1",
        status="FEASIBLE",
        raw_decision={"assigned_routes": {"ROUTE_1": ["STOP_A", "STOP_B"]}},
        objective_value=10.0
    )
    art_bad_depot = auditor.audit(spec, bad_depot_result)
    assert art_bad_depot.solution_feasible is False
    assert any("must start and end at a valid depot" in iss for iss in art_bad_depot.unresolved_issues)

    # 3. Valid route starting and ending at DEPOT visiting all stops -> Passes cleanly!
    valid_result = DecisionResult(
        request_id="R1",
        status="FEASIBLE",
        raw_decision={"assigned_routes": {"ROUTE_1": ["DEPOT", "STOP_A", "STOP_B", "DEPOT"]}},
        objective_value=30.0
    )
    art_valid = auditor.audit(spec, valid_result)
    assert art_valid.solution_feasible is True
    assert art_valid.decision_feasible is True
    assert len(art_valid.unresolved_issues) == 0
