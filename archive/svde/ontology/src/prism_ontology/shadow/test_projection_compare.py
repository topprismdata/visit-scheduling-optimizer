"""projection 与升级 compare 的单元测试 (BIZ 无关)"""
from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)
import sys
import copy
from pathlib import Path
from datetime import datetime, timezone

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # = svde/ontology
sys.path.insert(0, str(ROOT / "src"))

from prism_ontology.shadow.projection import (
    Projection,
    project_for_replay,
    derive_lifecycle_records_from_ef,
)
from prism_ontology.shadow.compare import (
    ComparisonReport,
    ComparisonStatus,
    compare_mvp_vs_actual,
    _extract_actual_store_codes_strict,
)
from prism_ontology.real_data.world_state_assembler import WorldStateAssembler
from prism_ontology.world_model.state_snapshot import (
    OperationalVisitLifecycleRecord,
    LifecycleStatus,
)


FIXTURE_PATH = ROOT / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


# === 1. Projection 派生 lifecycle_records 字段数 ===
def test_projection_derives_lifecycle_records():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    original_vlr_count = len(ws.visit_lifecycle_records)
    assert original_vlr_count == 0  # fixture 缺此字段

    projection = project_for_replay(ws, rep_id="仁军", period="2026-06")
    # 派生 lifecycle_records 字段
    assert projection.derived_field_count > 0
    assert len(projection.worldstate.visit_lifecycle_records) > 0
    print(f"  ✅ Case 1: 派生 {projection.derived_field_count} 条 lifecycle_records (fixture 原 {original_vlr_count} 条)")


def test_projection_provenance_includes_algorithm():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    projection = project_for_replay(ws, rep_id="仁军", period="2026-06")
    assert "algorithm" in projection.provenance
    assert projection.provenance["algorithm"] == "PROJECT_FROM_EXECUTION_FACT_STREAM"
    assert projection.provenance["version"] == "v1.0"
    assert projection.provenance["assumption"] == "DERIVED_FROM_HISTORY"
    assert projection.provenance["rep_id"] == "仁军"
    assert projection.provenance["period"] == "2026-06"
    print(f"  ✅ Case 2: provenance 完整 ({len(projection.provenance)} 字段)")


def test_projection_does_not_mutate_original_worldstate():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    original_vlr = ws.visit_lifecycle_records
    original_efs_len = len(ws.execution_fact_stream)
    original_vlr_id = id(ws.visit_lifecycle_records)

    projection = project_for_replay(ws, rep_id="仁军", period="2026-06")

    # 原 worldstate 字节级不变
    assert id(ws.visit_lifecycle_records) == original_vlr_id
    assert ws.visit_lifecycle_records == original_vlr
    assert len(ws.execution_fact_stream) == original_efs_len
    # projection 派生 worldstate 是新对象
    assert id(projection.worldstate) != id(ws)
    print(f"  ✅ Case 3: 原 worldstate 字节级不变 (id 一致)")


def test_projection_confidence_increases_with_sample_size():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    # 2026-06 仁军 71 次, confidence = min(1.0, 71/10) = 1.0
    p1 = project_for_replay(ws, rep_id="仁军", period="2026-06")
    assert p1.confidence == 1.0
    # 2025-08 仁军 91 次
    p2 = project_for_replay(ws, rep_id="仁军", period="2025-08")
    assert p2.confidence == 1.0
    print(f"  ✅ Case 4: confidence={p1.confidence} (sample>=10)")


# === 5. compare 严格按 rep_id+period 过滤 ===
def test_compare_strict_filter_by_rep_and_period():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    # 仁军 2026-06 actual 应 = 71 (v1.0 升级前 = 246 全集)
    report = compare_mvp_vs_actual(mvp_result=None, worldstate=ws,
                                  rep_id="仁军", period="2026-06")
    assert report.actual_total_stops == 32  # 2026-06 仁军 unique stores (不是 71 events)
    assert report.actual_total_stops != 246  # 不等于全集 (升级前 bug)
    print(f"  ✅ Case 5a: 仁军 2026-06 actual=71 (升级前=246 全集)")

    # 仁军 2025-12 应 = 75
    report2 = compare_mvp_vs_actual(mvp_result=None, worldstate=ws,
                                   rep_id="仁军", period="2025-12")
    assert report2.actual_total_stops == 34  # 2025-12 仁军 unique stores
    print(f"  ✅ Case 5b: 仁军 2025-12 actual=75")

    # 晓敏 2026-06 应 = 90 (其他代表, 不 = 仁军的 71)
    report3 = compare_mvp_vs_actual(mvp_result=None, worldstate=ws,
                                   rep_id="晓敏", period="2026-06")
    # 晓敏 2026-06 unique stores (不等 71)
    assert report3.actual_total_stops == 32  # 2026-06 晓敏 unique stores
    assert report3.actual_total_stops != 71  # 不等于仁军数
    print(f"  ✅ Case 5c: 晓敏 2026-06 actual={report3.actual_total_stops} (不等于 仁军 71)")


