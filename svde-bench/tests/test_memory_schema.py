"""
test_memory_schema.py — Decision Memory Schema Validation & Serialization Unit Tests (Sprint 1B)
"""
import pytest
from pydantic import ValidationError
from svdebench.core.memory import (
    MemoryObject,
    MemoryClass,
    MemoryLifecycleState,
    MemoryContext,
    MemoryTrigger,
    MemoryOutcomeEvaluation,
    MemorySourceEvidence,
)
from svdebench.core import load_memory_yaml, dump_memory_yaml

def test_memory_object_instantiation_normal():
    # Test 1: 正常 MemoryObject 创建
    mem = MemoryObject(
        memory_id="DMEM-DOM4-001",
        memory_class=MemoryClass.EPISODE,
        decision_domain="Dynamic Fleet Route Logistics",
        context=MemoryContext(
            applicable_scope=["Dynamic Rerouting", "Breakdown"],
            preconditions={"fleet_size": ">= 2", "has_locked_commitments": True},
            invalidation_conditions="single_fleet_all_breakdown"
        ),
        trigger=MemoryTrigger(
            event_type="VEHICLE_MECHANICAL_BREAKDOWN",
            variation_classification="SEMANTIC_VARIATION"
        ),
        semantic_recommendation={
            "guideline": "Prioritize VIP lock during breakdown without route disruption",
            "suggested_constraint_patch": {"type": "TimeWindowLock", "hardness": "HARD"}
        },
        outcome_evaluation=MemoryOutcomeEvaluation(
            predicted_outcome="0 commitment violations",
            realized_outcome="ORD_03 100% delivered on locked window",
            variance="0.0%",
            confidence_score=0.98
        ),
        lifecycle=MemoryLifecycleState.PROMOTED,
        source_evidence=MemorySourceEvidence(
            trace_id="DD-TRACE-SEQUENCE-001",
            case_id="CASE-DELIVERY-001",
            evidence_reference="P43-FINAL-REPORT-V1.0"
        ),
        expiration_date="2027-08-22"
    )
    
    assert mem.memory_id == "DMEM-DOM4-001"
    assert mem.memory_class == MemoryClass.EPISODE
    assert mem.lifecycle == MemoryLifecycleState.PROMOTED
    assert mem.outcome_evaluation.confidence_score == 0.98

def test_memory_lifecycle_state_coverage():
    # Test 2: Lifecycle 7 态全枚举覆盖校验
    all_states = [
        MemoryLifecycleState.CANDIDATE,
        MemoryLifecycleState.EVALUATING,
        MemoryLifecycleState.VALIDATED,
        MemoryLifecycleState.PROMOTED,
        MemoryLifecycleState.DEPRECATED,
        MemoryLifecycleState.SUPERSEDED,
        MemoryLifecycleState.REJECTED,
    ]
    assert len(all_states) == 7
    for s in all_states:
        mem = MemoryObject(
            memory_id=f"MEM-{s.value}",
            memory_class=MemoryClass.CAUSAL_DEPENDENCY,
            decision_domain="Warehouse",
            context=MemoryContext(applicable_scope=["Slotting"], preconditions={"space": "tight"}),
            semantic_recommendation={"rule": "isolate_hazmat"},
            outcome_evaluation=MemoryOutcomeEvaluation(confidence_score=0.9) if s == MemoryLifecycleState.PROMOTED else None,
            source_evidence=MemorySourceEvidence(trace_id="TR-001") if s == MemoryLifecycleState.PROMOTED else None,
            lifecycle=s
        )
        assert mem.lifecycle == s

