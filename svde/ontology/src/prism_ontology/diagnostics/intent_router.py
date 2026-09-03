"""Intent diagnostic — routes user questions to 5 decision levels (Phase 0)."""
from dataclasses import dataclass
from typing import Optional


# 5 decision levels (per v1.1 §4.3)
DECISION_LEVELS = [
    "TERRITORY_ALIGNMENT",
    "PERIODIC_COVERAGE",
    "DAILY_ROUTE_SEQUENCING",
    "ROLLING_REPLAN",
    "DISTANCE_TIME_TRADEOFF",
]


@dataclass
class IntentDiagnostic:
    """Phase 0 intent diagnostic output."""
    primary_decision_level: str
    secondary_decision_levels: list
    confidence: float
    required_inputs: list
    missing_inputs: list
    hard_constraints_to_confirm: list
    candidate_capabilities: list
    capability_status: dict
    needs_clarification: bool
    refusal_reason: str
    downstream_advice: str


# Phase 0 keyword mapping (v1.1 §6.4 anti-collapse)
KEYWORD_MAP = {
    "缩短": "DAILY_ROUTE_SEQUENCING",
    "距离": "DAILY_ROUTE_SEQUENCING",
    "在途": "DAILY_ROUTE_SEQUENCING",
    "顺路": "DAILY_ROUTE_SEQUENCING",
    "频次": "PERIODIC_COVERAGE",
    "节奏": "PERIODIC_COVERAGE",
    "周期": "PERIODIC_COVERAGE",
    "辖区": "TERRITORY_ALIGNMENT",
    "归属": "TERRITORY_ALIGNMENT",
    "代表": "TERRITORY_ALIGNMENT",
    "滚动": "ROLLING_REPLAN",
    "重排": "ROLLING_REPLAN",
    "权衡": "DISTANCE_TIME_TRADEOFF",
    "tradeoff": "DISTANCE_TIME_TRADEOFF",
}


class IntentRouter:
    """Phase 0 keyword-based intent router."""

    def route(self, question: str) -> IntentDiagnostic:
        question_lower = question.lower()
        matched_levels: list = []

        for kw, lvl in KEYWORD_MAP.items():
            if kw in question_lower and lvl not in matched_levels:
                matched_levels.append(lvl)

        if not matched_levels:
            return IntentDiagnostic(
                primary_decision_level="UNCLASSIFIED",
                secondary_decision_levels=[],
                confidence=0.0,
                required_inputs=[],
                missing_inputs=[],
                hard_constraints_to_confirm=[],
                candidate_capabilities=[],
                capability_status={},
                needs_clarification=True,
                refusal_reason="Query does not match any known decision level",
                downstream_advice="Ask user to clarify goal: territory / periodic / single-day route",
            )

        primary = matched_levels[0]
        secondary = matched_levels[1:]

        return IntentDiagnostic(
            primary_decision_level=primary,
            secondary_decision_levels=secondary,
            confidence=min(1.0, 0.5 + 0.1 * len(matched_levels)),
            required_inputs=[],
            missing_inputs=[],
            hard_constraints_to_confirm=[],
            candidate_capabilities=[],
            capability_status={},
            needs_clarification=False,
            refusal_reason="",
            downstream_advice=f"Decision level: {primary}. Phase 0 placeholder.",
        )
