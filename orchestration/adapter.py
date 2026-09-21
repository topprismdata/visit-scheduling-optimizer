# -*- coding: utf-8 -*-
"""LineData → 业务事实 适配器 + 整线语义规格编译.

LineData (core/base.py) 是母项目的 L3 内部数据结构, 其 days_orig 以
store_idx 计; L1 语义层只认业务身份 (customer_code). 本适配器做两件事:
1. line_data_facts: 索引空间 → 编码空间 (业务事实, LineData 不再直接进 L1);
2. compile_line_spec: 事实 + 策略档案 → VisitSemanticSpec (Phase B 所有权
   迁移的入口 — 走廊/f_c/核心保护从这里开始归 L1 所有).

注意: LineData.__post_init__ 的走廊静默推导在 L3 仍存在 (未迁移的存量),
但新链路一律经 compile_line_spec 取语义 — 存量走廊仅为 L3 内部快筛口径.
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from visit_ir import SemanticCompiler
from visit_semantic_api import CompilerProfile, VisitSemanticSpec

from core.base import LineData


def line_data_facts(line: LineData) -> dict:
    """LineData → L1 业务事实 (编码空间). days_orig: {date: [customer_code]}."""
    days: dict = {}
    for dd, seq in line.days_orig.items():
        days[dd] = [line.codes[i] for i in seq]
    return {"days_orig": days, "workdays": list(line.dates)}


def compile_line_spec(
    line: LineData,
    protected_codes: Sequence[str] = (),
    profile: Optional[CompilerProfile] = None,
) -> VisitSemanticSpec:
    """整线语义规格: 零例外闸在此触发 — 闸未过的线路直接抛 ValueError."""
    p = profile or CompilerProfile(
        snapshot_id=f"line-{line.line_id}",
        protected_codes=tuple(protected_codes),
    )
    return SemanticCompiler().compile(line_data_facts(line), p)
