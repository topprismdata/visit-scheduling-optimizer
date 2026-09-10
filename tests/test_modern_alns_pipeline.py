# -*- coding: utf-8 -*-
"""Task 4: 2026 现代 ALNS 端到端集成验证与对比评估.

验证链路 (合成微型实例, 房山线形态微缩):
  HGSR2Optimizer (方案一 双种群 HGS) ⊕ UCB1Selector (方案二)
  ⊕ SpatialPotentialField (方案三) → CP-SAT 单日精排 (Layer 2 口径)
  → 五道验收门 (走廊 / 合同 / R2' / 容量 / 守恒)
  → run_benchmark: 传统 R2ALNS vs 2026 HGS-R2' 对比报告.

门语义:
  走廊       全部日期覆盖, 每日店数落在双向作业走廊 [K_min, K_max];
  合同       每店日期集精确等于其 (合同 κ, 相位 φ, 星期几槽位) 派生集;
  R2'        每店全月单一星期几;
  容量       单日店数不超过硬上限 K_max (经典 capacity 闸);
  守恒       每店全月拜访次数 == 原频次, 日内无重复店, 店索引合法.
"""

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.base import LineData
from core.contract import contract_of
from core.metric import day_km
from algos.hgs_r2 import HGSR2Optimizer
from algos.tsp_engine import _exact_open_tsp
from experiments.run_modern_alns_benchmark import (
    FANGSHAN_FILES,
    GATE_LABELS,
    GATE_NAMES,
    check_five_gates,
    load_instance,
    run_benchmark,
)

# ---------------------------------------------------------------------------
# 合成微型实例: 3 簇 × 4 店 (北京房山一带坐标), 2 周 × Mon/Tue/Wed, 走廊 [3, 5]
# ---------------------------------------------------------------------------

_KM_PER_DEG_LNG = 85.8    # 111.32 × cos(39.6°N)
_KM_PER_DEG_LAT = 111.0

# 3 簇沿经度排开 (簇内 2×2 方块, 非退化凸包), 呼应房山线南北向通勤走廊形态
_CLUSTER_ORIGINS = {"A": (116.00, 39.60), "B": (116.20, 39.60), "C": (116.40, 39.60)}
_CORNERS = [(0.0, 0.0), (0.01, 0.0), (0.0, 0.01), (0.01, 0.01)]
COORDS = [(ox + dx, oy + dy)
          for ox, oy in (_CLUSTER_ORIGINS[k] for k in ("A", "B", "C"))
          for dx, dy in _CORNERS]

DATES = [dt.date(2026, 7, 6), dt.date(2026, 7, 7), dt.date(2026, 7, 8),
         dt.date(2026, 7, 13), dt.date(2026, 7, 14), dt.date(2026, 7, 15)]

# 原计划: 每星期几 4 店, 刻意跨簇混编 (R2' 合法但空间次优);
# 全员周访合同 (每店拜访其星期几全部 2 个槽位, f=2) → 任何整星期几换挡都保持合同合法
_ORIG_WEEKDAY_STORES = {0: [0, 1, 4, 5], 1: [2, 3, 8, 9], 2: [6, 7, 10, 11]}


def _make_line():
    days_orig = {}
    for wd, group in _ORIG_WEEKDAY_STORES.items():
        for d in (dd for dd in DATES if dd.weekday() == wd):
            days_orig[d] = sorted(group)
    freq = {}
    for seq in days_orig.values():
        for c in seq:
            freq[str(c)] = freq.get(str(c), 0) + 1
    return LineData(
        line_id="T4", line_name="modern-alns-synthetic",
        codes=[str(i) for i in range(len(COORDS))],
        lon=[p[0] for p in COORDS], lat=[p[1] for p in COORDS],
        dates=list(DATES), days_orig=days_orig, freq=freq,
        stores=len(COORDS), visits=sum(len(v) for v in days_orig.values()),
        min_daily_capacity=3, max_daily_capacity=5,
    )


def _dist_matrix():
    pts = np.asarray([(lon * _KM_PER_DEG_LNG, lat * _KM_PER_DEG_LAT)
                      for lon, lat in COORDS])
    return np.hypot(pts[:, None, 0] - pts[None, :, 0],
                    pts[:, None, 1] - pts[None, :, 1])


@pytest.fixture()
def line():
    return _make_line()


@pytest.fixture()
def D():
    return _dist_matrix()


def _run_hgs(line, D, **kw):
    opt = HGSR2Optimizer(pop_size=8, n_gens=6, ls_iters=16)
    res = opt.solve(line, D, time_budget=30.0, seed=7, exact_tl=5.0, **kw)
    return opt, res


# ---------------------------------------------------------------------------
# (1) 端到端: HGS-R2' 输出解通过五道验收门
# ---------------------------------------------------------------------------


def test_hgs_end_to_end_passes_five_gates(line, D):
    _opt, res = _run_hgs(line, D)
    gates = check_five_gates(line, res.days)
    assert set(gates) == set(GATE_NAMES)
    assert all(gates.values()), gates
    assert res.capacity_ok is True