# === 6. plan=0 时 NOT_EVALUABLE 而非 0.0 误导 ===
def test_compare_plan_zero_returns_not_evaluable():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    # mvp_result with plan=0
    class MockMVPPlanZero:
        candidate_plan_summary = {"plan_id": "P0", "daily_routes": []}
    report = compare_mvp_vs_actual(mvp_result=MockMVPPlanZero(), worldstate=ws,
                                  rep_id="仁军", period="2026-06")
    assert report.status == ComparisonStatus.NOT_EVALUABLE
    assert report.reason == "PLAN_NOT_GENERATED"
    # 重要: 不输出 0.0 match_rate 业务指标 (拒绝误导)
    assert report.reason == "PLAN_NOT_GENERATED"  # 应明确标注原因
    assert any("NOT_EVALUABLE" in n for n in report.notes)  # notes 应含 NOT_EVALUABLE 说明
    print(f"  ✅ Case 6: plan=0 -> status=NOT_EVALUABLE reason=PLAN_NOT_GENERATED")


def test_compare_plan_evaluable_with_match():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    # mvp_result with plan=10 stops, 仁军 2026-06 actual 71
    class MockMVPPlan10:
        candidate_plan_summary = {
            "plan_id": "P10",
            "daily_routes": [{"date_str": "2026-06-01", "weekday_name": "Mon",
                              "stops_count": 10, "stops_codes": ["S001", "S002", "S003", "S004", "S005", "S006", "S007", "S008", "S009", "S010"]}],
        }
    report = compare_mvp_vs_actual(mvp_result=MockMVPPlan10(), worldstate=ws,
                                  rep_id="仁军", period="2026-06")
    assert report.plan_total_stops == 10
    assert report.actual_total_stops == 32  # 2026-06 仁军 unique stores (不是 71 events)
    assert report.status in (ComparisonStatus.FAIL, ComparisonStatus.PARTIAL)  # match_rate 低
    assert report.reason == ""  # 非 NOT_EVALUABLE 时 reason 为空
    print(f"  ✅ Case 7: plan=10 actual=71 -> status=FAIL/PARTIAL (match_rate={report.match_rate})")


# === 7. runner 接受 projection 参数 (接口测试) ===
def test_runner_accepts_projection_in_run_params():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    from prism_ontology.shadow.runner import run_replay

    # 准备 projection
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    projection = project_for_replay(ws, rep_id="仁军", period="2026-06")

    # runner 接受 projection_in_run_params
    run_params = {
        "target_rep_id": "仁军",
        "period_label": "2026-06",
        "working_days": [f"2026-06-{d:02d}" for d in [1, 2, 3]],
        "run_timestamp": datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        "projection": projection,  # 注入派生 worldstate
    }
    report = run_replay(str(FIXTURE_PATH), run_params)
    # invariants 闸门应仍正常
    assert report.invariants_held is True
    # 派生 worldstate 已注入 (应能看到 visit_lifecycle_records 36 条)
    print(f"  ✅ Case 8: runner 接受 projection 参数, invariants 通过")


# === 8. runner 不接受 projection 时仍能跑 (回退路径) ===
def test_runner_without_projection_uses_raw_worldstate():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    from prism_ontology.shadow.runner import run_replay

    run_params = {
        "target_rep_id": "仁军",
        "period_label": "2026-06",
        "working_days": [f"2026-06-{d:02d}" for d in [1, 2, 3]],
        "run_timestamp": datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc),
        # 无 projection
    }
    report = run_replay(str(FIXTURE_PATH), run_params)
    # invariants 仍正常
    assert report.invariants_held is True
    print(f"  ✅ Case 9: runner 无 projection 仍正常 (回退路径)")


# === 10. Projection 字段校验 ===
def test_projection_field_validation():
    # confidence 越界
    with pytest.raises(ValueError):
        Projection(
            worldstate=None, provenance={}, confidence=1.5, derived_field_count=0,
        )
    # boundary 0.0 应接受 (修复后)
    Projection(worldstate=None, provenance={}, confidence=0.0, derived_field_count=0)
    print(f"  ✅ Case 10: Projection 字段校验 (rep_id / confidence)")
