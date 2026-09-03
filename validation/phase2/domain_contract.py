"""
domain_contract.py — A03 Domain-Contract-v1.0.1 faithful transcription (validation subset)
Phase 2 discipline: PURE domain objects. No solver, no math model, no optimization.
Source of truth: docs/sales_visit_domain_research/03_A03_domain_ontology_v1_0_1.md
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional


# ---------------- Enums ----------------
class FrequencySemantics(str, Enum):
    EXACT = "EXACT"; RANGE = "RANGE"; TARGET = "TARGET"

class DemandReason(str, Enum):
    COVERAGE_POLICY = "COVERAGE_POLICY"; CONTRACT_SLA = "CONTRACT_SLA"
    SALES_SIGNAL = "SALES_SIGNAL"; OUT_OF_STOCK = "OUT_OF_STOCK"
    CAMPAIGN = "CAMPAIGN"; CUSTOMER_REQUEST = "CUSTOMER_REQUEST"

class FulfillmentClass(str, Enum):
    REQUIRED = "REQUIRED"; COMMITTED = "COMMITTED"; OPTIONAL = "OPTIONAL"

class RequirementStrength(str, Enum):
    HARD = "HARD"; SOFT = "SOFT"; ADVISORY = "ADVISORY"

class RequirementAuthority(str, Enum):
    LEGAL = "LEGAL"; CONTRACT = "CONTRACT"; COMPANY_POLICY = "COMPANY_POLICY"
    MANAGER_RULE = "MANAGER_RULE"; USER_PREFERENCE = "USER_PREFERENCE"

class LifecycleState(str, Enum):
    PROPOSED = "PROPOSED"; PLANNED = "PLANNED"; COMMITTED = "COMMITTED"
    IN_PROGRESS = "IN_PROGRESS"; COMPLETED = "COMPLETED"; MISSED = "MISSED"; CANCELLED = "CANCELLED"

class CommitmentLock(str, Enum):
    FREE = "FREE"; RESOURCE_LOCKED = "RESOURCE_LOCKED"; DAY_LOCKED = "DAY_LOCKED"
    SEQUENCE_LOCKED = "SEQUENCE_LOCKED"; COMPLETELY_LOCKED = "COMPLETELY_LOCKED"

class StartEndPolicy(str, Enum):
    BASE_DEPOT = "BASE_DEPOT"; HOME_LOCATION = "HOME_LOCATION"; DYNAMIC_DAILY = "DYNAMIC_DAILY"

class ParameterEvidenceType(str, Enum):
    MEASURED = "MEASURED"; CALIBRATED = "CALIBRATED"; EMPIRICAL = "EMPIRICAL"
    EXTERNAL_REFERENCE = "EXTERNAL_REFERENCE"; DEFAULT = "DEFAULT"


# ---------------- Time value objects ----------------
@dataclass(frozen=True)
class DateRange:
    start_date: date; end_date: date
    def contains(self, d: date) -> bool: return self.start_date <= d <= self.end_date

@dataclass(frozen=True)
class TimeWindow:
    start_time: str; end_time: str  # "08:00"

@dataclass(frozen=True)
class WorkingCalendar:
    working_dates: tuple[date, ...]
    holiday_dates: tuple[date, ...] = ()
    def is_working_day(self, d: date) -> bool:
        return d in self.working_dates and d not in self.holiday_dates
    def weekday(self, d: date) -> int: return d.weekday()  # Mon=0


# ---------------- Target plane ----------------
@dataclass(frozen=True)
class GeoLocation:
    latitude: float; longitude: float; formatted_address: str = ""

@dataclass(frozen=True)
class WeeklyAvailabilityRule:
    weekday_to_time_windows: dict[int, tuple[TimeWindow, ...]]
    date_exceptions: dict[date, tuple[TimeWindow, ...]] = field(default_factory=dict)
    blackout_dates: tuple[date, ...] = ()
    def is_available(self, d: date) -> bool:
        if d in self.blackout_dates: return False
        if d in self.date_exceptions: return True
        return self.weekday_to_time_windows.get(d.weekday(), ()) != ()

@dataclass(frozen=True)
class TargetAvailability:
    weekly_rule: WeeklyAvailabilityRule

@dataclass(frozen=True)
class VisitTarget:
    target_id: str; code: str; name: str
    location: GeoLocation; territory_id: str
    availability: TargetAvailability
    business_attributes: dict


# ---------------- Resource plane ----------------
@dataclass(frozen=True)
class ResourceDayProfile:
    service_date: date
    working_windows: tuple[TimeWindow, ...]
    capacity_min: float
    day_start_location: GeoLocation; day_end_location: GeoLocation
    is_absent: bool = False

@dataclass(frozen=True)
class ResourceAvailability:
    default_policy: StartEndPolicy
    default_start: GeoLocation; default_end: GeoLocation
    date_profiles: dict[date, ResourceDayProfile] = field(default_factory=dict)
    def get_day_profile(self, d: date, calendar: WorkingCalendar, base_capacity: float) -> ResourceDayProfile:
        p = self.date_profiles.get(d)
        if p is not None: return p
        working = () if not calendar.is_working_day(d) else (TimeWindow("08:00", "18:00"),)
        return ResourceDayProfile(d, working, base_capacity if working else 0.0,
                                  self.default_start, self.default_end, is_absent=not working)

@dataclass(frozen=True)
class SalesResource:
    resource_id: str; code: str; name: str
    availability: ResourceAvailability
    max_daily_targets: int
    territory_tags: tuple[str, ...]
    base_capacity_min: float = 480.0
    qualifications: dict = field(default_factory=dict)


# ---------------- Policy plane ----------------
@dataclass(frozen=True)
class PolicyScope:
    scope_conditions: list[dict]  # [{"field":"segment","op":"==","value":"A"}]
    def matches(self, t: VisitTarget) -> bool:
        for c in self.scope_conditions:
            v = t.business_attributes.get(c["field"])
            if c["op"] == "==" and v != c["value"]: return False
        return True

@dataclass(frozen=True)
class FrequencySpec:
    semantics: FrequencySemantics
    target_occurrences: int; reference_period_days: int
    min_occurrences: int; max_occurrences: int

@dataclass(frozen=True)
class CadenceSpec:
    min_spacing_days: int; max_spacing_days: int

@dataclass(frozen=True)
class VisitPolicy:
    policy_id: str; scope: PolicyScope
    frequency_spec: FrequencySpec; cadence_spec: CadenceSpec
    standard_service_duration_min: float


# ---------------- Requirement & parameter governance ----------------
@dataclass(frozen=True)
class ParameterDescriptor:
    parameter_id: str; name: str
    evidence_type: ParameterEvidenceType
    source_description: str; verified_at: date
    value: object = None

@dataclass(frozen=True)
class ParameterRegistry:
    descriptors: dict[str, ParameterDescriptor]
    def get(self, pid: str) -> ParameterDescriptor:
        if pid not in self.descriptors:
            raise KeyError(f"missing registered parameter: {pid}")
        return self.descriptors[pid]

@dataclass(frozen=True)
class DeferralPolicy:
    policy_id: str
    deferrable: bool; max_deferral_days: int
    escalation_rule: str; unmet_consequence: str

@dataclass(frozen=True)
class BusinessRequirement:
    requirement_id: str; statement: str
    strength: RequirementStrength; authority: RequirementAuthority
    applies_to: PolicyScope
    parameter_refs: tuple[str, ...] = ()
    source_ref: str = ""
    exception_handling_policy_ref: Optional[str] = None  # DCR-SA-001-R

@dataclass(frozen=True)
class RequirementRegistry:
    requirements: dict[str, BusinessRequirement]
    def get(self, rid: str) -> BusinessRequirement:
        if rid not in self.requirements:
            raise KeyError(f"missing requirement: {rid}")
        return self.requirements[rid]


# ---------------- Demand / occurrence plane ----------------
@dataclass(frozen=True)
class VisitDemand:
    demand_id: str; target_id: str
    reason: DemandReason; fulfillment_class: FulfillmentClass
    expected_duration_min: float
    requested_date_range: DateRange
    metadata: dict = field(default_factory=dict)  # policy_ref = traceability pointer ONLY (G-07a)

@dataclass(frozen=True)
class VisitOccurrence:
    occurrence_id: str; demand_id: str; target_id: str
    occurrence_index: int
    eligible_date_range: DateRange
    expected_service_min: float

@dataclass(frozen=True)
class ExecutionHistory:
    completed_visits: tuple[tuple[str, date], ...] = ()
    missed_visits: tuple[tuple[str, date], ...] = ()
    def get_last_visit(self, target_id: str) -> Optional[date]:
        ds = [d for t, d in self.completed_visits if t == target_id]
        return max(ds) if ds else None

@dataclass(frozen=True)
class MergePolicy:
    allow_same_day_consolidation: bool = True
    max_consolidated_service_min: float = 480.0
    def consolidate(self, occurrences: list[VisitOccurrence], demands: dict[str, VisitDemand],
                    policy: VisitPolicy) -> list[list[VisitOccurrence]]:
        by_target: dict[str, list[VisitOccurrence]] = {}
        for o in occurrences: by_target.setdefault(o.target_id, []).append(o)
        groups = []
        for t, occs in by_target.items():
            occs.sort(key=lambda o: (o.demand_id, o.occurrence_index))
            if self.allow_same_day_consolidation:
                svc = sum(o.expected_service_min for o in occs)
                # same-policy baseline+stretch → ONE physical visit of standard duration (G-04)
                groups.append(occs if svc <= self.max_consolidated_service_min else
                              [[o] for o in occs])
            else:
                groups.extend([[o] for o in occs])
        return groups

@dataclass(frozen=True)
class VisitCandidate:
    candidate_id: str; target: VisitTarget
    source_occurrences: tuple[VisitOccurrence, ...]
    combined_reasons: tuple[DemandReason, ...]
    priority_score: float
    fulfillment_class: FulfillmentClass
    eligible_resource_ids: tuple[str, ...]
    consolidated_service_min: float


# ---------------- Ownership three axes ----------------
@dataclass(frozen=True)
class OwnershipPolicy:
    target_id: str; primary_resource_ids: tuple[str, ...]
    allow_shared_pool: bool = False

@dataclass(frozen=True)
class SubstitutionPolicy:
    allow_backup: bool; backup_resource_ids: tuple[str, ...] = ()
    conditions: dict = field(default_factory=dict)

@dataclass(frozen=True)
class EligibilityPolicy:
    required_qualifications: dict = field(default_factory=dict)
    required_territory_tags: dict = field(default_factory=dict)

def derive_eligible_resources(target_id, ownership: OwnershipPolicy, sub: SubstitutionPolicy,
                              elig: EligibilityPolicy, resources: list[SalesResource]) -> tuple[str, ...]:
    ids = list(ownership.primary_resource_ids)
    if ownership.allow_shared_pool:
        ids += [r.resource_id for r in resources if r.resource_id not in ids]
    if sub.allow_backup:
        ids += [r for r in sub.backup_resource_ids if r not in ids]
    out = []
    for rid in ids:
        r = next((x for x in resources if x.resource_id == rid), None)
        if r is None: continue
        if all(r.qualifications.get(k) == v for k, v in elig.required_qualifications.items()):
            if all(tt in r.territory_tags for tt in elig.required_territory_tags.get("any", ())):
                out.append(rid)
    return tuple(dict.fromkeys(out))


# ---------------- Commitment / plan plane ----------------
@dataclass(frozen=True)
class ExistingCommitment:
    commitment_id: str; target_id: str; resource_id: str
    committed_date: date; committed_time_window: TimeWindow
    lock_level: CommitmentLock

@dataclass(frozen=True)
class PlanningPolicy:
    mode: str; freeze_days_count: int; max_reassignment_ratio: float

class ObjectiveProfile(str, Enum):
    VALUE_IMPACT_FIRST = "VALUE_IMPACT_FIRST"; MAX_THROUGHPUT = "MAX_THROUGHPUT"
    BALANCED_STABILITY = "BALANCED_STABILITY"; COST_EFFICIENCY_FIRST = "COST_EFFICIENCY_FIRST"

@dataclass(frozen=True)
class ObjectivePolicy:
    profile: ObjectiveProfile; profile_weights: dict = field(default_factory=dict)

@dataclass(frozen=True)
class PlanningHorizon:
    date_range: DateRange; calendar: WorkingCalendar
    working_days_count: int

@dataclass(frozen=True)
class SalesVisitPlanningScenario:
    scenario_id: str
    horizon: PlanningHorizon
    planning_policy: PlanningPolicy; objective_policy: ObjectivePolicy
    visit_targets: list[VisitTarget]; sales_resources: list[SalesResource]
    visit_policies: list[VisitPolicy]
    ownership_policies: list[OwnershipPolicy]
    substitution_policies: list[SubstitutionPolicy]
    eligibility_policies: list[EligibilityPolicy]
    existing_commitments: list[ExistingCommitment]
    execution_history: ExecutionHistory
    deferral_policies: list[DeferralPolicy]
    requirement_registry: RequirementRegistry
    parameter_registry: ParameterRegistry
    def deferral_registry(self) -> dict:
        return {d.policy_id: d for d in self.deferral_policies}
