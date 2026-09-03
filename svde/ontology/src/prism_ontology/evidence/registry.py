"""Evidence registry — load evidence bundles from YAML/JSON."""
from pathlib import Path
from typing import Dict, Any, List
import yaml
import json
from prism_ontology.evidence.levels import EvidenceLevel


class EvidenceRegistry:
    """Phase 0: simple YAML/JSON loader for evidence sources and claims."""

    def __init__(self, bundle_path: Path):
        self.bundle_path = Path(bundle_path)
        self.sources: List[Dict[str, Any]] = []
        self.claims: List[Dict[str, Any]] = []
        if self.bundle_path.exists():
            self._load()

    def _load(self) -> None:
        for f in sorted(self.bundle_path.glob("*.y*ml")):
            with open(f, "r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp) or {}
            if "source_id" in data:
                self.sources.append(data)
            if "claim_id" in data:
                self.claims.append(data)
        for f in sorted(self.bundle_path.glob("*.json")):
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp) or {}
            if "source_id" in data:
                self.sources.append(data)
            if "claim_id" in data:
                self.claims.append(data)

    def add_source(self, source: Dict[str, Any]) -> None:
        """Register a new evidence source."""
        if "source_id" not in source:
            raise ValueError("source must contain 'source_id'")
        if "evidence_level" not in source:
            raise ValueError("source must contain 'evidence_level'")
        try:
            EvidenceLevel(source["evidence_level"])
        except ValueError as e:
            raise ValueError(f"invalid evidence_level: {e}")
        self.sources.append(source)

    def add_claim(self, claim: Dict[str, Any]) -> None:
        """Register a new business claim."""
        if "claim_id" not in claim:
            raise ValueError("claim must contain 'claim_id'")
        if "statement" not in claim:
            raise ValueError("claim must contain 'statement'")
        if "source_ids" not in claim or not claim["source_ids"]:
            raise ValueError("claim must reference at least one source_id")
        unknown = set(claim["source_ids"]) - {s["source_id"] for s in self.sources}
        if unknown:
            raise ValueError(f"claim references unknown sources: {unknown}")
        self.claims.append(claim)

    def claims_by_level(self, level: EvidenceLevel) -> List[Dict[str, Any]]:
        return [
            c for c in self.claims
            if c.get("evidence_level") == level.value
        ]

    def all_claims(self) -> List[Dict[str, Any]]:
        return list(self.claims)
