"""ReadOnlyGuard 单元测试 (BIZ 无关)

覆盖 6 项要求:
1. 全部 4 项不变量符合 -> passed=True, violations=[]
2. 阻止 external_dispatch=True (违反)
3. 阻止 baseline_writeback=True (违反)
4. 阻止 canonical_api_status='IMPLEMENTED' (违反)
5. 阻止 scenario_effect_applied=True (违反)
6. 只读: 不修改输入 dict
"""
import sys
import copy
from pathlib import Path

import pytest

# 添加 svde/ontology/src 到路径
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))

from prism_ontology.shadow.guard import (
    ReadOnlyViolation,
    GuardResult,
    check_mvp_invariants,
    assert_mvp_invariants,
    MVP_INVARIANT_FIELDS,
    EXPECTED_VALUES,
)


def valid_invariants() -> dict:
    """返回符合 4 项不变量的 dict (副本, 测试间互不影响)"""
    return {
        "external_dispatch": False,
        "baseline_writeback": False,
        "canonical_api_status": "NOT_IMPLEMENTED",
        "scenario_effect_applied": False,
    }


# === 1. 全通过 ===
def test_all_pass():
    result = check_mvp_invariants(valid_invariants())
    assert result.passed is True
    assert result.violations == []
    assert result.checked_fields == list(MVP_INVARIANT_FIELDS)
    assert all(f in result.checked_fields for f in MVP_INVARIANT_FIELDS)
    print("  ✅ Case 1: 全 4 项符合 -> passed=True, violations=[]")


# === 2-5. 单项违反 ===
def test_block_external_dispatch_true():
    inv = valid_invariants()
    inv["external_dispatch"] = True  # 违反
    with pytest.raises(ReadOnlyViolation) as exc_info:
        assert_mvp_invariants(inv)
    v = exc_info.value
    assert v.violated_field == "external_dispatch"
    assert v.observed is True
    assert v.required is False
    print(f"  ✅ Case 2: external_dispatch=True -> 阻止 ({v.violated_field})")


def test_block_baseline_writeback_true():
    inv = valid_invariants()
    inv["baseline_writeback"] = True
    with pytest.raises(ReadOnlyViolation) as exc_info:
        assert_mvp_invariants(inv)
    assert exc_info.value.violated_field == "baseline_writeback"
    print("  ✅ Case 3: baseline_writeback=True -> 阻止")


def test_block_canonical_api_status_implemented():
    inv = valid_invariants()
    inv["canonical_api_status"] = "IMPLEMENTED"  # 违反
    with pytest.raises(ReadOnlyViolation) as exc_info:
        assert_mvp_invariants(inv)
    assert exc_info.value.violated_field == "canonical_api_status"
    assert exc_info.value.observed == "IMPLEMENTED"
    assert exc_info.value.required == "NOT_IMPLEMENTED"
    print("  ✅ Case 4: canonical_api_status='IMPLEMENTED' -> 阻止")


def test_block_scenario_effect_applied_true():
    inv = valid_invariants()
    inv["scenario_effect_applied"] = True
    with pytest.raises(ReadOnlyViolation) as exc_info:
        assert_mvp_invariants(inv)
    assert exc_info.value.violated_field == "scenario_effect_applied"
    print("  ✅ Case 5: scenario_effect_applied=True -> 阻止")


# === 6. 多项违反: 报告所有违反, 不只首个 ===
def test_multiple_violations_all_reported():
    inv = valid_invariants()
    inv["external_dispatch"] = True
    inv["baseline_writeback"] = True
    inv["scenario_effect_applied"] = True
    result = check_mvp_invariants(inv)
    assert result.passed is False
    assert len(result.violations) == 3
    violated_fields = {v.violated_field for v in result.violations}
    assert violated_fields == {"external_dispatch", "baseline_writeback", "scenario_effect_applied"}
    print("  ✅ Case 6: 多项违反 -> 报告所有 (3 violations)")


