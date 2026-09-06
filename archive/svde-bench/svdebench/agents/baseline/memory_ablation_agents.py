"""Memory Ablation & Multi-Outcome Baseline Agents for SVDE-Bench v0.2.

Provides:
1. FullDecisionAgentWithoutMemory (Ablation: Full decision logic without memory generation/retrieval)
2. StaleMemoryAgent (Generates REJECTED memory due to context invalidation)
3. ConflictingMemoryAgent (Generates CONFLICT memory due to contradictory guidelines)
4. WeakEvidenceMemoryAgent (Generates PENDING/CANDIDATE memory due to low confidence/incomplete trace)
"""
from typing import Dict, Any, List
from svdebench.core import (
    DecisionCase, DecisionArtifact, DecisionTrace,
    MemoryObject, MemoryClass, MemoryContext, MemoryTrigger,
    MemoryOutcomeEvaluation, MemoryLifecycleState, MemorySourceEvidence
)
from svdebench.agents.base import BaseDecisionAgent
from svdebench.agents.baseline.generalized_agents import GeneralizedFullDecisionAgent


class FullDecisionAgentWithoutMemory(GeneralizedFullDecisionAgent):
    """Ablation Baseline: Same semantic & runtime decision logic, but with memory layer completely disabled."""
    def solve(self, case: DecisionCase) -> DecisionArtifact:
        art = super().solve(case)
        # Strip memory patch
        return DecisionArtifact(
            case_id=art.case_id,
            status=art.status,
            decision=art.decision,
            trace=art.trace,
            explanation=art.explanation,
            validation_result=art.validation_result,
            memory_patch=None
        )


class StaleMemoryAgent(GeneralizedFullDecisionAgent):
    """Generates memory with unbounded/invalidated scope, triggering REJECTED status (MP-G2 / Rule 2 fail)."""
    def solve(self, case: DecisionCase) -> DecisionArtifact:
        art = super().solve(case)
        # Unbounded context scope -> Over-generalized false memory
        bad_memory = MemoryObject(
            memory_id=f"DMEM-STALE-{case.metadata.id}",
            memory_class=MemoryClass.EPISODE,
            decision_domain=case.metadata.domain,
            context=MemoryContext(
                applicable_scope=["*"], # Over-generalized wildcard scope
                preconditions={}
            ),
            trigger=MemoryTrigger(event_type="UNBOUNDED_TRIGGER"),
            semantic_recommendation={"rule": "always detour 30km around bridge"},
            outcome_evaluation=MemoryOutcomeEvaluation(
                predicted_outcome="Unknown",
                realized_outcome="", # Missing empirical outcome
                confidence_score=0.4
            ),
            lifecycle=MemoryLifecycleState.CANDIDATE,
            source_evidence=MemorySourceEvidence(trace_id="")
        )
        return DecisionArtifact(
            case_id=art.case_id,
            status=art.status,
            decision=art.decision,
            trace=art.trace,
            explanation=art.explanation,
            validation_result=art.validation_result,
            memory_patch=bad_memory
        )


class WeakEvidenceMemoryAgent(GeneralizedFullDecisionAgent):
    """Generates memory with candidate lifecycle and incomplete trace, triggering CANDIDATE/PENDING status."""
    def solve(self, case: DecisionCase) -> DecisionArtifact:
        art = super().solve(case)
        pending_memory = MemoryObject(
            memory_id=f"DMEM-PENDING-{case.metadata.id}",
            memory_class=MemoryClass.EPISODE,
            decision_domain=case.metadata.domain,
            context=MemoryContext(
                applicable_scope=["Dynamic Delivery"],
                preconditions={"fleet_size": ">= 1"}
            ),
            trigger=MemoryTrigger(event_type="OBSERVATION"),
            semantic_recommendation={"rule": "tentative observation on route congestion"},
            outcome_evaluation=MemoryOutcomeEvaluation(
                predicted_outcome="Potential delay",
                realized_outcome="", # Outcome not yet verified
                confidence_score=0.5
            ),
            lifecycle=MemoryLifecycleState.CANDIDATE,
            source_evidence=MemorySourceEvidence(trace_id=f"TR-PENDING-{case.metadata.id}")
        )
        return DecisionArtifact(
            case_id=art.case_id,
            status=art.status,
            decision=art.decision,
            trace=art.trace,
            explanation=art.explanation,
            validation_result=art.validation_result,
            memory_patch=pending_memory
        )
