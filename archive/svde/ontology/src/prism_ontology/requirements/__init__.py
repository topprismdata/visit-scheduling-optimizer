"""Requirements subpackage — competency question registry."""
from pathlib import Path
from typing import Dict, Any, List
import yaml

from prism_ontology.models import CompetencyQuestion


class CQRegistry:
    """Phase 0 competency question registry."""

    def __init__(self, bundle_path: Path = None):
        self.bundle_path = Path(bundle_path) if bundle_path else None
        self.cqs: List[CompetencyQuestion] = []
        if self.bundle_path and self.bundle_path.exists():
            self._load()

    def _load(self) -> None:
        if not self.bundle_path:
            return
        for f in sorted(self.bundle_path.glob("cq_*.y*ml")):
            with open(f, "r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp) or {}
            if "cq_id" in data:
                self.cqs.append(CompetencyQuestion(**data))

    def add(self, cq: CompetencyQuestion) -> None:
        if not cq.cq_id:
            raise ValueError("CQ must have cq_id")
        self.cqs.append(cq)

    def all(self) -> List[CompetencyQuestion]:
        return list(self.cqs)
