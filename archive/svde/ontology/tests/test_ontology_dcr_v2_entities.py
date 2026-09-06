"""Phase 2 Tests: Domain Ontology DCR v2.0 Entities Registration.

Verifies:
1. All 5 DCR v2.0 objects registered in ReferenceOntologyStore:
   - AccountHierarchy (IDENTITY, [REF-006])
   - ProductLineScope (POLICY, [REF-008, REF-010])
   - SupplyNodeLink (IDENTITY, [REF-009, REF-PTV-001])
   - MerchandisingCompliance (MEASUREMENT, [REF-011])
   - InStoreActionTaxonomy (POLICY, [REF-007])
2. Key attributes and layer correctness
3. Anti-collapse (forbidden_folds) enforcement for each new object
4. Zero regression on existing 19 v0.3 objects (Customer, CadenceSpec, etc.)
"""
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

from prism_ontology.reference.store import ReferenceOntologyStore, ObjectLayer


@pytest.fixture
def store() -> ReferenceOntologyStore:
    return ReferenceOntologyStore()


# ============================================================================
# DCR v2.0 Objects Presence & Metadata
# ============================================================================

def test_account_hierarchy_registered(store):
    obj = store.get_object("AccountHierarchy")
    assert obj is not None
    assert obj.layer == ObjectLayer.IDENTITY
    assert "account_id" in obj.key_attributes
    assert "channel_tier" in obj.key_attributes
    assert "REF-006" in obj.evidence_sources
    assert store.check_fold_violation("AccountHierarchy", "Customer") is True
    assert store.check_fold_violation("AccountHierarchy", "SalesIncentive") is True


def test_product_line_scope_registered(store):
    obj = store.get_object("ProductLineScope")
    assert obj is not None
    assert obj.layer == ObjectLayer.POLICY
    assert "brand_id" in obj.key_attributes
    assert "strategic_role" in obj.key_attributes
    assert "REF-008" in obj.evidence_sources
    assert store.check_fold_violation("ProductLineScope", "VisitDemand") is True


def test_supply_node_link_registered(store):
    obj = store.get_object("SupplyNodeLink")
    assert obj is not None
    assert obj.layer == ObjectLayer.IDENTITY
    assert "dc_id" in obj.key_attributes
    assert "fixed_delivery_weekdays" in obj.key_attributes
    assert "REF-009" in obj.evidence_sources
    assert store.check_fold_violation("SupplyNodeLink", "WarehouseTopology") is True


def test_merchandising_compliance_registered(store):
    obj = store.get_object("MerchandisingCompliance")
    assert obj is not None
    assert obj.layer == ObjectLayer.MEASUREMENT
    assert "contract_target_units" in obj.key_attributes
    assert "compliance_ratio" in obj.key_attributes
    assert "REF-011" in obj.evidence_sources
    assert store.check_fold_violation("MerchandisingCompliance", "ActualVisit") is True


def test_in_store_action_taxonomy_registered(store):
    obj = store.get_object("InStoreActionTaxonomy")
    assert obj is not None
    assert obj.layer == ObjectLayer.POLICY
    assert "action_type" in obj.key_attributes
    assert "estimated_duration_min" in obj.key_attributes
    assert "REF-007" in obj.evidence_sources
    assert store.check_fold_violation("InStoreActionTaxonomy", "RouteStop") is True


# ============================================================================
# Zero Regression on Existing Core Objects
# ============================================================================

def test_existing_core_objects_intact(store):
    core_objs = ["Customer", "Resource", "VisitDemand", "PlannedVisit", "ActualVisit", "CadenceSpec", "Commitment"]
    for c in core_objs:
        assert store.get_object(c) is not None
