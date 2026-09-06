"""Governance 7-state lifecycle (v1.1 §8).

Phases: EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN → DEPRECATED
"""
from enum import Enum
from typing import List, Set


class LifecycleState(str, Enum):
    EXTRACTED = "EXTRACTED"
    EVIDENCE_PENDING = "EVIDENCE_PENDING"
    CANDIDATE = "CANDIDATE"
    DOMAIN_REVIEW = "DOMAIN_REVIEW"
    BUSINESS_APPROVED = "BUSINESS_APPROVED"
    FROZEN = "FROZEN"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


# Allowed forward transitions (strict, no skip, no regress)
ALLOWED_TRANSITIONS: dict = {
    LifecycleState.EXTRACTED: {LifecycleState.EVIDENCE_PENDING},
    LifecycleState.EVIDENCE_PENDING: {LifecycleState.CANDIDATE},
    LifecycleState.CANDIDATE: {LifecycleState.DOMAIN_REVIEW},
    LifecycleState.DOMAIN_REVIEW: {LifecycleState.BUSINESS_APPROVED},
    LifecycleState.BUSINESS_APPROVED: {LifecycleState.FROZEN},
    LifecycleState.FROZEN: {LifecycleState.DEPRECATED},   # Only via OntologyChangeRequest
    LifecycleState.DEPRECATED: {LifecycleState.RETIRED},   # Only via OntologyChangeRequest
    LifecycleState.RETIRED: set(),
}


class InvalidTransitionError(Exception):
    """Raised when attempting an illegal lifecycle state transition."""


class LifecycleManager:
    """Validates 7-state transitions. Used by governance gate."""

    def can_transition(self, from_state: LifecycleState, to_state: LifecycleState) -> bool:
        return to_state in ALLOWED_TRANSITIONS.get(from_state, set())

    def transition(self, from_state: LifecycleState, to_state: LifecycleState) -> LifecycleState:
        if not self.can_transition(from_state, to_state):
            raise InvalidTransitionError(
                f"Cannot transition from {from_state.value} to {to_state.value}. "
                f"Allowed: {[s.value for s in ALLOWED_TRANSITIONS.get(from_state, set())]}"
            )
        return to_state

    def is_frozen(self, state: LifecycleState) -> bool:
        return state == LifecycleState.FROZEN

    def is_terminal(self, state: LifecycleState) -> bool:
        return state == LifecycleState.RETIRED
