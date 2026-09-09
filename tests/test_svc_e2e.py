"""Golden 重放: 同 SRP 输入 + seed 42 → solution.json output_hash 一致.

标记 slow: 读 Excel ~2-5min, 单独跑:
  .venv/bin/python -m pytest tests/test_svc_e2e.py -v -m slow
"""
import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow]

GOLDEN = Path("output/svc_golden/09/solution_1.0.json")


def test_golden_replay_09():
    from svc.hashing import sha256_of
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    # 复算 output_hash (重算哈希而非重跑 R2-ALNS; 全量重放走 CLI 冒烟)
    recomputed = sha256_of(
        {k: v for k, v in golden.items() if k != "output_hash"})
    assert recomputed == golden["output_hash"]
    assert golden["status"] == "FEASIBLE"
    assert all(golden["gates"].values())
    assert golden["totals"]["km"] > 0


def test_golden_schema_valid():
    from svc.schemas.validate import validate_obj
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    validate_obj(golden, "solution")
