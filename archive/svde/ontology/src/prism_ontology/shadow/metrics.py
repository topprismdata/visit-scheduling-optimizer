"""ReplayMetrics — 指标采集 (BIZ 无关)

职责:
- 输入 MVPResult + WorldState (duck-typed)
- 输出结构化 MetricsReport (frozen dataclass)
- 纯函数, 不修改输入
- 字段缺失时优雅降级 (缺字段 -> 跳过指标 + notes 标注)

采集指标 (MVP 范围内, 不依赖 BIZ 业务规则):
- frequency_compliance_rate: 计划拜访总次数 / customer 频次规则累计 (仅当 policies.operational_policies 存在 target_frequency_per_month)
- unique_customers_visited: 计划拜访的 customer 唯一数
- total_routes: 计划路线数 (= plan 日数)
- total_stops: 计划拜访总次数
- avg_stops_per_route: total_stops / total_routes (0 路线时为 0.0)

严格红线:
- 不修改 MVPResult / WorldState
- 不加载 BIZ 规则
- 不写回 WorldState / 不下发外部系统
- 不实现 BaselineComparator / ShadowReplayRunner
- 不创建新状态报告版本
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass(frozen=True)
class MetricsReport:
    """ReplayMetrics 输出 (frozen dataclass)

    Fields:
        snapshot_id: 关联的 WorldState snapshot_id
        frequency_compliance_rate: 频次达成率 (0.0~1.0, 缺失时 None)
        unique_customers_visited: 计划拜访的 customer 唯一数 (缺失时 None)
        total_routes: 计划路线数 (缺失时 None)
        total_stops: 计划拜访总次数 (缺失时 None)
        avg_stops_per_route: 平均每条路线拜访数 (缺失或 total_routes=0 时 0.0)
        notes: 降级说明 (例如 "policies.operational_policies 缺失, 跳过频次达成率")
    """
    snapshot_id: str
    frequency_compliance_rate: Optional[float] = None
    unique_customers_visited: Optional[int] = None
    total_routes: Optional[int] = None
    total_stops: Optional[int] = None
    avg_stops_per_route: float = 0.0
    notes: List[str] = field(default_factory=list)


def _extract_plan(mvp_result) -> Optional[dict]:
    """从 MVPResult.candidate_plan_summary 提取 plan dict (若缺失则 None)"""
    if not hasattr(mvp_result, "candidate_plan_summary"):
        return None
    cps = mvp_result.candidate_plan_summary
    if not isinstance(cps, dict) or not cps:
        return None
    return cps


def _extract_worldstate_id(worldstate) -> str:
    """从 WorldState 提取 snapshot_id, 缺失时返回 "<unknown>"""
    if hasattr(worldstate, "snapshot_id") and worldstate.snapshot_id:
        return worldstate.snapshot_id
    return "<unknown>"


def _extract_planned_store_codes(plan: dict) -> List[str]:
    """从 plan.daily_routes 提取所有计划拜访的 store_code 列表"""
    store_codes: List[str] = []
    # MVP 真实产物键为 daily_routes_summary (vertical_slice_mvp._summarize_plan);
    # daily_routes 为早期测试 fixture 键, 保留兼容
    daily_routes = plan.get("daily_routes") or plan.get("daily_routes_summary") or []
    if not isinstance(daily_routes, list):
        return store_codes
    for route in daily_routes:
        if not isinstance(route, dict):
            continue
        # 优先用 stops_codes 字段 (MVP 已生成)
        codes = route.get("stops_codes")
        if isinstance(codes, list):
            store_codes.extend(c for c in codes if isinstance(c, str))
        else:
            # 备选: stops 列表
            stops = route.get("stops")
            if isinstance(stops, list):
                for s in stops:
                    if isinstance(s, dict) and isinstance(s.get("store_code"), str):
                        store_codes.append(s["store_code"])
    return store_codes


def _extract_policies_frequency_total(worldstate) -> Optional[int]:
    """从 WorldState.policies.operational_policies 提取所有 target_frequency_per_month 累计

    缺失或字段不存在 -> 返回 None
    """
    if not hasattr(worldstate, "policies"):
        return None
    policies = worldstate.policies
    if policies is None:
        return None
    # MVP 中 PolicyRegistry.operational_policies 是 Dict[str, OperationalVisitPolicy]
    op_policies = getattr(policies, "operational_policies", None)
    if not isinstance(op_policies, dict) or not op_policies:
        return None
    total = 0
    count = 0
    for op in op_policies.values():
        freq = getattr(op, "target_frequency_per_month", None)
        if isinstance(freq, (int, float)) and freq > 0:
            total += int(freq)
            count += 1
    if count == 0:
        return None
    return total


def compute_replay_metrics(mvp_result, worldstate) -> MetricsReport:
    """ReplayMetrics 主入口

    Args:
        mvp_result: MVPResult (MVP 主流程产物, 包含 candidate_plan_summary)
        worldstate: OperationalDecisionWorldState (基线 + 历史)

    Returns:
        MetricsReport (frozen)

    优雅降级: 字段缺失时指标为 None / 0.0, notes 记录降级原因
    """
    notes: List[str] = []
    snapshot_id = _extract_worldstate_id(worldstate)

    plan = _extract_plan(mvp_result)
    if plan is None:
        notes.append("MVPResult.candidate_plan_summary 缺失或为空, 所有指标设为 None")
        return MetricsReport(
            snapshot_id=snapshot_id,
            frequency_compliance_rate=None,
            unique_customers_visited=None,
            total_routes=None,
            total_stops=None,
            avg_stops_per_route=0.0,
            notes=notes,
        )

    # MVP 真实产物键为 daily_routes_summary; daily_routes 为早期 fixture 键
    daily_routes = plan.get("daily_routes") or plan.get("daily_routes_summary") or []
    total_routes = len(daily_routes) if isinstance(daily_routes, list) else 0

    store_codes = _extract_planned_store_codes(plan)
    total_stops = len(store_codes)
    unique_customers_visited = len(set(store_codes))

    if total_routes == 0:
        avg_stops_per_route = 0.0
        if total_stops == 0:
            notes.append("plan.daily_routes 为空且无 stop, 路线/停留数均为 0")
    else:
        avg_stops_per_route = round(total_stops / total_routes, 4)

    # 频次达成率 (依赖 policies.operational_policies, 缺失时降级)
    frequency_compliance_rate: Optional[float] = None
    freq_total = _extract_policies_frequency_total(worldstate)
    if freq_total is None:
        notes.append("WorldState.policies.operational_policies 缺失或不含 target_frequency_per_month, 跳过频次达成率")
    elif total_stops == 0:
        notes.append("无计划 stop, 频次达成率设为 0.0")
        frequency_compliance_rate = 0.0
    else:
        # ratio = min(1.0, total_stops / freq_total)
        ratio = total_stops / freq_total
        frequency_compliance_rate = round(min(1.0, ratio), 4)

    return MetricsReport(
        snapshot_id=snapshot_id,
        frequency_compliance_rate=frequency_compliance_rate,
        unique_customers_visited=unique_customers_visited,
        total_routes=total_routes if total_routes > 0 else None,
        total_stops=total_stops,
        avg_stops_per_route=avg_stops_per_route,
        notes=notes,
    )
