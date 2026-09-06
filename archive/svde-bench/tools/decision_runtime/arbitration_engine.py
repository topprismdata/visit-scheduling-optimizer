"""Arbitration Engine & Strategy for SVDE-Bench v0.4 Runtime.

Provides extensible arbitration across activated decision principles:
- BaseArbitrationPolicy (Interface)
- TierBasedArbitrationPolicy (Current baseline: Tier 3 > Tier 2 > Tier 1)
- ContextualArbitrationPolicy (Extension point for dynamic trade-offs)
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from tools.decision_runtime.principle_store import StoredPrinciple
from tools.decision_runtime.decision_context import DecisionContext


class BaseArbitrationPolicy(ABC):
    """Abstract interface for principle arbitration."""
    @abstractmethod
    def arbitrate(self, context: DecisionContext, principles: List[StoredPrinciple]) -> List[StoredPrinciple]:
        pass


class TierBasedArbitrationPolicy(BaseArbitrationPolicy):
    """
    Baseline arbitration policy:
    Sorts principles strictly by declared Precedence Tier descending:
    Tier 3 (Physical/Safety/Compliance) > Tier 2 (SLA/Commitment) > Tier 1 (Efficiency/Handoff)
    """
    def arbitrate(self, context: DecisionContext, principles: List[StoredPrinciple]) -> List[StoredPrinciple]:
        return sorted(principles, key=lambda p: p.precedence_tier, reverse=True)


class ContextualArbitrationPolicy(BaseArbitrationPolicy):
    """
    Extension point: Context-aware dynamic arbitration.
    Adjusts principle weighting based on real-time contention ratio and business severity.
    """
    def arbitrate(self, context: DecisionContext, principles: List[StoredPrinciple]) -> List[StoredPrinciple]:
        # If resource contention is extreme (>1.5), SLA commitment is prioritized over all else
        if context.resource_contention_ratio > 1.5:
            return sorted(principles, key=lambda p: (p.precedence_tier if p.precedence_tier == 3 else p.precedence_tier + 2), reverse=True)
        return sorted(principles, key=lambda p: p.precedence_tier, reverse=True)


class ArbitrationEngine:
    """Orchestrates principle arbitration using the configured policy."""
    def __init__(self, policy: Optional[BaseArbitrationPolicy] = None):
        self.policy = policy or TierBasedArbitrationPolicy()

    def arbitrate(self, context: DecisionContext, principles: List[StoredPrinciple]) -> List[StoredPrinciple]:
        return self.policy.arbitrate(context, principles)
