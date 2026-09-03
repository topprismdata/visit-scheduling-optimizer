"""
test_schema.py — Core Schema Validation & Serialization Unit Tests (Sprint 1A)
"""
import pytest
from pydantic import ValidationError
from svdebench.core.case import DecisionCase, CaseMetadata
from svdebench.core.artifact import DecisionArtifact
from svdebench.core.trace import DecisionTrace
from svdebench.core import load_case_yaml, dump_case_yaml

def test_decision_case_serialization_roundtrip():
    case = DecisionCase(
        metadata=CaseMetadata(
            id="CASE-DELIVERY-001",
            domain="Dynamic Fleet Route Logistics",
            name="Emergency Breakdown Reallocation",
            tags=["temporal", "dynamic", "breakdown"]
        ),
        intent={"objective": "min_lateness_and_cost", "target_service_level": 0.99},
        world_state={"depot": [0, 0], "fleet": ["VEH_01", "VEH_02", "VEH_03"]},
        semantic_contract={
            "constraints": ["C1_VehicleCapacity", "C2_HardTimeWindow"],
            "invariants": ["I1_PastFactImmutability", "I2_LockPreservation"]
        },
        runtime_context={"timestamp_min": 180, "past_delivered": ["ORD_01", "ORD_02"]},
        events=[{"event_type": "VEHICLE_BREAKDOWN", "vehicle_id": "VEH_02", "timestamp_min": 180}]
    )
    
    # 1. to_dict -> from_dict
    data = case.to_dict()
    reconstructed = DecisionCase.from_dict(data)
    assert reconstructed.metadata.id == "CASE-DELIVERY-001"
    assert reconstructed.semantic_contract["invariants"][0] == "I1_PastFactImmutability"
    
    # 2. YAML roundtrip
    yaml_str = dump_case_yaml(case)
    loaded_from_yaml = load_case_yaml(yaml_str)
    assert loaded_from_yaml.metadata.domain == "Dynamic Fleet Route Logistics"
    assert loaded_from_yaml.events[0]["vehicle_id"] == "VEH_02"

def test_decision_artifact_validation_and_trace():
    trace = DecisionTrace(
        trace_id="TR-DELIVERY-001",
        decision_chain=[{"stage": "Contract", "status": "PASS"}, {"stage": "MathOpt", "status": "OPTIMAL"}],
        causal_rationale=[{"order": "ORD_03", "action": "reassigned_to_VEH_03", "reason": "VIP_Lock_Preserved"}],
        constraint_provenance={"C1": "Fleet Payload Limit", "C4": "Customer SLA"}
    )
    
    artifact = DecisionArtifact(
        case_id="CASE-DELIVERY-001",
        status="FEASIBLE",
        decision={"routes": {"VEH_01": ["ORD_01", "ORD_04"], "VEH_03": ["ORD_03", "ORD_06"]}},
        trace=trace,
        explanation={"summary": "Successfully reallocated breakdown orders with 100% lock preservation"},
        validation_result={"dsvl_precheck": "PASS", "dsvl_postcheck": "PASS", "all_invariants_held": True},
        memory_patch={"candidate_heuristic": "Prioritize VIP lock during breakdown"}
    )
    
    assert artifact.status == "FEASIBLE"
    assert artifact.validation_result["all_invariants_held"] is True
    assert artifact.trace.causal_rationale[0]["order"] == "ORD_03"

def test_invalid_case_rejection():
    # 1. 动态场景包含 events 但缺失 runtime_context 必须被 validator 拦截
    with pytest.raises(ValidationError) as excinfo:
        DecisionCase(
            metadata=CaseMetadata(id="ERR-001", domain="delivery"),
            events=[{"event_type": "BREAKDOWN"}],
            runtime_context=None
        )
    assert "Dynamic cases containing 'events' must provide a non-null 'runtime_context'" in str(excinfo.value)
    
    # 2. Artifact status 非法值枚举拦截
    trace = DecisionTrace(trace_id="TR-001")
    with pytest.raises(ValidationError):
        DecisionArtifact(
            case_id="CASE-001",
            status="UNKNOWN_STATUS", # 必须为 FEASIBLE | INFEASIBLE
            trace=trace
        )

def test_trace_structure_integrity():
    trace = DecisionTrace(
        trace_id="TR-STRUCTURE-001",
        decision_chain=[{"step": "DSVL", "result": "PASS"}],
        causal_rationale=[{"entity": "SKU_A1", "location": "L01", "why": "High velocity near IO"}],
        constraint_provenance={"WC01": "WMS Mandatory Policy"}
    )
    assert trace.trace_id == "TR-STRUCTURE-001"
    assert len(trace.decision_chain) == 1
    assert trace.constraint_provenance["WC01"] == "WMS Mandatory Policy"
