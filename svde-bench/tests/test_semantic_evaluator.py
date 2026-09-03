"""
test_semantic_evaluator.py — Semantic Evaluator Unit Tests (Sprint 3A)
Covers:
  Test 1: Hard Commitment 满足
  Test 2: Hard Commitment 违反
  Test 3: Soft Preference 不满足但不导致 overall_pass 失败
  Test 4: Constraint Type 正确识别与分类
  Test 5: Golden Case 001 A/B 对比判定 (Baseline A -> FAIL, Baseline B -> PASS)
"""
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.evaluator.semantic import SemanticEvaluator, SemanticEvaluationResult
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent

CASE_PATH = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"

def test_1_hard_commitment_satisfied():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    evaluator = SemanticEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    assert res.overall_pass is True
    assert res.constraint_accuracy == 1.0
    assert len(res.violations) == 0
    
    # 验证 C4 锁定约束结果
    c4_res = [r for r in res.constraint_results if "C4" in r.constraint_id][0]
    assert c4_res.type == "HARD_COMMITMENT"
    assert c4_res.status == "SATISFIED"

def test_2_hard_commitment_violated():
    case = load_case_yaml(str(CASE_PATH))
    agent = PureSolverMockAgent()
    artifact = agent.solve(case)
    
    evaluator = SemanticEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    assert res.overall_pass is False
    assert res.constraint_accuracy < 1.0
    assert len(res.violations) >= 1
    
    # 验证 C4 锁定约束被判定为 VIOLATED
    c4_res = [r for r in res.constraint_results if "C4" in r.constraint_id][0]
    assert c4_res.status == "VIOLATED"
    assert "Hard commitment for ORD_03 violated" in res.violations[0]

def test_3_soft_preference_compromised_does_not_fail():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 人为向 Case 注入一条软偏好
    case.semantic_contract["constraints"].append({
        "id": "C7",
        "name": "MinimalDisruption",
        "type": "MINIMAL_DISRUPTION",
        "hardness": "SOFT_PREFERENCE"
    })
    
    evaluator = SemanticEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    # 虽然软偏好为 COMPROMISED/SATISFIED，但整体仍必须为 PASS
    assert res.overall_pass is True
    soft_res = [r for r in res.constraint_results if "C7" in r.constraint_id][0]
    assert soft_res.type == "SOFT_PREFERENCE"
    assert soft_res.status in ("SATISFIED", "COMPROMISED")

def test_4_constraint_type_classification():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    evaluator = SemanticEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    types_found = {r.type for r in res.constraint_results}
    assert "HARD_COMMITMENT" in types_found
    assert "HARD" in types_found
    assert "INVARIANT" in types_found

def test_5_golden_case_ab_comparison():
    case = load_case_yaml(str(CASE_PATH))
    agent_a = PureSolverMockAgent()
    agent_b = SemanticAwareAgent()
    
    artifact_a = agent_a.solve(case)
    artifact_b = agent_b.solve(case)
    
    evaluator = SemanticEvaluator()
    res_a = evaluator.evaluate(case, artifact_a)
    res_b = evaluator.evaluate(case, artifact_b)
    
    # 核心科学检验：Baseline A (裸优化) 判定失败，Baseline B (语义感知) 判定通过
    assert res_a.overall_pass is False
    assert res_b.overall_pass is True
    assert res_a.constraint_accuracy < res_b.constraint_accuracy
    assert len(res_a.violations) > len(res_b.violations)
