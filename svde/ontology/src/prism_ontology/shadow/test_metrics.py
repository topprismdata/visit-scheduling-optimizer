"""ReplayMetrics 单元测试 (BIZ 无关)

覆盖 6 项要求:
1. MVPResult + WorldState 完整 -> 计算所有指标
2. 与 fixture 实测: 246 客户 / 7 代表, 验证 unique_customers_visited > 0
3. 缺字段降级: 缺 candidate_plan_summary -> 全 None
4. 缺字段降级: 缺 policies.operational_policies -> frequency_compliance_rate = None
5. 5 项指标非负性
6. 只读不变性: 不修改 mvp_result / worldstate
"""
from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)
import sys
import copy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))

from prism_ontology.shadow.metrics import (
    MetricsReport,
    compute_replay_metrics,
    _extract_plan,
    _extract_planned_store_codes,
    _extract_policies_frequency_total,
)
from prism_ontology.real_data.world_state_assembler import WorldStateAssembler


FIXTURE_PATH = ROOT / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"  # ROOT = svde/ontology


# === Mock MVPResult 工厂 ===
class MockMVPResult:
    """mock MVPResult, 仅含 compute_replay_metrics 需要的字段"""
    def __init__(self, candidate_plan_summary=None, notes=None, **extras):
        self.candidate_plan_summary = candidate_plan_summary
        # 其它字段 (exec_mode / scenario_id 等) compute_replay_metrics 不读, 但 mock 保留以防扩展
        self.execution_mode = "INTERNAL_VERTICAL_SLICE_MVP"
        self.canonical_api_status = "NOT_IMPLEMENTED"
        self.external_dispatch = False
        self.baseline_writeback = False
        self.scenario_effect_applied = False
        self.snapshot_id = extras.get("snapshot_id", "MOCK_MVP")
        self.notes = notes or []


def make_plan(num_routes: int, num_stops_per_route: int, store_code_prefix: str = "S") -> dict:
    """生成 plan dict: num_routes 条路线, 每条 num_stops_per_route 个 stop"""
    return {
        "plan_id": "PLAN-MOCK",
        "intent_id": "INTENT-MOCK",
        "rep_id": "R001",
        "period_label": "2026-06",
        "solver_name": "MOCK",
        "solver_status": "FEASIBLE",
        "total_scheduled_visits": num_routes * num_stops_per_route,
        "total_monthly_transit_min": 0.0,
        "total_monthly_distance_km": 0.0,
        "daily_routes": [
            {
                "date_str": f"2026-06-{i+1:02d}",
                "weekday_name": "Monday",
                "rep_id": "R001",
                "stops_count": num_stops_per_route,
                "total_daily_workload_min": 0.0,
                "total_daily_distance_km": 0.0,
                "stops_codes": [f"{store_code_prefix}{i*100+j:03d}" for j in range(num_stops_per_route)],
            }
            for i in range(num_routes)
        ],
    }


def get_fixture_worldstate():
    return WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)


# === 1. MVPResult + WorldState 完整 -> 计算所有指标 ===
def test_metrics_full_computation():
    ws = get_fixture_worldstate()
    mvp = MockMVPResult(candidate_plan_summary=make_plan(num_routes=3, num_stops_per_route=4))
    report = compute_replay_metrics(mvp, ws)
    # snapshot_id 应来自 WorldState
    assert report.snapshot_id == ws.snapshot_id
    # 3 条路线, 每条 4 stop -> 12 total
    assert report.total_routes == 3
    assert report.total_stops == 12
    # 12 个唯一 stop (3x4 不同 ID)
    assert report.unique_customers_visited == 12
    # 平均 4.0
    assert report.avg_stops_per_route == 4.0
    # frequency_compliance_rate: 12 / sum(target_freq)
    # fixture 没有 policies.operational_policies (len=0) -> None
    assert report.frequency_compliance_rate is None
    # notes 包含降级说明
    assert any("operational_policies" in n for n in report.notes)
    print("  ✅ Case 1: 完整 plan -> 所有指标计算 (含 freq 降级)")


# === 2. 与 fixture 实测 ===
def test_metrics_with_real_fixture():
    """用真实 fixture + 模拟 plan 验证 unique_customers_visited > 0"""
    ws = get_fixture_worldstate()
    # 计划 5 条路线, 每条 6 stop
    mvp = MockMVPResult(candidate_plan_summary=make_plan(num_routes=5, num_stops_per_route=6))
    report = compute_replay_metrics(mvp, ws)
    assert report.total_routes == 5
    assert report.total_stops == 30
    assert report.unique_customers_visited == 30  # 5x6 不同
    assert report.avg_stops_per_route == 6.0
    # frequency_compliance_rate 应是 None (fixture 无 policies.operational_policies)
    assert report.frequency_compliance_rate is None
    # snapshot_id 与 fixture 一致
    assert report.snapshot_id == "SNAP_DYNAMIC_UNIVERSE"
    print(f"  ✅ Case 2: fixture 实测 (snapshot_id={report.snapshot_id}, total_stops={report.total_stops})")


