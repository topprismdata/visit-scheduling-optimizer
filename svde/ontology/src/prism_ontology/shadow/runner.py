"""ShadowReplayRunner — 顶层编排器 (BIZ 无关)

职责:
- 接收 fixture_path + run_params
- 编排 A-E 五个子模块 (无新业务逻辑)
- 4 项 MVP 运行不变量作为入口闸门 (ReadOnlyGuard)
- 输出 ReplayReport (frozen dataclass)
- 任意步骤失败 -> 聚合到 notes + 标记阶段, 仍输出 ReplayReport (不抛)
- 闸门违反 -> 直接标记 invariants_held=False, 不进入后续步骤

严格红线:
- 不实现新业务逻辑
- 不加载 BIZ 规则
- 不修改 MVPResult / WorldState
- 不写回 WorldState / 不下发外部系统
- 不创建新状态报告版本
- 不实现 BaselineComparator / ReplayMetrics / DataPrechecker / InputSnapshot / ReadOnlyGuard 的新逻辑 (仅编排)
"""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any


# 子模块导入 (A-E)
from prism_ontology.shadow.snapshot import InputSnapshot, snapshot_factory
from prism_ontology.shadow.data_precheck import (
    precheck_worldstate,
    DataPrecheckReport,
    Finding,
    FindingSeverity,
    ReportStatus as PrecheckStatus,
)
from prism_ontology.shadow.guard import (
    assert_mvp_invariants, MVP_INVARIANT_FIELDS,
    gate_pre_execution, gate_post_execution, GateBlocked, GateToken,
)
from prism_ontology.shadow.metrics import compute_replay_metrics, MetricsReport
from prism_ontology.shadow.compare import compare_mvp_vs_actual, ComparisonReport

# WorldState 装配 (仅读取, 不写回)
from prism_ontology.real_data.world_state_assembler import WorldStateAssembler

# MVP Runner (仅调用 run(), 不修改)
from prism_ontology.engine.vertical_slice_mvp import (
    VerticalSliceRunner,
    ScenarioParameters,
    MVPResult,
)


# 4 项 MVP 运行不变量期望值 (与 shadow/guard.py 一致)
INVARIANT_EXPECTED = {
    "external_dispatch": False,
    "baseline_writeback": False,
    "canonical_api_status": "NOT_IMPLEMENTED",
    "scenario_effect_applied": False,
}


