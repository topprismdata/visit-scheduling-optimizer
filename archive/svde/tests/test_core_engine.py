"""SVDE Core Acceptance Test (Sprint 6.2).

Validates that an external business caller can execute:
    request = svde.DecisionRequest(...)
    artifact = svde.decide(request)

Verifies:
- Solution Feasibility != Decision Feasibility independent derivation.
- Segregated evidence namespaces: physical, business, semantic.
- Strict fail-closed resolution on unknown domain / unknown capability.
- DecisionArtifact schema stability.
"""
import sys
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import svde
from svde.contracts import (
    DecisionRequest, DecisionArtifact, UnsupportedDomainError, UnsupportedCapabilityError
)


def test_core_svde_delivery_decision_execution():
    """Validates SVDE Core executing a delivery dispatch request directly."""
    request = DecisionRequest(
        request_id="REQ-DELIVERY-2026-08-24",
        domain="delivery",
        intent={
            "primary_objective": "maximize_vip_sla_fulfillment",
            "priority_rules": {"vip_customer": "high", "cost": "medium"}
        },
        world_state={
            "fleet": [
                {"id": "VEH_STD_01", "type": "STANDARD_VAN", "capacity_kg": 1000, "status": "AVAILABLE"},
                {"id": "VEH_STD_02", "type": "STANDARD_VAN", "capacity_kg": 800, "status": "AVAILABLE"}
            ],
            "orders": [
                {"id": "ORD_VIP_AMBIENT", "weight_kg": 250, "req_cold": False, "is_locked": True, "is_vip": True},
                {"id": "ORD_STD_AMBIENT", "weight_kg": 300, "req_cold": False, "is_locked": False, "is_vip": False}
            ]
        }
    )

    artifact = svde.decide(request)

    # 1. Verify structure and type
    assert isinstance(artifact, DecisionArtifact)
    assert artifact.request_id == "REQ-DELIVERY-2026-08-24"
    assert artifact.domain == "delivery"

    # 2. Verify Feasibility & Semantic Compliance
    assert artifact.solution_feasible is True
    assert artifact.decision_feasible is True
    assert artifact.semantic_compliance is True

    # 3. Verify Assignments
    assignments = artifact.decision.get("assignments", {})
    assert "VEH_STD_01" in assignments
    assert "ORD_VIP_AMBIENT" in assignments["VEH_STD_01"]

    # 4. Verify Principles & Segregated Evidence
    assert any(p["principle_id"] == "CORE-PRIN-001" for p in artifact.activated_principles)
    assert any(p["id"] == "CORE-PRIN-002" for p in artifact.rejected_principles)
    assert artifact.evidence.physical.satisfied is True
    assert artifact.evidence.business.satisfied is True
    assert artifact.evidence.semantic.satisfied is True
    assert len(artifact.unresolved_issues) == 0


def test_core_svde_visit_decision_execution():
    """Validates SVDE Core executing a field sales visit scheduling request directly."""
    request = DecisionRequest(
        request_id="REQ-VISIT-2026-08-24",
        domain="visit",
        intent={
            "primary_objective": "sla_specialist_match",
            "priority_rules": {"vip_customer": "high", "cost": "medium"}
        },
        world_state={
            "fleet": [
                {"id": "REP_SPECIALIST", "type": "SPECIALIST_REP", "max_daily_minutes": 480, "status": "AVAILABLE"},
                {"id": "REP_JUNIOR", "type": "JUNIOR_REP", "max_daily_minutes": 420, "status": "AVAILABLE"}
            ],
            "orders": [
                {"id": "VISIT_STRATEGIC_HOSPITAL", "duration_mins": 90, "required_skill": "SPECIALIST", "is_locked": True, "is_vip": True},
                {"id": "VISIT_COMMUNITY_CLINIC", "duration_mins": 30, "required_skill": "JUNIOR", "is_locked": False, "is_vip": False}
            ]
        }
    )

    artifact = svde.decide(request)

    assert isinstance(artifact, DecisionArtifact)
    assert artifact.solution_feasible is True
    assert artifact.decision_feasible is True
    assert artifact.semantic_compliance is True

    assignments = artifact.decision.get("assignments", {})
    assert "REP_SPECIALIST" in assignments
    assert "VISIT_STRATEGIC_HOSPITAL" in assignments["REP_SPECIALIST"]


def test_core_svde_detects_infeasibility_and_violations():
    """Validates SVDE Core auditor catches and records unresolved violations when physical capacity is breached."""
    request = DecisionRequest(
        request_id="REQ-OVERLOAD-TEST",
        domain="delivery",
        intent={"primary_objective": "test"},
        world_state={
            "fleet": [{"id": "VEH_TINY", "type": "STANDARD_VAN", "capacity_kg": 100, "status": "AVAILABLE"}],
            "orders": [
                {"id": "ORD_HUGE_1", "weight_kg": 80, "is_locked": True},
                {"id": "ORD_HUGE_2", "weight_kg": 80, "is_locked": True}
            ]
        }
    )

    artifact = svde.decide(request)

    # 160kg demand > 100kg capacity -> Physical overload!
    # solution_feasible must be False, and decision_feasible must be False
    assert artifact.solution_feasible is False
    assert artifact.decision_feasible is False
    assert artifact.evidence.physical.satisfied is False
    assert len(artifact.unresolved_issues) >= 1
    assert any("overloaded" in iss for iss in artifact.unresolved_issues)
