"""SVDE Adapter subpackage — Phase 3 bridge to SVDE Core DecisionGate."""
from prism_ontology.adapters.svde.bridge import (
    SVDEOntologyAdapter,
    BusinessDecisionIntent,
    BusinessQuestion,
    ValidationReport,
    QUESTION_TO_CAPABILITIES,
)

__all__ = [
    "SVDEOntologyAdapter",
    "BusinessDecisionIntent",
    "BusinessQuestion",
    "ValidationReport",
    "QUESTION_TO_CAPABILITIES",
]
