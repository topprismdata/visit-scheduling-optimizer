"""Phase 2 Tests — Operational Contract Compilation & Zero-Fold Verification."""
import json
import pytest
from pathlib import Path
from prism_ontology.reference.store import ReferenceOntologyStore
from prism_ontology.compiler.operational import OperationalCompiler
from prism_ontology.compiler.mapping_manifest import DomainAdapterMappingManifest


def test_compiler_produces_json_schema_with_required_fields():
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    customer_schema = compiler.compile_object_schema(store.get_object("Customer"))
    d = customer_schema.to_dict()
    assert d["$id"] == "prism:schema:Customer"
    assert "id" in d["properties"]
    assert "id" in d["required"]
    assert d["properties"]["id"]["type"] == "string"


def test_compiler_schema_includes_all_key_attributes():
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    obj = store.get_object("Customer")
    schema = compiler.compile_object_schema(obj)
    for attr in obj.key_attributes:
        assert attr in schema.to_dict()["properties"]


def test_schema_hash_is_deterministic():
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    s1 = compiler.compile_object_schema(store.get_object("Customer"))
    s2 = compiler.compile_object_schema(store.get_object("Customer"))
    assert s1.compute_hash() == s2.compute_hash()


def test_shacl_shape_contains_required_id_property():
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    shape = compiler.compile_shacl_shape(store.get_object("Customer"))
    ttl = shape.to_ttl()
    assert "sh:NodeShape" in ttl
    assert "sh:property" in ttl
    assert "xsd:string" in ttl


def test_export_all_writes_schemas_shapes_and_manifest(tmp_path: Path):
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    compiler.export_all(tmp_path)

    # 19+ object schemas
    json_files = list(tmp_path.glob("*.schema.json"))
    assert len(json_files) >= 19

    # 19+ SHACL shapes
    ttl_files = list(tmp_path.glob("*.shape.ttl"))
    assert len(ttl_files) >= 19

    # MANIFEST.json exists
    manifest = json.loads((tmp_path / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["source_object_count"] >= 19
    assert "Customer" in manifest["schemas"]


def test_zero_fold_audit_is_clean():
    store = ReferenceOntologyStore()
    manifest = DomainAdapterMappingManifest(store)
    report = manifest.expected_zero_fold()
    assert report["is_clean"] is True
    assert report["fold_violation_count"] == 0


def test_zero_fold_audit_detects_violation():
    store = ReferenceOntologyStore()
    manifest = DomainAdapterMappingManifest(store)
    # Simulate bad adapter that folds Customer → COMMITTED_TASK
    bad_mapping = {
        "Customer": "COMMITTED_TASK",
        "PlannedVisit": "RouteStop",
    }
    report = manifest.audit(bad_mapping)
    assert report["is_clean"] is False
    assert report["fold_violation_count"] >= 2
    violation_ids = {v["object_id"] for v in report["violations"]}
    assert "Customer" in violation_ids
    assert "PlannedVisit" in violation_ids


def test_type_inference_boolean_fields():
    from prism_ontology.compiler.operational import infer_type
    assert infer_type("is_locked") == "boolean"
    assert infer_type("requires_approval") == "boolean"
    assert infer_type("is_active") == "boolean"


def test_type_inference_numeric_fields():
    from prism_ontology.compiler.operational import infer_type
    assert infer_type("tenure_months") == "number"
    assert infer_type("weight_kg") == "number"
    assert infer_type("daily_capacity_minutes") == "number"
    assert infer_type("min_interval_days") == "number"


def test_type_inference_id_fields():
    from prism_ontology.compiler.operational import infer_type
    assert infer_type("customer_id") == "string"
    assert infer_type("rep_id") == "string"
    assert infer_type("source") == "string"


def test_all_objects_have_evidence_in_compiled_schemas():
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    for obj in store.objects.values():
        schema = compiler.compile_object_schema(obj)
        d = schema.to_dict()
        assert len(d["evidence_sources"]) > 0, f"{obj.object_id} schema has no evidence"
