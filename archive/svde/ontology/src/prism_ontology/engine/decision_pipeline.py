"""Decision Pipeline Runner — Human-in-the-Loop Production Implementation.

Core Principle:
Algorithms generate candidate plans and audit reports to surface trade-offs.
Humans (Managers / Sales Reps) provide context-specific intent and final approval.

Pipeline Flow:
WorldState + Rep-Specific PlanningIntent
  -> SVDEOntologyAdapter
  -> PeriodicPVRPSolver (Candidate Generation)
  -> ThreeDimensionalPlanAuditor (Exposes Physical/Business/Semantic trade-offs)
  -> Candidate Plan Artifact (PENDING_HUMAN_APPROVAL)
  -> Explicit Human Sign-off -> DecisionArtifact (APPROVED_FOR_EXECUTION)
"""
import datetime
from typing import Dict, Any, Optional

from prism_ontology.contracts.world_state import WorldState
from prism_ontology.contracts.planning_io import (
    PlanningIntent, PlanningCapabilityType, CandidatePlan,
    PlanAuditReport, DecisionArtifact
)
from prism_ontology.reference.store import ReferenceOntologyStore
from prism_ontology.compiler.operational import OperationalCompiler
from prism_ontology.adapters.svde.bridge import SVDEOntologyAdapter
from prism_ontology.engine.periodic_pvrp_solver import PeriodicPVRPSolver
from prism_ontology.diagnostics.plan_auditor import ThreeDimensionalPlanAuditor


class DecisionPipelineRunner:
    """Human-in-the-Loop Decision Pipeline Runner for SVDE."""

    @staticmethod
    def generate_candidate_and_audit(
        world_state: WorldState,
        intent: PlanningIntent,
        store: Optional[ReferenceOntologyStore] = None,
        compiler: Optional[OperationalCompiler] = None
    ) -> tuple[CandidatePlan, PlanAuditReport]:
        """
        Step 1 & 2: Generate candidate plan and run independent 3D audit.
        Surfaces all physical/business trade-offs to human decision maker.
        """
        if store is None:
            store = ReferenceOntologyStore()
        if compiler is None:
            compiler = OperationalCompiler(store)
            
        adapter = SVDEOntologyAdapter(store, compiler)
        
        # 1. Dispatch intent to generate mathematical payload
        payload = adapter.dispatch_planning_intent(intent, world_state)
        
        # 2. Invoke solver engine adapter
        candidate_plan: CandidatePlan = PeriodicPVRPSolver.solve(payload)
        
        # 3. Invoke three-dimensional independent auditor
        audit_report: PlanAuditReport = ThreeDimensionalPlanAuditor.audit_candidate_plan(candidate_plan, world_state)
        
        return candidate_plan, audit_report

    @staticmethod
    def human_approve_and_publish(
        candidate_plan: CandidatePlan,
        audit_report: PlanAuditReport,
        approver_id: str,
        approval_notes: str = ""
    ) -> DecisionArtifact:
        """
        Step 3: Explicit Human-in-the-loop sign-off and publishing.
        Guarantees that no plan is published without explicit human authorization.
        """
        if not approver_id or approver_id.strip() == "":
            raise ValueError("Explicit human approver_id is required to publish DecisionArtifact!")
            
        published_schedule = {}
        for route in candidate_plan.daily_routes:
            published_schedule[route.date_str] = [s.store_code for s in route.stops]
            
        return DecisionArtifact(
            artifact_id=f"DECISION_ART_{candidate_plan.rep_id}_{candidate_plan.period_label}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            candidate_plan_ref=candidate_plan.plan_id,
            audit_report_ref=audit_report.plan_id,
            approved_by=approver_id,
            approved_at=datetime.datetime.now(),
            published_schedule=published_schedule,
            status="APPROVED_FOR_EXECUTION"
        )
