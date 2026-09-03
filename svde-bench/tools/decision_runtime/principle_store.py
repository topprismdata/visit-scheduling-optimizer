"""Principle Store for SVDE-Bench v0.4 Runtime.

Provides a structured, file-backed repository for managing versioned,
governed decision principles with explicit boundaries, precedence tiers, and evidence traces.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field
import yaml


@dataclass
class StoredPrinciple:
    principle_id: str
    name: str
    dilemma_archetype: str
    trigger_conditions: Dict[str, Any]
    governing_rule: str
    tradeoff_sacrifice: str
    invalidation_boundaries: List[str]
    precedence_tier: int  # Tier 3 (Safety/Compliance) > Tier 2 (SLA) > Tier 1 (Efficiency)
    status: str  # PROMOTED, CANDIDATE, DEPRECATED, REJECTED
    evidence_cases: List[str]
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
            "evidence_cases": self.evidence_cases,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredPrinciple":
        return cls(
            principle_id=data["principle_id"],
            name=data.get("name", data["principle_id"]),
            dilemma_archetype=data.get("dilemma_archetype", "GENERAL"),
            trigger_conditions=data.get("trigger_conditions", {}),
            governing_rule=data.get("governing_rule", ""),
            tradeoff_sacrifice=data.get("tradeoff_sacrifice", ""),
            invalidation_boundaries=data.get("invalidation_boundaries", []),
            precedence_tier=data.get("precedence_tier", 2),
            status=data.get("status", "PROMOTED"),
            evidence_cases=data.get("evidence_cases", []),
            confidence_score=data.get("confidence_score", 0.99),
        )


class PrincipleStore:
    """File-backed repository for governed decision principles."""
    def __init__(self, store_file: Optional[Path] = None):
        self.store_file = store_file
        self.principles: Dict[str, StoredPrinciple] = {}
        if self.store_file and self.store_file.exists():
            self.load()
        else:
            self._load_default_governed_principles()

    def _load_default_governed_principles(self):
        """Loads the validated principles from Sprint 3.4 into store."""
        defaults = [
            StoredPrinciple(
                principle_id="DISC-PRIN-001",
                name="Commitment Preservation Invariant",
                dilemma_archetype="RIGID_COMMITMENT_UNDER_RESOURCE_CONTENTION",
                trigger_conditions={"has_locked_commitments": True, "resource_contention": "HIGH"},
                governing_rule="Immutable customer commitments and relational SLA windows strictly supersede local travel distance/cost heuristics under capacity strain.",
                tradeoff_sacrifice="Accepts higher transit expense and overtime to guarantee 100% commitment fulfillment.",
                invalidation_boundaries=["zero_locked_commitments", "unconstrained_infinite_capacity"],
                precedence_tier=2,
                status="PROMOTED",
                evidence_cases=["D01", "D03", "V01", "V02", "V03"],
                confidence_score=0.99
            ),
            StoredPrinciple(
                principle_id="DISC-PRIN-002",
                name="Rigid Competency & Compartment Matching",
                dilemma_archetype="RIGID_COMPETENCY_MATCHING",
                trigger_conditions={"task_requires_certification": True, "heterogeneous_resources": True},
                governing_rule="Tasks requiring specialized physical compartments or certification credentials must be assigned strictly to compatible execution resources.",
                tradeoff_sacrifice="Sacrifices route proximity to enforce strict physical/competency compliance.",
                invalidation_boundaries=["homogeneous_general_cargo", "universal_staff_qualification"],
                precedence_tier=3,
                status="PROMOTED",
                evidence_cases=["D07", "D08", "V03", "V04"],
                confidence_score=0.99
            ),
            StoredPrinciple(
                principle_id="DISC-PRIN-003",
                name="Surgical Orphan Task Absorption",
                dilemma_archetype="SURGICAL_ORPHAN_TASK_ABSORPTION",
                trigger_conditions={"resource_failure_event": True, "active_fleet_surplus": True},
                governing_rule="In sudden resource failure, orphaned locked tasks must be surgically transferred to standby resources while minimizing schedule ripple perturbations.",
                tradeoff_sacrifice="Accepts localized stand-in route extension to prevent regional schedule chaos.",
                invalidation_boundaries=["fleet_wide_catastrophic_collapse", "zero_surplus_capacity"],
                precedence_tier=1,
                status="PROMOTED",
                evidence_cases=["D03", "V07", "V08"],
                confidence_score=0.99
            ),
        ]
        for p in defaults:
            self.principles[p.principle_id] = p

    def add_principle(self, principle: StoredPrinciple):
        self.principles[principle.principle_id] = principle
        if self.store_file:
            self.save()

    def get_promoted_principles(self) -> List[StoredPrinciple]:
        return [p for p in self.principles.values() if p.status == "PROMOTED"]

    def save(self):
        if not self.store_file:
            return
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        data = [p.to_dict() for p in self.principles.values()]
        with open(self.store_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False)

    def load(self):
        if not self.store_file or not self.store_file.exists():
            return
        with open(self.store_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        self.principles = {item["principle_id"]: StoredPrinciple.from_dict(item) for item in data}
