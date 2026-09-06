# -*- coding: utf-8 -*-
"""兼容 shim: 合同-相位本体已剥离至独立项目 VisitIR (/Users/ghb/VisitIR).

母项目经 `visit-ir` 包消费语义核心 (安装: pip install -e /Users/ghb/VisitIR).
本 shim 保留旧 import 路径 `core.contract` 的兼容性; 新代码请直接 import visit_ir.
语义与测试定稿见 VisitIR 仓库 tests/ 与母项目 tests/test_semantic_contract.py (集成层).
"""
from visit_ir.contract import (  # noqa: F401
    check_contract,
    check_rhythm,
    contract_of,
    contract_slot_dates,
    illegal_slot_sets,
    legal_date_map,
    legal_slot_sets,
    phase_of,
    rhythm_ok_dates,
    slot_index_map,
    slots_per_weekday,
)
