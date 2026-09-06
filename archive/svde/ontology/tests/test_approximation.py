"""Phase 0 Unit Tests — ApproximationDeclaration Contract."""
import pytest
from prism_ontology.approximation.declaration import ApproximationDeclaration


def test_valid_approximation_declaration():
    decl = ApproximationDeclaration(
        name="test_capacity_approx",
        approximation_type="DEFAULT_VALUE",
        source_evidence_id="CLM-0001",
        justification="Standard approximation for smoke test",
        error_bound_pct=0.05,
        applicable_scope="assignment"
    )
    decl.validate()
    assert decl.name == "test_capacity_approx"
    assert decl.error_bound_pct == 0.05


def test_approximation_declaration_validation_error_missing_name():
    decl = ApproximationDeclaration(
        name="",
        approximation_type="DEFAULT_VALUE",
        source_evidence_id="CLM-0001",
        justification="Test",
        error_bound_pct=0.0
    )
    with pytest.raises(ValueError, match="name is required"):
        decl.validate()


def test_approximation_declaration_validation_error_invalid_bound():
    decl = ApproximationDeclaration(
        name="test",
        approximation_type="DEFAULT_VALUE",
        source_evidence_id="CLM-0001",
        justification="Test",
        error_bound_pct=1.5  # > 1.0 invalid
    )
    with pytest.raises(ValueError, match="error_bound_pct must be in"):
        decl.validate()


def test_approximation_declaration_to_prov_o():
    decl = ApproximationDeclaration(
        name="test_prov",
        approximation_type="TOLERANCE_EPSILON",
        source_evidence_id="CLM-0002",
        justification="Test prov",
        error_bound_pct=0.01
    )
    prov = decl.to_prov_o()
    assert prov["prov:type"] == "prism:ApproximationDeclaration"
    assert prov["prov:name"] == "test_prov"
    assert prov["source_evidence"] == "CLM-0002"