def test_gate_labels_match_names():
    """门顺序与任务口径一致: 走廊、合同、R2'、容量、守恒."""
    assert GATE_NAMES == ("corridor_ok", "contract_ok", "r2_ok",
                          "capacity_ok", "conservation_ok")
    assert len(GATE_LABELS) == len(GATE_NAMES)


# ---------------------------------------------------------------------------
# (2) CP-SAT 排序联调: 终解日路线 == 独立 CP-SAT 精排里程
# ---------------------------------------------------------------------------


def test_cpsat_reroute_integration(line, D):
    _opt, res = _run_hgs(line, D)
    for d, route in res.days.items():
        members = sorted(route)
        exact = _exact_open_tsp(members, D, 10.0)
        assert day_km(route, D) == pytest.approx(day_km(exact, D), abs=1e-6)
        # CP-SAT 精排不劣于未排序的原始序
        assert day_km(route, D) <= day_km(members, D) + 1e-9


# ---------------------------------------------------------------------------
# (3) 五道门判别力: 构造违例必须被对应门拦截 (防假通过)
# ---------------------------------------------------------------------------


def test_five_gates_flag_violations(line):
    days = {d: sorted(v) for d, v in _make_line().days_orig.items()}
    base = check_five_gates(line, days)
    assert all(base.values()), base  # 原计划本身应全过门

    # 走廊+容量: 周二全部并入周一 → 周一 8 店超上限, 周二空缺
    monday = DATES[0]
    tuesday = DATES[1]
    crowded = {d: list(v) for d, v in days.items()}
    crowded[monday] = sorted(crowded[monday] + crowded[tuesday])
    del crowded[tuesday]
    g = check_five_gates(line, crowded)
    assert g["corridor_ok"] is False and g["capacity_ok"] is False

    # R2'+合同: 0 号店 (周访) 第二周的周一挪到周二 → 星期几分裂
    mon2 = DATES[3]
    tue1 = DATES[1]
    split = {d: list(v) for d, v in days.items()}
    split[mon2] = [c for c in split[mon2] if c != 0]
    split[tue1] = sorted(split[tue1] + [0])
    g = check_five_gates(line, split)
    assert g["r2_ok"] is False and g["contract_ok"] is False

    # 守恒: 1 号店在周一重复出现 → 月次数 3 ≠ 原频次 2, 且日内重复
    dup = {d: list(v) for d, v in days.items()}
    dup[monday] = dup[monday] + [1]
    g = check_five_gates(line, dup)
    assert g["conservation_ok"] is False


# ---------------------------------------------------------------------------
# (4) 对比评估: R2ALNS (传统) vs HGS-R2' (2026) 报告结构与门检查
# ---------------------------------------------------------------------------


def test_run_benchmark_report(line, D):
    rep = run_benchmark(line, D, pop_size=6, generations=4, budget=20.0,
                        alns_budget=2.0, seed=7, exact_tl=5.0)
    assert rep["line_id"] == "T4"
    assert rep["initial_km"] > 0
    for key in ("r2_alns", "hgs_r2"):
        blk = rep[key]
        assert {"final_km", "reduction_pct", "iterations", "elapsed",
                "gates"} <= set(blk), (key, blk.keys())
        assert blk["final_km"] > 0
        assert blk["elapsed"] > 0
        assert isinstance(blk["iterations"], int) and blk["iterations"] > 0
        assert blk["reduction_pct"] == pytest.approx(
            (rep["initial_km"] - blk["final_km"]) / rep["initial_km"] * 100,
            abs=1e-3)
        assert set(blk["gates"]) == set(GATE_NAMES)
        # 两算法在本实例上 (全员周访, 各星期几槽位数相同) 均应结构化过门
        assert all(blk["gates"].values()), (key, blk["gates"])
    # HGS 独有组件指标: 世代演化 + UCB1 调度 + 空间势能
    hgs = rep["hgs_r2"]
    assert hgs["gens"] > 0
    assert hgs["ls_pulls"] > 0
    assert sum(hgs["mab_pulls"].values()) == hgs["ls_pulls"]
    assert hgs["spatial_penalty"] >= 0.0


# ---------------------------------------------------------------------------
# (5) FS 房山线实例加载 (数据文件未入库, 缺失时跳过)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not all(Path(p).exists() for p in FANGSHAN_FILES.values()),
                    reason="房山线数据文件缺失 (output/fangshan_*.json|npy)")
def test_load_instance_fangshan():
    data, D = load_instance("FS")
    assert data.line_id == "FS"
    assert data.stores == D.shape[0] == 201
    assert len(data.dates) == 21
    assert D.shape == (201, 201)
    # OSM 驾车矩阵为有向 (单行道/转向限制), 仅要求非负对角与零对角
    assert np.all(np.diag(D) == 0) and np.all(D >= 0)
    # 原计划可反解合同且每日店数落在走廊内
    contracts = contract_of(data.days_orig, sorted(data.dates))
    assert len(contracts) == data.stores
    kmin, kmax = data.min_daily_capacity, data.max_daily_capacity
    assert all(kmin <= len(v) <= kmax for v in data.days_orig.values())
    # 守恒: 原计划频次自洽
    from core.metric import check_freq
    assert check_freq(data.days_orig, data.codes, data.freq)
