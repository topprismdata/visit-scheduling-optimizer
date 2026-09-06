"""
test_feasibility_evaluator.py — Feasibility Evaluator Unit Tests (Sprint 3B)
Covers:
  Test 1: 容量满足 (Capacity Satisfied)
  Test 2: 容量超限违反 (Capacity Overload Violated)
  Test 3: 时间窗越界违反 (Time Window Out of Bound)
  Test 4: Oracle 对比接口与 Gap 计算
  Test 5: Golden Case A/B 核心对账 (Baseline A: Semantic FAIL + Feasibility PASS)
"""
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.evaluator.feasibility import FeasibilityEvaluator
from svdebench.evaluator.semantic import SemanticEvaluator
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent

CASE_PATH = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"

def test_1_capacity_satisfied():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    evaluator = FeasibilityEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    assert res.overall_pass is True
    assert res.feasibility_status == "FEASIBLE"
    assert len(res.violations) == 0
    assert all(r["status"] == "SATISFIED" for r in res.constraint_results if r["type"] == "VEHICLE_CAPACITY")

def test_2_capacity_overload_violation():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 人为修改解：向 VEH_03 (限重 800kg) 塞入超重订单组合 (总重 > 800)
    artifact.decision["reassigned_routes"]["VEH_03"] = ["ORD_02", "ORD_03", "ORD_06", "ORD_04"] # 300+250+200+150 = 900kg > 800kg
    
    evaluator = FeasibilityEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    assert res.overall_pass is False
    assert res.feasibility_status == "INFEASIBLE"
    assert any("overloaded" in v for v in res.violations)
    
    overload_res = [r for r in res.constraint_results if r["entity"] == "VEH_03" and r["type"] == "VEHICLE_CAPACITY"][0]
    assert overload_res["status"] == "VIOLATED"
    assert overload_res["actual_load_kg"] == 900

def test_3_time_window_out_of_bound():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 注入违规到达时间：ORD_03 窗口为 [120, 200]，人为设置到达时间为 250 (迟到)
    artifact.decision["arrival_times"] = {"ORD_03": 250}
    
    evaluator = FeasibilityEvaluator()
    res = evaluator.evaluate(case, artifact)
    
    assert res.overall_pass is False
    assert res.feasibility_status == "INFEASIBLE"
    assert any("out of window" in v for v in res.violations)

def test_4_oracle_comparison_interface():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    # 模拟外部 Gold Oracle 输出
    gold_reference = {
        "oracle_solution": {
            "status": "OPTIMAL",
            "objective": 480.0,
            "feasible": True
        }
    }
    
    evaluator = FeasibilityEvaluator()
    res = evaluator.evaluate(case, artifact, gold=gold_reference)
    
    assert res.oracle_comparison is not None
    assert res.oracle_comparison["oracle_objective"] == 480.0
    assert res.oracle_comparison["candidate_cost"] == 480.0
    assert res.objective_gap == 0.0 # 零 Gap

def test_5_golden_case_ab_comparison_semantic_vs_feasibility():
    case = load_case_yaml(str(CASE_PATH))
    agent_a = PureSolverMockAgent() # 裸优化器
    agent_b = SemanticAwareAgent()   # 语义感知

    artifact_a = agent_a.solve(case)
    artifact_b = agent_b.solve(case)
    
    sem_eval = SemanticEvaluator()
    feas_eval = FeasibilityEvaluator()
    
    sem_res_a = sem_eval.evaluate(case, artifact_a)
    feas_res_a = feas_eval.evaluate(case, artifact_a)
    
    sem_res_b = sem_eval.evaluate(case, artifact_b)
    feas_res_b = feas_eval.evaluate(case, artifact_b)
    
    # ⭐ 核心科学命题实证：
    # Baseline A: 数学/物理可行 (Feasibility PASS)，但业务语义失败 (Semantic FAIL)！
    assert feas_res_a.overall_pass is True
    assert sem_res_a.overall_pass is False
    
    # Baseline B: 语义可行 + 物理可行 (双 PASS)！
    assert feas_res_b.overall_pass is True
    assert sem_res_b.overall_pass is True
