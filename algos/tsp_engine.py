# -*- coding: utf-8 -*-
"""TSP engine shim — 公式+驱动已外迁 visitmodel.tsp.open_chain; 纯几何启发在 opticore.

旧 import 路径 (algos.tsp_engine) 全量 re-export 兼容 (Hyrum's law):
  CP-SAT 开链公式 + 求解凭证契约 (_exact_open_tsp_status 等) → visitmodel.tsp.open_chain
  纯几何 NN+2opt (_nn2opt_open) → opticore.heuristics.nn2opt_open
"""
from visitmodel.tsp.open_chain import (      # noqa: F401 — 兼容 re-export
    _exact_open_tsp, _exact_open_tsp_status,
    TSPEngine, ExactTSPEngine, NN2OptEngine, ENGINES, get_engine)
from opticore.heuristics import nn2opt_open  # noqa: F401 — 兼容 re-export

# --- 公开 API (Hyrum's law fix): 统一走公开名; 下划线旧名保留一版过渡 ---
__all__ = ["exact_open_tsp", "nn2opt_open"]
exact_open_tsp = _exact_open_tsp
_nn2opt_open = nn2opt_open
