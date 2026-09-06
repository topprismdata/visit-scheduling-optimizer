"""ApproximationDeclaration — per v1.1 §6.1 rule 5.

All approximations must have explicit declaration.
Phase 0 only implements the contract skeleton.
"""
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ApproximationDeclaration:
    """Explicit declaration of any approximation used in computation.

    Required for any non-exact computation in Phase 1+ capabilities.
    """
    name: str                                  # e.g., "default_capacity_per_km"
    approximation_type: str                   # DEFAULT_VALUE | BIG_M_PENALTY | TOLERANCE_EPSILON
    source_evidence_id: str                    # Must link to a Claim
    justification: str                          # Why this approximation is acceptable
    error_bound_pct: float = 0.0               # 0.0 = exact, e.g., 0.05 = +/-5%
    applicable_scope: str = ""                 # assignment | routing | simulation
    deprecated_after: str = ""                 # ISO 8601 date or empty
    notes: str = ""

    def to_prov_o(self) -> Dict[str, Any]:
        """Emit PROV-O compatible provenance for this approximation."""
        return {
            "prov:type": "prism:ApproximationDeclaration",
            "prov:name": self.name,
            "approximation_type": self.approximation_type,
            "source_evidence": self.source_evidence_id,
            "error_bound_pct": self.error_bound_pct,
        }

    def validate(self) -> None:
        """Validate the declaration. Raises ValueError on invalid input."""
        if not self.name:
            raise ValueError("ApproximationDeclaration.name is required")
        if not self.source_evidence_id:
            raise ValueError("ApproximationDeclaration.source_evidence_id is required")
        if not 0.0 <= self.error_bound_pct <= 1.0:
            raise ValueError(
                f"error_bound_pct must be in [0.0, 1.0], got {self.error_bound_pct}"
            )
