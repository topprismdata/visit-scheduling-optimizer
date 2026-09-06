"""
svdebench.calibration.case_quality — Golden Case Quality Assessment Engine v0.1
Evaluates Case Quality across 3 Dimensions:
  Dimension 1: Decision Separation (Ability to distinguish Baseline A vs B)
  Dimension 2: Constraint Coverage (Hard, Soft, Invariant, Runtime Events)
  Dimension 3: Failure Interpretability (Causal and structural explanation of failures)
"""
from __future__ import annotations
from typing import Any, Dict
from svdebench.core import load_case_yaml
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent
from svdebench.runner.pipeline import run_case_pipeline

def assess_case_quality(case_path: str) -> Dict[str, Any]:
    case = load_case_yaml(case_path)
    
    agent_a = PureSolverMockAgent()
    agent_b = SemanticAwareAgent()
    
    rep_a = run_case_pipeline(case, agent_a)
    rep_b = run_case_pipeline(case, agent_b)
    
    prof_a = rep_a["evaluation_profile"]
    prof_b = rep_b["evaluation_profile"]
    
    # 1. Dimension 1: Decision Separation
    # 检查两个 Agent 是否在语义维度产生显著区分 (A 失败, B 通过)
    a_pass = prof_a["semantic"]["overall_pass"]
    b_pass = prof_b["semantic"]["overall_pass"]
    has_separation = (a_pass != b_pass)
    
    # 2. Dimension 2: Constraint Coverage
    contract = case.semantic_contract or {}
    constraints = contract.get("constraints", [])
    invariants = contract.get("invariants", [])
    has_hard = any(c.get("hardness") == "HARD" or c.get("hardness") == "HARD_COMMITMENT" for c in constraints)
    has_soft = any(c.get("hardness") == "SOFT_PREFERENCE" for c in constraints)
    has_invar = len(invariants) > 0
    has_events = len(case.events) > 0
    coverage_score = round((sum([has_hard, has_soft, has_invar, has_events]) / 4.0), 2)
    
    # 3. Dimension 3: Failure Interpretability
    violations = prof_a["semantic"].get("violations", [])
    has_interpretable_failure = len(violations) > 0 and all(len(v) > 5 for v in violations)
    
    overall_quality_pass = has_separation and (coverage_score >= 0.75) and has_interpretable_failure
    
    return {
        "case_id": case.metadata.id,
        "overall_quality_pass": overall_quality_pass,
        "dimension_1_decision_separation": {
            "has_separation": has_separation,
            "pure_solver_semantic_pass": a_pass,
            "semantic_aware_semantic_pass": b_pass,
            "verdict": "STRONG_SEPARATION" if has_separation else "WEAK_SEPARATION"
        },
        "dimension_2_constraint_coverage": {
            "coverage_score": coverage_score,
            "has_hard": has_hard,
            "has_soft": has_soft,
            "has_invariants": has_invar,
            "has_runtime_events": has_events
        },
        "dimension_3_failure_interpretability": {
            "interpretable": has_interpretable_failure,
            "sample_violation_explanation": violations[0] if violations else None
        }
    }
