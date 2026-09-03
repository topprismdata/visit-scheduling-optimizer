"""
svdebench.evaluator.failure_taxonomy — Standardized Failure Taxonomy v0.1
Freezes the canonical set of failure modes for SVDE-Bench v0.1.
"""
from __future__ import annotations
from enum import Enum

class FailureTaxonomy(str, Enum):
    FT_01_SEMANTIC_VIOLATION = "FT-01"
    FT_02_PHYSICAL_INFEASIBILITY = "FT-02"
    FT_03_RUNTIME_INSTABILITY = "FT-03"
    FT_04_MEMORY_OVERGENERALIZATION = "FT-04"
    FT_05_CONSTRAINT_CONFLICT_FAILURE = "FT-05"
