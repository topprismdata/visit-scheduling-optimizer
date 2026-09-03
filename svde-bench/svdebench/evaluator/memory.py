"""
svdebench.evaluator.memory — Memory Evaluator v0.1 (Sprint 3D Frozen)
Evaluates memory artifact governance, MDVL MP-G1..G5 promotion gates,
evidence sufficiency, context boundaries, contradiction detection, and false memory risk.
Strictly evaluation-only, zero vector DB / retrieval algorithms.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from svdebench.core.case import DecisionCase
from svdebench.core.artifact import DecisionArtifact
from svdebench.core.memory import MemoryObject, MemoryLifecycleState
from svdebench.evaluator.base import BaseEvaluator
from svdebench.evaluator.models import MemoryEvaluationResult

class MemoryEvaluator(BaseEvaluator):
    def evaluate(
        self,
        case: DecisionCase,
        artifact: DecisionArtifact,
        memory: Optional[MemoryObject] = None,
        historical_context: Optional[List[MemoryObject]] = None
    ) -> MemoryEvaluationResult:
        # 若未显式传入 memory，从 artifact.memory_patch 获取
        mem = memory or (artifact.memory_patch if isinstance(artifact.memory_patch, MemoryObject) else None)
        if not mem and isinstance(artifact.memory_patch, dict):
            mem = MemoryObject.from_dict(artifact.memory_patch)
            
        violations: List[str] = []
        findings: List[Dict[str, Any]] = []
        
        if not mem:
            return MemoryEvaluationResult(
                evaluator_name="MemoryEvaluator",
                overall_pass=False,
                score=0.0,
                promotion_status="REJECTED",
                lifecycle_validation=False,
                evidence_sufficiency=False,
                context_boundary_check=False,
                contradiction_check=False,
                false_memory_probability=1.0,
                violations=["Missing MemoryObject payload in artifact"]
            )
            
        # ── Rule 1 & MP-G1: Evidence Sufficiency (Trace + Case) & MP-G3: Outcome Gate ──
        has_trace = bool(mem.source_evidence and (mem.source_evidence.trace_id or mem.source_evidence.case_id))
        has_outcome = bool(mem.outcome_evaluation and mem.outcome_evaluation.realized_outcome)
        evidence_ok = has_trace and has_outcome
        if not evidence_ok:
            violations.append("MP-G1 / Rule 1 FAIL: Insufficient evidence (missing trace_id or realized_outcome)")
            findings.append({"gate": "MP-G1", "issue": "Memory lacks empirical verification evidence"})

        # ── Rule 2 & MP-G2: Context Boundary Validation (No Context, No Memory) ──
        ctx = mem.context
        has_scope = bool(ctx.applicable_scope and len(ctx.applicable_scope) > 0)
        has_precond = bool(ctx.preconditions and len(ctx.preconditions) > 0)
        
        is_over_generalized = any(s.lower() in ("all", "*", "everything", "any") for s in ctx.applicable_scope)
        context_ok = has_scope and has_precond and not is_over_generalized
        if not context_ok:
            violations.append("MP-G2 / Rule 2 FAIL: Context boundary missing or over-generalized (No Context, No Memory)")
            findings.append({"gate": "MP-G2", "issue": "Memory applicable scope is unbounded or missing preconditions"})

        # ── Rule 3: Lifecycle Validation ──
        lifecycle_ok = True
        if mem.lifecycle == MemoryLifecycleState.PROMOTED:
            if not (evidence_ok and context_ok):
                lifecycle_ok = False
                violations.append("Rule 3 FAIL: PROMOTED state claimed without meeting evidence and context criteria")

        # ── Rule 4 & MP-G4: Contradiction Detection ──
        has_contradiction = False
        if historical_context:
            for hist in historical_context:
                if hist.memory_id != mem.memory_id and hist.decision_domain == mem.decision_domain:
                    # 若适用范围相同，对比建议内容是否存在互斥冲突
                    if hist.context.applicable_scope == mem.context.applicable_scope:
                        rec_curr = str(mem.semantic_recommendation).lower()
                        rec_hist = str(hist.semantic_recommendation).lower()
                        # 识别对立语义词组
                        opposing_pairs = [
                            ("increase", "reduce"), ("increase", "decrease"),
                            ("lock", "unlock"), ("expand", "shrink"), ("harden", "relax")
                        ]
                        for w1, w2 in opposing_pairs:
                            if (w1 in rec_curr and w2 in rec_hist) or (w2 in rec_curr and w1 in rec_hist):
                                has_contradiction = True
                                violations.append(f"MP-G4 / Rule 4 FAIL: Direct semantic contradiction with {hist.memory_id}")
                                findings.append({"gate": "MP-G4", "conflict_with": hist.memory_id})
                                break
        contradiction_ok = not has_contradiction

        # ── Rule 5: False Memory Probability Assessment ──
        false_memory_risk = 0.0
        if not has_outcome:
            false_memory_risk += 0.4
        if is_over_generalized:
            false_memory_risk += 0.4
        if not has_trace:
            false_memory_risk += 0.2
        false_memory_risk = min(1.0, false_memory_risk)

        # ── MP-G5: Promotion Gate Ruling ──
        if len(violations) == 0 and false_memory_risk <= 0.1:
            promotion_status = "PROMOTED"
            overall_pass = True
            score = mem.outcome_evaluation.confidence_score if mem.outcome_evaluation else 1.0
        elif not contradiction_ok or not context_ok:
            promotion_status = "REJECTED" # 冲突或边界不清直接拒绝
            overall_pass = False
            score = 0.0
        elif not evidence_ok and mem.lifecycle == MemoryLifecycleState.CANDIDATE:
            promotion_status = "CANDIDATE" # 证据不全留待候选
            overall_pass = True
            score = 0.5
        else:
            promotion_status = "REJECTED"
            overall_pass = False
            score = 0.0

        return MemoryEvaluationResult(
            evaluator_name="MemoryEvaluator",
            overall_pass=overall_pass,
            score=round(score, 4),
            promotion_status=promotion_status,
            lifecycle_validation=lifecycle_ok,
            evidence_sufficiency=evidence_ok,
            context_boundary_check=context_ok,
            contradiction_check=contradiction_ok,
            false_memory_probability=round(false_memory_risk, 2),
            violations=violations,
            findings=findings,
            evidence={
                "memory_id": mem.memory_id,
                "memory_class": mem.memory_class.value,
                "declared_lifecycle": mem.lifecycle.value,
                "evaluated_promotion_status": promotion_status,
                "false_memory_probability": round(false_memory_risk, 2)
            }
        )
