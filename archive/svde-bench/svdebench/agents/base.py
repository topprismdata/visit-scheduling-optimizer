"""
svdebench.agents.base — Base Decision Agent Interface
Strictly isolated from oracle solutions and gold labels.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from svdebench.core.schema import DecisionCase, DecisionArtifact

class BaseDecisionAgent(ABC):
    @abstractmethod
    def solve(self, case: DecisionCase) -> DecisionArtifact:
        """Produce a decision artifact given a public decision case."""
        pass
