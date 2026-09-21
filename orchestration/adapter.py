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


def contract_view(line: LineData, spec: Optional[VisitSemanticSpec] = None) -> dict:
    """语义规格 → 索引空间编译视图 (供 L3 SP/定价/闸使用).

    输出:
      legal    {store_idx: frozenset[date]}  σ 可换超集: W→全工作日, B(φ)→相位匹配日
      fw       {store_idx: {weekday: f}}     星期 w 的合同槽位数 (z 覆盖 RHS)
      contracts {store_idx: ("W",None)|("B",φ)}
      k_c      {store_idx: obligation}

    本函数是 L1 语义 → L3 数学参数的唯一转译点 (Phase D2): L3 收视图,
    不再自行调用 contract_of / legal_date_map.
    """
    spec = spec or compile_line_spec(line)
    code2idx = {c: i for i, c in enumerate(line.codes)}
    wd_dates: dict[int, list] = {}
    for dd in sorted(line.dates):
        wd_dates.setdefault(dd.weekday(), []).append(dd)

    legal, fw, contracts, k_c = {}, {}, {}, {}
    for c in spec.contracts:
        i = code2idx[c.customer_code]
        if c.contract_type.value == "W":
            sup = frozenset(line.dates)
            kappa = ("W", None)
        else:
            sup = frozenset(
                dd for dd in line.dates
                if dd.isocalendar()[1] % 2 == c.phase
            )
            kappa = ("B", c.phase)
        legal[i] = sup
        fw[i] = {w: len(sup & frozenset(ds)) for w, ds in wd_dates.items()}
        contracts[i] = kappa
        k_c[i] = c.obligation
    return {"legal": legal, "fw": fw, "contracts": contracts, "k_c": k_c}
