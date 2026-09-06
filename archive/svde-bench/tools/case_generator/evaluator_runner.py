"""Evaluator Runner Orchestrator for SVDE-Bench v0.2.

Coordinates existing v0.1 evaluators (Semantic, Feasibility, Runtime, Memory)
without modifying their internal logic.
"""
from typing import Dict, Any, Optional
from svdebench.core import DecisionCase, DecisionArtifact
from svdebench.evaluator.semantic import SemanticEvaluator
from svdebench.evaluator.feasibility import FeasibilityEvaluator
from svdebench.evaluator.runtime import RuntimeEvaluator
from svdebench.evaluator.memory import MemoryEvaluator


class EvaluatorRunner:
    def __init__(self):
        self.semantic_evaluator = SemanticEvaluator()
        self.feasibility_evaluator = FeasibilityEvaluator()
        self.runtime_evaluator = RuntimeEvaluator()
        self.memory_evaluator = MemoryEvaluator()

    def evaluate(
        self,
        case: DecisionCase,
        oracle_result: Dict[str, Any],
        agent_artifact: DecisionArtifact,
        agent_name: str = "EvaluatedAgent",
    ) -> Dict[str, Any]:
        """Runs the four-dimensional evaluation pipeline on the agent output."""
        # 1. Semantic Evaluation
        sem_res = self.semantic_evaluator.evaluate(case, agent_artifact)
        sem_dict = sem_res.to_dict() if hasattr(sem_res, "to_dict") else sem_res.__dict__
        
        # 2. Feasibility Evaluation
        feas_res = self.feasibility_evaluator.evaluate(case, agent_artifact, oracle_result)
        feas_dict = feas_res.to_dict() if hasattr(feas_res, "to_dict") else feas_res.__dict__
        
        # 3. Runtime Evaluation
        runtime_res = self.runtime_evaluator.evaluate(case, agent_artifact)
        runtime_dict = runtime_res.to_dict() if hasattr(runtime_res, "to_dict") else runtime_res.__dict__
        
        # 4. Memory Evaluation
        mem_patch = getattr(agent_artifact, "memory_patch", None)
        if mem_patch:
            mem_res = self.memory_evaluator.evaluate(case, agent_artifact, memory=mem_patch)
            mem_dict = mem_res.to_dict() if hasattr(mem_res, "to_dict") else mem_res.__dict__
        else:
            mem_dict = {
                "evaluator_name": "MemoryEvaluator",
                "overall_pass": True,
                "score": 1.0,
                "promotion_status": "NONE_REQUIRED",
                "memory_id": None,
                "memory_class": None,
                "declared_lifecycle": None,
                "evaluated_promotion_status": "NONE_REQUIRED",
                "false_memory_probability": 0.0,
                "checks": {
                    "MP-G1_Validity": {"passed": True, "reason": "no_patch_provided"},
                    "MP-G2_Evidence": {"passed": True, "reason": "no_patch_provided"},
                    "MP-G3_Stability": {"passed": True, "reason": "no_patch_provided"},
                    "MP-G4_Impact": {"passed": True, "reason": "no_patch_provided"},
                    "MP-G5_Safety": {"passed": True, "reason": "no_patch_provided"},
                },
                "violations": [],
            }

        return {
            "case_id": case.metadata.id,
            "agent_name": agent_name,
            "semantic": sem_dict,
            "feasibility": feas_dict,
            "runtime": runtime_dict,
            "memory": mem_dict,
        }
