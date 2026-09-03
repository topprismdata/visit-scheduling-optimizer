"""Vertical Slice MVP 端到端测试 — 验证最小可运行主流程

测试覆盖：
1. 可行重排案例（baseline rep，无资源不可用）
2. 不可行案例（极小有效集，期望 bridge/solver/audit 失败或 PARTIALLY_FEASIBLE）
3. 资源不可用案例（scenario 显式标记 rep 不可用，验证 MVP 不修改 WorldState）

MVP 元数据断言（每次运行都应包含）：
- execution_mode = INTERNAL_VERTICAL_SLICE_MVP
- canonical_api_status = NOT_IMPLEMENTED
- external_dispatch = false
- baseline_writeback = false
- runtime_scope = LEGACY_SVDE_PIPELINE
"""
from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# 添加 svde/ontology/src 到路径
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))

import pytest

from prism_ontology.real_data.world_state_assembler import WorldStateAssembler
from prism_ontology.engine.vertical_slice_mvp import (
    VerticalSliceRunner, ScenarioParameters, MVPResult,
)


FIXTURE_PATH = ROOT / "svde" / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"
FIXTURE_PATH_ALT = Path("/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/svde/ontology/tests/data/fmcg_visit_history_with_geo.xlsx")


def get_world_state():
    """从 fixture 装载 WorldState。"""
    path = str(FIXTURE_PATH if FIXTURE_PATH.exists() else FIXTURE_PATH_ALT)
    return WorldStateAssembler.assemble_from_excel(path, assembled_at=_ASSEMBLED_AT)


def get_working_days_june_2026(n=18):
    """生成 2026 年 6 月的 n 个工作日（简化为日期列表）。"""
    return [f"2026-06-{(i+1):02d}" for i in range(n)]


# ---------- MVP 元数据常量化断言 ----------

MVP_METADATA_KEYS = {
    "execution_mode", "canonical_api_status", "external_dispatch",
    "baseline_writeback", "runtime_scope",
}

def assert_mvp_metadata(result: MVPResult):
    """断言 MVP 元数据完整且符合约定。"""
    for k in MVP_METADATA_KEYS:
        assert hasattr(result, k), f"missing metadata field: {k}"
    assert result.execution_mode == "INTERNAL_VERTICAL_SLICE_MVP"
    assert result.canonical_api_status == "NOT_IMPLEMENTED"
    assert result.external_dispatch is False
    assert result.baseline_writeback is False
    assert result.runtime_scope == "LEGACY_SVDE_PIPELINE"


def assert_mvp_audit_recorded(result: MVPResult, test_name: str):
    """断言 MVP 结果包含可审计字段：scenario_id / run_timestamp / source_world_state 等。"""
    assert result.scenario_id, "scenario_id 缺失"
    assert result.run_timestamp, "run_timestamp 缺失"
    assert result.source_world_state_snapshot_id, "source_world_state_snapshot_id 缺失"
    assert result.legacy_pipeline_steps, "legacy_pipeline_steps 缺失"
    assert result.feasibility_judgment in ("FEASIBLE", "INFEASIBLE", "PARTIALLY_FEASIBLE"), \
        f"无效可行性判定: {result.feasibility_judgment}"
    # 不应有真实写回
    assert result.baseline_writeback is False
    # 不应实际下发
    assert result.external_dispatch is False


# ---------- Case 1: 可行重排 ----------

