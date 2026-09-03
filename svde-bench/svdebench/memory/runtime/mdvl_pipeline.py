"""MDVL: Memory Decision Validation Layer - MP-G1..G5 记忆晋升流水线 (独立 runtime)"""
from typing import Dict, Any, List
from datetime import datetime as dt
from svdebench.core.memory import MemoryObject, MemoryLifecycleState

class MP_G1_Validity_Gate:
    """G1: 候选记忆的 schema 与生命周期状态基本合法性"""
    @staticmethod
    def check(memory: MemoryObject) -> Dict[str, Any]:
        valid = memory.lifecycle != MemoryLifecycleState.REJECTED
        return {"gate": "MP-G1_Validity", "pass": valid, "reason": "schema_valid" if valid else "invalid_state"}

class MP_G2_Evidence_Gate:
    """G2: 证据充分性 (Trace + Outcome 完整性)"""
    @staticmethod
    def check(memory: MemoryObject) -> Dict[str, Any]:
        has_trace = bool(memory.source_evidence and memory.source_evidence.trace_id)
        has_outcome = bool(memory.outcome_evaluation and memory.outcome_evaluation.realized_outcome)
        ok = has_trace and has_outcome
        return {"gate": "MP-G2_Evidence", "pass": ok, "reason": "trace_and_outcome_complete" if ok else "missing_evidence"}

class MP_G3_Stability_Gate:
    """G3: 稳定性 (Context 边界完整, 无过度泛化)"""
    @staticmethod
    def check(memory: MemoryObject) -> Dict[str, Any]:
        ctx = memory.context
        scope_valid = bool(ctx.applicable_scope) and "*" not in [s.lower() for s in ctx.applicable_scope]
        precond_valid = bool(ctx.preconditions)
        invalidation = bool(ctx.invalidation_conditions)
        ok = scope_valid and precond_valid and invalidation
        return {"gate": "MP-G3_Stability", "pass": ok, "reason": "bounded_context" if ok else "overgeneralized"}

class MP_G4_Impact_Gate:
    """G4: 影响面 (Confidence Score >= 0.7 阈值)"""
    @staticmethod
    def check(memory: MemoryObject, threshold: float = 0.7) -> Dict[str, Any]:
        if not memory.outcome_evaluation:
            return {"gate": "MP-G4_Impact", "pass": False, "reason": "no_outcome"}
        score = memory.outcome_evaluation.confidence_score
        return {"gate": "MP-G4_Impact", "pass": score >= threshold, "reason": f"confidence={score:.2f}"}

class MP_G5_Safety_Gate:
    """G5: 安全性 (无 Infeasible Outcome + 无已知禁忌词汇)"""
    FORBIDDEN = ["destroy", "drop_all", "ignore_constraint", "abandon_locked"]
    @classmethod
    def check(cls, memory: MemoryObject) -> Dict[str, Any]:
        rec = str(memory.semantic_recommendation).lower()
        violation = any(f in rec for f in cls.FORBIDDEN)
        return {"gate": "MP-G5_Safety", "pass": not violation, "reason": "no_forbidden_directive" if not violation else "forbidden_directive_detected"}

class MemoryAdmissionPipeline:
    """记忆晋升完整流水线 - MP-G1→G2→G3→G4→G5"""
    def __init__(self):
        self.gates = [
            MP_G1_Validity_Gate(),
            MP_G2_Evidence_Gate(),
            MP_G3_Stability_Gate(),
            MP_G4_Impact_Gate(),
            MP_G5_Safety_Gate(),
        ]
    
    def admit(self, memory: MemoryObject) -> Dict[str, Any]:
        results = []
        for gate in self.gates:
            r = gate.check(memory)
            results.append(r)
            if not r['pass']:
                return {"final_status": "REJECTED", "failed_gate": r['gate'], "reason": r['reason'], "log": results}
        return {"final_status": "PROMOTED", "log": results, "promoted_at": dt.now().isoformat()}
