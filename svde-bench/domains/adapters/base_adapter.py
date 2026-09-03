"""Base Domain Adapter Interface for SVDE-Bench v0.5.

Defines the contract for transforming domain-specific multi-file case representations
into canonical, de-grounded DecisionContext instances and vice versa.
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from pathlib import Path
from svdebench.core import DecisionCase
from tools.decision_runtime.decision_context import DecisionContext, NormalizedResource, NormalizedTask


class BaseDomainAdapter(ABC):
    """Abstract interface for domain-specific adapters."""
    
    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Returns the domain identifier (e.g. 'delivery', 'visit', 'warehouse')."""
        pass

    @abstractmethod
    def to_decision_context(self, case: DecisionCase) -> DecisionContext:
        """
        Transforms a domain-specific DecisionCase into a canonical DecisionContext
        without concept downgrading or field remapping hacks.
        """
        pass

    @abstractmethod
    def adapt_solution_to_domain(self, decision_routes: Dict[str, List[str]], case: DecisionCase) -> Dict[str, Any]:
        """
        Translates canonical resource-task assignments back into domain-specific execution artifacts.
        """
        pass
