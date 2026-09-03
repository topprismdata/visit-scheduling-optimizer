"""BaselineComparator — Plan vs Actual 指标对比 (BIZ 无关, 升级版)

职责:
- 输入 MVPResult + WorldState (含 execution_fact_stream 历史实际拜访) + 可选 projection
- 对比 plan_total_stops / actual_total_stops / unique_customers / match_rate
- 输出结构化 ComparisonReport (frozen)
- 严格按 (rep_id, period) 过滤 actual_total_stops
- plan=0 时返回 status=NOT_EVALUABLE, 禁止输出 0.0 误导性指标

严格红线:
- 不修改 MVPResult / WorldState
- 不加载 BIZ 规则
- 不写回 WorldState / 不下发
- 不实现 ShadowReplayRunner
- 不创建新状态报告版本
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set, Any


class ComparisonStatus:
    """ComparisonReport.status (v1.0 升级: 增加 NOT_EVALUABLE)"""
    PASS = "PASS"                 # 一致
    PARTIAL = "PARTIAL"           # 部分一致
    FAIL = "FAIL"                 # 不一致
    NOT_EVALUABLE = "NOT_EVALUABLE"   # 无法评估 (如 plan=0)


@dataclass(frozen=True)
class ComparisonReport:
    """BaselineComparator 输出 (frozen dataclass, v1.0 升级)

    Fields:
        period_label: 计划周期标签
        plan_total_stops: plan 中总 stop 数 (None = plan 缺失)
        actual_total_stops: execution_fact_stream 中按 (rep_id, period) 过滤后总 stop 数 (None = actual 缺失)
        stop_diff: plan - actual (None = 任一缺失)
        plan_unique_customers: plan 中唯一 customer 数
        actual_unique_customers: 按 (rep_id, period) 过滤后唯一 store_code 数
        customer_diff: plan - actual
        match_rate: actual_stops 命中 plan_stops 的比例 (0.0~1.0; 1.0=完全一致)
        status: PASS / PARTIAL / FAIL / NOT_EVALUABLE
        reason: NOT_EVALUABLE 时给出原因 (如 "PLAN_NOT_GENERATED")
        notes: 降级说明列表
    """
    period_label: str
    plan_total_stops: Optional[int] = None
    actual_total_stops: Optional[int] = None
    stop_diff: Optional[int] = None
    plan_unique_customers: Optional[int] = None
    actual_unique_customers: Optional[int] = None
    customer_diff: Optional[int] = None
    match_rate: float = 0.0
    status: str = "NOT_EVALUABLE"
    reason: str = ""
    notes: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.status not in (ComparisonStatus.PASS, ComparisonStatus.PARTIAL,
                                ComparisonStatus.FAIL, ComparisonStatus.NOT_EVALUABLE):
            raise ValueError(f"status 必须是 PASS/PARTIAL/FAIL/NOT_EVALUABLE, 实际: {self.status}")


def _extract_plan_store_codes(mvp_result) -> Optional[Set[str]]:
    if not hasattr(mvp_result, "candidate_plan_summary"):
        return None
    cps = mvp_result.candidate_plan_summary
    if not isinstance(cps, dict) or not cps:
        return None
    store_codes: Set[str] = set()
    # MVP 真实产物键为 daily_routes_summary; daily_routes 为早期 fixture 键
    daily_routes = cps.get("daily_routes") or cps.get("daily_routes_summary") or []
    if not isinstance(daily_routes, list):
        return None
    for route in daily_routes:
        if not isinstance(route, dict):
            continue
        codes = route.get("stops_codes")
        if isinstance(codes, list):
            for c in codes:
                if isinstance(c, str):
                    store_codes.add(c)
        else:
            stops = route.get("stops")
            if isinstance(stops, list):
                for s in stops:
                    if isinstance(s, dict) and isinstance(s.get("store_code"), str):
                        store_codes.add(s["store_code"])
    return store_codes if store_codes else set()


def _extract_actual_store_codes_strict(worldstate, rep_id: str, period: str) -> Optional[Set[str]]:
    """严格按 (rep_id, period) 过滤 actual_total_stops

    v1.0 升级: 之前是全集唯一 store, 现在严格过滤 (rep_id, period)
    """
    if not hasattr(worldstate, "execution_fact_stream"):
        return None
    efs = worldstate.execution_fact_stream
    if efs is None or not isinstance(efs, list):
        return None
    if not efs:
        return set()
    store_codes: Set[str] = set()
    for evt in efs:
        if not isinstance(evt, object):
            continue
        if not hasattr(evt, "rep_id") or not hasattr(evt, "visit_date"):
            continue
        if evt.rep_id != rep_id:
            continue
        # 兼容 datetime.date 和 datetime.datetime (fixture visit_date 是 date 类型)
        if not hasattr(evt.visit_date, "strftime"):
            continue
        evt_month = evt.visit_date.strftime("%Y-%m")
        if evt_month != period:
            continue
        if hasattr(evt, "store_code") and isinstance(evt.store_code, str):
            store_codes.add(evt.store_code)
    return store_codes


def _extract_period_label(mvp_result) -> str:
    if hasattr(mvp_result, "candidate_plan_summary"):
        cps = mvp_result.candidate_plan_summary
        if isinstance(cps, dict):
            pl = cps.get("period_label")
            if isinstance(pl, str):
                return pl
    return "<unknown>"


def compare_mvp_vs_actual(mvp_result, worldstate, rep_id: str = None,
                          period: str = None) -> ComparisonReport:
    """BaselineComparator 主入口 (v1.0 升级)

    Args:
        mvp_result: MVPResult (含 candidate_plan_summary)
        worldstate: WorldState (含 execution_fact_stream)
        rep_id: 目标代表 (新增, 用于 actual 严格过滤)
        period: 计划周期 "YYYY-MM" (新增, 用于 actual 严格过滤)

    Returns:
        ComparisonReport (frozen, 含 status 和 reason)
    """
    notes: List[str] = []
    period_label = _extract_period_label(mvp_result)

    # 1. plan 侧
    plan_codes = _extract_plan_store_codes(mvp_result)
    if plan_codes is None:
        notes.append("MVPResult.candidate_plan_summary 缺失或不可解析, plan 侧指标设为 None")

    plan_total_stops: Optional[int] = len(plan_codes) if plan_codes is not None else None

    # 2. actual 侧 (v1.0 升级: 严格按 rep_id + period 过滤)
    actual_codes: Optional[Set[str]] = None
    actual_total_stops: Optional[int] = None
    if rep_id and period:
        actual_codes = _extract_actual_store_codes_strict(worldstate, rep_id, period)
        if actual_codes is not None:
            actual_total_stops = len(actual_codes)
    else:
        notes.append("rep_id 或 period 缺失, actual 侧用全集唯一 store (v1.0 升级前行为, 不推荐)")

    # 3. status 判定 (v1.0 升级: plan=0 走 NOT_EVALUABLE 路径)
    if plan_total_stops is None or actual_total_stops is None:
        status = ComparisonStatus.NOT_EVALUABLE
        reason = "PLAN_OR_ACTUAL_MISSING"
        stop_diff = None
        customer_diff = None
        match_rate = 0.0
    elif plan_total_stops == 0 and actual_total_stops > 0:
        # v1.0 升级: plan=0 + actual>0 时输出 NOT_EVALUABLE + reason, 禁止 0.0 误导
        status = ComparisonStatus.NOT_EVALUABLE
        reason = "PLAN_NOT_GENERATED"
        stop_diff = None
        customer_diff = None
        match_rate = 0.0
        notes.append("plan=0 时不允许输出 match_rate=0.0 业务指标, 改用 NOT_EVALUABLE")
    else:
        # 正常路径
        stop_diff = plan_total_stops - actual_total_stops
        plan_unique_customers = plan_total_stops
        actual_unique_customers = actual_total_stops
        customer_diff = plan_unique_customers - actual_unique_customers

        if plan_codes is None or actual_codes is None:
            match_rate = 0.0
        elif not actual_codes:
            match_rate = 0.0
        else:
            intersection = plan_codes & actual_codes
            match_rate = round(len(intersection) / len(actual_codes), 4)
            if match_rate == 0.0 and plan_codes:
                notes.append(f"actual 与 plan 无交集 (match_rate=0.0), 但 plan 有 {len(plan_codes)} stops")

        # 状态: PASS>=0.99, PARTIAL=[0.5, 0.99), FAIL<0.5
        if match_rate >= 0.99:
            status = ComparisonStatus.PASS
        elif match_rate >= 0.5:
            status = ComparisonStatus.PARTIAL
        else:
            status = ComparisonStatus.FAIL
        reason = ""

    # 4. 输出
    return ComparisonReport(
        period_label=period_label,
        plan_total_stops=plan_total_stops,
        actual_total_stops=actual_total_stops,
        stop_diff=stop_diff,
        plan_unique_customers=plan_total_stops if plan_total_stops else None,
        actual_unique_customers=actual_total_stops if actual_total_stops else None,
        customer_diff=stop_diff,  # 同义于 plan_total_stops - actual_total_stops
        match_rate=match_rate,
        status=status,
        reason=reason,
        notes=notes,
    )
