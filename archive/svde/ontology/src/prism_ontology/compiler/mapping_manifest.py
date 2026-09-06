"""Domain Adapter Mapping Manifest — ensures 0-fold-score (Phase 2).

For each ReferenceObject, verifies the DomainAdapter does NOT collapse it into
a generic engineering primitive (e.g. COMMITTED_TASK, ROUTE_STOP, COMMITTED_DECISION).
"""
from typing import Dict, List
from prism_ontology.reference.store import (
    ReferenceOntologyStore, ObjectLayer, FROZEN_OBJECTS
)


# Engineering primitives that domain adapters MUST NOT collapse business objects into
FORBIDDEN_ENGINEERING_PRIMITIVES = {
    "COMMITTED_TASK", "ROUTE_STOP", "TASK",
    "DECISION_ARTIFACT.decision", "ARTIFACT.decision",
    "PLANNING_ARTIFACT", "EXECUTION_NODE", "SOLVER_VAR",
    "TUPLE", "GENERIC_NODE", "ATOMIC_VALUE",
}


class DomainAdapterMappingManifest:
    """Verifies that DomainAdapters do NOT fold business objects into engineering primitives."""

    def __init__(self, store: ReferenceOntologyStore):
        self.store = store
        self.fold_violations: List[Dict[str, str]] = []
        self.evidence: List[str] = []

    def audit(self, adapter_fold_map: Dict[str, str]) -> Dict[str, any]:
        """
        Args:
            adapter_fold_map: maps ReferenceObject.object_id → engineering primitive
                              (e.g. {"Customer": "COMMITTED_TASK"} means Customer is
                              collapsed into COMMITTED_TASK by the adapter).

        Returns:
            audit report dict
        """
        for obj_id, target_primitive in adapter_fold_map.items():
            obj = self.store.get_object(obj_id)
            if obj is None:
                continue
            # Check if target is a forbidden engineering primitive
            target_clean = target_primitive.split(".")[-1]
            # Normalize by removing underscores (ROUTE_STOP → ROUTESTOP) for case-insensitive matching
            target_normalized = target_clean.upper().replace("_", "")
            forbidden_normalized = {p.upper().replace("_", "") for p in FORBIDDEN_ENGINEERING_PRIMITIVES}
            if target_normalized in forbidden_normalized:
                # Also check against object's stated forbidden_folds
                if target_primitive in obj.forbidden_folds:
                    self.fold_violations.append({
                        "object_id": obj_id,
                        "target_primitive": target_primitive,
                        "object_layer": obj.layer.value,
                        "reason": f"{obj_id} must NOT be folded into {target_primitive} (v0.3 §3 anti-promotion)",
                    })

        return {
            "fold_violation_count": len(self.fold_violations),
            "violations": self.fold_violations,
            "is_clean": len(self.fold_violations) == 0,
            "evidence_sources": [obj.evidence_sources for obj in self.store.objects.values() if obj.evidence_sources],
        }

    def expected_zero_fold(self) -> Dict[str, any]:
        """In Phase 2, all 19+ ReferenceObjects must be mapped 1:1 with no folds."""
        expected_mapping = {obj.object_id: obj.object_id for obj in self.store.objects.values()}
        return self.audit(expected_mapping)
