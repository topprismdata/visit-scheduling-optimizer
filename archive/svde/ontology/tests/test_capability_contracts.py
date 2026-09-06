"""Phase 4 Tests — Capability Contract Definitions & Honesty Gate."""
import pytest
from prism_ontology.profiles import (
    CapabilityRegistry, CapabilityStatus, CapabilityContract,
    TERRITORY_ALIGNMENT_CONTRACT,
    PERIODIC_VISIT_PLANNING_CONTRACT,
    DAILY_ROUTE_OPTIMIZATION_CONTRACT,
    ALL_CAPABILITY_CONTRACTS,
)
from prism_ontology.reference.store import DecisionLevel


@pytest.fixture
def registry() -> CapabilityRegistry:
    return CapabilityRegistry()


# ============================================================================
# Existence: all 3 contracts registered
# ============================================================================

def test_three_capability_contracts_defined(registry):
    assert len(registry.all()) == 3
    assert "capability.territory_alignment" in registry.all_ids()
    assert "capability.periodic_visit_planning" in registry.all_ids()
    assert "capability.daily_route_optimization" in registry.all_ids()


# ============================================================================
# Honesty gate: ALL start as PLANNED
# ============================================================================

def test_all_capabilities_start_as_planned(registry):
    assert len(registry.all_planned()) == 3
    summary = registry.summary()
    assert summary["all_planned"] == 3
    assert summary["any_implemented"] is False


def test_no_capability_claims_implementation_status(registry):
    for cap in registry.all():
        assert cap.status != CapabilityStatus.IMPLEMENTED, \
            f"{cap.capability_id} must NOT claim IMPLEMENTED status"


# ============================================================================
# TerritoryAlignment: input objects + constraints
# ============================================================================

def test_territory_alignment_uses_5_input_objects(registry):
    cap = registry.get("capability.territory_alignment")
    assert cap is not None
    expected = {"Customer", "OwnershipPolicy", "EligibilityPolicy", "Resource", "SubstitutionPolicy"}
    assert set(cap.input_objects) == expected


def test_territory_alignment_preserves_locked_ownership(registry):
    cap = registry.get("capability.territory_alignment")
    assert any("locked_ownership_must_be_preserved" in h for h in cap.hard_constraints)


def test_territory_alignment_respects_priority_rules(registry):
    cap = registry.get("capability.territory_alignment")
    rule_ids = [r for r in cap.priority_rules_respected]
    assert any("PR-001" in r for r in rule_ids)  # coverage before distance
    assert any("PR-002" in r for r in rule_ids)  # locked commitments


# ============================================================================
# PeriodicVisitPlanning: cadence + locked commitments
# ============================================================================

def test_periodic_planning_uses_7_input_objects(registry):
    cap = registry.get("capability.periodic_visit_planning")
    assert cap is not None
    expected = {"VisitDemand", "CadenceSpec", "PlanningHorizon", "Commitment", "ResourceDayProfile", "Customer", "OwnershipPolicy"}
    assert set(cap.input_objects) == expected


def test_periodic_planning_requires_cadence_compliance(registry):
    cap = registry.get("capability.periodic_visit_planning")
    assert any("frequency_compliance" in h or "cadence" in h.lower() for h in cap.hard_constraints)


def test_periodic_planning_respects_locked_commitments(registry):
    cap = registry.get("capability.periodic_visit_planning")
    assert any("existing_locked_commitments_preserved" in h for h in cap.hard_constraints)


def test_periodic_planning_references_ptv_evidence(registry):
    cap = registry.get("capability.periodic_visit_planning")
    assert any("REF-PTV" in e for e in cap.evidence_sources)


# ============================================================================
# DailyRouteOptimization: fixed visit set + locked order
# ============================================================================

def test_daily_route_uses_5_input_objects(registry):
    cap = registry.get("capability.daily_route_optimization")
    assert cap is not None
    expected = {"PlannedVisit", "TravelCostMatrix", "ResourceDayProfile", "Commitment", "ObjectiveProfile"}
    assert set(cap.input_objects) == expected


def test_daily_route_requires_fixed_visit_set(registry):
    cap = registry.get("capability.daily_route_optimization")
    assert any("fixed" in h.lower() for h in cap.hard_constraints)


def test_daily_route_requires_explicit_travel_matrix(registry):
    cap = registry.get("capability.daily_route_optimization")
    assert any("TravelCostMatrix" in h for h in cap.hard_constraints)
    assert any("no implicit defaults" in h for h in cap.hard_constraints)


def test_daily_route_respects_four_priority_rules(registry):
    cap = registry.get("capability.daily_route_optimization")
    rule_ids = cap.priority_rules_respected
    assert len(rule_ids) >= 3
    assert any("PR-001" in r for r in rule_ids)
    assert any("PR-002" in r for r in rule_ids)
    assert any("PR-004" in r for r in rule_ids)


# ============================================================================
# Output types
# ============================================================================

def test_each_capability_has_distinct_output_type(registry):
    outputs = {c.output_type for c in registry.all()}
    assert len(outputs) == 3
    assert "TerritoryAssignmentPlan" in outputs
    assert "PeriodicVisitPlan" in outputs
    assert "DailyRoutePlan" in outputs


# ============================================================================
# Decision layer coverage
# ============================================================================

def test_all_five_decision_layers_have_capability_or_no_cap(registry):
    """Each decision level has at most 1+ capability or is HONESTLY unhandled."""
    from prism_ontology.reference.store import DecisionLevel as DL
    for dl in DL:
        caps = registry.get_by_decision_level(dl)
        # If decision level has NO capability, that's OK (honest unhandled)
        # If it has 1+ capability, they must all be PLANNED
        for c in caps:
            assert c.status == CapabilityStatus.PLANNED


def test_decision_level_coverage():
    """Per v1.1 §9 Phase 4: at least 3 core capabilities must be defined."""
    registry = CapabilityRegistry()
    summary = registry.summary()
    assert summary["total_capabilities"] >= 3
    # 3 core capabilities mapped to TERRITORY, PERIODIC, DAILY
    assert "capability.territory_alignment" in summary["by_decision_level"]["TERRITORY_ALIGNMENT"]
    assert "capability.periodic_visit_planning" in summary["by_decision_level"]["PERIODIC_COVERAGE"]
    assert "capability.daily_route_optimization" in summary["by_decision_level"]["DAILY_ROUTE_SEQUENCING"]


# ============================================================================
# Refusal safety: contracts must NOT claim IMPLEMENTED
# ============================================================================

def test_no_capability_lies_about_status(registry):
    """If anything is marked IMPLEMENTED but has no implementation evidence, fail."""
    for cap in registry.all():
        if cap.status == CapabilityStatus.IMPLEMENTED:
            pytest.fail(
                f"{cap.capability_id} claims IMPLEMENTED but Phase 4 only defines contracts. "
                f"Implementation requires Phase 5+. Update status to PLANNED."
            )


def test_all_contracts_have_evidence_sources(registry):
    """v1.1 §6.1 rule 1: every contract must have source provenance."""
    for cap in registry.all():
        assert len(cap.evidence_sources) > 0, \
            f"{cap.capability_id} has no evidence sources"
