"""SVDE Core Business Intent Diagnostic Engine.

Pure-diagnostic layer (NO solving). Accepts natural-language intent + minimal context,
outputs DecisionIntentDiagnostic describing:
- which decision level the question belongs to
- what inputs are required
- which candidate capabilities can address it
- which hard constraints must be confirmed
- which fields are missing
- which capabilities are NOT yet implemented
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from svde.contracts.sales_visit_contracts import (
    SalesVisitCapabilityType, SalesVisitCapabilityStatus
)


class BusinessQuestion(str, Enum):
    TERRITORY_ALIGNMENT = "TERRITORY_ALIGNMENT"             # 谁负责哪些客户
    PERIODIC_COVERAGE = "PERIODIC_COVERAGE"                  # 多周期频次与节奏
    DAILY_ROUTE_SEQUENCE = "DAILY_ROUTE_SEQUENCE"            # 单日访问顺序
    ROLLING_REPLAN = "ROLLING_REPLAN"                        # 滚动重排
    DISTANCE_TIME_TRADEOFF = "DISTANCE_TIME_TRADEOFF"         # 距离/时间权衡

    UNCLASSIFIED = "UNCLASSIFIED"                            # 无法归类 → 显式拒绝降维


# Mapping: Business Question → Candidate Sales Visit Capabilities
QUESTION_TO_CAPABILITIES: Dict[BusinessQuestion, List[SalesVisitCapabilityType]] = {
    BusinessQuestion.TERRITORY_ALIGNMENT: [SalesVisitCapabilityType.TERRITORY_ALIGNMENT],
    BusinessQuestion.PERIODIC_COVERAGE: [SalesVisitCapabilityType.PERIODIC_VISIT_PLANNING],
    BusinessQuestion.DAILY_ROUTE_SEQUENCE: [SalesVisitCapabilityType.DAILY_ROUTE_OPTIMIZATION],
    BusinessQuestion.ROLLING_REPLAN: [
        SalesVisitCapabilityType.TERRITORY_ALIGNMENT,
        SalesVisitCapabilityType.PERIODIC_VISIT_PLANNING,
        SalesVisitCapabilityType.DAILY_ROUTE_OPTIMIZATION,
    ],
    BusinessQuestion.DISTANCE_TIME_TRADEOFF: [SalesVisitCapabilityType.DAILY_ROUTE_OPTIMIZATION],
    BusinessQuestion.UNCLASSIFIED: [],
}


@dataclass
class DecisionIntentDiagnostic:
    """Pure diagnostic output — NO solving, NO numbers, NO false promises."""
    raw_user_query: str
    classified_decision_level: BusinessQuestion
    required_inputs: List[str] = field(default_factory=list)
    hard_constraints_to_confirm: List[str] = field(default_factory=list)
    candidate_capabilities: List[str] = field(default_factory=list)
    capability_status: Dict[str, str] = field(default_factory=dict)   # cap_name -> status
    missing_data: List[str] = field(default_factory=list)
    confidence: float = 0.0                    # 0.0-1.0 classifier confidence
    refusal_to_advance: bool = False
    refusal_reason: str = ""
    downstream_advice: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_user_query": self.raw_user_query,
            "classified_decision_level": self.classified_decision_level.value,
            "required_inputs": self.required_inputs,
            "hard_constraints_to_confirm": self.hard_constraints_to_confirm,
            "candidate_capabilities": self.candidate_capabilities,
            "capability_status": self.capability_status,
            "missing_data": self.missing_data,
            "confidence": self.confidence,
            "refusal_to_advance": self.refusal_to_advance,
            "refusal_reason": self.refusal_reason,
            "downstream_advice": self.downstream_advice,
        }


class IntentDiagnosticEngine:
    """Keyword + structure-based intent classifier. Deterministic. No ML."""

    # Keyword pattern → (decision_level, base_confidence)
    _KEYWORD_MAP: List = [
        (["缩短", "在途", "距离", "公里", "km", "km数", "路线", "顺序"], BusinessQuestion.DAILY_ROUTE_SEQUENCE, 0.6),
        (["频次", "节奏", "周期", "周计划", "覆盖率", "锁定日", "频次合规"], BusinessQuestion.PERIODIC_COVERAGE, 0.7),
        (["辖区", "归属", "代表", "客户分配", "匹配"], BusinessQuestion.TERRITORY_ALIGNMENT, 0.7),
        (["滚动", "重排", "本周变更", "调整计划"], BusinessQuestion.ROLLING_REPLAN, 0.6),
        (["时间", "分钟", "在途时间", "总时长"], BusinessQuestion.DAILY_ROUTE_SEQUENCE, 0.5),
    ]

    # Per-capability required inputs (the SOURCE OF TRUTH for "missing data")
    _CAP_INPUTS: Dict[str, List[str]] = {
        SalesVisitCapabilityType.TERRITORY_ALIGNMENT.value: [
            "customer_list_with_locations_and_commercial_value",
            "sales_rep_list_with_base_location_and_weekly_capacity_minutes",
            "optional_historical_assignments_baseline",
        ],
        SalesVisitCapabilityType.PERIODIC_VISIT_PLANNING.value: [
            "customer_list_with_visit_policy_and_cadence_spec",
            "planning_horizon_weeks",
            "working_days_per_week",
            "weekly_availability_per_customer",
            "existing_commitments_locked_visits",
            "representative_day_profile_per_rep",
            "objective_policy_with_priority_levels",
        ],
        SalesVisitCapabilityType.DAILY_ROUTE_OPTIMIZATION.value: [
            "target_date",
            "rep_id_for_the_day",
            "depot_location",
            "fixed_customer_set_for_target_day",
            "real_distance_or_time_matrix_between_all_nodes",
            "service_duration_per_customer",
            "time_window_per_customer",
            "max_daily_work_minutes",
            "locked_visit_order_if_any",
        ],
    }

    # Per-capability mandatory hard constraints to confirm
    _CAP_CONSTRAINTS: Dict[str, List[str]] = {
        SalesVisitCapabilityType.TERRITORY_ALIGNMENT.value: [
            "every_customer_assigned_exactly_once",
            "rep_weekly_load_must_not_exceed_capacity",
            "locked_ownership_must_be_preserved",
        ],
        SalesVisitCapabilityType.PERIODIC_VISIT_PLANNING.value: [
            "each_customer_must_be_visited_at_cadence",
            "visits_must_occur_on_allowed_weekdays_and_time_windows",
            "existing_locked_commitments_must_be_preserved",
            "rep_daily_workload_must_not_exceed_daily_capacity",
        ],
        SalesVisitCapabilityType.DAILY_ROUTE_OPTIMIZATION.value: [
            "customer_set_must_be_FIXED",
            "locked_visit_order_must_be_preserved",
            "every_customer_served_within_time_window",
            "route_must_start_and_end_at_depot",
            "max_daily_work_minutes_must_not_be_exceeded",
        ],
    }

    # Real availability status (honesty gate)
    _CAPABILITY_STATUS: Dict[str, str] = {
        SalesVisitCapabilityType.TERRITORY_ALIGNMENT.value: SalesVisitCapabilityStatus.PLANNED.value,
        SalesVisitCapabilityType.PERIODIC_VISIT_PLANNING.value: SalesVisitCapabilityStatus.PLANNED.value,
        SalesVisitCapabilityType.DAILY_ROUTE_OPTIMIZATION.value: SalesVisitCapabilityStatus.PLANNED.value,
    }

    def diagnose(
        self,
        user_query: str,
        provided_inputs: Optional[Dict[str, Any]] = None
    ) -> DecisionIntentDiagnostic:
        provided = provided_inputs or {}
        decision_level, confidence, matched_keywords = self._classify(user_query)
        candidate_caps = QUESTION_TO_CAPABILITIES.get(decision_level, [])

        # Required inputs aggregated from candidate capabilities
        required_inputs: List[str] = []
        hard_constraints: List[str] = []
        for cap in candidate_caps:
            for inp in self._CAP_INPUTS.get(cap.value, []):
                if inp not in required_inputs:
                    required_inputs.append(inp)
            for cons in self._CAP_CONSTRAINTS.get(cap.value, []):
                if cons not in hard_constraints:
                    hard_constraints.append(cons)

        # Identify missing data (only those required inputs not in provided)
        provided_keys = set(provided.keys())
        missing_data = [
            r for r in required_inputs
            if not self._is_input_provided(r, provided_keys, provided)
        ]

        # Determine refusal to advance
        refusal_to_advance = False
        refusal_reason = ""
        if decision_level == BusinessQuestion.UNCLASSIFIED:
            refusal_to_advance = True
            refusal_reason = "Query does not match any known Sales Visit decision level. Ask user to clarify goal (territory / periodic / single-day)."
        elif not candidate_caps:
            refusal_to_advance = True
            refusal_reason = "No candidate capability can address this decision level."
        elif not missing_data and all(
            self._CAPABILITY_STATUS[c.value] == SalesVisitCapabilityStatus.PLANNED.value
            for c in candidate_caps
        ):
            refusal_to_advance = True
            refusal_reason = (
                f"All candidate capabilities are PLANNED (not implemented). "
                f"Diagnostic complete; downstream solve refused pending implementation."
            )

        downstream_advice = self._build_advice(decision_level, missing_data, candidate_caps, matched_keywords)

        return DecisionIntentDiagnostic(
            raw_user_query=user_query,
            classified_decision_level=decision_level,
            required_inputs=required_inputs,
            hard_constraints_to_confirm=hard_constraints,
            candidate_capabilities=[c.value for c in candidate_caps],
            capability_status={c.value: self._CAPABILITY_STATUS[c.value] for c in candidate_caps},
            missing_data=missing_data,
            confidence=confidence,
            refusal_to_advance=refusal_to_advance,
            refusal_reason=refusal_reason,
            downstream_advice=downstream_advice,
        )

    # ---------- internal helpers ----------

    def _classify(self, query: str) -> tuple:
        query_lower = query.lower()
        best_match: Optional[BusinessQuestion] = None
        best_score: float = 0.0
        matched_kws: List[str] = []
        for keywords, level, base_conf in self._KEYWORD_MAP:
            hits = [k for k in keywords if k in query_lower]
            if hits and base_conf > best_score:
                best_score = base_conf
                best_match = level
                matched_kws = hits
        # Refuse patterns that look like "shorten distance" but lack any structural scope → still default to DAILY if no better
        if best_match is None:
            # Refuse rather than silently fall back to UNCLASSIFIED guess
            return BusinessQuestion.UNCLASSIFIED, 0.0, []
        return best_match, best_score, matched_kws

    def _is_input_provided(self, required_key: str, provided_keys: set, provided: Dict[str, Any]) -> bool:
        # Heuristic: required keys are snake_case segments; provided keys are camelCase or contain them
        for k in provided_keys:
            kl = str(k).lower()
            if required_key in kl or kl in required_key:
                if provided[k] is not None and provided[k] != "" and provided[k] != []:
                    return True
        return False

    def _build_advice(
        self,
        level: BusinessQuestion,
        missing: List[str],
        candidate_caps: List,
        keywords: List[str],
    ) -> str:
        if level == BusinessQuestion.UNCLASSIFIED:
            return "未匹配到已识别的销售拜访业务问题层级。请明确：(1) 辖区/归属问题 (2) 周期频次/锁定日问题 (3) 单日路线顺序问题"
        if not candidate_caps:
            return "无候选能力可处理该决策层级"
        cap_names = ", ".join(c.value for c in candidate_caps)
        missing_summary = "、".join(missing) if missing else "无"
        return (
            f"判定决策层级={level.value}，候选能力=[{cap_names}]。缺失输入=[{missing_summary}]。"
            f"由于能力状态均为 PLANNED，拒绝继续推进求解。请补齐缺失输入并明确硬约束后再调用对应能力。"
        )
