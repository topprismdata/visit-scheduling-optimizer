"""Oracle Registry - 记录所有 Oracle 实现实例"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Any

@dataclass
class OracleEntry:
    entry_id: str
    case_id: str
    solver: str
    version: str
    constraints: List[str]
    objective: str
    runtime_seconds: float
    timeout: float
    status: str  # OPTIMAL | FEASIBLE | INFEASIBLE
    objective_value: float
    wall_time: float
    leakage_scan: str = "PASS"

class OracleRegistry:
    def __init__(self):
        self._entries: Dict[str, OracleEntry] = {}

    def register(self, entry: OracleEntry):
        self._entries[entry.entry_id] = entry

    def get(self, entry_id: str) -> OracleEntry:
        return self._entries[entry_id]

    def list_by_case(self, case_id: str) -> List[OracleEntry]:
        return [e for e in self._entries.values() if e.case_id == case_id]

    def export(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self._entries.values()]

    def size(self) -> int:
        return len(self._entries)
