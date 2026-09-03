"""ReadOnlyGuard Runtime Safety Gate 单元测试 (BIZ 无关)

覆盖:
1. 指纹确定性 (同内容两次计算一致)
2. 指纹突变敏感性 (list 原地突变 -> 指纹变化)
3. pre-gate 通过 (干净 fixture -> GateToken, 64-hex 指纹)
4. pre-gate 阻止 fixture 篡改 (GateBlocked)
5. pre-gate 阻止非 frozen 对象
6. post-gate 检测原地突变 (passed=False + violation)
7. post-gate 无突变通过
"""
import sys
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

import pytest
ROOT = Path(__file__).resolve().parent.parent.parent.parent  # = svde/ontology
sys.path.insert(0, str(ROOT / "src"))

from prism_ontology.shadow.guard import (
    gate_pre_execution,
    gate_post_execution,
    compute_worldstate_fingerprint,
    GateBlocked,
    GateToken,
)
from prism_ontology.shadow.snapshot import snapshot_factory
from prism_ontology.real_data.world_state_assembler import WorldStateAssembler

from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)

FIXTURE_PATH = ROOT / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


def _load_ws():
    return WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)


def _make_snapshot():
    return snapshot_factory(
        FIXTURE_PATH.read_bytes(),
        source_path=str(FIXTURE_PATH),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        schema_version="fmcg_visit_history_v1.0",
        captured_at=None,
    )


# === 1+2. 指纹确定性与突变敏感性 ===
def test_fingerprint_deterministic_and_mutation_sensitive():
    @dataclass(frozen=True)
    class Inner:
        x: int

    @dataclass(frozen=True)
    class Holder:
        items: List[Inner] = field(default_factory=list)
        mapping: Dict[str, int] = field(default_factory=dict)

    h = Holder(items=[Inner(1), Inner(2)], mapping={"a": 1})
    fp1 = compute_worldstate_fingerprint(h)
    fp2 = compute_worldstate_fingerprint(h)
    assert fp1 == fp2, "同内容两次指纹必须一致"
    assert len(fp1) == 64, "指纹必须是 64 hex 字符 (256-bit SHA-256)"

    # list 原地突变 -> 指纹变化
    h.items.append(Inner(3))
    fp3 = compute_worldstate_fingerprint(h)
    assert fp3 != fp1, "list 原地突变必须改变指纹"

    # dict 原地突变 -> 指纹变化
    h2 = Holder(items=[Inner(1), Inner(2)], mapping={"a": 1})
    h2.mapping["a"] = 999
    assert compute_worldstate_fingerprint(h2) != fp1, "dict 原地突变必须改变指纹"
    print("  [OK] Case 1+2: 指纹确定性 + 突变敏感性")


# === 3. pre-gate 通过 ===
def test_pre_gate_passes_clean_fixture():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = _load_ws()
    snap = _make_snapshot()
    token = gate_pre_execution(ws, snap, str(FIXTURE_PATH))
    assert isinstance(token, GateToken)
    assert len(token.worldstate_fingerprint) == 64
    assert token.fixture_sha256 == snap.content_sha256
    assert token.is_frozen_dataclass is True
    print(f"  [OK] Case 3: pre-gate 通过 (fingerprint={token.worldstate_fingerprint[:16]}...)")


# === 4. pre-gate 阻止 fixture 篡改 ===
def test_pre_gate_blocks_tampered_fixture():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = _load_ws()
    snap = _make_snapshot()
    tmp = Path(tempfile.mkdtemp()) / "tampered.xlsx"
    shutil.copy(FIXTURE_PATH, tmp)
    try:
        with open(tmp, "ab") as f:
            f.write(b"tampered-bytes")
        with pytest.raises(GateBlocked, match="篡改"):
            gate_pre_execution(ws, snap, str(tmp))
    finally:
        tmp.unlink(missing_ok=True)
    print("  [OK] Case 4: fixture 篡改 -> pre-gate 阻止")


# === 5. pre-gate 阻止非 frozen 对象 ===
def test_pre_gate_blocks_non_frozen():
    snap = _make_snapshot() if FIXTURE_PATH.exists() else None
    if snap is None:
        pytest.skip("fixture 不存在")

    @dataclass
    class MutableWS:  # 非 frozen
        snapshot_id: str = "X"

    with pytest.raises(GateBlocked, match="frozen"):
        gate_pre_execution(MutableWS(), snap, str(FIXTURE_PATH))
    print("  [OK] Case 5: 非 frozen dataclass -> pre-gate 阻止")


# === 6+7. post-gate 突变检测 ===
def test_post_gate_detects_and_passes():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = _load_ws()
    snap = _make_snapshot()
    token = gate_pre_execution(ws, snap, str(FIXTURE_PATH))

    # 无突变 -> 通过
    r_ok = gate_post_execution(token, ws)
    assert r_ok.passed is True
    assert r_ok.violations == []

    # 原地突变 (list append) -> 检测
    ws.execution_fact_stream.append(ws.execution_fact_stream[0])
    r_bad = gate_post_execution(token, ws)
    assert r_bad.passed is False
    assert len(r_bad.violations) == 1
    assert r_bad.violations[0].violated_field == "worldstate_fingerprint"
    assert "原地突变" in r_bad.violations[0].message
    print("  [OK] Case 6+7: post-gate 无突变通过 + 原地突变检测")
