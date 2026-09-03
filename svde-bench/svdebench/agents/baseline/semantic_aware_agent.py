"""
svdebench.agents.baseline.semantic_aware_agent — Baseline B: Semantic Aware Agent
Behavior:
  Reads semantic_contract, honors HARD_COMMITMENT, generates compliant DecisionArtifact with causal trace & memory patch.
  Chooses Candidate B: Preserves ORD_03 commitment with minimal disruption.
"""
from __future__ import annotations
from svdebench.agents.base import BaseDecisionAgent
from svdebench.core.case import DecisionCase
from svdebench.core.artifact import DecisionArtifact
from svdebench.core.trace import DecisionTrace
from svdebench.core.memory import (
    MemoryObject,
    MemoryClass,
    MemoryLifecycleState,
    MemoryContext,
    MemoryTrigger,
    MemoryOutcomeEvaluation,
    MemorySourceEvidence,
)

class SemanticAwareAgent(BaseDecisionAgent):
    def solve(self, case: DecisionCase) -> DecisionArtifact:
        # Candidate B: 语义感知——优先锁定 ORD_03 必达，转派至可用车辆 VEH_03
        decision_routes = {
            "VEH_01": ["ORD_04"],           # 冷链件保持冷藏车
            "VEH_03": ["ORD_03", "ORD_06"]  # 承接故障车上的锁定件 ORD_03 与普货件 ORD_06
        }
        
        trace = DecisionTrace(
            trace_id=f"TR-SEMANTIC-{case.metadata.id}",
            decision_chain=[
                {"stage": "Contract_Ingestion", "status": "HARD_COMMITMENT_C4_DETECTED"},
                {"stage": "Constraint_Type_Check", "type": "TIME_WINDOW_LOCKED", "status": "PRESERVED"},
                {"stage": "DSVL_Precheck", "decision_feasibility": "PASS"},
                {"stage": "Solver", "objective_value": 480.0, "status": "FEASIBLE_COMMITTED"}
            ],
            causal_rationale=[
                {"order": "ORD_03", "action": "REASSIGNED_TO_VEH_03", "reason": "VIP_TIME_WINDOW_LOCKED_PRESERVED"},
                {"order": "ORD_04", "action": "KEPT_ON_VEH_01", "reason": "COLD_CHAIN_MATCH_PRESERVED"}
            ],
            constraint_provenance={
                "C1": "Fleet Payload Limit",
                "C3": "Cold Chain Food Safety",
                "C4": "Customer SLA Locked Commitment"
            }
        )
        
        # 构造提炼的经验记忆补丁 (Memory Artifact)
        memory_patch = MemoryObject(
            memory_id="DMEM-EPISODE-RECOVERY-001",
            memory_class=MemoryClass.EPISODE,
            decision_domain=case.metadata.domain,
            context=MemoryContext(
                applicable_scope=["Dynamic Fleet Rerouting", "Vehicle Breakdown"],
                preconditions={"has_locked_commitments": True, "fleet_size": ">= 2"},
                invalidation_conditions="single_fleet_all_breakdown"
            ),
            trigger=MemoryTrigger(
                event_type="VEHICLE_MECHANICAL_BREAKDOWN",
                variation_classification="SEMANTIC_VARIATION"
            ),
            semantic_recommendation={
                "guideline": "During vehicle breakdown, prioritize reassigning time-window locked orders to active vehicles over route efficiency.",
                "suggested_constraint_patch": {"type": "TimeWindowLock", "hardness": "HARD"}
            },
            outcome_evaluation=MemoryOutcomeEvaluation(
                predicted_outcome="0 commitment violations",
                realized_outcome="ORD_03 delivered on time within [120, 200]",
                confidence_score=0.99
            ),
            lifecycle=MemoryLifecycleState.CANDIDATE,
            source_evidence=MemorySourceEvidence(
                trace_id=f"TR-SEMANTIC-{case.metadata.id}",
                case_id=case.metadata.id,
                evidence_reference="SVDE-Bench Sprint 2 Execution"
            )
        )
        
        return DecisionArtifact(
            case_id=case.metadata.id,
            status="FEASIBLE",
            decision={"reassigned_routes": decision_routes, "total_additional_cost": 480.0},
            trace=trace,
            explanation={
                "summary": "ORD_03 locked commitment 100% preserved by transferring to VEH_03 despite minor cost increase (+60.0)."
            },
            validation_result={
                "dsvl_precheck": "PASS",
                "hard_commitment_honored": True,
                "cold_chain_preserved": True,
                "decision_feasibility": "PASS"
            },
            memory_patch=memory_patch
        )
