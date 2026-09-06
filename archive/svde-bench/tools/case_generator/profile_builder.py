"""DecisionProfile Builder for SVDE-Bench v0.2.

Builds structured, typed DecisionProfile dictionaries strictly conforming to
schemas/profile/decision_profile.yaml with deterministic grading and evidence preservation.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime as dt


def compute_grade(semantic_pass: bool, feasibility_status: str, commitment_survival: float) -> str:
    if not semantic_pass:
        return "F"
    if feasibility_status == "INFEASIBLE":
        return "F"
    if commitment_survival < 0.5:
        return "D"
    if commitment_survival < 0.8:
        return "C"
    if commitment_survival < 1.0:
        return "B"
    return "A"


class ProfileBuilder:
    @staticmethod
    def build(
        case_id: str,
        domain: str,
        decision_intent: Dict[str, Any],
        solution_summary: Dict[str, Any],
        evaluation_results: Dict[str, Any],
        reproducibility: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sem = evaluation_results.get("semantic", {})
        feas = evaluation_results.get("feasibility", {})
        runtime = evaluation_results.get("runtime", {})
        mem = evaluation_results.get("memory", {})

        sem_pass = bool(sem.get("overall_pass", False))
        feas_status = str(feas.get("feasibility_status", "UNKNOWN"))
        surv_rate = float(runtime.get("commitment_survival_rate", 1.0))
        
        grade = compute_grade(sem_pass, feas_status, surv_rate)
        
        # Build strict Profile dictionary conforming to schemas/profile/decision_profile.yaml
        profile: Dict[str, Any] = {
            "decision_profile": {
                "case_id": case_id,
                "domain": domain,
                "decision_intent": decision_intent,
                "solution_summary": solution_summary,
            },
            "evaluation": {
                "semantic": {
                    "score": 1.0 if sem_pass else 0.0,
                    "evidence": str(sem.get("evidence", f"semantic_pass={sem_pass}")),
                },
                "feasibility": {
                    "score": float(feas.get("optimality_gap", 0.0)),
                    "violations": feas.get("violations", []),
                },
                "runtime": {
                    "score": surv_rate,
                    "adaptation": f"disruption_ratio={runtime.get('disruption_ratio', 0.0)}",
                },
                "memory": {
                    "score": float(mem.get("score", 1.0)),
                    "admitted_memory": {
                        "promotion_status": mem.get("promotion_status", "NONE_REQUIRED"),
                        "checks": mem.get("checks", {}),
                    },
                },
            },
            "overall": {
                "grade": grade,
                "score": 1.0 if grade == "A" else (0.8 if grade == "B" else (0.5 if grade == "C" else 0.0)),
            },
            "failure_analysis": {
                "failure_modes": sem.get("failure_modes", []) + (["INFEASIBLE"] if feas_status == "INFEASIBLE" else []),
                "root_causes": feas.get("violations", []) + (["COMMITMENT_BROKEN"] if surv_rate < 1.0 else []),
            },
            "reproducibility": reproducibility or {
                "run_count": 1,
                "deterministic": True,
            },
        }

        return profile
