"""SHACL runner — Phase 0 stub (no shapes committed yet)."""
from pathlib import Path
from typing import Dict, Any


class SHACLRunner:
    """Phase 0 SHACL validation interface.

    In Phase 0, the runner returns a placeholder result.
    In Phase 1+, real SHACL shapes (from v0.3 ontology) will be registered.
    """

    def validate(self, bundle_path: Path) -> Dict[str, Any]:
        """Returns a validation report dict."""
        return {
            "conforms": True,
            "results": [],
            "note": "Phase 0 — no SHACL shapes committed yet",
            "bundle": str(bundle_path),
        }