def test_mvp_feasible_replan_basic():
    """基线代表重排：fixture 中真实代表 → MVP 跑通，输出可审计结果。"""
    world_state = get_world_state()
    runner = VerticalSliceRunner()

    # fixture 中含 7 位代表；选第一个有完整数据的代表
    rep_id = sorted(world_state.resources.keys())[0]
    assert rep_id, "fixture 中应至少有一位代表"

    scenario = ScenarioParameters(
        scenario_id="FEASIBLE_001",
        description=f"基线代表 {rep_id} 重排（无资源不可用约束）",
        scenario_unavailable_rep_ids=frozenset(),  # 无约束
        must_satisfy_min_audit_compliance_rate=0.0,
    )

    result = runner.run(
        world_state=world_state,
        target_rep_id=rep_id,
        period_label="2026-06",
        working_days=get_working_days_june_2026(18),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    # MVP 元数据断言
    assert_mvp_metadata(result)
    assert_mvp_audit_recorded(result, "feasible")

    # 至少应该有 CandidatePlan
    assert result.candidate_plan_summary, "未生成候选方案"
    assert result.candidate_plan_summary.get("rep_id") == rep_id

    # 至少应该跑通 audit
    assert result.audit_report_summary, "未生成审计报告"

    # legacy_pipeline_steps 应记录全部 4 步
    assert len(result.legacy_pipeline_steps) >= 4, "legacy_pipeline_steps 应至少 4 步"

    # 不应有约束违约的元描述 (但 MVP 允许 PARTIALLY_FEASIBLE)
    assert result.feasibility_judgment in ("FEASIBLE", "PARTIALLY_FEASIBLE"), \
        f"基线代表重排应可达 FEASIBLE 或 PARTIALLY_FEASIBLE, 实际: {result.feasibility_judgment}"

    # 强断言: DecisionArtifact 必须生成 (修复前曾因 NameError 缺失)
    assert result.decision_artifact_preview is not None, \
        f"DecisionArtifact preview 必须存在; notes={result.notes}"
    # status 必须是 MVP_PREVIEW, 禁止使用 APPROVED_FOR_EXECUTION (避免业务方误解为已批准)
    assert result.decision_artifact_preview["status"] == "MVP_PREVIEW", \
        f"status 必须是 MVP_PREVIEW (非 APPROVED_FOR_EXECUTION), 实际: {result.decision_artifact_preview['status']}"
    # 必须显式声明是模拟批准
    assert result.decision_artifact_preview.get("approval_simulated") is True, \
        f"必须显式声明 approval_simulated=True, 实际 preview keys: {list(result.decision_artifact_preview.keys())}"
    assert result.decision_artifact_preview.get("external_dispatch") is False
    assert result.decision_artifact_preview.get("baseline_writeback") is False
    assert "MVP_INTERNAL_APPROVER" in result.decision_artifact_preview["approved_by"]
    assert "_preview_warning" in result.decision_artifact_preview
    assert result.notes == [], f"可行案例不应有 notes 错误: {result.notes}"

    # 错误分类应非 PIPELINE_ERROR
    assert result.error_kind != "PIPELINE_ERROR", \
        f"基线代表重排不应触发 PIPELINE_ERROR; error_kind={result.error_kind}"


# ---------- Case 2: 不可行案例 (非法 rep_id) ----------

def test_mvp_infeasible_replan_nonexistent_rep():
    """不存在的 rep_id → 不可行，但 MVP 元数据完整。"""
    world_state = get_world_state()
    runner = VerticalSliceRunner()

    scenario = ScenarioParameters(
        scenario_id="INFEASIBLE_001",
        description="不存在的 rep_id 测试（不可行）",
        scenario_unavailable_rep_ids=frozenset(),
    )

    result = runner.run(
        world_state=world_state,
        target_rep_id="NONEXISTENT_REP_999",
        period_label="2026-06",
        working_days=get_working_days_june_2026(18),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    # MVP 元数据完整
    assert_mvp_metadata(result)
    assert_mvp_audit_recorded(result, "infeasible")

    # business feasibility = INFEASIBLE (目标 rep 在 WorldState 中不存在，业务上无解)
    assert result.feasibility_judgment == "INFEASIBLE", \
        f"non-existent rep 应判 INFEASIBLE, 实际: {result.feasibility_judgment}"
    # system error_kind = PIPELINE_ERROR (Bridge dispatch 失败)
    assert result.error_kind == "PIPELINE_ERROR", \
        f"non-existent rep Bridge 失败应判 PIPELINE_ERROR, 实际: {result.error_kind}"
    # 无候选方案或审计
    assert not result.candidate_plan_summary
    assert not result.audit_report_summary
    # 应记录 legacy 步骤仍尝试
    assert result.legacy_pipeline_steps
    # 应记录失败原因
    assert any("FAILED" in n for n in result.notes), f"应记录失败原因, notes={result.notes}"
    # DecisionArtifact preview 应为 None (因 audit_report 为 None)
    assert result.decision_artifact_preview is None


# ---------- Case 3: 资源不可用（情景注入，不伪造状态机）----------

def test_mvp_resource_unavailable_as_explicit_scenario_input():
    """资源不可用作为情景输入，不伪造 ActualVisitEvent 或状态机。

    验证：
    1. MVP 接受 unavailable_rep_ids 作为测试输入
    2. MVP 不修改 WorldState (baseline_writeback=false)
    3. MVP notes 包含显式说明含 scenario_effect_applied=false
    """
    world_state = get_world_state()
    runner = VerticalSliceRunner()

    # 选 fixture 中第一个代表作为 target
    rep_id = sorted(world_state.resources.keys())[0]

    # 捕获原始 WorldState 的执行流（用于对比）
    original_world_state_id = world_state.snapshot_id
    original_visits_count = len(world_state.execution_fact_stream)
    original_policies_keys = len(world_state.policies.operational_policies)

    scenario = ScenarioParameters(
        scenario_id="RESOURCE_UNAVAIL_001",
        description=f"代表 {rep_id} 不可用测试（场景注入，不修改 WorldState）",
        scenario_unavailable_rep_ids=frozenset({rep_id}),
    )

    result = runner.run(
        world_state=world_state,
        target_rep_id=rep_id,
        period_label="2026-06",
        working_days=get_working_days_june_2026(18),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    # MVP 元数据
    assert_mvp_metadata(result)
    assert_mvp_audit_recorded(result, "resource_unavailable")

    # 场景描述记录
    assert rep_id in result.scenario_unavailable_rep_ids
    assert scenario.scenario_id == result.scenario_id

    # 关键约束：WorldState 必须未被修改（baseline_writeback=false 在 MVP 中强制）
    assert result.baseline_writeback is False
    assert world_state.snapshot_id == original_world_state_id, "WorldState.snapshot_id 被修改！"
    assert len(world_state.execution_fact_stream) == original_visits_count, "WorldState.execution_fact_stream 被修改！"
    assert len(world_state.policies.operational_policies) == original_policies_keys, "WorldState.policies 被修改！"

    # 应记录显式说明
    assert any("Scenario explicitly marks" in n for n in result.notes), \
        f"应记录显式场景说明, notes={result.notes}"
    # 必须显式标注 scenario_effect_applied=false (no-writeback control case)
    assert any("scenario_effect_applied=false" in n for n in result.notes), \
        f"必须显式标注 scenario_effect_applied=false, notes={result.notes}"
    # 资源不可用是显式控制输入 — MVP 不伪造 ActualVisitEvent 或 AVAILABILITY_BLOCKED
    for n in result.notes:
        assert "AVAILABILITY_BLOCKED" not in n, \
            f"MVP 不应伪造 AVAILABILITY_BLOCKED, notes={result.notes}"
        assert "ActualVisitEvent" not in n, \
            f"MVP 不应伪造 ActualVisitEvent, notes={result.notes}"

    # 没有伪造 ActualVisitEvent 或 AVAILABILITY_BLOCKED
    for n in result.notes:
        assert "AVAILABILITY_BLOCKED" not in n
        assert "ActualVisitEvent" not in n or "ResourceAvailability" in n  # ResourceAvailabilityObservation 是允许的（设计目标）

    # 资源不可用案例: Pipeline 跑通（feasibility=FEASIBLE 或 PARTIALLY_FEASIBLE）
    assert result.feasibility_judgment in ("FEASIBLE", "PARTIALLY_FEASIBLE"), \
        f"Pipeline 跑通应可达 FEASIBLE 或 PARTIALLY_FEASIBLE, 实际: {result.feasibility_judgment}"
    # 系统执行状态: 应为 FEASIBLE (Pipeline 全部跑通)
    assert result.error_kind == "FEASIBLE", \
        f"资源不可用情景 Pipeline 全部跑通应判 FEASIBLE, 实际: {result.error_kind}"

    # 强断言: 资源不可用案例仍跑通全流程, DecisionArtifact 必须生成
    assert result.decision_artifact_preview is not None, \
        f"资源不可用案例 DecisionArtifact 必须生成; notes={result.notes}"
    assert result.decision_artifact_preview["status"] == "MVP_PREVIEW"
    assert result.decision_artifact_preview.get("approval_simulated") is True
    assert result.decision_artifact_preview.get("external_dispatch") is False
    assert result.decision_artifact_preview.get("baseline_writeback") is False
    assert "MVP_INTERNAL_APPROVER" in result.decision_artifact_preview["approved_by"]

    # 结构化布尔字段 (替代纯文本 notes): scenario_effect_applied 必须是 False
    # 资源不可用案例是 no-writeback control case — MVP 不真正改派/延期
    assert hasattr(result, "scenario_effect_applied"), "MVPResult 必须含 scenario_effect_applied 结构化字段"
    assert result.scenario_effect_applied is False, \
        f"scenario_effect_applied 必须是 False (no-writeback control case), 实际: {result.scenario_effect_applied}"
    # notes 中的文本标注应与结构化字段一致 (双重记录便于审计追溯)
    assert any("scenario_effect_applied=false" in n for n in result.notes), \
        f"notes 应保留 scenario_effect_applied=false 文本标注以供审计追溯, notes={result.notes}"


# ---------- Case 4": MVP 元数据完整性 ----------

def test_mvp_result_has_all_required_metadata_fields():
    """MVPResult 数据结构必须含全部元数据字段；可序列化为 JSON。"""
    import dataclasses
    fields = {f.name for f in dataclasses.fields(MVPResult)}
    required = {
        "execution_mode", "canonical_api_status", "external_dispatch",
        "baseline_writeback", "runtime_scope",
        "scenario_id", "scenario_description", "scenario_unavailable_rep_ids",
        "scenario_effect_applied",     # 结构化布尔字段（替代纯文本 notes）
        "run_timestamp", "source_world_state_snapshot_id", "source_world_state_path",
        "target_rep_id", "period_label",
        "candidate_plan_summary", "audit_report_summary",
        "constraint_violations", "feasibility_judgment", "error_kind",
        "legacy_pipeline_steps", "decision_artifact_preview", "notes",
    }
    missing = required - fields
    assert not missing, f"MVPResult 缺字段: {missing}"
    # scenario_effect_applied 必须是 bool (结构化字段, 非字符串)
    assert "scenario_effect_applied" in fields
    sf_field = next(f for f in dataclasses.fields(MVPResult) if f.name == "scenario_effect_applied")
    assert sf_field.type is bool or sf_field.type == bool, \
        f"scenario_effect_applied 必须是 bool, 实际 type: {sf_field.type}"


def test_mvp_run_timestamp_required_no_silent_default():
    """MVP run_timestamp 必须显式传入, 禁止 datetime.now() 静默默认."""
    world_state = get_world_state()
    runner = VerticalSliceRunner()
    rep_id = sorted(world_state.resources.keys())[0]
    scenario = ScenarioParameters(scenario_id="TS_REQUIRED", description="run_timestamp 必填校验")

    # 1. 不传 run_timestamp 应抛 ValueError
    try:
        runner.run(
            world_state=world_state, target_rep_id=rep_id,
            period_label="2026-06", working_days=get_working_days_june_2026(4),
            scenario=scenario,
            run_timestamp=None,
        )
        assert False, "MVP 应拒绝 None run_timestamp"
    except ValueError as e:
        assert "MVP requires explicit run_timestamp" in str(e), f"错误信息应说明显式必填, 实际: {e}"

    # 2. 传非 datetime 类型应抛 TypeError
    try:
        runner.run(
            world_state=world_state, target_rep_id=rep_id,
            period_label="2026-06", working_days=get_working_days_june_2026(4),
            scenario=scenario,
            run_timestamp="2026-06-01T09:00:00",  # str 非 datetime
        )
        assert False, "MVP 应拒绝非 datetime 的 run_timestamp"
    except TypeError as e:
        assert "datetime" in str(e)

    # 3. 正常 datetime 应成功
    result = runner.run(
        world_state=world_state, target_rep_id=rep_id,
        period_label="2026-06", working_days=get_working_days_june_2026(4),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )
    assert result.run_timestamp == "2026-06-01T09:00:00+00:00"


def test_mvp_serializable_to_json():
    """MVPResult 可序列化为 JSON（可审计）。"""
    world_state = get_world_state()
    runner = VerticalSliceRunner()
    rep_id = sorted(world_state.resources.keys())[0]

    scenario = ScenarioParameters(
        scenario_id="SERIAL_001",
        description="JSON 序列化测试",
        scenario_unavailable_rep_ids=frozenset(),
    )
    result = runner.run(
        world_state=world_state,
        target_rep_id=rep_id,
        period_label="2026-06",
        working_days=get_working_days_june_2026(4),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    # JSON 序列化必须成功
    import json
    audit_dict = result.to_audit_dict()
    json_str = json.dumps(audit_dict, ensure_ascii=False, indent=2, default=str)
    assert "INTERNAL_VERTICAL_SLICE_MVP" in json_str
    assert "NOT_IMPLEMENTED" in json_str
    assert "false" in json_str  # external_dispatch / baseline_writeback
    assert scenario.scenario_id in json_str


# ---------- Case 5: ConstraintViolation 显式记录 ----------

def test_mvp_constraint_violations_are_recorded():
    """任何约束违约都应在 constraint_violations 中显式记录。"""
    world_state = get_world_state()
    runner = VerticalSliceRunner()
    rep_id = sorted(world_state.resources.keys())[0]

    scenario = ScenarioParameters(
        scenario_id="CONSTRAINT_001",
        description="约束违约记录测试",
        scenario_unavailable_rep_ids=frozenset(),
        must_satisfy_min_audit_compliance_rate=0.99,
    )

    result = runner.run(
        world_state=world_state,
        target_rep_id=rep_id,
        period_label="2026-06",
        working_days=get_working_days_june_2026(18),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    # constraint_violations 字段必须存在 (即使为空)
    assert hasattr(result, "constraint_violations")
    assert isinstance(result.constraint_violations, list)
    # MVP 不修改 WorldState
    assert result.baseline_writeback is False


# ---------- 入口 ----------



# ---------- Case 8: BIZ 框架集成测试 (EXPERIMENTAL DRAFT, NOT SIGNED — MVP 正式基线不启用) ----------
# 注: 本 case 验证 EXPERIMENTAL 框架存在, 但不计入 MVP 正式基线
@pytest.mark.skip(reason="BIZ 框架标记为 EXPERIMENTAL DRAFT, 不计入 MVP 正式基线. 业务方签署前不启用.")
def test_mvp_biz_registry_default_signing_present():
    """MVP 默认应已注册 BIZ-01~09 占位规则 (业务方签署后填实际逻辑)"""
    from prism_ontology.engine.biz_signing import build_default_registry
    registry = build_default_registry()
    for biz_id in ["BIZ-01","BIZ-02","BIZ-03","BIZ-04","BIZ-05","BIZ-06","BIZ-07","BIZ-08","BIZ-09"]:
        assert registry.has(biz_id), f"{biz_id} 未注册"
    print(f"  ✅ 9 项 BIZ 默认注册: {[biz_id for biz_id in ['BIZ-01','BIZ-02','BIZ-03','BIZ-04','BIZ-05','BIZ-06','BIZ-07','BIZ-08','BIZ-09'] if registry.has(biz_id)]}")


@pytest.mark.skip(reason="BIZ 框架标记为 EXPERIMENTAL DRAFT, 不计入 MVP 正式基线. 业务方签署前不启用.")
def test_mvp_biz_violations_overlay_constraint_violations():
    """BIZ 校验违反应叠加到 MVPResult.constraint_violations (结构化字段同时保留)

    验证:
    1. MVPResult.biz_violations 列表含 BIZ 违反结构化数据
    2. MVPResult.constraint_violations 含 BIZ 违反文本 (与结构化字段冗余记录便于审计追溯)
    3. MVPResult.biz_rules_applied = True
    """
    world_state = get_world_state()
    runner = VerticalSliceRunner()
    rep_id = sorted(world_state.resources.keys())[0]
    scenario = ScenarioParameters(
        scenario_id="BIZ_001",
        description="BIZ 框架集成验证 (BIZ 违反叠加到 audit)",
    )
    result = runner.run(
        world_state=world_state, target_rep_id=rep_id,
        period_label="2026-06",
        working_days=get_working_days_june_2026(4),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    # BIZ 框架结构性字段
    assert hasattr(result, "biz_rules_applied"), "MVPResult 必须含 biz_rules_applied 字段"
    assert hasattr(result, "biz_violations"), "MVPResult 必须含 biz_violations 字段"
    assert result.biz_rules_applied is True
    # 业务方签署前 BIZ 校验 mock 全部返回空, biz_violations 为空 list
    assert isinstance(result.biz_violations, list)

    # 业务方签署后 (BIZ-04 mock 模拟 Key 店违规) → biz_violations 含 WARNING/CRITICAL_INCIDENT
    from prism_ontology.engine.biz_signing import BIZSigningRegistry, BIZRule, ConstraintViolation
    custom_registry = BIZSigningRegistry()
    def mock_key_store_violation(plan, world_state, rule):
        return [ConstraintViolation(
            biz_id=rule.biz_id, severity="CRITICAL_INCIDENT",
            message="Key store S001 has 0 visits this month", target="S001"
        )]
    custom_registry.register(
        BIZRule(biz_id="BIZ-04", version="v1.0-MOCK", scope="Tier=Key stores",
                predicate_name="mock_key_store_violation",
                severity_on_violation="CRITICAL_INCIDENT"),
        mock_key_store_violation,
    )
    custom_runner = VerticalSliceRunner(biz_registry=custom_registry)
    result2 = custom_runner.run(
        world_state=world_state, target_rep_id=rep_id,
        period_label="2026-06",
        working_days=get_working_days_june_2026(4),
        scenario=scenario,
        run_timestamp=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
    )
    # 结构化字段含 BIZ 违反
    assert len(result2.biz_violations) >= 1
    biz_v = result2.biz_violations[0]
    assert biz_v["biz_id"] == "BIZ-04"
    assert biz_v["severity"] == "CRITICAL_INCIDENT"
    # constraint_violations 含 BIZ 违反文本
    biz_text_violations = [v for v in result2.constraint_violations if v.startswith("BIZ[")]
    assert len(biz_text_violations) >= 1, f"constraint_violations 应含 BIZ 违反文本, 实际: {result2.constraint_violations}"
    assert "BIZ-04" in biz_text_violations[0]
    # BIZ 校验框架不修改 MVP 主流程主链路
    assert result2.feasibility_judgment == result.feasibility_judgment  # 与默认 registry 一致
    assert result2.error_kind == result.error_kind
    # 4 项 MVP 运行不变量保持
    assert result2.external_dispatch is False
    assert result2.baseline_writeback is False
    assert result2.canonical_api_status == "NOT_IMPLEMENTED"
    assert result2.scenario_effect_applied is False


if __name__ == "__main__":
    # 命令行直接运行（不依赖 pytest）
    import json
    print("Running Vertical Slice MVP end-to-end tests directly...\n")
    print(f"Fixture path: {FIXTURE_PATH if FIXTURE_PATH.exists() else FIXTURE_PATH_ALT}")

    test_funcs = [
        ("MVP 元数据完整性", test_mvp_result_has_all_required_metadata_fields),
        ("Case 1: 可行重排 (强断言 DecisionArtifact)", test_mvp_feasible_replan_basic),
        ("Case 2: 不可行 (nonexistent rep -> PIPELINE_ERROR)", test_mvp_infeasible_replan_nonexistent_rep),
        ("Case 3: 资源不可用 (情景注入)", test_mvp_resource_unavailable_as_explicit_scenario_input),
        ("Case 4: JSON 可序列化", test_mvp_serializable_to_json),
        ("Case 5: 约束违约记录", test_mvp_constraint_violations_are_recorded),
        ("Case 6: run_timestamp 必填校验", test_mvp_run_timestamp_required_no_silent_default),
        ("Case 8: SKIPPED (BIZ EXPERIMENTAL DRAFT — 框架存在性测试, 不计入 MVP 正式基线)", test_mvp_biz_registry_default_signing_present),
        ("Case 9: SKIPPED (BIZ EXPERIMENTAL DRAFT — violations 叠加测试, 不计入 MVP 正式基线)", test_mvp_biz_violations_overlay_constraint_violations),
    ]

    failed = 0
    for name, fn in test_funcs:
        try:
            fn()
            print(f"  ✅ PASS: {name}")
        except Exception as e:
            print(f"  ❌ FAIL: {name} — {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    if failed == 0:
        print(f"All {len(test_funcs)} tests PASSED")
    else:
        print(f"{failed}/{len(test_funcs)} tests FAILED")
        sys.exit(1)