def test_invalid_memory_rejection():
    # Test 3: Invalid Memory rejection (Rule 1 & Rule 3 校验)
    # 3.1 空 memory_id 拦截
    with pytest.raises(ValidationError) as excinfo:
        MemoryObject(
            memory_id="   ", # 空白
            memory_class=MemoryClass.OUTCOME,
            decision_domain="Retail Channel",
            context=MemoryContext(applicable_scope=["Channel"], preconditions={"budget": 1000}),
            semantic_recommendation={"patch": "recalibrate_potential"}
        )
    assert "Rule 1 Violation: memory_id cannot be empty" in str(excinfo.value)

    # 3.2 PROMOTED 状态下缺失 source_evidence 必须被拦截 (Rule 3)
    with pytest.raises(ValidationError) as excinfo2:
        MemoryObject(
            memory_id="MEM-PROMOTED-NO-EVIDENCE",
            memory_class=MemoryClass.CONSTRAINT_EVOLUTION,
            decision_domain="Visit Scheduling",
            context=MemoryContext(applicable_scope=["Visit"], preconditions={"cadence": True}),
            semantic_recommendation={"patch": "harden_min_gap"},
            outcome_evaluation=MemoryOutcomeEvaluation(confidence_score=1.0),
            source_evidence=None, # 缺失
            lifecycle=MemoryLifecycleState.PROMOTED
        )
    assert "Rule 3 Violation: PROMOTED memory must specify 'source_evidence'" in str(excinfo2.value)

    # 3.3 PROMOTED 状态下缺失 outcome_evaluation 必须被拦截 (Rule 3)
    with pytest.raises(ValidationError) as excinfo3:
        MemoryObject(
            memory_id="MEM-PROMOTED-NO-OUTCOME",
            memory_class=MemoryClass.CONSTRAINT_EVOLUTION,
            decision_domain="Visit Scheduling",
            context=MemoryContext(applicable_scope=["Visit"], preconditions={"cadence": True}),
            semantic_recommendation={"patch": "harden_min_gap"},
            outcome_evaluation=None, # 缺失
            source_evidence=MemorySourceEvidence(trace_id="TR-002"),
            lifecycle=MemoryLifecycleState.PROMOTED
        )
    assert "Rule 3 Violation: PROMOTED memory must specify 'outcome_evaluation'" in str(excinfo3.value)

def test_memory_serialization_roundtrip():
    # Test 4: Serialization roundtrip (Pydantic -> YAML -> Pydantic)
    mem = MemoryObject(
        memory_id="DMEM-ROUNDTRIP-001",
        memory_class=MemoryClass.COUNTERFACTUAL,
        decision_domain="Dynamic Delivery",
        context=MemoryContext(
            applicable_scope=["Fleet"],
            preconditions={"heavy_traffic": True},
            invalidation_conditions="traffic_cleared"
        ),
        semantic_recommendation={"advice": "Consider on-demand carrier if delay > 30min"},
        lifecycle=MemoryLifecycleState.VALIDATED
    )
    
    # 4.1 to_dict -> from_dict
    data = mem.to_dict()
    reconstructed = MemoryObject.from_dict(data)
    assert reconstructed.memory_id == "DMEM-ROUNDTRIP-001"
    assert reconstructed.memory_class == MemoryClass.COUNTERFACTUAL
    
    # 4.2 YAML roundtrip
    yaml_str = dump_memory_yaml(mem)
    loaded_mem = load_memory_yaml(yaml_str)
    assert loaded_mem.context.invalidation_conditions == "traffic_cleared"
    assert loaded_mem.lifecycle == MemoryLifecycleState.VALIDATED

def test_forbidden_solver_variable_injection():
    # Test 5: 禁止 Solver Variable 注入 (The Semantic Impact Law / Rule 4)
    forbidden_payloads = [
        {"action": "set_solver_variable_x=1"},
        {"patch": "x[0, 1] == 1"},
        {"guideline": "Direct assignment: f2_x_ORD01_VEH01 = 1"},
        {"options": "primal_solution variable_value override"}
    ]
    
    for payload in forbidden_payloads:
        with pytest.raises(ValidationError) as excinfo:
            MemoryObject(
                memory_id="MEM-POLLUTED-SOLVER",
                memory_class=MemoryClass.EPISODE,
                decision_domain="Delivery",
                context=MemoryContext(applicable_scope=["Delivery"], preconditions={"veh_count": 2}),
                semantic_recommendation=payload, # 含有求解器底层变量字符串
                lifecycle=MemoryLifecycleState.CANDIDATE
            )
        assert "Rule 4 Violation (The Semantic Impact Law)" in str(excinfo.value)
