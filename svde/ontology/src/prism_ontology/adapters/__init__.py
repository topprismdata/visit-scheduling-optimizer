"""Adapters subpackage — SVDE adapter interface."""
from typing import Any, Dict


class SVDEOntologyAdapter:
    """Phase 0 adapter stub. Phase 1+ will bridge prism-ontology to SVDE Core DecisionGate."""

    def get_decision_gate(self) -> Dict[str, Any]:
        return {
            "status": "PHASE_0_STUB",
            "message": "SVDE adapter not active in Phase 0",
        }