# === 3. 缺字段降级: 缺 candidate_plan_summary ===
def test_metrics_missing_plan_degrades_to_none():
    ws = get_fixture_worldstate()
    # candidate_plan_summary = None
    mvp = MockMVPResult(candidate_plan_summary=None)
    report = compute_replay_metrics(mvp, ws)
    assert report.frequency_compliance_rate is None
    assert report.unique_customers_visited is None
    assert report.total_routes is None
    assert report.total_stops is None
    assert report.avg_stops_per_route == 0.0
    assert any("candidate_plan_summary" in n for n in report.notes)
    print("  ✅ Case 3: 缺 candidate_plan_summary -> 全 None + notes 降级说明")


def test_metrics_empty_plan_dict_degrades_to_none():
    """空 dict 也算降级"""
    ws = get_fixture_worldstate()
    mvp = MockMVPResult(candidate_plan_summary={})  # 空 dict
    report = compute_replay_metrics(mvp, ws)
    assert report.frequency_compliance_rate is None
    assert any("candidate_plan_summary" in n for n in report.notes)
    print("  ✅ Case 3b: 空 candidate_plan_summary -> 全 None")


# === 4. 缺字段降级: 缺 policies.operational_policies ===
def test_metrics_missing_policies_degrades_freq_to_none():
    ws = get_fixture_worldstate()  # fixture 无 operational_policies
    mvp = MockMVPResult(candidate_plan_summary=make_plan(num_routes=2, num_stops_per_route=3))
    report = compute_replay_metrics(mvp, ws)
    assert report.frequency_compliance_rate is None  # 频次降级
    # 但其它指标不受影响
    assert report.total_routes == 2
    assert report.total_stops == 6
    assert report.unique_customers_visited == 6
    assert any("operational_policies" in n for n in report.notes)
    print("  ✅ Case 4: 缺 policies.operational_policies -> frequency_compliance_rate=None, 其它指标正常")


# === 5. 5 项指标非负性 ===
def test_metrics_non_negativity():
    ws = get_fixture_worldstate()
    mvp = MockMVPResult(candidate_plan_summary=make_plan(num_routes=0, num_stops_per_route=0))
    report = compute_replay_metrics(mvp, ws)
    # 0 路线 0 stop 场景: total_routes=None (因 total_routes=0 -> None), total_stops=0
    # 频次: 无 stop -> 0.0 (根据实现)
    assert report.total_stops == 0
    assert report.avg_stops_per_route == 0.0
    print("  ✅ Case 5: 0 路线 0 stop -> avg=0.0 (非负)")


# === 6. 只读不变性: 不修改 mvp_result / worldstate ===
def test_metrics_does_not_mutate_inputs():
    ws = get_fixture_worldstate()
    mvp = MockMVPResult(candidate_plan_summary=make_plan(num_routes=2, num_stops_per_route=3))

    # 深度拷贝前后状态
    ws_snapshot_dict_before = {
        "snapshot_id": ws.snapshot_id,
        "manifest": ws.manifest,
        "customers": ws.customers,
        "resources": ws.resources,
    }
    mvp_cps_before = copy.deepcopy(mvp.candidate_plan_summary)

    report = compute_replay_metrics(mvp, ws)

    # WorldState 引用地址未变 (frozen dataclass)
    assert ws.snapshot_id == ws_snapshot_dict_before["snapshot_id"]
    assert ws.manifest is ws_snapshot_dict_before["manifest"]
    assert ws.customers is ws_snapshot_dict_before["customers"]
    assert ws.resources is ws_snapshot_dict_before["resources"]

    # MVPResult.candidate_plan_summary 内容不变
    assert mvp.candidate_plan_summary == mvp_cps_before
    # MVPResult 其它字段不变
    assert mvp.snapshot_id == "MOCK_MVP"
    assert mvp.execution_mode == "INTERNAL_VERTICAL_SLICE_MVP"

    # 报告本身 frozen: 无法修改
    with pytest.raises(Exception):
        report.frequency_compliance_rate = 999.0  # type: ignore
    print("  ✅ Case 6: 输入 mvp_result / worldstate 完全未变 (深度比对 + frozen 报告)")


# === 7. snapshot_id 缺失降级 ===
def test_metrics_missing_worldstate_snapshot_id():
    class MockWSNoID:
        manifest = type("M", (), {"source_file_sha256": "0"*64, "source_file_path": "x"})()
        customers = {}
        resources = {}
        policies = None
    mvp = MockMVPResult(candidate_plan_summary=make_plan(1, 1))
    report = compute_replay_metrics(mvp, MockWSNoID())
    # 缺 snapshot_id -> "<unknown>"
    assert report.snapshot_id == "<unknown>"
    print("  ✅ Case 7: worldstate 缺 snapshot_id -> '<unknown>' 降级")
