"""
svdebench.core — Core models, memory schemas, and serialization utilities.
"""
import yaml
from svdebench.core.case import DecisionCase, CaseMetadata
from svdebench.core.artifact import DecisionArtifact
from svdebench.core.trace import DecisionTrace
from svdebench.core.memory import (
    MemoryObject,
    MemoryClass,
    MemoryLifecycleState,
    MemoryContext,
    MemoryTrigger,
    MemoryOutcomeEvaluation,
    MemorySourceEvidence,
)

def load_case_yaml(path_or_str: str) -> DecisionCase:
    if path_or_str.endswith(".yaml") or path_or_str.endswith(".yml"):
        with open(path_or_str, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = yaml.safe_load(path_or_str)
    return DecisionCase.from_dict(data)

def dump_case_yaml(case: DecisionCase) -> str:
    return yaml.dump(case.to_dict(), sort_keys=False, allow_unicode=True)

def load_memory_yaml(path_or_str: str) -> MemoryObject:
    if path_or_str.endswith(".yaml") or path_or_str.endswith(".yml"):
        with open(path_or_str, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        data = yaml.safe_load(path_or_str)
    return MemoryObject.from_dict(data)

def dump_memory_yaml(memory: MemoryObject) -> str:
    return yaml.dump(memory.to_dict(), sort_keys=False, allow_unicode=True)

__all__ = [
    "DecisionCase",
    "CaseMetadata",
    "DecisionArtifact",
    "DecisionTrace",
    "MemoryObject",
    "MemoryClass",
    "MemoryLifecycleState",
    "MemoryContext",
    "MemoryTrigger",
    "MemoryOutcomeEvaluation",
    "MemorySourceEvidence",
    "load_case_yaml",
    "dump_case_yaml",
    "load_memory_yaml",
    "dump_memory_yaml",
]
