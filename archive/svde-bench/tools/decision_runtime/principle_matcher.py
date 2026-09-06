"""Principle Matcher for SVDE-Bench v0.4 Runtime.

Matches DecisionContext against StoredPrinciples and produces detailed PrincipleRuntimeTrace:
1. Evaluates trigger conditions against normalized DecisionContext.
2. Checks invalidation boundaries to prevent negative transfer.
3. Records explicit activation reasons and rejection boundary findings.
"""
from typing import Dict, Any, List, Optional, Tuple
from svdebench.core import DecisionCase
from tools.decision_runtime.principle_store import StoredPrinciple, PrincipleStore
from tools.decision_runtime.decision_context import DecisionContext
from tools.decision_runtime.principle_trace import (
    PrincipleRuntimeTrace, PrincipleActivationRecord, PrincipleRejectionRecord
)
from tools.decision_runtime.arbitration_engine import ArbitrationEngine, TierBasedArbitrationPolicy


class PrincipleMatcher:
    """Matches DecisionContext instances to applicable governed principles and generates observability traces."""
    def __init__(self, store: Optional[PrincipleStore] = None, arbitration_engine: Optional[ArbitrationEngine] = None):
        self.store = store or PrincipleStore()
        self.arbitration_engine = arbitration_engine or ArbitrationEngine()

    def match_with_trace(self, context: DecisionContext) -> Tuple[List[StoredPrinciple], PrincipleRuntimeTrace]:
        promoted = self.store.get_promoted_principles()
        activated: List[StoredPrinciple] = []
        activation_records: List[PrincipleActivationRecord] = []
        rejection_records: List[PrincipleRejectionRecord] = []

        for p in self.store.principles.values():
            # 1. Check if promoted
            if p.status != "PROMOTED":
                rejection_records.append(PrincipleRejectionRecord(
                    principle_id=p.principle_id,
                    principle_name=p.name,
                    rejection_reason=f"Status is {p.status}, not PROMOTED",
                    failed_boundary_check="lifecycle_status_check"
                ))
                continue

            # 2. Check Invalidation Boundaries (MP-G2 & MP-G5)
            boundary_hit = False
            failed_boundary = ""
            
            for b in p.invalidation_boundaries:
                if b == "zero_locked_commitments" and not context.has_hard_commitments:
                    boundary_hit = True
                    failed_boundary = "zero_locked_commitments: Context has no locked commitments"
                    break
                elif b == "unconstrained_infinite_capacity" and context.resource_contention_ratio < 0.2:
                    boundary_hit = True
                    failed_boundary = "unconstrained_infinite_capacity: Contention ratio < 0.2"
                    break
                elif b == "homogeneous_general_cargo" and not context.has_competency_constraints:
                    boundary_hit = True
                    failed_boundary = "homogeneous_general_cargo: No specialized compartment or certification needed"
                    break
                elif b == "fleet_wide_catastrophic_collapse" and context.active_resource_count == 0:
                    boundary_hit = True
                    failed_boundary = "fleet_wide_catastrophic_collapse: Zero active fleet resources"
                    break

            if boundary_hit:
                rejection_records.append(PrincipleRejectionRecord(
                    principle_id=p.principle_id,
                    principle_name=p.name,
                    rejection_reason="Invalidation boundary condition verified in context",
                    failed_boundary_check=failed_boundary
                ))
                continue

            # 3. Check Trigger Conditions
            is_match = False
            reason = ""
            conditions_met = []

            if p.principle_id == "DISC-PRIN-001" and context.has_hard_commitments:
                is_match = True
                reason = "Resource contention present with immutable SLA customer commitments"
                conditions_met = ["has_hard_commitments=True", f"contention_ratio={context.resource_contention_ratio}"]
            elif p.principle_id == "DISC-PRIN-002" and context.has_competency_constraints:
                is_match = True
                reason = "Heterogeneous cargo requiring physical compartment or specialist certification"
                conditions_met = ["has_competency_constraints=True"]
            elif p.principle_id == "DISC-PRIN-003" and context.has_resource_failure and context.active_resource_count >= 1:
                is_match = True
                reason = "Sudden resource disruption detected with surplus capacity available on standby fleet"
                conditions_met = ["has_resource_failure=True", f"active_resources={context.active_resource_count}"]

            if is_match:
                activated.append(p)
                activation_records.append(PrincipleActivationRecord(
                    principle_id=p.principle_id,
                    principle_name=p.name,
                    precedence_tier=p.precedence_tier,
                    activation_reason=reason,
                    verified_conditions=conditions_met
                ))
            else:
                rejection_records.append(PrincipleRejectionRecord(
                    principle_id=p.principle_id,
                    principle_name=p.name,
                    rejection_reason="Trigger conditions not satisfied in context",
                    failed_boundary_check="trigger_condition_mismatch"
                ))

        # 4. Arbitrate Precedence
        arbitrated = self.arbitration_engine.arbitrate(context, activated)
        arbitrated_ids = [p.principle_id for p in arbitrated]

        trace = PrincipleRuntimeTrace(
            case_id=context.case_id,
            arbitration_mode=self.arbitration_engine.policy.__class__.__name__,
            activated_principles=activation_records,
            rejected_principles=rejection_records,
            arbitrated_precedence=arbitrated_ids,
            explanation_summary=f"Activated {len(arbitrated)} principles in precedence order: {arbitrated_ids}"
        )

        return arbitrated, trace

    def match_applicable_principles(self, case: Any) -> List[StoredPrinciple]:
        """Backward compatibility helper taking DecisionCase or DecisionContext."""
        if isinstance(case, DecisionCase):
            ctx = DecisionContext.from_decision_case(case)
        elif isinstance(case, DecisionContext):
            ctx = case
        else:
            return self.store.get_promoted_principles()
        principles, _ = self.match_with_trace(ctx)
        return principles
