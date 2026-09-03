"""
test_memory_evaluator.py — Memory Evaluator Unit Tests (Sprint 3D)
Covers:
  Test 1: 证据完整且上下文明确的 Memory 判定 PROMOTED
  Test 2: 无 Trace/Outcome 证据的 Memory 拒绝 (MP-G1 拦截)
  Test 3: Context Boundary 缺失或过度泛化的 Memory 拒绝 (MP-G2 拦截)
  Test 4: 语义直接冲突检测 (MP-G4 冲突拦截)
  Test 5: Golden Case 001 Valid Memory (PROMOTED) vs False Memory (REJECTED)
"""
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.core.memory import (
    MemoryObject,
    MemoryClass,
    MemoryLifecycleState,
    MemoryContext,
    MemoryTrigger,
    MemoryOutcomeEvaluation,
    MemorySourceEvidence,
)
from svdebench.evaluator.memory import MemoryEvaluator
from svdebench.agents.baseline import SemanticAwareAgent

CASE_PATH = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"

def test_1_evidence_sufficient_memory_promoted():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 完整的有效记忆
    valid_mem = MemoryObject(
        memory_id="DMEM-VALID-001",
        memory_class=MemoryClass.EPISODE,
        decision_domain="Dynamic Fleet Route Logistics",
        context=MemoryContext(
            applicable_scope=["Dynamic Delivery Breakdown"],
            preconditions={"fleet_size": ">= 2", "has_locked_commitments": True},
            invalidation_conditions="all_vehicles_fail"
        ),
        trigger=MemoryTrigger(event_type="VEHICLE_MECHANICAL_BREAKDOWN"),
        semantic_recommendation={"rule": "prioritize_time_window_locked_orders"},
        outcome_evaluation=MemoryOutcomeEvaluation(
            realized_outcome="ORD_03 100% delivered on locked window",
            confidence_score=0.99
        ),
        lifecycle=MemoryLifecycleState.CANDIDATE,
        source_evidence=MemorySourceEvidence(
            trace_id="TR-SEMANTIC-CASE-001",
            case_id=case.metadata.id
        )
    )
    
    evaluator = MemoryEvaluator()
    res = evaluator.evaluate(case, artifact, memory=valid_mem)
    
    assert res.overall_pass is True
    assert res.promotion_status == "PROMOTED"
    assert res.evidence_sufficiency is True
    assert res.context_boundary_check is True
    assert res.false_memory_probability == 0.0

def test_2_insufficient_evidence_memory_rejected():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 缺失 Outcome 且无 Trace 的记忆（凭空猜测）
    guess_mem = MemoryObject(
        memory_id="DMEM-GUESS-001",
        memory_class=MemoryClass.EPISODE,
        decision_domain="Dynamic Fleet Route Logistics",
        context=MemoryContext(
            applicable_scope=["Breakdown"],
            preconditions={"fleet": 2}
        ),
        semantic_recommendation={"advice": "some speculative advice"},
        outcome_evaluation=None, # 缺失成效
        source_evidence=None,    # 缺失证据
        lifecycle=MemoryLifecycleState.CANDIDATE
    )
    
    evaluator = MemoryEvaluator()
    res = evaluator.evaluate(case, artifact, memory=guess_mem)
    
    # 证据不全，保持 CANDIDATE 或未满足 PROMOTED 门限
    assert res.evidence_sufficiency is False
    assert res.promotion_status == "CANDIDATE" # 候选状态暂不晋升

def test_3_over_generalized_context_boundary_rejected():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 过度泛化：适用范围设为 "ALL" (无边界裸知识)
    broad_mem = MemoryObject(
        memory_id="DMEM-BROAD-001",
        memory_class=MemoryClass.EPISODE,
        decision_domain="Dynamic Fleet Route Logistics",
        context=MemoryContext(
            applicable_scope=["ALL"], # 过度泛化
            preconditions={"everything": True}
        ),
        semantic_recommendation={"rule": "always_prioritize_vip"},
        outcome_evaluation=MemoryOutcomeEvaluation(
            realized_outcome="success once",
            confidence_score=0.7
        ),
        source_evidence=MemorySourceEvidence(trace_id="TR-001"),
        lifecycle=MemoryLifecycleState.CANDIDATE
    )
    
    evaluator = MemoryEvaluator()
    res = evaluator.evaluate(case, artifact, memory=broad_mem)
    
    # 必须被 MP-G2 拦截直接拒绝 (REJECTED)
    assert res.overall_pass is False
    assert res.promotion_status == "REJECTED"
    assert res.context_boundary_check is False
    assert res.false_memory_probability >= 0.4
    assert any("MP-G2" in v for v in res.violations)

def test_4_contradiction_detection():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 历史已有记忆：增加安全缓冲
    hist_mem = MemoryObject(
        memory_id="DMEM-HIST-001",
        memory_class=MemoryClass.CONSTRAINT_EVOLUTION,
        decision_domain="Dynamic Fleet Route Logistics",
        context=MemoryContext(
            applicable_scope=["Fleet Strategy"],
            preconditions={"zone": "urban"}
        ),
        semantic_recommendation={"policy": "increase buffer capacity for safety"}
    )
    
    # 新候选记忆：在相同上下文中要求减少安全缓冲
    conflict_mem = MemoryObject(
        memory_id="DMEM-NEW-002",
        memory_class=MemoryClass.CONSTRAINT_EVOLUTION,
        decision_domain="Dynamic Fleet Route Logistics",
        context=MemoryContext(
            applicable_scope=["Fleet Strategy"],
            preconditions={"zone": "urban"}
        ),
        semantic_recommendation={"policy": "reduce buffer capacity aggressively"},
        outcome_evaluation=MemoryOutcomeEvaluation(realized_outcome="cost saved", confidence_score=0.8),
        source_evidence=MemorySourceEvidence(trace_id="TR-002")
    )
    
    evaluator = MemoryEvaluator()
    res = evaluator.evaluate(case, artifact, memory=conflict_mem, historical_context=[hist_mem])
    
    # MP-G4 冲突检测拦截
    assert res.overall_pass is False
    assert res.contradiction_check is False
    assert any("MP-G4" in v for v in res.violations)

def test_5_golden_case_valid_vs_false_memory():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    evaluator = MemoryEvaluator()
    
    # 1. 真实有效记忆（由 Agent 产出）
    valid_res = evaluator.evaluate(case, artifact, memory=artifact.memory_patch)
    assert valid_res.overall_pass is True
    assert valid_res.promotion_status == "PROMOTED"
    
    # 2. 伪造的过度泛化假记忆
    false_mem = MemoryObject(
        memory_id="DMEM-FALSE-001",
        memory_class=MemoryClass.EPISODE,
        decision_domain=case.metadata.domain,
        context=MemoryContext(
            applicable_scope=["*"], # 无边界
            preconditions={"any": True}
        ),
        semantic_recommendation={"rule": "all delivery failures should prioritize VIP universally"},
        outcome_evaluation=MemoryOutcomeEvaluation(realized_outcome="1 case worked"),
        source_evidence=MemorySourceEvidence(case_id=case.metadata.id)
    )
    
    false_res = evaluator.evaluate(case, artifact, memory=false_mem)
    assert false_res.overall_pass is False
    assert false_res.promotion_status == "REJECTED"
    assert false_res.false_memory_probability > 0.3
