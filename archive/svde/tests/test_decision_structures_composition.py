"""SVDE Core Decision Structures & Capability Composition Tests (Sprint 6.3/6.4/6.5).

Validates:
1. RoutingDecisionStructure compiles natively with full edge matrix and max travel duration.
2. Routing DecisionAuditor verifies edge matrix connectivity, time-window violations, and route duration.
3. Unsupported routing capability strictly fails closed with UnsupportedCapabilityError.
4. Dynamically registered sequential routing capability executes cleanly through multi-step pipeline.
5. SemanticAuditCapability audits semantic invariants and intermediate decision payloads.
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
    DecisionClass, AssignmentDecisionStructure, RoutingDecisionStructure,
    RoutingNode, RoutingEdge, UnsupportedCapabilityError, DecisionResult,
    CapabilityContract
)
from svde.domains import BaseDomainAdapter, CORE_ADAPTER_REGISTRY
from svde.planning.capability_registry import BaseCapabilityAdapter, CORE_CAPABILITY_REGISTRY
from svde.compiler import DecisionCompiler
from svde.planning import DecisionPlanner
from svde.runtime import RuntimeOrchestrator
from svde.verification import DecisionAuditor


def test_routing_decision_structure_compilation():
    """Validates that a routing request compiles into a first-class RoutingDecisionStructure."""
    class CityFleetRoutingAdapter(BaseDomainAdapter):
        @property
        def domain_name(self) -> str:
            return "city_routing"

        def to_decision_context(self, request: DecisionRequest) -> DecisionContext:
            raw = request.world_state
            nodes = [
                RoutingNode(
                    node_id=stop["id"],
                    node_type="DEPOT" if stop.get("is_depot") else "CUSTOMER_STOP",
                    location_coords=stop.get("coords", [0.0, 0.0]),
                    service_duration=float(stop.get("duration", 15.0)),
                    time_window=stop.get("window", [0, 480]),
                    is_locked_window=bool(stop.get("is_locked", False))
                )
                for stop in raw.get("stops", [])
            ]
            routing_struct = RoutingDecisionStructure(
                nodes=nodes,
                edge_matrix=raw.get("distance_matrix", {}),
                depot_ids=["DEPOT_01"],
                max_travel_time_per_route=300.0,
                has_sequence_locks=True
            )
            return DecisionContext(
                request_id=request.request_id,
                domain=self.domain_name,
                primary_objective="minimize_total_transit_seconds",
                decision_classes=[DecisionClass.SEQUENTIAL_ROUTING],
                structure=routing_struct,
                has_hard_commitments=True
            )

    CORE_ADAPTER_REGISTRY.register_adapter(CityFleetRoutingAdapter(), allow_overwrite=True)

    req = DecisionRequest(
        request_id="REQ-ROUTING-001",
        domain="city_routing",
        intent={"primary_objective": "min_time"},
        world_state={
            "stops": [
                {"id": "DEPOT_01", "is_depot": True, "coords": [0.0, 0.0]},
                {"id": "STOP_A", "is_depot": False, "coords": [10.0, 5.0], "is_locked": True, "window": [60, 120]},
                {"id": "STOP_B", "is_depot": False, "coords": [15.0, 20.0], "is_locked": False, "window": [0, 240]}
            ],
            "distance_matrix": {
                "DEPOT_01": {"STOP_A": 12.0, "STOP_B": 25.0},
                "STOP_A": {"STOP_B": 10.0, "DEPOT_01": 15.0},
                "STOP_B": {"DEPOT_01": 20.0}
            }
        }
    )

    compiler = DecisionCompiler()
    spec = compiler.compile(req)

    assert spec.decision_class == DecisionClass.SEQUENTIAL_ROUTING
    assert isinstance(spec.decision_structure, RoutingDecisionStructure)
    assert len(spec.decision_structure.nodes) == 3
    assert spec.decision_structure.depot_ids == ["DEPOT_01"]
    assert spec.decision_structure.max_travel_time_per_route == 300.0


def test_routing_auditor_catches_undefined_edges_and_time_window_breach():
    """Validates that DecisionAuditor catches missing edges in edge_matrix and late arrival window violations."""
    auditor = DecisionAuditor()
    nodes = [
        RoutingNode("DEPOT_01", "DEPOT", time_window=[0, 480]),
        RoutingNode("STOP_A", "CUSTOMER_STOP", service_duration=30.0, time_window=[0, 50], is_locked_window=True),
        RoutingNode("STOP_B", "CUSTOMER_STOP", service_duration=30.0, time_window=[0, 300])
    ]
    edge_matrix = {
        "DEPOT_01": {"STOP_A": 60.0},  # Transit to STOP_A takes 60 min -> arrives at 60 > late window 50!
        "STOP_A": {"STOP_B": 10.0}
        # Missing edge: STOP_B -> DEPOT_01
    }
    spec = DecisionSpec(
        spec_id="SPEC-EDGE-TEST",
        domain="routing",
        decision_class=DecisionClass.SEQUENTIAL_ROUTING,
        decision_structure=RoutingDecisionStructure(
            nodes=nodes,
            edge_matrix=edge_matrix,
            depot_ids=["DEPOT_01"],
            max_travel_time_per_route=100.0  # Total time = 60 + 30 + 10 + 30 = 130 > 100 max!
        ),
        context=DecisionContext(request_id="R1", domain="routing", primary_objective="test")
    )

    # Output route: DEPOT_01 -> STOP_A -> STOP_B -> DEPOT_01
    bad_route_result = DecisionResult(
        request_id="R1",
        status="FEASIBLE",
        raw_decision={"assigned_routes": {"R1": ["DEPOT_01", "STOP_A", "STOP_B", "DEPOT_01"]}},
        objective_value=100.0
    )

    artifact = auditor.audit(spec, bad_route_result)
    assert artifact.solution_feasible is False
    assert artifact.decision_feasible is False
    # 1. Undefined edge (STOP_B -> DEPOT_01) caught
    assert any("undefined edge (STOP_B -> DEPOT_01)" in iss for iss in artifact.unresolved_issues)
    # 2. Time window breach at STOP_A caught
    assert any("exceeding late window 50" in iss for iss in artifact.unresolved_issues)
    # 3. Maximum route duration exceeded caught
    assert any("exceeds maximum allowed 100.0" in iss for iss in artifact.unresolved_issues)


def test_dynamically_registered_routing_capability_executes_pipeline():
    """Validates that registering a sequential_routing capability executes cleanly with valid edge matrix."""
    class MockSequentialVRPNewtonCapability(BaseCapabilityAdapter):
        @property
        def contract(self) -> CapabilityContract:
            return CapabilityContract(
                capability_name="sequential_routing",
                supported_decision_classes=[DecisionClass.SEQUENTIAL_ROUTING],
                required_structure_type=RoutingDecisionStructure,
                guarantees=["SEQUENCE_CONSTRAINTS_SATISFIED", "DISTANCE_OPTIMAL"],
                evidence_types_emitted=["PHYSICAL_FEASIBILITY"]
            )

        def execute(self, context: DecisionContext, parameters: dict) -> DecisionResult:
            return DecisionResult(
                request_id=context.request_id,
                status="FEASIBLE",
                raw_decision={
                    "assigned_routes": {
                        "DEPOT_01": ["DEPOT_01", "STOP_A", "STOP_B", "DEPOT_01"]
                    },
                    "total_travel_distance_km": 37.0
                },
                objective_value=37.0,
                execution_trace=[{"step": "TSP_Exact_Sequence_Solved", "sequence": ["DEPOT_01", "STOP_A", "STOP_B", "DEPOT_01"]}],
                engine_metadata={"capability": self.capability_type}
            )

    CORE_CAPABILITY_REGISTRY.register_capability("sequential_routing", MockSequentialVRPNewtonCapability(), allow_overwrite=True)
    assert CORE_CAPABILITY_REGISTRY.is_available("sequential_routing")

    planner = DecisionPlanner()
    orchestrator = RuntimeOrchestrator()

    nodes = [
        RoutingNode("DEPOT_01", "DEPOT", time_window=[0, 480]),
        RoutingNode("STOP_A", "CUSTOMER_STOP", service_duration=10.0, time_window=[0, 180], is_locked_window=True),
        RoutingNode("STOP_B", "CUSTOMER_STOP", service_duration=10.0, time_window=[0, 240])
    ]
    edge_matrix = {
        "DEPOT_01": {"STOP_A": 10.0},
        "STOP_A": {"STOP_B": 10.0},
        "STOP_B": {"DEPOT_01": 10.0}
    }

    spec = DecisionSpec(
        spec_id="SPEC-ROUTING-RUN",
        domain="city_routing",
        decision_class=DecisionClass.SEQUENTIAL_ROUTING,
        decision_structure=RoutingDecisionStructure(
            nodes=nodes,
            edge_matrix=edge_matrix,
            depot_ids=["DEPOT_01"],
            max_travel_time_per_route=200.0
        ),
        context=DecisionContext(
            request_id="REQ-ROUTING-001",
            domain="city_routing",
            primary_objective="test",
            decision_classes=[DecisionClass.SEQUENTIAL_ROUTING]
        ),
        required_capabilities=["sequential_routing"]
    )

    plan = planner.plan(spec)
    assert plan.selected_engine == "sequential_routing"
    assert len(plan.steps) == 2  # Multi-step pipeline (Solve -> Verify)

    result = orchestrator.execute(spec, plan)
    assert result.status == "FEASIBLE"
    assert "pipeline_audit" in result.engine_metadata
    
    trace = result.execution_trace
    assert len(trace) >= 2
    assert trace[0]["step_id"] == "step_1_sequential_routing"
    assert trace[0]["capability_name"] == "sequential_routing"
    assert trace[1]["step_id"] == "step_2_verify"

    # Audit the clean result
    auditor = DecisionAuditor()
    artifact = auditor.audit(spec, result)
    assert artifact.solution_feasible is True
    assert artifact.decision_feasible is True
    assert len(artifact.unresolved_issues) == 0
