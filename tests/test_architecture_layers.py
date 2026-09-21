# -*- coding: utf-8 -*-
"""主仓跨层 import 架构测试 (CI 强制, 棘轮式).

> 出处: docs/design/THREE_LAYER_ARCHITECTURE_v0.2.md §3.0 依赖规则.

三仓生态下的主仓职责 (Phase A 落点, 2026-09-20):
- VisitIR (L1) / VisitModel (L2) 独立成仓, 各自带 AST 守卫测试;
- 本仓只剩 L3 (algos/**): 禁止 import visit_ir / core.contract /
  visit_semantic_api / visitmodel (允许 visit_math_api — 数学实例是
  L3 唯一合法入口);
- 既有违规冻结在 _L3_WAIVERS, 只许修复缩减, 不许新增 (棘轮);
- 防 shadow 守卫: 本仓禁止出现 visitmodel / visit_math_api / 
  visit_semantic_api 同名目录 (会遮蔽 editable 安装的独立仓包,
  2026-09-20 已实际踩坑一次).
"""
import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

_L3_FORBIDDEN = ("visit_ir", "core.contract", "visit_semantic_api", "visitmodel")

# Phase D1/D2 已修复出列: sp_matheuristic.py (改收 contract_view)
# 剩余豁免: 合同输入型解码器/精确求解器, 待 D3/D4 参数化
_L3_WAIVERS = frozenset({
    ("alns_v4.py", "core.contract"),
    ("branch_and_price.py", "core.contract"),
    ("hgs_r2.py", "core.contract"),
    ("r2_alns_v2_backup.py", "core.contract"),
})

# 这些包属于独立仓, 本仓出现同名目录 = 遮蔽 editable 安装 (shadow)
_SHADOW_BANNED = ("visitmodel", "visit_math_api", "visit_semantic_api")


def _imports_of(py_file: Path) -> set:
    """AST 提取绝对 import 的顶层.子模块对; 包内相对 import 视为合法."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                parts = a.name.split(".")
                found.add(".".join(parts[:2]) if len(parts) > 1 else parts[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                continue  # 包内相对 import
            if node.module:
                parts = node.module.split(".")
                found.add(".".join(parts[:2]) if len(parts) > 1 else parts[0])
    return found


def test_l3_import_discipline_ratchet():
    pkg_dir = REPO / "algos"
    hits = set()
    for py in sorted(pkg_dir.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        for mod in _imports_of(py):
            if mod in _L3_FORBIDDEN:
                hits.add((py.name, mod))
    new = hits - _L3_WAIVERS
    assert not new, f"algos 新增跨层 import (棘轮不许新增, 只许修复): {sorted(new)}"
    assert len(hits) <= len(_L3_WAIVERS), (
        f"违规数 {len(hits)} 超过冻结额度 {len(_L3_WAIVERS)} — "
        f"修复后请同步缩减 _L3_WAIVERS"
    )


def test_no_shadow_packages_in_main_repo():
    """独立仓包不得以同名目录出现在主仓 (遮蔽 pip editable 安装)."""
    for name in _SHADOW_BANNED:
        assert not (REPO / name).exists(), (
            f"主仓出现 {name}/ — 会遮蔽独立仓 editable 包; "
            f"该代码应落在对应独立仓"
        )
