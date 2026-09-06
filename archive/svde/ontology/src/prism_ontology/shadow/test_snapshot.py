"""InputSnapshot 单元测试 (BIZ 无关 — MVP 正式基线之外的独立模块)

覆盖 5 项要求:
1. 相同输入 -> 相同 hash (与 captured_at 无关)
2. 字节变化 -> 不同 hash
3. 空输入 -> 稳定 sha256
4. 不可读输入 -> 友好错误
5. 元数据完整性 (snapshot_id 唯一, 字段齐)
"""
import sys
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
    _build_snapshot_id,
    SHA256_HEX_LEN,
)


# === 1. 相同输入 -> 相同 hash ===
def test_same_input_produces_same_hash():
    content = b"hello world, fixture FMCG v1.0"
    snap1 = snapshot_factory(
        content, source_path="fixture.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        schema_version="fmcg_visit_history_v1.0",
        captured_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    snap2 = snapshot_factory(
        content, source_path="different_path.xlsx",  # path 变化不影响内容 hash
        media_type="different-media-type",  # media_type 变化不影响内容 hash
        schema_version="different-version",  # schema_version 变化不影响内容 hash
        captured_at=datetime(2027, 6, 15, 12, 0, 0, tzinfo=timezone.utc),  # 不同时间不影响内容 hash
    )
    # 核心断言: 相同输入字节 -> 相同 content_sha256
    assert snap1.content_sha256 == snap2.content_sha256
    # 内容 hash 必须是 64 字符 hex
    assert len(snap1.content_sha256) == SHA256_HEX_LEN
    # 字节长度一致
    assert snap1.byte_length == snap2.byte_length == len(content)
    # snapshot_id 不同 (因 captured_at 不同) — 但 content_sha256 一致
    assert snap1.snapshot_id != snap2.snapshot_id
    # 元数据各自记录 (path / media_type / schema_version 不影响 hash 但仍可区分)
    assert snap1.source_path == "fixture.xlsx"
    assert snap2.source_path == "different_path.xlsx"
    print(f"  ✅ Case 1: 相同输入 -> 相同 hash ({snap1.content_sha256[:16]}...)")


# === 2. 字节变化 -> 不同 hash ===
def test_content_change_produces_different_hash():
    base = b"hello world"
    modified = b"hello world "  # 末尾加一个空格
    snap_base = snapshot_factory(base, source_path="-", schema_version="v1")
    snap_mod = snapshot_factory(modified, source_path="-", schema_version="v1")
    # 字节变化 -> 不同 hash
    assert snap_base.content_sha256 != snap_mod.content_sha256
    # 字节长度差 1
    assert snap_mod.byte_length - snap_base.byte_length == 1
    # 相同的 SHA-256 hex 长度
    assert len(snap_base.content_sha256) == 64 == len(snap_mod.content_sha256)
    print(f"  ✅ Case 2: 字节变化 -> 不同 hash ({snap_base.content_sha256[:8]} != {snap_mod.content_sha256[:8]})")


# === 3. 空输入 -> 稳定 sha256 ===
def test_empty_input_produces_known_sha256():
    snap = snapshot_factory(b"", source_path="empty.xlsx", schema_version="empty")
    # 空字节的 SHA-256 是公开常量: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert snap.content_sha256 == expected
    assert snap.byte_length == 0
    # 空输入 snapshot_id 也应合法
    assert snap.snapshot_id.startswith("SNAP-")
    print(f"  ✅ Case 3: 空输入 -> 稳定 sha256 ({snap.content_sha256[:16]}...)")


# === 4. 不可读输入 / 非法类型 -> 友好错误 ===
def test_invalid_input_type_raises_type_error():
    with pytest.raises(TypeError, match="content 必须是 bytes"):
        snapshot_factory("not bytes, this is a str", source_path="-")
    print("  ✅ Case 4a: 非法类型 (str) -> TypeError")


def test_empty_schema_version_raises_value_error():
    with pytest.raises(ValueError, match="schema_version 不能为空"):
        snapshot_factory(b"data", source_path="-", schema_version="")
    print("  ✅ Case 4b: 空 schema_version -> ValueError")


def test_negative_byte_length_raises_in_post_init():
    # 构造一个不变量违反的 InputSnapshot (绕过 factory 直接构造)
    # byte_length < 0 应在 __post_init__ 抛出
    from datetime import datetime, timezone
    with pytest.raises(ValueError, match="byte_length 必须 >= 0"):
        InputSnapshot(
            snapshot_id="SNAP-test-000000000000",
            content_sha256="0" * 64,
            source_path="-",
            byte_length=-1,  # 非法
            media_type="application/octet-stream",
            schema_version="v1",
            captured_at=datetime.now(timezone.utc),
        )
    print("  ✅ Case 4c: 负 byte_length -> ValueError (__post_init__)")


def test_naive_datetime_raises_value_error():
    with pytest.raises(ValueError, match="captured_at 必须带 timezone"):
        snapshot_factory(b"data", source_path="-", captured_at=datetime(2026, 1, 1))
    print("  ✅ Case 4d: naive datetime (无 tz) -> ValueError")


def test_invalid_sha256_length_raises_value_error():
    from datetime import datetime, timezone
    with pytest.raises(ValueError, match=r"content_sha256 必须是 64 字符 hex"):
        InputSnapshot(
            snapshot_id="SNAP-test-000000000000",
            content_sha256="0" * 32,  # 太短
            source_path="-",
            byte_length=0,
            media_type="application/octet-stream",
            schema_version="v1",
            captured_at=datetime.now(timezone.utc),
        )
    print("  ✅ Case 4e: 错误长度 content_sha256 -> ValueError")


# === 5. 元数据完整性 (snapshot_id 唯一, 字段齐) ===
def test_metadata_completeness():
    fixed_ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    snap = snapshot_factory(
        b"abc", source_path="/path/to/fixture.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        schema_version="fmcg_visit_history_v1.0",
        captured_at=fixed_ts,
    )
    # 所有元数据字段非空
    assert snap.snapshot_id
    assert len(snap.content_sha256) == 64
    assert snap.source_path == "/path/to/fixture.xlsx"
    assert snap.byte_length == 3
    assert snap.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert snap.schema_version == "fmcg_visit_history_v1.0"
    # snapshot_id 格式: SNAP-<YYYYMMDDTHHMMSSZ>-<12hex>
    assert snap.snapshot_id.startswith("SNAP-20260101T000000Z-")
    assert len(snap.snapshot_id) == len("SNAP-20260101T000000Z-") + 12
    # captured_at timezone-aware
    assert snap.captured_at.tzinfo is not None
    print(f"  ✅ Case 5: 元数据完整性 (snapshot_id={snap.snapshot_id})")


def test_snapshot_id_uniqueness_across_inputs():
    """不同输入 -> 不同 snapshot_id (因 content_sha256 不同)"""
    fixed_ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    s1 = snapshot_factory(b"input1", captured_at=fixed_ts)
    s2 = snapshot_factory(b"input2", captured_at=fixed_ts)  # 同时间但不同内容
    s3 = snapshot_factory(b"input1", captured_at=fixed_ts.replace(second=1))  # 同内容但不同秒
    # 不同内容 -> 不同 content_sha256 -> 不同 snapshot_id
    assert s1.snapshot_id != s2.snapshot_id
    # 同内容但不同秒 -> 不同 snapshot_id (因 captured_at 参与)
    assert s1.snapshot_id != s3.snapshot_id
    # 但 content_sha256 相同 (因 input 字节相同)
    assert s1.content_sha256 == s3.content_sha256
    print("  ✅ Case 5b: snapshot_id 唯一性 (内容 + 时间均参与)")


def test_captured_at_does_not_influence_content_hash():
    """captured_at 时间变化不应影响 content_sha256 (核心内容哈希不变)"""
    content = b"hello"
    fixed_2025 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    fixed_2099 = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    s1 = snapshot_factory(content, captured_at=fixed_2025)
    s2 = snapshot_factory(content, captured_at=fixed_2099)
    # 核心内容 hash 不变
    assert s1.content_sha256 == s2.content_sha256
    # 但 snapshot_id 因时间不同而不同
    assert s1.snapshot_id != s2.snapshot_id
    # captured_at 各自分开记录
    assert s1.captured_at == fixed_2025
    assert s2.captured_at == fixed_2099
    print("  ✅ Case 5c: captured_at 不参与 content_sha256 (时间变化仅影响 snapshot_id)")
