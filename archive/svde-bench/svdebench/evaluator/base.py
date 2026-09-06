"""
svdebench.evaluator.base — Evaluator Interfaces
Input is strictly DecisionCase + DecisionArtifact.
Does not access agent internal state or private memory.
"""
from __future__ import annotations
from typing import Any, Dict
from abc import ABC, abstractmethod
from svdebench.core.schema import DecisionCase, DecisionArtifact

class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, case: DecisionCase, artifact: DecisionArtifact, gold: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate artifact against case specification and gold reference."""
        pass
