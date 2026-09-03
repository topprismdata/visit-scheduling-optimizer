"""Public Python API for prism-ontology (Phase 0)."""
from pathlib import Path
from typing import Optional

from prism_ontology.evidence import EvidenceRegistry
from prism_ontology.validator import SHACLRunner, CQRunner
from prism_ontology.diagnostics import IntentRouter
from prism_ontology.governance import LifecycleManager
from prism_ontology.provenance import ProvenanceWriter


def load_bundle(bundle_path: str | Path) -> EvidenceRegistry:
    """Load an evidence bundle from a directory."""
    return EvidenceRegistry(Path(bundle_path))


def validate_bundle(bundle_path: str | Path) -> dict:
    """Run SHACL validation on a bundle (Phase 0 stub)."""
    return SHACLRunner().validate(Path(bundle_path))


def run_cq_checks(bundle_path: str | Path) -> dict:
    """Run competency question checks (Phase 0 placeholder)."""
    return CQRunner().run(Path(bundle_path))


def diagnose_question(question: str) -> dict:
    """Route a user question to one of the 5 decision levels."""
    diag = IntentRouter().route(question)
    return {
        "primary": diag.primary_decision_level,
        "secondary": diag.secondary_decision_levels,
        "confidence": diag.confidence,
        "needs_clarification": diag.needs_clarification,
        "refusal_reason": diag.refusal_reason,
        "advice": diag.downstream_advice,
    }


def check_governance() -> LifecycleManager:
    """Get the 7-state lifecycle manager."""
    return LifecycleManager()


def write_provenance(bundle_id: str) -> ProvenanceWriter:
    """Create a provenance writer for the given bundle."""
    return ProvenanceWriter(bundle_id=bundle_id)
