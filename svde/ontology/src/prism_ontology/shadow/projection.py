"""PlanningInputProjection — 历史观测 → 规划输入投影层 (BIZ 无关)

职责:
- 输入 WorldState + rep_id + period (不修改 WorldState)
- 派生 visit_lifecycle_records 从 execution_fact_stream (历史事实)
- 输出 Projection 命名元组 (新 worldstate + provenance + confidence)
- 内存投影, 不写回 fixture / WorldState

BIZ 不实现:
- 不加载 BIZ 业务规则
- 不写回
- 不修改 fixture

被 compare.py 消费: 严格按 (rep_id, period) 过滤 actual_total_stops
被 runner.py 消费: 接受 projection 参数
"""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone, date
from typing import List, Dict, Any, Optional
import copy

from prism_ontology.world_model.state_snapshot import (
    OperationalVisitLifecycleRecord,
    LifecycleStatus,
)


@dataclass(frozen=True)
class Projection:
    """PlanningInputProjection 输出 (frozen)

    Fields:
        worldstate: 派生后的新 WorldState (原 WorldState 深拷贝 + 派生字段)
        provenance: dict (algorithm / assumption / source / period)
        confidence: float 0.0~1.0 (基于样本量)
        derived_field_count: int (本次派生新增的字段数)
    """
    worldstate: Any  # WorldState 派生结果
    provenance: Dict[str, Any]
    confidence: float
    derived_field_count: int

    def __post_init__(self):
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"confidence 必须在 [0, 1], 实际: {self.confidence}")
        if self.derived_field_count < 0:
            raise ValueError(f"derived_field_count 必须 >= 0, 实际: {self.derived_field_count}")


def derive_lifecycle_records_from_ef(worldstate, rep_id: str, period: str) -> List[OperationalVisitLifecycleRecord]:
    """从 execution_fact_stream 派生该 rep 该月的 visit_lifecycle_records

    映射关系:
        ActualVisitEvent.event_id         -> OperationalVisitLifecycleRecord.visit_id
        ActualVisitEvent.store_code       -> OperationalVisitLifecycleRecord.store_code
        ActualVisitEvent.rep_id           -> OperationalVisitLifecycleRecord.rep_id
        ActualVisitEvent.visit_date       -> OperationalVisitLifecycleRecord.scheduled_date
        ActualVisitEvent.service_duration_min -> OperationalVisitLifecycleRecord.service_duration_min
    """
    derived = []
    for evt in worldstate.execution_fact_stream:
        if not isinstance(evt.event_id, str):
            continue
        if evt.rep_id != rep_id:
            continue
        evt_month = evt.visit_date.strftime("%Y-%m")
        if evt_month != period:
            continue
        # 派生 LifecycleRecord (历史事件 -> 完成态记录, assumption: 历史已完成)
        record = OperationalVisitLifecycleRecord(
            visit_id=evt.event_id,
            store_code=evt.store_code,
            rep_id=evt.rep_id,
            scheduled_date=evt.visit_date,
            current_status=LifecycleStatus.COMPLETED,  # assumption: 历史已完成
            status_history=[(LifecycleStatus.COMPLETED, evt.visit_date)],
            actual_arrival=None,  # 历史事件无实际打卡时间
            actual_departure=None,
            service_duration_min=evt.service_duration_min or 0.0,
        )
        derived.append(record)
    return derived


def project_for_replay(worldstate, rep_id: str, period: str,
                        provenance_assumption: str = "DERIVED_FROM_HISTORY") -> Projection:
    """主入口: 派生 projection worldstate

    严格只读 worldstate (深拷贝), 派生 lifecycle_records 注入到副本 (in-memory)

    Args:
        worldstate: WorldState (只读, 不修改)
        rep_id: 目标代表
        period: YYYY-MM
        provenance_assumption: 派生假设 (默认 "DERIVED_FROM_HISTORY")

    Returns:
        Projection (新 worldstate + provenance + confidence + derived_field_count)
    """
    if not isinstance(rep_id, str) or not rep_id:
        raise ValueError("rep_id 必须是非空字符串")
    if not isinstance(period, str) or len(period) != 7 or period[4] != "-":
        raise ValueError(f"period 必须 YYYY-MM, 实际: {period!r}")

    # 深拷贝 (避免污染原 worldstate)
    projected_ws = copy.deepcopy(worldstate)

    # 派生 lifecycle_records
    derived_records = derive_lifecycle_records_from_ef(projected_ws, rep_id, period)
    # 注入到副本 (in-memory, 不写回 fixture)
    if hasattr(projected_ws, "visit_lifecycle_records"):
        # 替换原字段 (深拷贝, 不影响原 ws)
        object.__setattr__(projected_ws, "visit_lifecycle_records", {r.visit_id: r for r in derived_records})
    else:
        # worldstate 不支持 setattr (frozen), 需要换用 replace
        projected_ws = replace(projected_ws, visit_lifecycle_records={r.visit_id: r for r in derived_records})

    # 计算 confidence (基于样本量)
    sample_size = len(derived_records)
    confidence = min(1.0, sample_size / 10.0)  # >= 10 个样本 -> 1.0

    # provenance 字段
    provenance = {
        "algorithm": "PROJECT_FROM_EXECUTION_FACT_STREAM",
        "version": "v1.0",
        "assumption": provenance_assumption,
        "source": f"WorldState.execution_fact_stream (rep_id={rep_id}, period={period})",
        "period": period,
        "rep_id": rep_id,
        "sample_size": sample_size,
        "derived_field": "visit_lifecycle_records",
        "note": "此为派生 (derived) 字段, 不修改原 WorldState/fixture",
    }

    return Projection(
        worldstate=projected_ws,
        provenance=provenance,
        confidence=confidence,
        derived_field_count=len(derived_records),
    )
