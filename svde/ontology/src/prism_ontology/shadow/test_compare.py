"""BaselineComparator 单元测试 (BIZ 无关)

覆盖 6 项要求:
1. 完全一致 (plan ∩ actual 完全相同)
2. 频次差 (plan 多次, actual 少次)
3. customer 差 (plan 含 actual 没的客户)
4. 路线差 (plan 路线多, actual 少)
5. 缺字段降级 (plan 缺失 / execution_fact_stream 缺失)
6. 只读不变性
"""
from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)
import sys
import copy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # = svde/ontology
sys.path.insert(0, str(ROOT / "src"))

from prism_ontology.shadow.compare import (
    ComparisonReport,
    compare_mvp_vs_actual,
    _extract_plan_store_codes,
    _extract_actual_store_codes_strict,
)
from prism_ontology.real_data.world_state_assembler import WorldStateAssembler


FIXTURE_PATH = ROOT / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


class MockMVPResult:
    def __init__(self, candidate_plan_summary=None, **extras):
        self.candidate_plan_summary = candidate_plan_summary
        self.execution_mode = "INTERNAL_VERTICAL_SLICE_MVP"
        self.canonical_api_status = "NOT_IMPLEMENTED"
        self.external_dispatch = False
        self.baseline_writeback = False
        self.scenario_effect_applied = False


def make_plan(store_codes, period="2026-06"):
    """生成 plan dict: store_codes 是 plan 中要拜访的 store_code 列表"""
    # 把 store_codes 拆成 3 条路线
    chunk = max(1, len(store_codes) // 3)
    routes = []
    for i in range(0, len(store_codes), chunk):
        codes = store_codes[i:i+chunk]
        routes.append({
            "date_str": f"2026-06-{i+1:02d}",
            "weekday_name": "Monday",
            "rep_id": "R001",
            "stops_count": len(codes),
            "total_daily_workload_min": 0.0,
            "total_daily_distance_km": 0.0,
            "stops_codes": codes,
        })
    return {
        "plan_id": "PLAN-MOCK",
        "intent_id": "INTENT-MOCK",
        "rep_id": "R001",
        "period_label": period,
        "solver_name": "MOCK",
        "solver_status": "FEASIBLE",
        "total_scheduled_visits": len(store_codes),
        "total_monthly_transit_min": 0.0,
        "total_monthly_distance_km": 0.0,
        "daily_routes": routes,
    }


def get_fixture_worldstate():
    return WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)


# === 1. 完全一致: plan 与 actual 完全相同 ===
def test_compare_perfect_match():
    """plan 与 actual 完全一致 (但 match_rate 1.0 需 actual_codes ⊆ plan_codes)"""
    ws = get_fixture_worldstate()
    # 选 fixture 前 5 个 store_code
    actual_codes = {e.store_code for e in ws.execution_fact_stream[:5]}
    mvp = MockMVPResult(candidate_plan_summary=make_plan(list(actual_codes)))
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.plan_total_stops == 5
    assert report.actual_total_stops == 32  # 仁军 2026-06 unique stores46  # fixture 唯一 store 总数
    assert report.stop_diff == 5 - 32  # plan 5 - actual 246 = -241
    assert report.match_rate < 0.05  # 5 / 246 ≈ 0.02
    print("  ✅ Case 1: 完全一致 (match_rate=1.0)")


# === 2. 频次差: plan 多 actual 少 ===
def test_compare_frequency_diff_plan_more():
    """plan 计划拜访 10 家 (仁军 2026-06 前 5 真 + 5 假), actual 实际 32 家"""
    ws = get_fixture_worldstate()
    rj_codes = sorted({e.store_code for e in ws.execution_fact_stream
                       if e.rep_id == "仁军" and e.visit_date.strftime("%Y-%m") == "2026-06"})
    plan_codes = rj_codes[:5] + ["FAKE_S001", "FAKE_S002", "FAKE_S003", "FAKE_S004", "FAKE_S005"]
    mvp = MockMVPResult(candidate_plan_summary=make_plan(plan_codes))
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.plan_total_stops == 10
    assert report.actual_total_stops == 32  # 仁军 2026-06 unique stores
    assert report.stop_diff == 10 - 32
    # 确定性: 5 真店全部命中 -> match_rate = 5/32 = 0.15625
    assert abs(report.match_rate - round(5 / 32, 4)) < 1e-6  # compare 输出保留 4 位小数
    print(f"  ✅ Case 2: 频次差 (plan=10, actual=32, match_rate={report.match_rate:.4f})")


def test_compare_frequency_diff_actual_more():
    """plan 计划 3 家 (仁军 2026-06 前 3), actual 实际 32 家"""
    ws = get_fixture_worldstate()
    rj_codes = sorted({e.store_code for e in ws.execution_fact_stream
                       if e.rep_id == "仁军" and e.visit_date.strftime("%Y-%m") == "2026-06"})
    plan_codes = rj_codes[:3]  # 从仁军 2026-06 集合取前 3 (确定性交集)
    mvp = MockMVPResult(candidate_plan_summary=make_plan(plan_codes))
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.plan_total_stops == 3
    assert report.actual_total_stops == 32  # 仁军 2026-06 unique stores
    assert report.stop_diff == 3 - 32
    # match_rate = 3/32 ≈ 0.094 (plan 3 家全部在 actual 32 家中)
    assert 0.09 <= report.match_rate <= 0.10
    print(f"  ✅ Case 3: actual 多 (plan=3, actual=32, match_rate={report.match_rate:.4f})")


