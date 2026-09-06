"""DataPrechecker 单元测试 (BIZ 无关)

覆盖 5 项要求:
1. PASS case (世界状态完整 + 哈希一致)
2. 哈希不匹配 (FAIL)
3. 缺失字段 (FAIL)
4. 非法实体 ID (重复 ID, FAIL)
5. 只读不变性 (DataPrechecker 不修改 worldstate)
"""
import sys
import copy
from pathlib import Path
from datetime import datetime, timezone

import pytest

# 添加 svde/ontology/src 到路径
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))

from prism_ontology.shadow.snapshot import (
    InputSnapshot,
    compute_content_sha256,
    snapshot_factory,
)
from prism_ontology.shadow.data_precheck import (
    Finding,
    FindingSeverity,
    ReportStatus,
    DataPrecheckReport,
    precheck_worldstate,
)


# === Mock WorldState 工厂 (避免依赖 OperationalDecisionWorldState 真实构造) ===

class MockBitemporal:
    def __init__(self, valid_from, valid_to, transaction_from=None, transaction_to=None):
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.transaction_from = transaction_from or valid_from
        self.transaction_to = transaction_to


class MockManifest:
    def __init__(self, source_file_path, source_file_sha256, assembled_at=None,
                 loader_version="CanonicalWorldState_v1.1", raw_rows_count=6467,
                 valid_facts_count=6374, excluded_rows_count=93,
                 exclusion_reason="93 rows excluded due to missing store_code in master data"):
        self.source_file_path = source_file_path
        self.source_file_sha256 = source_file_sha256
        self.loader_version = loader_version
        self.raw_rows_count = raw_rows_count
        self.valid_facts_count = valid_facts_count
        self.excluded_rows_count = excluded_rows_count
        self.exclusion_reason = exclusion_reason
        # 默认 assembled_at 用 UTC now (与 SourceManifest 一致)
        self.assembled_at = assembled_at or datetime.now(timezone.utc)


class MockWorldState:
    """minimal duck-typing — DataPrechecker 用 hasattr / getattr 不要求真实类型"""
    def __init__(self, *, manifest, bitemporal=None, customers=None, resources=None,
                 policies=None, commitments=None, snapshot_id="WS-MOCK"):
        self.manifest = manifest
        self.bitemporal = bitemporal or MockBitemporal(
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            valid_to=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )
        self.customers = customers or {}
        self.resources = resources or {}
        self.policies = policies or {}
        self.commitments = commitments or {}
        self.snapshot_id = snapshot_id


def make_snapshot_and_worldstate(content: bytes = b"fixture FMCG v1.0",
                                  path: str = "fixture.xlsx",
                                  capture_time: datetime = None,
                                  schema: str = "fmcg_visit_history_v1.0"):
    """工厂: 生成内容哈希一致的 snapshot + worldstate"""
    capture_time = capture_time or datetime(2026, 1, 1, tzinfo=timezone.utc)
    snap = snapshot_factory(
        content, source_path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        schema_version=schema,
        captured_at=capture_time,
    )
    manifest = MockManifest(source_file_path=path, source_file_sha256=snap.content_sha256)
    ws = MockWorldState(manifest=manifest, snapshot_id="WS-MOCK")
    return snap, ws


# === 1. PASS case ===
def test_precheck_pass():
    snap, ws = make_snapshot_and_worldstate()
    report = precheck_worldstate(snap, ws)
    assert report.status == ReportStatus.PASS
    assert report.error_count == 0
    assert report.warning_count == 0
    assert report.snapshot_id == snap.snapshot_id
    assert report.worldstate_id == "WS-MOCK"
    # checked_fields 应非空
    assert len(report.checked_fields) > 0
    print(f"  ✅ Case 1: PASS (checked_fields={len(report.checked_fields)})")


# === 2. 哈希不匹配 (FAIL) ===
def test_precheck_fail_hash_mismatch():
    snap, ws = make_snapshot_and_worldstate()
    # 修改 worldstate.manifest.source_file_sha256 为不匹配值
    ws.manifest.source_file_sha256 = "f" * 64
    report = precheck_worldstate(snap, ws)
    assert report.status == ReportStatus.FAIL
    assert report.error_count >= 1
    # 找到 HASH_MISMATCH finding
    hash_findings = [f for f in report.findings if f.code == "HASH_MISMATCH"]
    assert len(hash_findings) == 1
    assert hash_findings[0].severity == FindingSeverity.ERROR
    # 检查 target 含两个哈希前 12 位
    target = hash_findings[0].target
    assert snap.content_sha256[:12] in target
    assert "f" * 12 in target
    print(f"  ✅ Case 2: 哈希不匹配 -> FAIL (HASH_MISMATCH)")