@dataclass(frozen=True)
class ReplayReport:
    """ShadowReplayRunner 输出 (frozen dataclass)

    Fields:
        snapshot_id: InputSnapshot.snapshot_id
        worldstate_id: OperationalDecisionWorldState.snapshot_id
        period_label: 计划周期标签
        precheck_status: PASS / WARN / FAIL
        precheck_error_count: Precheck error_count
        precheck_warning_count: Precheck warning_count
        metrics: ReplayMetrics 输出
        comparison: BaselineComparator 输出
        invariants_held: 4 项 MVP 不变量是否全部通过
        target_rep_id: 重排目标代表
        notes: 整体运行说明 (含闸门违反/步骤异常等)
        elapsed_seconds: 总运行耗时
        executed_at: 完成时间 (timezone-aware, 默认 UTC)
    """
    snapshot_id: str
    worldstate_id: str
    period_label: str
    precheck_status: str
    precheck_error_count: int
    precheck_warning_count: int
    metrics: Optional[MetricsReport] = None
    comparison: Optional[ComparisonReport] = None
    invariants_held: bool = True
    target_rep_id: str = ""
    notes: List[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    executed_at: Optional[datetime] = None


def _read_fixture_bytes(fixture_path: str) -> bytes:
    """读取 fixture 字节 (只读)"""
    p = Path(fixture_path)
    if not p.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    return p.read_bytes()  # 只读 (不写)


def _load_worldstate(fixture_path: str, assembled_at) -> Any:
    """从 fixture 加载 WorldState (只读, 不写回; 时间契约: assembled_at 必须显式传入且带时区)"""
    if assembled_at is None or assembled_at.tzinfo is None:
        raise ValueError(
            f"run_params['run_timestamp'] 必须显式传入且带时区 (timezone-aware), 实际: {assembled_at!r}"
        )
    return WorldStateAssembler.assemble_from_excel(fixture_path, assembled_at=assembled_at)


def _build_invariants_from_mvp(mvp_result: MVPResult) -> Dict[str, Any]:
    """从 MVPResult 提取 4 项 MVP 运行不变量值"""
    return {
        "external_dispatch": getattr(mvp_result, "external_dispatch", None),
        "baseline_writeback": getattr(mvp_result, "baseline_writeback", None),
        "canonical_api_status": getattr(mvp_result, "canonical_api_status", None),
        "scenario_effect_applied": getattr(mvp_result, "scenario_effect_applied", None),
    }


def run_replay(fixture_path: str, run_params: Dict[str, Any], projection: Any = None) -> ReplayReport:
    """ShadowReplayRunner 顶层入口

    Args:
        fixture_path: fixture 文件绝对路径 (如 "svde/ontology/tests/data/fmcg_visit_history_with_geo.xlsx")
        run_params: dict 含
            - target_rep_id: str
            - period_label: str
            - working_days: List[str]
            - scenario_id: str (默认 "SHADOW_REPLAY")
            - description: str (默认 "Shadow replay run")
            - unavailable_rep_ids: List[str] (默认 [])
            - run_timestamp: datetime (默认 UTC now)

    Returns:
        ReplayReport (frozen)
    """
    start = time.time()
    notes: List[str] = []
    executed_at = datetime.now(timezone.utc)

    # 1. 读取 fixture 字节
    try:
        content_bytes = _read_fixture_bytes(fixture_path)
    except Exception as e:
        return ReplayReport(
            snapshot_id="<load-failed>",
            worldstate_id="<load-failed>",
            period_label=run_params.get("period_label", "<unknown>"),
            precheck_status="FAIL",
            precheck_error_count=1,
            precheck_warning_count=0,
            invariants_held=False,  # fixture 缺失 -> 闸门未通过 = False (不是 True)
            target_rep_id="",
            notes=[f"读取 fixture 字节失败: {e!r}"],
            elapsed_seconds=time.time() - start,
            executed_at=executed_at,
        )

    # 2. 构造 InputSnapshot
    scenario_unavailable = frozenset(run_params.get("unavailable_rep_ids", []))
    scenario = ScenarioParameters(
        scenario_id=run_params.get("scenario_id", "SHADOW_REPLAY"),
        description=run_params.get("description", "Shadow replay run"),
        scenario_unavailable_rep_ids=scenario_unavailable,
    )
    try:
        snapshot = snapshot_factory(
            content_bytes,
            source_path=fixture_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            schema_version=run_params.get("schema_version", "fmcg_visit_history_v1.0"),
            captured_at=run_params.get("run_timestamp"),
        )
    except Exception as e:
        return ReplayReport(
            snapshot_id="<snapshot-failed>",
            worldstate_id="<load-failed>",
            period_label=run_params.get("period_label", "<unknown>"),
            precheck_status="FAIL",
            precheck_error_count=1,
            precheck_warning_count=0,
            notes=[f"InputSnapshot 构造失败: {e!r}"],
            elapsed_seconds=time.time() - start,
            executed_at=executed_at,
        )

    # 3. 加载 WorldState (或接受 projection 注入)
    try:
        worldstate = _load_worldstate(fixture_path, assembled_at=run_params.get("run_timestamp"))
        # 如果调用方传 projection, 用 projection.worldstate 替换 (in-memory, 不写回)
        if projection is not None:
            worldstate = projection.worldstate
            notes.append(f"已注入 projection (provenance={projection.provenance.get('algorithm', '?')})")
    except Exception as e:
        return ReplayReport(
            snapshot_id=snapshot.snapshot_id,
            worldstate_id="<load-failed>",
            period_label=run_params.get("period_label", "<unknown>"),
            precheck_status="FAIL",
            precheck_error_count=1,
            precheck_warning_count=0,
            notes=[f"WorldState 加载失败: {e!r}"],
            elapsed_seconds=time.time() - start,
            executed_at=executed_at,
        )

    # 4. DataPrecheck
    try:
        precheck = precheck_worldstate(snapshot, worldstate)
    except Exception as e:
        notes.append(f"DataPrecheck 异常: {e!r}")
        precheck = DataPrecheckReport(
            status=PrecheckStatus.FAIL,
            snapshot_id=snapshot.snapshot_id,
            worldstate_id=worldstate.snapshot_id,
            checked_fields=[],
            findings=[Finding(FindingSeverity.ERROR, "PRECHECK_EXCEPTION", f"DataPrecheck 执行异常: {e!r}")],
            error_count=1,
            warning_count=0,
        )

    # 4.5 Pre-execution Runtime Gate (可阻止): fixture 完整性 + frozen 类型 + 指纹捕获
    gate_token: Optional[GateToken] = None
    if precheck.status == PrecheckStatus.FAIL:
        notes.append(f"Precheck FAIL ({precheck.error_count} errors), 不进入 MVP run")
    else:
        try:
            gate_token = gate_pre_execution(worldstate, snapshot, fixture_path)
        except GateBlocked as e:
            notes.append(f"Pre-execution gate 阻止: {e.reason}")
        except Exception as e:
            notes.append(f"Pre-execution gate 异常: {e!r}")

    # 5. MVP Run (仅当 pre-gate 通过)
    mvp_result: Optional[MVPResult] = None
    if gate_token is not None:
        try:
            runner = VerticalSliceRunner()
            mvp_result = runner.run(
                world_state=worldstate,
                target_rep_id=run_params["target_rep_id"],
                period_label=run_params.get("period_label", "2026-06"),
                working_days=run_params.get("working_days", []),
                scenario=scenario,
                run_timestamp=run_params.get("run_timestamp"),
            )
        except Exception as e:
            notes.append(f"MVP run 异常: {e!r}")

    # 6. MVP 不变量闸门 (仅当 mvp_result 存在时)
    invariants_held = True
    if mvp_result is not None:
        invariants = _build_invariants_from_mvp(mvp_result)
        try:
            assert_mvp_invariants(invariants)
        except Exception as e:
            invariants_held = False
            notes.append(
                f"4 项 MVP 不变量闸门违反: {e.violated_field if hasattr(e, 'violated_field') else e!r}"
            )

        # Post-execution 突变检测 (runtime gate): 比对 WorldState 深度指纹
        if gate_token is not None:
            mutation_result = gate_post_execution(gate_token, worldstate)
            if not mutation_result.passed:
                invariants_held = False
                notes.append(f"Post-execution 突变检测: {mutation_result.violations[0].message}")
    else:
        invariants_held = None  # 尚未运行 MVP, 不评判闸门

    # 7. ReplayMetrics (仅当 mvp_result 存在)
    metrics: Optional[MetricsReport] = None
    if mvp_result is not None:
        try:
            metrics = compute_replay_metrics(mvp_result, worldstate)
        except Exception as e:
            notes.append(f"ReplayMetrics 异常: {e!r}")

    # 8. BaselineComparator (仅当 mvp_result 存在, 传 rep_id + period 用于严格过滤)
    comparison: Optional[ComparisonReport] = None
    if mvp_result is not None:
        try:
            comparison = compare_mvp_vs_actual(
                mvp_result, worldstate,
                rep_id=run_params.get("target_rep_id"),
                period=run_params.get("period_label"),
            )
        except Exception as e:
            notes.append(f"BaselineComparator 异常: {e!r}")

    return ReplayReport(
        snapshot_id=snapshot.snapshot_id,
        worldstate_id=worldstate.snapshot_id,
        period_label=run_params.get("period_label", "<unknown>"),
        precheck_status=precheck.status,
        precheck_error_count=precheck.error_count,
        precheck_warning_count=precheck.warning_count,
        metrics=metrics,
        comparison=comparison,
        invariants_held=bool(invariants_held) if invariants_held is not None else False,
        target_rep_id=run_params.get("target_rep_id", ""),
        notes=notes,
        elapsed_seconds=time.time() - start,
        executed_at=executed_at,
    )
