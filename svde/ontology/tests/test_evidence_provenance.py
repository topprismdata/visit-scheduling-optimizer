"""Phase 0 Unit Tests — Evidence, Provenance & Validator."""
from pathlib import Path
import pytest
from prism_ontology.evidence.levels import EvidenceLevel
from prism_ontology.evidence.registry import EvidenceRegistry
from prism_ontology.validator.shacl_runner import SHACLRunner
from prism_ontology.provenance import ProvenanceWriter


def test_evidence_levels():
    assert EvidenceLevel.PRODUCT_FACT.value == "PRODUCT_FACT"
    assert EvidenceLevel.DOMAIN_PRACTICE.value == "DOMAIN_PRACTICE"
    assert EvidenceLevel.MATHEMATICAL_THEORY.value == "MATHEMATICAL_THEORY"


def test_evidence_registry_validation(tmp_path: Path):
    reg = EvidenceRegistry(tmp_path)
    
    # Valid source
    reg.add_source({
        "source_id": "REF-001",
        "author_org": "OR Group",
        "year": 2020,
        "evidence_level": "DOMAIN_PRACTICE"
    })
    assert len(reg.sources) == 1

    # Invalid source without evidence_level
    with pytest.raises(ValueError, match="evidence_level"):
        reg.add_source({"source_id": "REF-002"})

    # Valid claim linking to known source
    reg.add_claim({
        "claim_id": "CLM-001",
        "statement": "Coverage > Distance",
        "source_ids": ["REF-001"],
        "evidence_level": "DOMAIN_PRACTICE",
        "supports_objects": ["ObjectiveProfile"]
    })
    assert len(reg.claims) == 1

    # Claim linking to unknown source
    with pytest.raises(ValueError, match="unknown sources"):
        reg.add_claim({
            "claim_id": "CLM-002",
            "statement": "Bad",
            "source_ids": ["UNKNOWN-SOURCE"]
        })


def test_shacl_runner_phase0_stub(tmp_path: Path):
    runner = SHACLRunner()
    report = runner.validate(tmp_path)
    assert report["conforms"] is True
    assert "Phase 0" in report["note"]


def test_provenance_writer():
    writer = ProvenanceWriter(bundle_id="bundle-001")
    writer.record(
        activity="compile",
        entity="reference.ttl",
        agent="OperationalCompiler",
        attributes={"profile": "sales_visit"}
    )
    bundle = writer.emit()
    assert bundle["prov:bundle"] == "bundle-001"
    assert len(bundle["prov:entries"]) == 1
    assert bundle["prov:entries"][0]["prov:activity"] == "compile"
