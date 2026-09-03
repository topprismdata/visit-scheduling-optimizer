"""Principle Activation & Rejection Trace for SVDE-Bench v0.4 Runtime.

Provides full observability into the runtime decision process:
- Why a specific principle was activated (trigger conditions matched).
- Why another candidate was rejected (boundary invalidation or scope mismatch).
- Which boundary conditions were verified.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class PrincipleActivationRecord:
    principle_id: str
    principle_name: str
    precedence_tier: int
    activation_reason: str
    verified_conditions: List[str]


@dataclass
class PrincipleRejectionRecord:
    principle_id: str
    principle_name: str
    rejection_reason: str
    failed_boundary_check: str


@dataclass
class PrincipleRuntimeTrace:
    case_id: str
    arbitration_mode: str  # e.g., tier_based
    activated_principles: List[PrincipleActivationRecord] = field(default_factory=list)
    rejected_principles: List[PrincipleRejectionRecord] = field(default_factory=list)
    arbitrated_precedence: List[str] = field(default_factory=list)
    explanation_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "arbitration_mode": self.arbitration_mode,
            "activated_principles": [
                {
                    "id": a.principle_id,
                    "name": a.principle_name,
                    "tier": a.precedence_tier,
                    "reason": a.activation_reason,
                    "conditions": a.verified_conditions,
                }
                for a in self.activated_principles
            ],
            "rejected_principles": [
                {
                    "id": r.principle_id,
                    "name": r.principle_name,
                    "reason": r.rejection_reason,
                    "boundary": r.failed_boundary_check,
                }
                for r in self.rejected_principles
            ],
            "arbitrated_precedence": self.arbitrated_precedence,
            "explanation_summary": self.explanation_summary,
        }