# === 7. 缺字段 (缺 canonical_api_status) ===
def test_missing_field_causes_violation():
    inv = valid_invariants()
    del inv["canonical_api_status"]
    with pytest.raises(ReadOnlyViolation) as exc_info:
        assert_mvp_invariants(inv)
    assert exc_info.value.violated_field == "canonical_api_status"
    assert exc_info.value.observed == "<MISSING>"
    print("  ✅ Case 7: 缺字段 -> 阻止 (observed=<MISSING>)")


# === 8. 类型校验: invariants 不是 dict ===
def test_non_dict_input_raises_type_error():
    with pytest.raises(TypeError, match="invariants 必须是 dict"):
        check_mvp_invariants("not a dict")
    with pytest.raises(TypeError):
        check_mvp_invariants([("external_dispatch", False)])  # list 不接受
    print("  ✅ Case 8: 非 dict 输入 -> TypeError")


# === 9. GuardResult 一致性校验 (passed=True 但有 violations -> ValueError) ===
def test_guard_result_consistency_validation():
    # passed=True 但有 violations -> 矛盾
    with pytest.raises(ValueError, match="passed=True 但有"):
        GuardResult(passed=True, violations=[
            ReadOnlyViolation("external_dispatch", True, False)
        ], checked_fields=list(MVP_INVARIANT_FIELDS))
    # passed=False 但无 violations -> 矛盾
    with pytest.raises(ValueError, match="passed=False 但无 violations"):
        GuardResult(passed=False, violations=[], checked_fields=list(MVP_INVARIANT_FIELDS))
    # checked_fields 缺 MVP 字段 -> ValueError
    with pytest.raises(ValueError, match="checked_fields 必须包含"):
        GuardResult(passed=True, violations=[], checked_fields=["external_dispatch"])  # 缺 3 项
    print("  ✅ Case 9: GuardResult 一致性校验 (3 种矛盾)")


# === 10. 只读: check_mvp_invariants 不修改输入 dict ===
def test_does_not_mutate_input():
    inv = valid_invariants()
    snapshot = copy.deepcopy(inv)
    # 跑全通过
    check_mvp_invariants(inv)
    assert inv == snapshot
    # 跑违反场景
    inv_bad = valid_invariants()
    inv_bad["external_dispatch"] = True
    inv_bad["canonical_api_status"] = "WRONG"
    snapshot_bad = copy.deepcopy(inv_bad)
    try:
        assert_mvp_invariants(inv_bad)
    except ReadOnlyViolation:
        pass
    assert inv_bad == snapshot_bad
    print("  ✅ Case 10: 只读 (输入 dict 不变)")


# === 11. assert_mvp_invariants 与 check_mvp_invariants 行为对齐 ===
def test_assert_matches_check():
    inv = valid_invariants()
    # 全通过: assert 不抛
    assert_mvp_invariants(inv)
    # 违反: 抛首个 (与 check_mvp_invariants 返回的 violations[0] 一致)
    inv_bad = valid_invariants()
    inv_bad["external_dispatch"] = True
    inv_bad["canonical_api_status"] = "X"
    inv_bad["baseline_writeback"] = True
    try:
        assert_mvp_invariants(inv_bad)
    except ReadOnlyViolation as e:
        # 抛首个违反 (MVP_INVARIANT_FIELDS 顺序遍历)
        assert e.violated_field == MVP_INVARIANT_FIELDS[0]  # external_dispatch
    print("  ✅ Case 11: assert_mvp_invariants 抛首个违反 (与 check 顺序一致)")


# === 12. 边界: scenario_effect_applied=False (正确) 不抛 ===
def test_scenario_effect_applied_false_passes():
    inv = valid_invariants()
    inv["scenario_effect_applied"] = False  # 正确
    result = check_mvp_invariants(inv)
    assert result.passed is True
    print("  ✅ Case 12: scenario_effect_applied=False (no-writeback) -> 通过")
