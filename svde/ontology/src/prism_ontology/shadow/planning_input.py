"""PlanningInputProjection v2 — 观察事实流 → 规划输入 (含数据可信度清洗接入).

修复 renjun-18d A 策略的根因缺口:
- synthesize_policies_from_fixture 只把合成频次写入 ws.policies.operational_policies;
- 而 bridge.dispatch_planning_intent / solver 实际消费的是 CustomerEntity.planned_frequency;
- PolicyRegistry → Customer 之间没有任何编译器 -> 注入永不生效 (plan 恒为 0).

本模块提供两个显式、带 provenance 的投影:
1. project_for_replay_v2: execution_fact_stream -> visit_lifecycle_records
   (继承 v1 语义, 新增: 优先消费已清洗事件)
2. materialize_planned_frequency: policy_registry -> CustomerEntity.planned_frequency
   (canonical 契约要求的编译步骤: "Source must be PolicyRegistry, not observation")

红线 (与 projection v1 一致):
- 输入 worldstate 绝不原地修改 (deepcopy 后 object.__setattr__)
- 不写回 fixture; 不加载 BIZ; 派生字段全部带 provenance
"""
from __future__ import annotations

import copy
from dataclasses import replace
from statistics import median
from typing import Any, Dict, List, Optional

from prism_ontology.shadow.projection import (
    Projection, derive_lifecycle_records_from_ef,
)


def materialize_planned_frequency(
    worldstate: Any,
    *,
    rep_id: Optional[str] = None,
    plannable_only: bool = True,
    provenance_assumption: str = "OBSERVED_POLICY_MATERIALIZED",
) -> Projection:
    """把 PolicyRegistry.operational_policies 的 target_frequency_per_month
    编译进 (副本) CustomerEntity.planned_frequency, 供 bridge pattern_space 使用.

    Args:
        worldstate: OperationalDecisionWorldState (只读)
        rep_id: 仅物化该 rep 归属店 (None = 全 universe)
        plannable_only: True 时仅物化 geo_quality EXACT_MATCH/DERIVED 且 location 非空的店
                        (UNMAPPED 店不可参与路线规划 — canonical 门禁)

    Returns:
        Projection(worldstate=副本, provenance, confidence, derived_field_count)
    """
    projected = copy.deepcopy(worldstate)
    registry = getattr(projected, "policies", None)
    op_policies: Dict[str, Any] = dict(getattr(registry, "operational_policies", {}) or {})

    targets = sorted(op_policies)
    if rep_id is not None:
        res = projected.resources.get(rep_id)
        assigned = set(res.assigned_store_codes) if res else set()
        targets = [c for c in targets if c in assigned]

    materialized = 0
    skipped_unmapped = 0
    new_customers = dict(projected.customers)
    for code in targets:
        cust = new_customers.get(code)
        if cust is None:
            continue
        if plannable_only and not cust.is_plannable:
            skipped_unmapped += 1
            continue
        freq = int(op_policies[code].target_frequency_per_month)
        # bridge pattern_space 只支持 1..4 (weekly..monthly); 越界钳位并记录
        clamped = max(1, min(4, freq))
        new_customers[code] = replace(cust, planned_frequency=clamped)
        materialized += 1
    object.__setattr__(projected, "customers", new_customers)

    confidence = round(materialized / len(targets), 3) if targets else 0.0
    return Projection(
        worldstate=projected,
        provenance={
            "algorithm": "MATERIALIZE_PLANNED_FREQUENCY_FROM_POLICY_REGISTRY",
            "version": "v2.0",
            "assumption": provenance_assumption,
            "rep_id": rep_id or "*",
            "targets": len(targets),
            "materialized": materialized,
            "skipped_unmapped": skipped_unmapped,
            "derived_field": "CustomerEntity.planned_frequency",
            "note": "policy_registry -> customer DTO 编译; 不修改原 worldstate",
        },
        confidence=confidence,
        derived_field_count=materialized,
    )


def observed_service_minutes(worldstate: Any, rep_id: str) -> Optional[float]:
    """从 (已清洗) execution_fact_stream 提取该 rep 的在店时长中位数 (分钟).

    仅统计 credit>0 的事件 (summary 无 R2/R3 标记), 防止虚打卡把服务时间基线拉低.
    返回 None = 无可用观测.
    """
    durs = [
        e.service_duration_min for e in worldstate.execution_fact_stream
        if e.rep_id == rep_id and e.service_duration_min and e.service_duration_min > 0
        and "R2:batch_suspect" not in (e.summary or "")
        and "R3:gps_dev" not in (e.summary or "")
    ]
    return round(median(durs), 1) if durs else None


def project_for_replay_v2(worldstate: Any, rep_id: str, period: str,
                          *, materialize_freq: bool = True) -> Projection:
    proj = worldstate
    materialized_n = 0
    if materialize_freq:
        p1 = materialize_planned_frequency(proj, rep_id=rep_id)
        proj = p1.worldstate
        materialized_n = p1.derived_field_count
    p2 = _derive_lifecycle_into(proj, rep_id, period)
    prov = dict(p2.provenance)
    prov["materialized"] = materialized_n
    prov["composed"] = ["materialize_planned_frequency(v2.0)", "derive_lifecycle(v1.0)"]
    return Projection(
        worldstate=p2.worldstate,
        provenance=prov,
        confidence=min(
            p1.confidence if materialize_freq else 1.0, p2.confidence),
        derived_field_count=materialized_n + p2.derived_field_count,
    )


def _derive_lifecycle_into(worldstate: Any, rep_id: str, period: str) -> Projection:
    """projection v1 的纯派生逻辑复用 (derive_lifecycle_records_from_ef)."""
    derived = derive_lifecycle_records_from_ef(worldstate, rep_id, period)
    projected = copy.deepcopy(worldstate)
    object.__setattr__(projected, "visit_lifecycle_records", {r.visit_id: r for r in derived})
    sample = len(derived)
    return Projection(
        worldstate=projected,
        provenance={
            "algorithm": "PROJECT_FROM_EXECUTION_FACT_STREAM",
            "version": "v1.0",
            "assumption": "DERIVED_FROM_HISTORY_CLEANED",
            "source": f"WorldState.execution_fact_stream (rep_id={rep_id}, period={period})",
            "period": period,
            "rep_id": rep_id,
            "sample_size": sample,
            "derived_field": "visit_lifecycle_records",
            "note": "输入事件已经过 R1-R4 清洗",
        },
        confidence=min(1.0, sample / 10.0),
        derived_field_count=sample,
    )
