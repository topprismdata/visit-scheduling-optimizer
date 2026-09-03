"""
test_runtime_evaluator.py — Runtime Evaluator Unit Tests (Sprint 3C)
Covers:
  Test 1: 正常事件序列回放与状态转移 (Valid State Transition)
  Test 2: 非法状态跳转拦截 (Illegal Transition Rejection)
  Test 3: Commitment Survival Rate 计算
  Test 4: Disruption Ratio 扰动率计算
  Test 5: Golden Case 001 A/B 动态适应性对比 (Baseline A Survival < 1 vs Baseline B Survival = 1)
"""
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.evaluator.runtime import RuntimeEvaluator
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent

CASE_PATH = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"

def test_1_normal_state_transition_replay():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    evaluator = RuntimeEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    assert res.overall_pass is True
    assert res.state_transition_validity is True
    assert len(res.event_results) >= 1
    assert res.event_results[0]["status"] == "VALID"
    assert res.commitment_survival_rate == 1.0

def test_2_illegal_state_transition_rejection():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 模拟非法事件：车辆已经是 BREAKDOWN 状态，再次发生 BREAKDOWN
    case.events.append({
        "event_id": "EVT_ILLEGAL_002",
        "event_type": "VEHICLE_MECHANICAL_BREAKDOWN",
        "affected_vehicle": "VEH_02"
    })
    
    evaluator = RuntimeEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    assert res.overall_pass is False
    assert res.state_transition_validity is False
    assert any("already broken down" in v for v in res.violations)

def test_3_commitment_survival_rate_calculation():
    case = load_case_yaml(str(CASE_PATH))
    # 增加第二个锁定约束 (共有 2 个锁定客户)
    case.semantic_contract["constraints"].append({
        "id": "C4_bis",
        "name": "TimeWindowLock_ORD06",
        "type": "TIME_WINDOW_LOCKED",
        "hardness": "HARD_COMMITMENT",
        "target_order": "ORD_06"
    })
    
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    evaluator = RuntimeEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    # SemanticAwareAgent 同时服务了 ORD_03 与 ORD_06 -> Survival = 2/2 = 1.0
    assert res.commitment_survival_rate == 1.0

def test_4_disruption_ratio_calculation():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 显式注入重调数量
    artifact.decision["reassigned_count"] = 3
    
    evaluator = RuntimeEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    # 总订单数 5, 重调 3 -> ratio = 3/5 = 0.6
    assert res.disruption_ratio == 0.6

def test_5_golden_case_ab_dynamic_comparison():
    case = load_case_yaml(str(CASE_PATH))
    agent_a = PureSolverMockAgent() # 裸优化
    agent_b = SemanticAwareAgent()   # 语义感知

    artifact_a = agent_a.solve(case)
    artifact_b = agent_b.solve(case)
    
    evaluator = RuntimeEvaluator()
    res_a = evaluator.evaluate(case, artifact_a)
    res_b = evaluator.evaluate(case, artifact_b)
    
    # ⭐ 核心动态命题实证：
    # Baseline A: 破坏锁定客户承诺 -> Commitment Survival Rate = 0.0 -> overall_pass = False
    assert res_a.commitment_survival_rate == 0.0
    assert res_a.overall_pass is False
    assert len(res_a.violations) >= 1
    
    # Baseline B: 保持锁定客户承诺 -> Commitment Survival Rate = 1.0 -> overall_pass = True
    assert res_b.commitment_survival_rate == 1.0
    assert res_b.overall_pass is True
    assert len(res_b.violations) == 0
