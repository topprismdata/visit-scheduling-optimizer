"""CQ runner — anti-fabrication competency question validator (Phase 0)."""
from pathlib import Path
from typing import Dict, Any, List


# Anti-fabrication CQ tests (per v1.1 §5.4, 8 minimum CQ with full text)
ANTI_COLLAPSE_CQS: List[Dict[str, Any]] = [
    {
        "cq_id": "CQ-T1",
        "question": "客户被分错了代表",
        "expected_decision_level": "TERRITORY_ALIGNMENT",
        "forbidden_levels": ["DAILY_ROUTE_SEQUENCING"],
    },
    {
        "cq_id": "CQ-T2",
        "question": "四周拜访频次不均匀",
        "expected_decision_level": "PERIODIC_COVERAGE",
        "forbidden_levels": ["DAILY_ROUTE_SEQUENCING"],
    },
    {
        "cq_id": "CQ-T3",
        "question": "单日路线必须使用固定拜访集合",
        "expected_decision_level": "DAILY_ROUTE_SEQUENCING",
        "hard_constraint": "customer_set_must_be_FIXED",
    },
    {
        "cq_id": "CQ-T4",
        "question": "锁定承诺不可降级",
        "hard_constraint": "DistanceMinimization.mustNotOverride(CommitmentLock)",
    },
    {
        "cq_id": "CQ-T5",
        "question": "距离下降不能导致覆盖率下降",
        "hard_constraint": "DistanceMinimization.subordinateTo(CoverageCompliance)",
    },
    {
        "cq_id": "CQ-T6",
        "question": "GAP-6 已永久关闭：销售拜访本体不引入 SOP 对象",
        "frozen_rule": "SOPPolicy / CustomerSOPBinding / CustomerOpRequirement NOT in ontology",
    },
    {
        "cq_id": "CQ-T7",
        "question": "实际拜访不得回写覆盖计划拜访",
        "hard_constraint": "ActualVisit must NOT modify PlannedVisit state",
    },
    {
        "cq_id": "CQ-T8",
        "question": "Customer 不得折叠为 COMMITTED_TASK",
        "hard_constraint": "DomainAdapter fold-score for Customer -> COMMITTED_TASK must be 0",
    },
]


class CQRunner:
    """Phase 0 CQ registry and execution interface."""

    def __init__(self):
        self.cqs: List[Dict[str, Any]] = list(ANTI_COLLAPSE_CQS)

    def all(self) -> List[Dict[str, Any]]:
        return list(self.cqs)

    def run(self, bundle_path: Path) -> Dict[str, Any]:
        """Phase 0 placeholder: returns all CQs as registered without execution."""
        return {
            "total": len(self.cqs),
            "cqs": [cq["cq_id"] for cq in self.cqs],
            "note": "Phase 0 — CQ registration only, no execution yet",
            "bundle": str(bundle_path),
        }