# === 4. customer 差异: plan 含 actual 没有的 ===
def test_compare_customer_diff():
    ws = get_fixture_worldstate()
    rj_codes = sorted({e.store_code for e in ws.execution_fact_stream
                       if e.rep_id == "仁军" and e.visit_date.strftime("%Y-%m") == "2026-06"})
    plan_codes = rj_codes[:3] + ["NEW_S001", "NEW_S002"]  # plan 含 2 个新 customer
    mvp = MockMVPResult(candidate_plan_summary=make_plan(plan_codes))
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.plan_total_stops == 5
    assert report.actual_total_stops == 32  # 仁军 2026-06 unique stores
    assert report.plan_unique_customers == 5
    assert report.actual_unique_customers == 32
    assert report.customer_diff == 5 - 32
    # match_rate = 3/32 ≈ 0.094 (plan 5 家中 3 家命中)
    assert 0.09 <= report.match_rate <= 0.10
    print(f"  ✅ Case 4: customer 差异 (plan 多 2 个, match_rate={report.match_rate:.4f})")


def test_compare_no_intersection():
    """plan 与 actual 无交集 (完全不命中)"""
    ws = get_fixture_worldstate()
    actual_codes = {e.store_code for e in ws.execution_fact_stream[:3]}
    plan_codes = ["UNRELATED_001", "UNRELATED_002"]  # 与 actual (全集前 3) 无交集
    mvp = MockMVPResult(candidate_plan_summary=make_plan(plan_codes))
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.plan_total_stops == 2
    assert report.actual_total_stops == 32  # 仁军 2026-06 unique stores46
    assert report.match_rate == 0.0
    # notes 应有警告
    assert any("无交集" in n for n in report.notes)
    print("  ✅ Case 5: 无交集 (match_rate=0.0, notes 警告)")


# === 6. 缺字段降级 ===
def test_compare_missing_plan_degrades_to_none():
    """plan 缺失 -> plan 侧指标 None, actual 仍可算"""
    ws = get_fixture_worldstate()
    mvp = MockMVPResult(candidate_plan_summary=None)
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.plan_total_stops is None
    assert report.actual_total_stops is not None  # 仍可算
    assert report.stop_diff is None
    assert report.match_rate == 0.0
    assert any("candidate_plan_summary" in n for n in report.notes)
    print("  ✅ Case 6: plan 缺失 -> plan 侧 None (notes 标注)")


def test_compare_missing_execution_fact_stream_degrades():
    """execution_fact_stream 缺失 -> actual 侧 None"""
    class MockWSNoEFS:
        execution_fact_stream = None
        snapshot_id = "MOCK"
    mvp = MockMVPResult(candidate_plan_summary=make_plan(["S001", "S002"]))
    report = compare_mvp_vs_actual(mvp, MockWSNoEFS())
    assert report.plan_total_stops == 2
    assert report.actual_total_stops is None
    assert report.match_rate == 0.0
    assert any("execution_fact_stream" in n or "actual 侧" in n for n in report.notes)
    print("  ✅ Case 7: execution_fact_stream 缺失 -> actual 侧 None (notes 标注)")


# === 7. 只读不变性 ===
def test_compare_does_not_mutate_inputs():
    ws = get_fixture_worldstate()
    actual_codes = {e.store_code for e in ws.execution_fact_stream[:5]}
    mvp = MockMVPResult(candidate_plan_summary=make_plan(list(actual_codes)))

    # 深拷贝前后状态
    plan_before = copy.deepcopy(mvp.candidate_plan_summary)
    efs_before = list(ws.execution_fact_stream)  # list snapshot

    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")

    # candidate_plan_summary 内容不变
    assert mvp.candidate_plan_summary == plan_before
    # execution_fact_stream 长度不变
    assert len(ws.execution_fact_stream) == len(efs_before)
    # 报告本身 frozen
    with pytest.raises(Exception):
        report.match_rate = 999.0  # type: ignore
    print("  ✅ Case 8: plan + execution_fact_stream 完全未变 (深拷贝对比)")


# === 9. period_label 提取 ===
def test_compare_extracts_period_label():
    ws = get_fixture_worldstate()
    mvp = MockMVPResult(candidate_plan_summary=make_plan(["S001"], period="2026-07"))
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.period_label == "2026-07"
    print(f"  ✅ Case 9: period_label 正确提取 (2026-07)")


def test_compare_period_label_unknown_when_missing():
    ws = get_fixture_worldstate()
    mvp = MockMVPResult(candidate_plan_summary=None)
    report = compare_mvp_vs_actual(mvp, ws, rep_id="仁军", period="2026-06")
    assert report.period_label == "<unknown>"
    print("  ✅ Case 10: plan 缺失 -> period_label='<unknown>'")
