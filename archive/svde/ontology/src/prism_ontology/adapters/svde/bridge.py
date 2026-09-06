"""SVDE Adapter — bridges prism-ontology to SVDE Core DecisionGate.

Phase 3 deliverable per v1.1 §9 Phase 3.

Flow:
  DecisionRequest (SVDE Core)
    → SVDEOntologyAdapter.diagnose()
      → calls prism_ontology.diagnostics.IntentRouter
      → returns BusinessDecisionIntent
    → DecisionCompiler (SVDE Core) receives BusinessDecisionIntent
    → DecisionPlanner uses capabilities from prism-ontology CapabilityRegistry
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from prism_ontology.reference.store import (
    ReferenceOntologyStore,
    ReferenceObject,
    ObjectLayer,
    DecisionLevel as PrismDecisionLevel,
)
from prism_ontology.diagnostics import IntentRouter, IntentDiagnostic
from prism_ontology.compiler.operational import OperationalCompiler, JSONSchema


# =====================================================================
# SVDE BusinessDecisionIntent — produced by SVDE adapter from prism-ontology
# =====================================================================

class BusinessQuestion(str, Enum):
    """SVDE decision levels aligned with prism-ontology DecisionLevel."""
    TERRITORY_ALIGNMENT = "TERRITORY_ALIGNMENT"
    PERIODIC_COVERAGE = "PERIODIC_COVERAGE"
    DAILY_ROUTE_SEQUENCE = "DAILY_ROUTE_SEQUENCE"
    ROLLING_REPLAN = "ROLLING_REPLAN"
    DISTANCE_TIME_TRADEOFF = "DISTANCE_TIME_TRADEOFF"
    UNCLASSIFIED = "UNCLASSIFIED"


QUESTION_TO_CAPABILITIES: Dict[BusinessQuestion, List[str]] = {
    BusinessQuestion.TERRITORY_ALIGNMENT: ["territory_alignment"],
    BusinessQuestion.PERIODIC_COVERAGE: ["periodic_visit_planning"],
    BusinessQuestion.DAILY_ROUTE_SEQUENCE: ["daily_route_optimization"],
    BusinessQuestion.ROLLING_REPLAN: [
        "territory_alignment",
        "periodic_visit_planning",
        "daily_route_optimization",
    ],
    BusinessQuestion.DISTANCE_TIME_TRADEOFF: ["daily_route_optimization"],
    BusinessQuestion.UNCLASSIFIED: [],
}


@dataclass
class BusinessDecisionIntent:
    """Pure diagnostic output: maps user question to decision level + required capabilities."""
    primary_decision_level: BusinessQuestion
    secondary_decision_levels: List[BusinessQuestion] = field(default_factory=list)
    confidence: float = 0.0
    required_objects: List[str] = field(default_factory=list)   # ReferenceObject ids
    hard_constraints_to_confirm: List[str] = field(default_factory=list)
    candidate_capabilities: List[str] = field(default_factory=list)
    capability_availability: Dict[str, str] = field(default_factory=dict)
    operational_schemas: Dict[str, JSONSchema] = field(default_factory=dict)
    missing_inputs: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_reason: str = ""
    downstream_advice: str = ""


@dataclass
class ValidationReport:
    """ValidationReport emitted by the DecisionGate (per v1.1 §9 Phase 3)."""
    is_valid: bool
    gate_passed: bool
    fold_violation_count: int = 0
    capability_honesty: Dict[str, str] = field(default_factory=dict)
    lifecycle_state_progression: str = "EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN"
    blocking_issues: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)


class SVDEOntologyAdapter:
    """Bridge adapter: SVDE DecisionRequest → prism-ontology → SVDE DecisionGate output."""

    def __init__(self, store: ReferenceOntologyStore, operational_compiler: OperationalCompiler):
        self.store = store
        self.compiler = operational_compiler
        self.intent_router = IntentRouter()

    def diagnose(self, question: str) -> BusinessDecisionIntent:
        """Call prism-ontology IntentRouter, translate to SVDE BusinessDecisionIntent."""
        diag: IntentDiagnostic = self.intent_router.route(question)
        primary = self._map_level(diag.primary_decision_level)
        secondary = [self._map_level(l) for l in diag.secondary_decision_levels]
        candidate_caps = QUESTION_TO_CAPABILITIES.get(primary, [])
        required_objects = self._extract_required_objects(primary)
        hard_constraints = self._extract_hard_constraints(primary)
        # Determine capability availability status
        cap_availability = self._check_capability_availability(candidate_caps)
        operational_schemas = {
            obj_id: self.compiler.compile_object_schema(self.store.get_object(obj_id))
            for obj_id in required_objects if self.store.get_object(obj_id)
        }
        return BusinessDecisionIntent(
            primary_decision_level=primary,
            secondary_decision_levels=secondary,
            confidence=diag.confidence,
            required_objects=required_objects,
            hard_constraints_to_confirm=hard_constraints,
            candidate_capabilities=candidate_caps,
            capability_availability=cap_availability,
            operational_schemas=operational_schemas,
            missing_inputs=self._infer_missing_inputs(primary, required_objects),
            needs_clarification=diag.needs_clarification,
            clarification_reason=diag.refusal_reason,
            downstream_advice=diag.downstream_advice,
        )

    def validate(self, request_mapping: Dict[str, str]) -> ValidationReport:
        """Run zero-fold audit on the provided adapter mapping."""
        from prism_ontology.compiler.mapping_manifest import DomainAdapterMappingManifest
        manifest = DomainAdapterMappingManifest(self.store)
        report = manifest.audit(request_mapping)
        blocking = [v["object_id"] for v in report["violations"]]
        return ValidationReport(
            is_valid=report["is_clean"],
            gate_passed=report["is_clean"],
            fold_violation_count=report["fold_violation_count"],
            capability_honesty=cap_availability(),
            blocking_issues=blocking,
            evidence_sources=self._all_evidence_sources(),
        )

    # ---- Internal helpers ----

    def _map_level(self, prism_level: str) -> BusinessQuestion:
        if prism_level == "DAILY_ROUTE_SEQUENCING":
            return BusinessQuestion.DAILY_ROUTE_SEQUENCE
        if prism_level == "PERIODIC_COVERAGE":
            return BusinessQuestion.PERIODIC_COVERAGE
        if prism_level == "TERRITORY_ALIGNMENT":
            return BusinessQuestion.TERRITORY_ALIGNMENT
        if prism_level == "ROLLING_REPLAN":
            return BusinessQuestion.ROLLING_REPLAN
        if prism_level == "DISTANCE_TIME_TRADEOFF":
            return BusinessQuestion.DISTANCE_TIME_TRADEOFF
        return BusinessQuestion.UNCLASSIFIED

    def _extract_required_objects(self, level: BusinessQuestion) -> List[str]:
        if level == BusinessQuestion.TERRITORY_ALIGNMENT:
            return ["Customer", "OwnershipPolicy", "EligibilityPolicy", "Resource"]
        if level == BusinessQuestion.PERIODIC_COVERAGE:
            return ["VisitDemand", "CadenceSpec", "PlanningHorizon", "Commitment"]
        if level == BusinessQuestion.DAILY_ROUTE_SEQUENCE:
            return ["PlannedVisit", "TravelCostMatrix", "ResourceDayProfile", "Commitment"]
        if level == BusinessQuestion.ROLLING_REPLAN:
            return ["Commitment", "ActualVisit", "VisitDemand"]
        if level == BusinessQuestion.DISTANCE_TIME_TRADEOFF:
            return ["RoutePlan", "ObjectiveProfile"]
        return []

    def _extract_hard_constraints(self, level: BusinessQuestion) -> List[str]:
        if level == BusinessQuestion.TERRITORY_ALIGNMENT:
            return ["locked_ownership_preserved", "every_customer_assigned_exactly_once"]
        if level == BusinessQuestion.PERIODIC_COVERAGE:
            return ["existing_locked_commitments_must_be_preserved", "frequency_compliance"]
        if level == BusinessQuestion.DAILY_ROUTE_SEQUENCE:
            return ["customer_set_must_be_FIXED", "every_customer_served_within_time_window"]
        if level == BusinessQuestion.ROLLING_REPLAN:
            return ["existing_commitments_must_be_preserved"]
        if level == BusinessQuestion.DISTANCE_TIME_TRADEOFF:
            return ["forbid_relaxing_locked"]
        return []

    def _check_capability_availability(self, candidate_caps: List[str]) -> Dict[str, str]:
        # Per v1.1 honesty gate: all Sales Visit capabilities are PLANNED (not implemented)
        return {cap: "PLANNED" for cap in candidate_caps}

    def _infer_missing_inputs(self, level: BusinessQuestion, required: List[str]) -> List[str]:
        return [f"reference_object:{obj}" for obj in required]

    def _all_evidence_sources(self) -> List[str]:
        sources = set()
        for obj in self.store.objects.values():
            for s in obj.evidence_sources:
                sources.add(s)
        return sorted(sources)

    def dispatch_planning_intent(
        self,
        intent: Any,
        world_state: Any
    ) -> Dict[str, Any]:
        """
        Phase 3: Dispatch PlanningIntent against WorldState runtime snapshot.
        Extracts un-filtered Customer Universe and generates Solver-ready Mathematical Payload.
        """
        rep_id = getattr(intent, "target_rep_id", "")
        rep_universe = world_state.get_rep_universe(rep_id)
        if not rep_universe:
            raise ValueError(f"No assigned Customer Universe found in WorldState for rep: {rep_id}")
            
        working_days = getattr(intent, "working_days", ())
        same_weekday = getattr(intent, "same_weekday_required", True)
        
        # Build strict pattern space P_i for each assigned store
        pattern_space = {}
        for code, store in rep_universe.items():
            freq = store.planned_frequency
            p_list = []
            if freq == 4: # Weekly
                for k in range(5):
                    p_list.append([(w, k) for w in range(4)])
            elif freq == 3: # 3 times / month
                for k in range(5):
                    for skip_w in range(4):
                        p_list.append([(w, k) for w in range(4) if w != skip_w])
            elif freq == 2: # Bi-weekly
                for k in range(5):
                    p_list.append([(0, k), (2, k)])
                    p_list.append([(1, k), (3, k)])
            elif freq == 1: # Monthly
                for w in range(4):
                    for k in range(5):
                        p_list.append([(w, k)])
            pattern_space[code] = p_list
            
        return {
            "intent_id": getattr(intent, "intent_id", ""),
            "rep_id": rep_id,
            "assigned_stores_count": len(rep_universe),
            "assigned_stores": rep_universe,
            "pattern_space": pattern_space,
            "working_days_count": len(working_days),
            "working_days": working_days,
            "period_label": getattr(intent, "target_horizon_label", "CURRENT_PERIOD"),
            "depot_coordinate": world_state.resources[rep_id].home_depot_coord if rep_id in world_state.resources else world_state.policies.chongchuan_depot,
            "dispatch_status": "READY_FOR_SOLVER"
        }


# Capability availability helper
def cap_availability() -> Dict[str, str]:
    return {
        "territory_alignment": "PLANNED",
        "periodic_visit_planning": "PLANNED",
        "daily_route_optimization": "PLANNED",
    }
