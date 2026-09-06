"""SVDE Core Decision Memory & Governance."""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GovernedPrinciple:
    principle_id: str
    name: str
    dilemma_archetype: str
    trigger_conditions: Dict[str, Any]
    governing_rule: str
    tradeoff_sacrifice: str
    invalidation_boundaries: List[str]
    precedence_tier: int  # Tier 3 (Safety/Compliance) > Tier 2 (SLA) > Tier 1 (Efficiency)
    status: str  # PROMOTED, CANDIDATE, DEPRECATED, REJECTED
    evidence_sources: List[str]
    confidence_score: float = 0.99

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principle_id": self.principle_id,
            "name": self.name,
            "dilemma_archetype": self.dilemma_archetype,
            "trigger_conditions": self.trigger_conditions,
            "governing_rule": self.governing_rule,
            "tradeoff_sacrifice": self.tradeoff_sacrifice,
            "invalidation_boundaries": self.invalidation_boundaries,
            "precedence_tier": self.precedence_tier,
            "status": self.status,
            "evidence_sources": self.evidence_sources,
            "confidence_score": self.confidence_score,
        }


class MemoryStore:
    """Core Memory Store managing governed decision principles (Fix #7: zero un-packaged runtime dependencies)."""
    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file
        self.principles: Dict[str, GovernedPrinciple] = {}
        self._load_core_principles()

    def _load_core_principles(self):
        defaults = [
            GovernedPrinciple(
                principle_id="CORE-PRIN-001",
                name="Commitment Preservation Invariant",
                dilemma_archetype="RIGID_COMMITMENT_UNDER_RESOURCE_CONTENTION",
                trigger_conditions={"has_hard_commitments": True},
                governing_rule="Immutable customer SLA commitments strictly supersede local distance/cost heuristics under capacity strain.",
                tradeoff_sacrifice="Accepts higher transit expense to guarantee 100% commitment fulfillment.",
                invalidation_boundaries=["zero_locked_commitments"],
                precedence_tier=2,
                status="PROMOTED",
                evidence_sources=["Enterprise SLA Policy"]
            ),
            GovernedPrinciple(
                principle_id="CORE-PRIN-002",
                name="Rigid Competency & Compartment Matching",
                dilemma_archetype="RIGID_COMPETENCY_MATCHING",
                trigger_conditions={"has_competency_constraints": True},
                governing_rule="Tasks requiring specialized physical compartments or certification credentials must be assigned strictly to compatible execution resources.",
                tradeoff_sacrifice="Sacrifices route proximity to enforce strict physical/competency compliance.",
                invalidation_boundaries=["homogeneous_general_cargo"],
                precedence_tier=3,
                status="PROMOTED",
                evidence_sources=["Safety & Compliance Standard"]
            ),
            GovernedPrinciple(
                principle_id="CORE-PRIN-003",
                name="Surgical Orphan Task Absorption",
                dilemma_archetype="SURGICAL_ORPHAN_TASK_ABSORPTION",
                trigger_conditions={"has_resource_failure": True},
                governing_rule="In sudden resource failure, orphaned locked tasks must be surgically transferred to standby resources while minimizing schedule ripple perturbations.",
                tradeoff_sacrifice="Accepts localized stand-in route extension to prevent regional schedule chaos.",
                invalidation_boundaries=["fleet_wide_catastrophic_collapse"],
                precedence_tier=1,
                status="PROMOTED",
                evidence_sources=["Operational Continuity Guideline"]
            ),
        ]
        for p in defaults:
            self.principles[p.principle_id] = p

    def get_promoted_principles(self) -> List[GovernedPrinciple]:
        return [p for p in self.principles.values() if p.status == "PROMOTED"]
