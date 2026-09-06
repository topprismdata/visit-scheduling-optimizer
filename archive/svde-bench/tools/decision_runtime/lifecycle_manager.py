"""Principle Lifecycle Manager for SVDE-Bench v0.4 Runtime.

Governs the complete state transitions of decision principles:
DISCOVERED -> CANDIDATE -> PROMOTED -> DEPRECATED / REJECTED
"""
from typing import Dict, Any, List, Optional
from datetime import datetime as dt
from tools.decision_runtime.principle_store import StoredPrinciple, PrincipleStore


class PrincipleLifecycleManager:
    """Manages lifecycle transitions, deprecation decay, and status queries for principles."""
    VALID_TRANSITIONS = {
        "DISCOVERED": ["CANDIDATE", "REJECTED"],
        "CANDIDATE": ["PROMOTED", "REJECTED"],
        "PROMOTED": ["DEPRECATED", "REJECTED"],
        "DEPRECATED": ["PROMOTED", "REJECTED"],
        "REJECTED": [],  # Terminal state
    }

    def __init__(self, store: Optional[PrincipleStore] = None):
        self.store = store or PrincipleStore()
        self.transition_history: List[Dict[str, Any]] = []

    def transition_status(
        self,
        principle_id: str,
        new_status: str,
        reason: str,
        operator: str = "System"
    ) -> bool:
        if principle_id not in self.store.principles:
            return False

        principle = self.store.principles[principle_id]
        current = principle.status
        allowed = self.VALID_TRANSITIONS.get(current, [])

        if new_status not in allowed and new_status != current:
            return False

        # Apply transition
        principle.status = new_status
        record = {
            "timestamp": dt.now().isoformat(),
            "principle_id": principle_id,
            "previous_status": current,
            "new_status": new_status,
            "reason": reason,
            "operator": operator,
        }
        self.transition_history.append(record)
        return True

    def deprecate_outdated_principle(self, principle_id: str, deprecation_reason: str) -> bool:
        """Explicitly deprecates an obsolete principle due to context shift or domain decay."""
        return self.transition_status(
            principle_id=principle_id,
            new_status="DEPRECATED",
            reason=f"Decay / Context Obsolete: {deprecation_reason}"
        )

    def reject_flawed_principle(self, principle_id: str, rejection_reason: str) -> bool:
        """Rejects a flawed or poisoned candidate principle."""
        return self.transition_status(
            principle_id=principle_id,
            new_status="REJECTED",
            reason=f"Falsified / Negative Transfer: {rejection_reason}"
        )