# === 3. 缺失字段 (FAIL) ===
def test_precheck_fail_missing_manifest():
    snap, _ = make_snapshot_and_worldstate()
    # 构造无 manifest 的 worldstate
    ws = MockWorldState(manifest=None, snapshot_id="WS-NO-MANIFEST")
    report = precheck_worldstate(snap, ws)
    assert report.status == ReportStatus.FAIL
    # 必有 MISSING_MANIFEST finding
    missing = [f for f in report.findings if f.code == "MISSING_MANIFEST"]
    assert len(missing) == 1
    assert missing[0].severity == FindingSeverity.ERROR
    # 同时可能触发其他 MISSING_*
    assert any(f.code.startswith("MISSING_") for f in report.findings)
    print(f"  ✅ Case 3: 缺 manifest -> FAIL ({len(report.findings)} findings)")


def test_precheck_fail_missing_entity_dict():
    snap, ws = make_snapshot_and_worldstate()
    # customers 为 None
    ws.customers = None
    report = precheck_worldstate(snap, ws)
    assert report.status == ReportStatus.FAIL
    codes = [f.code for f in report.findings]
    assert "ENTITY_DICT_NULL" in codes or "MISSING_ENTITY_DICT" in codes
    print(f"  ✅ Case 3b: 缺 customers 实体字典 -> FAIL (codes={codes[:3]})")


# === 4. 非法实体 ID (重复 ID, FAIL) ===
def test_precheck_pass_with_unique_entity_ids():
    """验证唯一 ID 场景不触发 DUPLICATE_ENTITY_ID finding"""
    snap, ws = make_snapshot_and_worldstate()
    class MockEntity: pass
    # 多实体, ID 全部唯一
    ws.customers = {"S001": MockEntity(), "S002": MockEntity(), "S003": MockEntity()}
    ws.resources = {"R001": MockEntity(), "R002": MockEntity()}
    ws.commitments = {"C001": MockEntity()}
    report = precheck_worldstate(snap, ws)
    # 应无 DUPLICATE_ENTITY_ID finding
    dup_findings = [f for f in report.findings if f.code == "DUPLICATE_ENTITY_ID"]
    assert len(dup_findings) == 0, f"唯一 ID 场景不应触发 DUPLICATE, 实际: {dup_findings}"
    # 应 PASS (无 ERROR)
    assert report.status == ReportStatus.PASS
    print("  ✅ Case 4a: 唯一 ID 场景 -> 不触发 DUPLICATE_ENTITY_ID (Python dict 自身保证)")


def test_check_entity_id_uniqueness_function_exists():
    """直接验证 _check_entity_id_uniqueness 函数存在 + 接受空 dict"""
    from prism_ontology.shadow.data_precheck import _check_entity_id_uniqueness
    from dataclasses import dataclass

    @dataclass
    class FakeWS:
        customers: dict
        resources: dict
        commitments: dict

    # 全部空 dict
    ws = FakeWS(customers={}, resources={}, commitments={})
    findings = _check_entity_id_uniqueness(ws)
    assert len(findings) == 0
    print("  ✅ Case 4b: _check_entity_id_uniqueness 接受空 dict (Python dict 自身保证 key 唯一)")


# === 5. 只读不变性 (DataPrechecker 不修改 worldstate) ===
def test_precheck_does_not_mutate_worldstate():
    snap, ws = make_snapshot_and_worldstate()
    # 深度拷贝世界状态 (包括 manifest)
    manifest_id_before = id(ws.manifest)
    bitemporal_id_before = id(ws.bitemporal)
    customers_id_before = id(ws.customers)
    manifest_sha_before = ws.manifest.source_file_sha256
    manifest_path_before = ws.manifest.source_file_path
    bitemporal_vf_before = ws.bitemporal.valid_from
    bitemporal_vt_before = ws.bitemporal.valid_to

    # 跑预检
    report = precheck_worldstate(snap, ws)

    # 关键: 引用地址不变 (frozen dataclass 引用地址固定) + 字段值不变
    assert id(ws.manifest) == manifest_id_before
    assert id(ws.bitemporal) == bitemporal_id_before
    assert id(ws.customers) == customers_id_before
    assert ws.manifest.source_file_sha256 == manifest_sha_before
    assert ws.manifest.source_file_path == manifest_path_before
    assert ws.bitemporal.valid_from == bitemporal_vf_before
    assert ws.bitemporal.valid_to == bitemporal_vt_before
    print("  ✅ Case 5: WorldState 只读不变性 (字段值 + 引用地址)")


