"""
test_evaluation_profile.py — Decision Intelligence Profile & Report Schema Tests (Sprint 3.5)
Covers:
  Test 1: 四类 Evaluator 结果统一聚合为 DecisionIntelligenceProfile
  Test 2: Profile 与 Report JSON/Dict 序列化稳定性
  Test 3: 缺失某个 Evaluator 结果（如无 Memory）的优雅兼容处理
  Test 4: Report Schema 结构完整性校验（case_id, agent_name, decision_artifact, evaluation_profile）
  Test 5: Golden Case 001 全量 Profile 标准报告输出与断言
"""
import json
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent
from svdebench.evaluator.semantic import SemanticEvaluator
from svdebench.evaluator.feasibility import FeasibilityEvaluator
from svdebench.evaluator.runtime import RuntimeEvaluator
from svdebench.evaluator.memory import MemoryEvaluator
from svdebench.evaluator.profile import DecisionIntelligenceProfile
from svdebench.runner.pipeline import run_case_pipeline

CASE_PATH = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"
REPORT_DIR = Path(__file__).parent.parent / "reports"

def test_1_four_dimensional_profile_aggregation():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    sem_res = SemanticEvaluator().evaluate(case, artifact)
    feas_res = FeasibilityEvaluator().evaluate(case, artifact)
    run_res = RuntimeEvaluator().evaluate(case, artifact)
    mem_res = MemoryEvaluator().evaluate(case, artifact)
    
    profile = DecisionIntelligenceProfile.from_evaluators(
        case_id=case.metadata.id,
        agent_name=agent.__class__.__name__,
        semantic_res=sem_res,
        feasibility_res=feas_res,
        runtime_res=run_res,
        memory_res=mem_res
    )
    
    assert profile.case_id == "CASE-001-DELIVERY-RECOVERY"
    assert profile.agent_name == "SemanticAwareAgent"
    assert profile.semantic_result.overall_pass is True
    assert profile.feasibility_result.feasibility_status == "FEASIBLE"
    assert profile.runtime_result.commitment_survival_rate == 1.0
    assert profile.memory_result.promotion_status == "PROMOTED"
    assert profile.overall_summary["all_mandatory_passed"] is True

def test_2_profile_serialization():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    artifact = agent.solve(case)
    
    sem_res = SemanticEvaluator().evaluate(case, artifact)
    profile = DecisionIntelligenceProfile.from_evaluators(
        case_id=case.metadata.id,
        agent_name=agent.__class__.__name__,
        semantic_res=sem_res
    )
    
    data = profile.to_dict()
    assert data["case_id"] == "CASE-001-DELIVERY-RECOVERY"
    json_str = json.dumps(data)
    assert "SemanticAwareAgent" in json_str

def test_3_missing_evaluator_compatibility():
    # 模拟无 Memory 结果的 Agent 输出
    profile = DecisionIntelligenceProfile.from_evaluators(
        case_id="TEST-001",
        agent_name="PureSolverMockAgent",
        semantic_res=None,
        feasibility_res=None,
        runtime_res=None,
        memory_res=None
    )
    assert profile.memory_result is None
    assert profile.overall_summary["memory_promotion_status"] is None
    assert profile.overall_summary["all_mandatory_passed"] is True

def test_4_report_schema_integrity():
    case = load_case_yaml(str(CASE_PATH))
    agent = SemanticAwareAgent()
    
    report = run_case_pipeline(case, agent)
    
    # 必须严格包含四大标准一级字段
    assert "case_id" in report
    assert "agent_name" in report
    assert "decision_artifact" in report
    assert "evaluation_profile" in report
    
    # evaluation_profile 必须包含四维画像
    prof = report["evaluation_profile"]
    assert "semantic" in prof
    assert "feasibility" in prof
    assert "runtime" in prof
    assert "memory" in prof
    assert "profile_summary" in prof

def test_5_golden_case_001_standard_report_emission():
    case = load_case_yaml(str(CASE_PATH))
    agent_a = PureSolverMockAgent()
    agent_b = SemanticAwareAgent()
    
    report_a = run_case_pipeline(case, agent_a)
    report_b = run_case_pipeline(case, agent_b)
    
    # Baseline A: Semantic FAIL, Feasibility PASS, Runtime FAIL
    assert report_a["evaluation_profile"]["semantic"]["overall_pass"] is False
    assert report_a["evaluation_profile"]["feasibility"]["feasibility_status"] == "FEASIBLE"
    assert report_a["evaluation_profile"]["runtime"]["commitment_survival_rate"] == 0.0
    
    # Baseline B: 全维 PASS
    assert report_b["evaluation_profile"]["semantic"]["overall_pass"] is True
    assert report_b["evaluation_profile"]["feasibility"]["feasibility_status"] == "FEASIBLE"
    assert report_b["evaluation_profile"]["runtime"]["commitment_survival_rate"] == 1.0
    assert report_b["evaluation_profile"]["memory"]["promotion_status"] == "PROMOTED"
    
    # 保存标准产物
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / "golden_case_001_report.json"
    report_file.write_text(json.dumps(report_b, indent=2, ensure_ascii=False))
    assert report_file.exists()
