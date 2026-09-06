"""
svdebench.oracle.base — Independent Oracle Interfaces
Strictly isolated from agents and solvers.
"""
from __future__ import annotations
from typing import Any, Dict
from abc import ABC, abstractmethod
from svdebench.core.case import DecisionCase
from svdebench.oracle.models import OracleReference

class BaseOracle(ABC):
    @abstractmethod
    def solve(self, case: DecisionCase) -> OracleReference:
        """Compute independent mathematical reference."""
        pass

class ExactOracle(BaseOracle):
    """Abstract base for exact mathematical reference solvers."""
    pass
