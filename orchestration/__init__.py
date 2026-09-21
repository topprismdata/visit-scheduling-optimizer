# -*- coding: utf-8 -*-
"""orchestration — 应用编排层: 组装 L1→L2→L3 流水线, 不属于任何一层.

> 出处: docs/design/THREE_LAYER_ARCHITECTURE v0.2 §8 (Orchestrator 是控制流,
> 不是第四个建模层 — GPT 评审确认).

Phase B 落点: LineData(母项目 L3 内部结构) → 业务事实 → L1 SemanticCompiler.
"""
from orchestration.adapter import compile_line_spec, contract_view, line_data_facts
from orchestration.episode import emit_episode

__all__ = ["line_data_facts", "compile_line_spec", "contract_view", "emit_episode"]
