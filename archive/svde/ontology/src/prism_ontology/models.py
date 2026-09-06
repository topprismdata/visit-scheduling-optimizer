"""Core data models for prism-ontology (Phase 0 stubs)."""
from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime


@dataclass
class Evidence:
    """Evidence Bundle entry."""
    source_id: str
    author_org: str
    year: int
    evidence_level: str
    scope: str
    chapter_or_page: str
    original_quote: str
    supports_claims: List[str] = field(default_factory=list)


@dataclass
class Claim:
    """Business claim derived from evidence."""
    claim_id: str
    statement: str
    source_ids: List[str]
    evidence_level: str
    supports_objects: List[str]
    confidence: str = "MEDIUM"
    status: str = "EVIDENCE_CONFIRMED"
    reviewed_by: str = ""


@dataclass
class CompetencyQuestion:
    """Anti-fabrication competency question."""
    cq_id: str
    question: str
    expected_decision_level: str
    required_classes: List[str] = field(default_factory=list)
    forbidden_levels: List[str] = field(default_factory=list)
    expected_answer_shape: str = ""


@dataclass
class GovernanceDecision:
    """Frozen / Approved / Deprecated decision record."""
    object_id: str
    current_state: str
    decision_log: List[Dict[str, Any]] = field(default_factory=list)
    approved_at: str = ""
    approved_by: str = ""
