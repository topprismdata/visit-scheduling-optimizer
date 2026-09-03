"""
svdebench.runner.pipeline — Standardized Benchmark Runner Pipeline v0.1 (Sprint 3.5 Frozen)
Loads Case -> Runs Agent -> Runs 4-Dimensional Evaluators -> Emits DecisionIntelligenceProfile & Standard Report
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

from svdebench.core import DecisionCase, DecisionArtifact, load_case_yaml
from svdebench.core.memory import MemoryObject, MemoryClass, MemoryLifecycleState, MemoryContext, MemoryTrigger, MemoryOutcomeEvaluation, MemorySourceEvidence
from svdebench.agents.base import BaseDecisionAgent
from svdebench.evaluator.semantic import SemanticEvaluator
from svdebench.evaluator.feasibility import FeasibilityEvaluator
from svdebench.evaluator.runtime import RuntimeEvaluator
from svdebench.evaluator.memory import MemoryEvaluator
from svdebench.evaluator.profile import DecisionIntelligenceProfile

def validate_artifact_semantics(case: DecisionCase, artifact: DecisionArtifact) -> Dict[str, Any]:
    """兼容旧接口：由 SemanticEvaluator 委托执行"""
    sem_res = SemanticEvaluator().evaluate(case, artifact)
    
    # 检查 ORD_03 是否在指派路线中
    routes = artifact.decision.get("reassigned_routes", {}) or artifact.decision.get("routes", {})
    all_assigned = set()
    for group in routes.values():
        if isinstance(group, list): all_assigned.update(group)
        elif isinstance(group, str): all_assigned.add(group)
    lock_honored = "ORD_03" in all_assigned
    
    return {
        "lock_commitment_honored": lock_honored,
        "decision_feasible": sem_res.overall_pass,
        "trace_present": bool(artifact.trace and artifact.trace.trace_id),
        "explanation_present": bool(artifact.explanation),
        "memory_patch_valid": bool(artifact.memory_patch),
        "verdict": "PASS" if sem_res.overall_pass else "FAIL"
    }

def run_case_pipeline(
    case_path_or_obj: str | DecisionCase,
    agent: BaseDecisionAgent,
    gold_reference: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    执行完整标准化评测流水线，产出符合 Benchmark Report Schema 的评测报告。
    """
    # 1. Load Case
    if isinstance(case_path_or_obj, str):
        case = load_case_yaml(case_path_or_obj)
    else:
        case = case_path_or_obj
        
    # 2. Agent Solve (Strictly inputs only DecisionCase)
    artifact = agent.solve(case)
    
    # 3. 运行四大独立评估器
    sem_eval = SemanticEvaluator()
    feas_eval = FeasibilityEvaluator()
    run_eval = RuntimeEvaluator()
    mem_eval = MemoryEvaluator()
    
    sem_res = sem_eval.evaluate(case, artifact, gold=gold_reference)
    feas_res = feas_eval.evaluate(case, artifact, gold=gold_reference)
    run_res = run_eval.evaluate(case, artifact, gold=gold_reference)
    mem_res = None
    if artifact.memory_patch:
        mem_input = artifact.memory_patch
        if not isinstance(mem_input, MemoryObject) and isinstance(mem_input, dict):
            try:
                mem_input = MemoryObject.from_dict(mem_input)
            except Exception:
                mem_input = None
        if mem_input is not None:
            mem_res = mem_eval.evaluate(case, artifact, memory=mem_input)
    
    # 4. 聚合为统一四维决策智能画像 (DecisionIntelligenceProfile)
    profile = DecisionIntelligenceProfile.from_evaluators(
        case_id=case.metadata.id,
        agent_name=agent.__class__.__name__,
        semantic_res=sem_res,
        feasibility_res=feas_res,
        runtime_res=run_res,
        memory_res=mem_res
    )
    
    # 5. 生成标准 Benchmark 报告
    report = {
        "case_id": case.metadata.id,
        "agent_name": agent.__class__.__name__,
        "decision_artifact": artifact.to_dict(),
        "decision": artifact.decision,
        "validation": validate_artifact_semantics(case, artifact),
        "trace": artifact.trace.model_dump(),
        "memory": artifact.memory_patch.to_dict() if artifact.memory_patch and hasattr(artifact.memory_patch, "to_dict") else artifact.memory_patch,
        "evaluation_profile": {
            "semantic": sem_res.to_dict() if sem_res else None,
            "feasibility": feas_res.to_dict() if feas_res else None,
            "runtime": run_res.to_dict() if run_res else None,
            "memory": mem_res.to_dict() if mem_res else None,
            "profile_summary": profile.overall_summary
        }
    }
    return report
