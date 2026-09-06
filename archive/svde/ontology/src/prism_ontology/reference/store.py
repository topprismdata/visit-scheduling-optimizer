"""Sales Visit Reference Ontology — v0.3 FROZEN objects loaded per Phase 1.

Per v1.1 §9 Phase 1: Load Customer, VisitDemand, VisitOccurrence, PlannedVisit,
ActualVisit, PlanningHorizon, CadenceSpec, ExistingCommitment, three-layer decisions,
and ONT-1 through ONT-8 anti-collapse tests.

All objects carry source provenance (v1.1 §6.1 rule 1).
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class ObjectLayer(str, Enum):
    IDENTITY = "Identity"
    POLICY = "Policy"
    EVENT = "Event"
    MEASUREMENT = "Measurement"
    PLAN = "Plan"


class DecisionLevel(str, Enum):
    TERRITORY_ALIGNMENT = "TERRITORY_ALIGNMENT"
    PERIODIC_COVERAGE = "PERIODIC_COVERAGE"
    DAILY_ROUTE_SEQUENCING = "DAILY_ROUTE_SEQUENCING"
    ROLLING_REPLAN = "ROLLING_REPLAN"
    DISTANCE_TIME_TRADEOFF = "DISTANCE_TIME_TRADEOFF"


@dataclass
class ReferenceObject:
    """A single business object in the reference ontology."""
    object_id: str
    layer: ObjectLayer
    definition: str
    key_attributes: List[str]
    forbidden_folds: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)  # source_id refs
    lifecycle_state: str = "FROZEN"
    frozen_at: str = "2026-08-24"
    frozen_by: str = "Business Owner + Project Architect"


@dataclass
class DecisionLayerSpec:
    """Input/output contract for a decision layer."""
    level: DecisionLevel
    input_objects: List[str]
    output_type: str
    hard_constraints: List[str] = field(default_factory=list)
    forbidden_overreach: List[str] = field(default_factory=list)


@dataclass
class PriorityRule:
    """Machine-verifiable objective priority rule."""
    rule_id: str
    statement: str
    verification_method: str
    evidence_source: str


# ============================================================================
# v0.3 FROZEN Business Objects (19 objects, 5 layers)
# ============================================================================

FROZEN_OBJECTS: List[ReferenceObject] = [
    # --- Identity Layer ---
    ReferenceObject(
        object_id="Customer",
        layer=ObjectLayer.IDENTITY,
        definition="被服务的业务主体（零售/医疗客户）",
        key_attributes=["id", "tier", "commercial_value", "location", "required_cadence_class"],
        forbidden_folds=["COMMITTED_TASK", "RouteStop"],
        evidence_sources=["REF-011", "REF-018", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="Resource",
        layer=ObjectLayer.IDENTITY,
        definition="销售代表（基线容量定义）",
        key_attributes=["id", "rep_id", "type", "base_location", "weekly_capacity_minutes"],
        forbidden_folds=["ResourceDayProfile"],
        evidence_sources=["REF-002", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    # --- Policy Layer ---
    ReferenceObject(
        object_id="VisitPolicy",
        layer=ObjectLayer.POLICY,
        definition="客户拜访政策（频次/星期/时段/间隔）",
        key_attributes=["id", "customer_id", "cadence_spec_id", "weekly_availability", "time_window", "min_interval_days", "max_interval_days"],
        forbidden_folds=["COMMITTED_TASK"],
        evidence_sources=["REF-001", "REF-013", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="CadenceSpec",
        layer=ObjectLayer.POLICY,
        definition="拜访频次规格",
        key_attributes=["id", "customer_id", "visits_per_week", "visits_per_month", "tolerance_days"],
        forbidden_folds=["RouteStop"],
        evidence_sources=["REF-001", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="OwnershipPolicy",
        layer=ObjectLayer.POLICY,
        definition="客户-代表归属政策",
        key_attributes=["customer_id", "rep_id", "is_locked", "tenure_months"],
        forbidden_folds=["soft_preference"],
        evidence_sources=["REF-011", "REF-012", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="EligibilityPolicy",
        layer=ObjectLayer.POLICY,
        definition="代表资质筛选政策",
        key_attributes=["rep_id", "allowed_customer_tiers", "excluded_customer_ids"],
        forbidden_folds=["OwnershipPolicy"],
        evidence_sources=["REF-013", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="SubstitutionPolicy",
        layer=ObjectLayer.POLICY,
        definition="替补代表关系政策",
        key_attributes=["customer_id", "primary_rep_id", "substitute_rep_ids"],
        forbidden_folds=["OwnershipPolicy"],
        evidence_sources=["REF-011", "REF-013", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="ObjectiveProfile",
        layer=ObjectLayer.POLICY,
        definition="分层目标与权衡政策",
        key_attributes=["priority_levels", "distance_metric", "customer_facing_time", "stability_penalty", "forbidden_tradeoffs", "deferral_cost"],
        forbidden_folds=["SolverParameter"],
        evidence_sources=["REF-003", "REF-004", "REF-019", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="DeferralPolicy",
        layer=ObjectLayer.POLICY,
        definition="延期政策（可选业务代价）",
        key_attributes=["customer_id", "allowed_deferral_days", "requires_approval", "business_cost_per_day"],
        forbidden_folds=["no_deferral_hard_constraint"],
        evidence_sources=["REF-001", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    # --- Event Layer ---
    ReferenceObject(
        object_id="VisitDemand",
        layer=ObjectLayer.EVENT,
        definition="业务上需要一次拜访（未排期）",
        key_attributes=["id", "customer_id", "policy_id", "requested_window"],
        forbidden_folds=["COMMITTED_TASK.demand", "PlannedVisit"],
        evidence_sources=["REF-001", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="PlannedVisit",
        layer=ObjectLayer.EVENT,
        definition="已安排日期/代表/时段的计划拜访",
        key_attributes=["id", "customer_id", "date", "rep_id", "time_window", "is_locked", "frequency_compliance", "status"],
        forbidden_folds=["ActualVisit", "policy", "RouteStop"],
        evidence_sources=["REF-002", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="ActualVisit",
        layer=ObjectLayer.EVENT,
        definition="实际执行/打卡事件",
        key_attributes=["id", "customer_id", "date", "rep_id", "actual_arrival", "actual_departure", "status"],
        forbidden_folds=["PlannedVisit"],
        evidence_sources=["REF-002", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="Commitment",
        layer=ObjectLayer.EVENT,
        definition="具体日期/时段/代表的承诺实例（不可降级）",
        key_attributes=["id", "customer_id", "rep_id", "date", "time_window", "lifecycle_state", "source"],
        forbidden_folds=["soft_preference"],
        evidence_sources=["REF-002", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="TimeDeviation",
        layer=ObjectLayer.EVENT,
        definition="实际vs计划时间偏差",
        key_attributes=["id", "planned_visit_id", "actual_visit_id", "deviation_minutes"],
        forbidden_folds=["metric_history_only"],
        evidence_sources=["REF-005", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="Product",
        layer=ObjectLayer.IDENTITY,
        definition="拜访涉及的SKU/商品（GAP-1批准）",
        key_attributes=["id", "name", "sku_code", "category"],
        forbidden_folds=["Customer"],
        evidence_sources=["GAP-1-BUSINESS-APPROVED", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    # --- Measurement Layer ---
    ReferenceObject(
        object_id="TravelCostMatrix",
        layer=ObjectLayer.MEASUREMENT,
        definition="路网成本输入事实",
        key_attributes=["source", "matrix", "captured_at", "confidence"],
        forbidden_folds=["optimization_target", "straight_line_default"],
        evidence_sources=["REF-016", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="TravelCostEstimate",
        layer=ObjectLayer.MEASUREMENT,
        definition="对某条路线的成本评估结果",
        key_attributes=["route_id", "total_distance_km", "total_in_transit_min", "model_used"],
        forbidden_folds=["fact_input"],
        evidence_sources=["REF-016", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    # --- Plan Layer ---
    ReferenceObject(
        object_id="PlanningHorizon",
        layer=ObjectLayer.PLAN,
        definition="规划周期（4周/20工作日）",
        key_attributes=["id", "start_date", "end_date", "working_days", "timezone", "planning_cycle"],
        forbidden_folds=["implicit"],
        evidence_sources=["REF-005", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="ResourceDayProfile",
        layer=ObjectLayer.PLAN,
        definition="代表日容量快照",
        key_attributes=["rep_id", "date", "total_capacity_minutes", "committed_minutes", "available_minutes"],
        forbidden_folds=["Resource"],
        evidence_sources=["REF-002", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="RouteStop",
        layer=ObjectLayer.PLAN,
        definition="路线中的物理顺序节点",
        key_attributes=["id", "planned_visit_id", "planned_arrival", "service_duration", "sequence_idx"],
        forbidden_folds=["Customer", "master_data"],
        evidence_sources=["REF-005", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="RoutePlan",
        layer=ObjectLayer.PLAN,
        definition="固定拜访集合的排序计划",
        key_attributes=["id", "target_date", "rep_id", "sequence", "depot_id", "total_distance_km", "total_in_transit_min"],
        forbidden_folds=["DecisionArtifact.decision", "PeriodPlan"],
        evidence_sources=["REF-005", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    # ====================================================================
    # DCR v2.0 Extensions: 5 Core Business Objects (Woodburn, Zoltners, etc.)
    # ====================================================================
    ReferenceObject(
        object_id="AccountHierarchy",
        layer=ObjectLayer.IDENTITY,
        definition="大客户组织与渠道层级 (Woodburn 2002/2014): 表达零售连锁总部 (NKA/RKA) 与子店的组织层级，子店继承总部统一协议。",
        key_attributes=["account_id", "account_name", "channel_tier", "parent_account_ref", "central_agreement_ref"],
        forbidden_folds=["Customer", "ChannelHierarchy", "SalesIncentive"],
        evidence_sources=["REF-006", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="ProductLineScope",
        layer=ObjectLayer.POLICY,
        definition="多产品线与品牌组合 (Johnston & Marshall 2016, Kotler 2016): 区分拜访中覆盖的不同战略品牌线 (如皇家美素爆品 vs 源悦新品)。",
        key_attributes=["brand_id", "brand_name", "strategic_role", "default_action_refs"],
        forbidden_folds=["VisitDemand", "BrandMarketingCampaign"],
        evidence_sources=["REF-008", "REF-010", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="SupplyNodeLink",
        layer=ObjectLayer.IDENTITY,
        definition="供应链大仓供货协同 (Shanahan 2007/2019): 表达 18 个专属大仓与门店供货到货时序联动，协同代表巡店。",
        key_attributes=["dc_id", "dc_name", "served_ka_names", "fixed_delivery_weekdays", "visit_lead_time_hours"],
        forbidden_folds=["Customer", "WarehouseTopology", "FleetRouting"],
        evidence_sources=["REF-009", "REF-PTV-001", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="MerchandisingCompliance",
        layer=ObjectLayer.MEASUREMENT,
        definition="合同陈列对赌量化履约 (Anderson & Stern 2004, Coughlan 2014): 对端架/地堆陈列资产进行目标数、达标数与达成率量化核销。",
        key_attributes=["contract_target_units", "actual_compliant_units", "compliance_ratio", "has_oos_risk", "audit_timestamp"],
        forbidden_folds=["ActualVisit", "FulfillmentClass", "FinancialIncentive"],
        evidence_sources=["REF-011", "GAP-6-PERMANENTLY-CLOSED"],
    ),
    ReferenceObject(
        object_id="InStoreActionTaxonomy",
        layer=ObjectLayer.POLICY,
        definition="现场五大核心动作分类学 (Zoltners et al. 2006): 解构在店时长黑盒，将作业分解为开新派样/缺货补货/效期防损/陈列核销/店长订单。",
        key_attributes=["action_type", "estimated_duration_min", "is_mandatory", "brand_line_ref"],
        forbidden_folds=["RouteStop", "TaskTemplate", "AlgorithmStep"],
        evidence_sources=["REF-007", "GAP-6-PERMANENTLY-CLOSED"],
    ),
]

# ============================================================================
# v0.3 FROZEN Decision Layers (5 layers)
# ============================================================================

FROZEN_DECISION_LAYERS: List[DecisionLayerSpec] = [
    DecisionLayerSpec(
        level=DecisionLevel.TERRITORY_ALIGNMENT,
        input_objects=["Customer", "OwnershipPolicy", "EligibilityPolicy", "Resource"],
        output_type="TerritoryAssignmentPlan",
        hard_constraints=[
            "every_customer_assigned_exactly_once",
            "rep_weekly_load_must_not_exceed_capacity",
            "locked_ownership_must_be_preserved",
        ],
        forbidden_overreach=[
            "改变拜访频次",
            "改变单日路线",
        ],
    ),
    DecisionLayerSpec(
        level=DecisionLevel.PERIODIC_COVERAGE,
        input_objects=["VisitDemand", "CadenceSpec", "PlanningHorizon", "Commitment"],
        output_type="PeriodicVisitPlan",
        hard_constraints=[
            "each_customer_must_be_visited_at_cadence",
            "visits_must_occur_on_allowed_weekdays_and_time_windows",
            "existing_locked_commitments_must_be_preserved",
            "rep_daily_workload_must_not_exceed_daily_capacity",
        ],
        forbidden_overreach=[
            "改变单日路线顺序",
            "改变具体时段到分钟",
        ],
    ),
    DecisionLayerSpec(
        level=DecisionLevel.DAILY_ROUTE_SEQUENCING,
        input_objects=["PlannedVisit", "TravelCostMatrix", "ResourceDayProfile", "Commitment"],
        output_type="DailyRoutePlan",
        hard_constraints=[
            "customer_set_must_be_FIXED",
            "locked_visit_order_must_be_preserved",
            "every_customer_served_within_time_window",
            "route_must_start_and_end_at_depot",
            "max_daily_work_minutes_must_not_be_exceeded",
        ],
        forbidden_overreach=[
            "改变发生项集合",
            "改变频次",
            "改变代表",
            "取消锁定项",
        ],
    ),
    DecisionLayerSpec(
        level=DecisionLevel.ROLLING_REPLAN,
        input_objects=["Commitment", "ExecutionSignal", "VisitDemand"],
        output_type="RollingReplanProposal",
        hard_constraints=[
            "existing_commitments_must_be_preserved",
        ],
        forbidden_overreach=[
            "取消已批准延期",
        ],
    ),
    DecisionLayerSpec(
        level=DecisionLevel.DISTANCE_TIME_TRADEOFF,
        input_objects=["RoutePlan", "ObjectiveProfile"],
        output_type="TradeoffAssessment",
        hard_constraints=[
            "forbid_relaxing_locked",
        ],
        forbidden_overreach=[
            "任何降频",
            "改锁定",
            "改归属",
        ],
    ),
]

# ============================================================================
# v0.3 FROZEN Priority Rules (5 rules)
# ============================================================================

FROZEN_PRIORITY_RULES: List[PriorityRule] = [
    PriorityRule(
        rule_id="PR-001",
        statement="DistanceMinimization.subordinateTo(CoverageCompliance)",
        verification_method="coverage_compliance_pct == 100% required before reporting distance reduction",
        evidence_source="REF-001",
    ),
    PriorityRule(
        rule_id="PR-002",
        statement="DistanceMinimization.mustNotOverride(CommitmentLock)",
        verification_method="commitment.lifecycle_state == LOCKED must have time window preserved",
        evidence_source="REF-002",
    ),
    PriorityRule(
        rule_id="PR-003",
        statement="DistanceMinimization.cannotReduce(CadenceSpec.min_interval_days)",
        verification_method="same customer adjacent visits interval >= min_interval_days",
        evidence_source="REF-001",
    ),
    PriorityRule(
        rule_id="PR-004",
        statement="DailyRouteOptimization.requires(FixedVisitSet)",
        verification_method="input RouteStop[] set must not be modified",
        evidence_source="REF-005",
    ),
    PriorityRule(
        rule_id="PR-005",
        statement="PeriodicVisitPlanning.requires(PlanningHorizon)",
        verification_method="horizon.start_date <= visit.date <= horizon.end_date",
        evidence_source="REF-005",
    ),
]

# ============================================================================
# v0.3 FROZEN Anti-Promotion Rules (10 rules)
# ============================================================================

FROZEN_ANTI_PROMOTION_RULES: List[Dict[str, str]] = [
    {"rule": "Customer must NOT be folded into Task or RouteStop", "source": "v0.3 §3"},
    {"rule": "PlannedVisit / ActualVisit must NOT be folded into RouteStop", "source": "v0.3 §3"},
    {"rule": "RoutePlan must NOT be folded into DecisionArtifact.decision", "source": "v0.3 §3"},
    {"rule": "VisitPolicy must NOT be folded into COMMITTED_TASK", "source": "v0.3 §3"},
    {"rule": "Commitment must NOT be downgraded to soft preference", "source": "v0.3 §3"},
    {"rule": "BusinessPolicy must NOT be treated as SolverParameter", "source": "v0.3 §3"},
    {"rule": "Algorithm concepts (Column Generation, LNS, Tabu, Simplex, Big-M) must NOT enter business ontology", "source": "v0.3 §3"},
    {"rule": "Channel hierarchy (Kotler 4P) must NOT enter sales visit ontology", "source": "v0.3 §3"},
    {"rule": "Sales force incentive must NOT enter sales visit ontology", "source": "v0.3 §3"},
    {"rule": "Any SOP-related object (SOPPolicy, CustomerSOPBinding, CustomerOpRequirement) permanently rejected", "source": "GAP-6-PERMANENTLY-CLOSED"},
]


class ReferenceOntologyStore:
    """In-memory store for the v0.3 frozen reference ontology."""

    def __init__(self):
        self.objects: Dict[str, ReferenceObject] = {o.object_id: o for o in FROZEN_OBJECTS}
        self.decision_layers: Dict[str, DecisionLayerSpec] = {
            d.level.value: d for d in FROZEN_DECISION_LAYERS
        }
        self.priority_rules: List[PriorityRule] = list(FROZEN_PRIORITY_RULES)
        self.anti_promotion_rules: List[Dict[str, str]] = list(FROZEN_ANTI_PROMOTION_RULES)

    def get_object(self, object_id: str) -> Optional[ReferenceObject]:
        return self.objects.get(object_id)

    def get_objects_by_layer(self, layer: ObjectLayer) -> List[ReferenceObject]:
        return [o for o in self.objects.values() if o.layer == layer]

    def get_decision_layer(self, level: str) -> Optional[DecisionLayerSpec]:
        return self.decision_layers.get(level)

    def all_object_ids(self) -> List[str]:
        return sorted(self.objects.keys())

    def check_fold_violation(self, source_id: str, target_id: str) -> bool:
        """Returns True if folding source into target is a violation."""
        obj = self.objects.get(source_id)
        if obj is None:
            return False
        return target_id in obj.forbidden_folds

    def total_objects(self) -> int:
        return len(self.objects)

    def total_decision_layers(self) -> int:
        return len(self.decision_layers)

    def total_priority_rules(self) -> int:
        return len(self.priority_rules)

    def total_anti_promotion_rules(self) -> int:
        return len(self.anti_promotion_rules)