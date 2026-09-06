"""Provenance subpackage — PROV-O compatible writer stub (Phase 0)."""
from typing import Dict, Any, List
from datetime import datetime, timezone


class ProvenanceWriter:
    """Phase 0 placeholder for PROV-O compatible output.

    In Phase 1, this will emit real PROV-O TTL using rdflib.
    """

    def __init__(self, bundle_id: str):
        self.bundle_id = bundle_id
        self.entries: List[Dict[str, Any]] = []

    def record(self, activity: str, entity: str, agent: str, attributes: Dict[str, Any] = None) -> None:
        """Record a provenance triple in PROV-O compatible form."""
        self.entries.append({
            "prov:type": "prov:Activity",
            "prov:activity": activity,
            "prov:entity": entity,
            "prov:agent": agent,
            "prov:atTime": datetime.now(timezone.utc).isoformat(),
            "prov:attributes": attributes or {},
        })

    def emit(self) -> Dict[str, Any]:
        """Emit the full provenance bundle."""
        return {
            "prov:bundle": self.bundle_id,
            "prov:generatedAt": datetime.now(timezone.utc).isoformat(),
            "prov:entries": self.entries,
        }
