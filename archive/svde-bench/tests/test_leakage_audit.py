"""
test_leakage_audit.py — Code-Level Anti-Leakage & Evaluator Independence Audit Tests (Sprint 4.5)
Covers:
  Test 1: 静态 AST 全量防泄露扫描 (Agent !=> Oracle, Evaluator !=> Agent, Oracle !=> Evaluator)
  Test 2: Evaluator 独立性与非 Oracle Checker 验证
  Test 3: Case Quality 质检评估 (Golden Case 001 区分度、覆盖度、失败可解释度)
"""
from pathlib import Path
from svdebench.calibration.leakage_scan import scan_repository_leakage
from svdebench.calibration.evaluator_audit import audit_evaluator_independence
from svdebench.calibration.case_quality import assess_case_quality

REPO_ROOT = Path(__file__).parent.parent
CASE_001_PATH = REPO_ROOT / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"

def test_1_ast_static_leakage_scan():
    res = scan_repository_leakage(REPO_ROOT)
    assert res["status"] == "PASS"
    assert res["all_clean"] is True
    assert len(res["violations"]) == 0

def test_2_evaluator_independence_audit():
    res = audit_evaluator_independence()
    assert res["semantic_independent"] is True
    assert res["feasibility_independent"] is True
    assert res["runtime_independent"] is True
    assert res["memory_independent"] is True

def test_3_golden_case_001_quality_assessment():
    res = assess_case_quality(str(CASE_001_PATH))
    
    assert res["case_id"] == "CASE-001-DELIVERY-RECOVERY"
    assert res["overall_quality_pass"] is True
    
    # 验证三大质量维度
    assert res["dimension_1_decision_separation"]["has_separation"] is True
    assert res["dimension_1_decision_separation"]["verdict"] == "STRONG_SEPARATION"
    assert res["dimension_2_constraint_coverage"]["coverage_score"] == 1.0 # 100% 覆盖 Hard, Soft, Invariant, Events
    assert res["dimension_3_failure_interpretability"]["interpretable"] is True
