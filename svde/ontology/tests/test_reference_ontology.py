"""Phase 1 Tests — v0.3 Reference Ontology Loading & Anti-Collapse (ONT-1~ONT-8)."""
import pytest
from prism_ontology.reference import (
    ReferenceOntologyStore,
    ObjectLayer,
    DecisionLevel,
    FROZEN_OBJECTS,
    FROZEN_PRIORITY_RULES,
)


def test_reference_store_loads_minimum_19_objects():
    store = ReferenceOntologyStore()
    assert store.total_objects() >= 19


def test_all_objects_have_evidence_sources():
    store = ReferenceOntologyStore()
    for obj in FROZEN_OBJECTS:
        assert len(obj.evidence_sources) > 0, f"{obj.object_id} has no evidence"


def test_all_objects_frozen():
    store = ReferenceOntologyStore()
    for obj in FROZEN_OBJECTS:
        assert obj.lifecycle_state == "FROZEN"


def test_identity_layer():
    store = ReferenceOntologyStore()
    ids = {o.object_id for o in store.get_objects_by_layer(ObjectLayer.IDENTITY)}
    assert "Customer" in ids
    assert "Resource" in ids
    assert "Product" in ids  # GAP-1


def test_policy_layer():
    store = ReferenceOntologyStore()
    ids = {o.object_id for o in store.get_objects_by_layer(ObjectLayer.POLICY)}
    expected = {"VisitPolicy", "CadenceSpec", "OwnershipPolicy", "EligibilityPolicy",
                "SubstitutionPolicy", "ObjectiveProfile", "DeferralPolicy"}
    assert expected.issubset(ids)


def test_event_lifecycle_chain_distinct():
    store = ReferenceOntologyStore()
    assert store.get_object("VisitDemand") is not None
    assert store.get_object("PlannedVisit") is not None
    assert store.get_object("ActualVisit") is not None


def test_objective_profile_has_customer_facing_time():
    store = ReferenceOntologyStore()
    assert "customer_facing_time" in store.get_object("ObjectiveProfile").key_attributes


def test_objective_profile_has_stability_penalty():
    store = ReferenceOntologyStore()
    assert "stability_penalty" in store.get_object("ObjectiveProfile").key_attributes


def test_five_decision_layers():
    store = ReferenceOntologyStore()
    assert store.total_decision_layers() == 5


def test_daily_route_fixed_visit_set():
    store = ReferenceOntologyStore()
    layer = store.get_decision_layer("DAILY_ROUTE_SEQUENCING")
    assert "customer_set_must_be_FIXED" in layer.hard_constraints


def test_periodic_requires_planning_horizon():
    store = ReferenceOntologyStore()
    layer = store.get_decision_layer("PERIODIC_COVERAGE")
    assert "PlanningHorizon" in layer.input_objects


def test_five_priority_rules():
    store = ReferenceOntologyStore()
    assert store.total_priority_rules() == 5


def test_distance_subordinate_to_coverage():
    store = ReferenceOntologyStore()
    rule = store.priority_rules[0]
    assert "subordinateTo" in rule.statement


def test_anti_promotion_rules():
    store = ReferenceOntologyStore()
    assert store.total_anti_promotion_rules() >= 10


def test_customer_fold_into_task():
    store = ReferenceOntologyStore()
    assert store.check_fold_violation("Customer", "COMMITTED_TASK") is True


def test_customer_fold_into_route_stop():
    store = ReferenceOntologyStore()
    assert store.check_fold_violation("Customer", "RouteStop") is True


def test_planned_visit_fold_into_route_stop():
    store = ReferenceOntologyStore()
    assert store.check_fold_violation("PlannedVisit", "RouteStop") is True


def test_route_plan_fold_into_decision_artifact():
    store = ReferenceOntologyStore()
    assert store.check_fold_violation("RoutePlan", "DecisionArtifact.decision") is True


def test_valid_composition_not_flagged():
    store = ReferenceOntologyStore()
    assert store.check_fold_violation("Customer", "TerritoryAssignmentPlan") is False