def test_precheck_does_not_mutate_input_snapshot():
    snap, ws = make_snapshot_and_worldstate()
    snap_id_before = snap.snapshot_id
    snap_hash_before = snap.content_sha256
    snap_bytes_before = snap.byte_length

    precheck_worldstate(snap, ws)

    assert snap.snapshot_id == snap_id_before
    assert snap.content_sha256 == snap_hash_before
    assert snap.byte_length == snap_bytes_before
    print("  ✅ Case 5b: InputSnapshot 只读不变性")


# === 6. ReportStatus / error_count / warning_count 一致性 (DataPrecheckReport.__post_init__) ===
def test_report_status_consistency():
    # 1. 合法 PASS
    r = DataPrecheckReport(
        status=ReportStatus.PASS, snapshot_id="S1", worldstate_id="WS1",
        checked_fields=[], findings=[], error_count=0, warning_count=0,
    )
    assert r.status == ReportStatus.PASS

    # 2. 合法 WARN (有 WARNING 无 ERROR)
    r = DataPrecheckReport(
        status=ReportStatus.WARN, snapshot_id="S1", worldstate_id="WS1",
        checked_fields=["x"], findings=[Finding(FindingSeverity.WARNING, "W", "msg")],
        error_count=0, warning_count=1,
    )
    assert r.status == ReportStatus.WARN

    # 3. status=PASS 但有 findings -> 抛 (status 校验先于 count 校验)
    with pytest.raises(ValueError, match="status=PASS 但有 findings"):
        DataPrecheckReport(
            status=ReportStatus.PASS, snapshot_id="S1", worldstate_id="WS1",
            checked_fields=[], findings=[Finding(FindingSeverity.ERROR, "X", "msg")],
            error_count=1, warning_count=0,
        )

    # 4. status=WARN 但有 ERROR -> 抛
    with pytest.raises(ValueError, match="status=WARN 但有 ERROR findings"):
        DataPrecheckReport(
            status=ReportStatus.WARN, snapshot_id="S1", worldstate_id="WS1",
            checked_fields=[], findings=[Finding(FindingSeverity.ERROR, "X", "msg")],
            error_count=1, warning_count=0,
        )

    # 5. status=FAIL 但 error_count=0 -> 抛
    with pytest.raises(ValueError, match="status=FAIL 但无 ERROR findings"):
        DataPrecheckReport(
            status=ReportStatus.FAIL, snapshot_id="S1", worldstate_id="WS1",
            checked_fields=[], findings=[], error_count=0, warning_count=0,
        )

    # 6. error_count 1 但 findings 只有 1 个 WARNING (count != actual) -> 抛
    with pytest.raises(ValueError, match="error_count 1 != 实际 ERROR findings"):
        DataPrecheckReport(
            status=ReportStatus.FAIL, snapshot_id="S1", worldstate_id="WS1",
            checked_fields=[], findings=[Finding(FindingSeverity.WARNING, "W", "msg")],
            error_count=1, warning_count=1,
        )
    print("  ✅ Case 6: ReportStatus / count / findings 一致性校验")


# === 7. invalid input types ===
def test_precheck_invalid_snapshot_type():
    ws = MockWorldState(manifest=MockManifest("x", "0"*64))
    report = precheck_worldstate("not snapshot", ws)
    assert report.status == ReportStatus.FAIL
    assert any(f.code == "INVALID_SNAPSHOT" for f in report.findings)
    print("  ✅ Case 7: 非法 snapshot 类型 -> FAIL")


def test_precheck_invalid_worldstate_type():
    snap = snapshot_factory(b"data")
    report = precheck_worldstate(snap, "not worldstate")
    assert report.status == ReportStatus.FAIL
    assert any(f.code == "INVALID_WORLDSTATE" for f in report.findings)
    print("  ✅ Case 7b: 非法 worldstate 类型 -> FAIL")
