# -*- coding: utf-8 -*-
"""HGS-R2' 双种群演化底座单元测试 — 方案一 (2026 现代 ALNS 演进).

验证契约 (Vidal et al. 2012/2014 HGS 框架 × 本项目 R2'/走廊铁律):
- R2' 不变量: 染色体 σ: store→weekday 经合同槽位解码, 每店全月单一星期几
  由构造保证 (可换星期几, 但整店全月一致, 严禁周内分裂);
- 双向作业走廊: 可行种群个体 (含最终输出解) 单日店数严格落 [K_min, K_max];
- 方案二/三组件融合: UCB1Selector 冷启动全覆盖调度 R2' 算子臂,
  SpatialPotentialField 势能参与适应度且可从输出解逐日复算对账;
- 双种群演化: 个体按可行性分流进可行/惩罚松弛两种群, 多代演化 incumbent
  单调不增且严格改进基线.

微型实例: 12 店 3 簇 × Mon/Tue/Wed 各 2 周 (2026-07); 原计划每星期几刻意
混两簇 (跨簇长链, R2' 合法但空间次优); 走廊显式放宽为 [3,5] 给足换挡
自由 — 同簇整周聚合是显著更优的合法解.
"""

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.hgs_r2 import HGSR2Optimizer
from algos.mab_selector import UCB1Selector
from algos.registry import get as registry_get
from algos.sp_matheuristic import check_r2prime
from core.base import LineData
from core.metric import check_capacity
from core.spatial_potential import SpatialPotentialField

# ---------------------------------------------------------------------------
# 微型 LineData: 12 店 3 簇, Mon/Tue/Wed × 2 周 (2026-07), 走廊 [3, 5]
# ---------------------------------------------------------------------------

DATES = [dt.date(2026, 7, 6), dt.date(2026, 7, 7), dt.date(2026, 7, 8),
         dt.date(2026, 7, 13), dt.date(2026, 7, 14), dt.date(2026, 7, 15)]

_KM_PER_DEG_LNG = 96.0   # 111.32 × cos(30°N)
_KM_PER_DEG_LAT = 111.0

# 3 簇 × 4 店 (簇内 2×2 方块, 非退化凸包): A≈120.0°E, B≈120.2°E, C≈120.4°E
_CLUSTER_ORIGINS = {"A": (120.00, 30.00), "B": (120.20, 30.00), "C": (120.40, 30.00)}
_CORNERS = [(0.0, 0.0), (0.01, 0.0), (0.0, 0.01), (0.01, 0.01)]
COORDS = [(ox + dx, oy + dy)
          for ox, oy in (_CLUSTER_ORIGINS[k] for k in ("A", "B", "C"))
          for dx, dy in _CORNERS]

# 原计划: 每星期几 4 店, 刻意跨两簇混编 (R2' 合法但空间次优);
# 全员周访合同 (每店拜访其星期几全部 2 个槽位, f=2); 走廊显式 [3,5].
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
        line_id="H0", line_name="hgs-r2-synthetic",
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


def _solve(line, D, **kw):
    opt = HGSR2Optimizer(pop_size=8, n_gens=6, ls_iters=16)
    res = opt.solve(line, D, time_budget=30.0, seed=7, **kw)
    return opt, res


def _store_weekdays(days):
    seen = {}
    for d, seq in days.items():
        for c in seq:
            seen.setdefault(c, set()).add(d.weekday())
    return seen


# ---------------------------------------------------------------------------
# 注册与构造校验
# ---------------------------------------------------------------------------


def test_registered_in_registry():
    assert registry_get("hgs_r2") is HGSR2Optimizer


def test_init_rejects_invalid_config():
    with pytest.raises(ValueError):
        HGSR2Optimizer(pop_size=1)
    with pytest.raises(ValueError):
        HGSR2Optimizer(n_gens=0)
    with pytest.raises(ValueError):
        HGSR2Optimizer(ls_iters=0)
    with pytest.raises(ValueError):
        HGSR2Optimizer(w_capacity=-1.0)
    with pytest.raises(ValueError):
        HGSR2Optimizer(w_spatial=float("nan"))


# ---------------------------------------------------------------------------
# (a) R2' 不变量: 每店全月单一星期几
# ---------------------------------------------------------------------------


def test_solution_satisfies_r2prime_invariant(line, D):
    opt, res = _solve(line, D)
    assert check_r2prime(res.days) == []                     # 零星期几分裂
    wd_of = _store_weekdays(res.days)
    assert set(wd_of) == set(range(line.stores))             # 12 店全勤覆盖
    assert all(len(ws) == 1 for ws in wd_of.values())        # 整店一致
    counts = {}
    for seq in res.days.values():
        for c in seq:
            counts[c] = counts.get(c, 0) + 1
    # 本实例各星期几槽位等宽 (均 2 槽) → 换挡不改变月内次数
    assert all(n == line.freq[str(c)] for c, n in counts.items())
    assert res.metadata["r2_ok"] is True


# ---------------------------------------------------------------------------
# (b) 双向作业走廊 [K_min, K_max]
# ---------------------------------------------------------------------------


def test_solution_satisfies_capacity_corridor(line, D):
    opt, res = _solve(line, D)
    assert res.capacity_ok is True
    assert check_capacity(res.days, line.max_daily_capacity, line.min_daily_capacity)
    assert set(res.days) == set(DATES)                       # 全部 6 个工作日在场
    assert all(line.min_daily_capacity <= len(seq) <= line.max_daily_capacity
               for seq in res.days.values())


# ---------------------------------------------------------------------------
# (c) 方案二/三组件融合: UCB1Selector + SpatialPotentialField
# ---------------------------------------------------------------------------


def test_integrates_mab_selector_and_spatial_field(line, D):
    opt, res = _solve(line, D)
    assert isinstance(opt.selector, UCB1Selector)
    assert set(opt.selector.arms) == set(HGSR2Optimizer.ARMS)
    assert min(opt.selector.pulls.values()) >= 1             # 冷启动每臂至少探索一次
    assert sum(opt.selector.pulls.values()) > opt.ls_iters   # 持续拉动而非摆设
    assert isinstance(opt.potential, SpatialPotentialField)
    assert opt.potential.n_days == len(DATES)
    assert opt.potential.total_area_km2 > 0.0                # 2-D 坐标 → 实际凸包
    expected_sp = sum(opt.potential.evaluate_day_assignment(seq)
                      for seq in res.days.values())
    assert res.metadata["spatial_penalty"] == pytest.approx(expected_sp, rel=1e-9)


# ---------------------------------------------------------------------------
# (d) 多代演化收敛
# ---------------------------------------------------------------------------


def test_convergence_over_generations(line, D):
    opt, res = _solve(line, D)
    hist = res.metadata["history"]
    assert len(hist) == 6                                    # 每代留痕
    fits = [h["best_fit"] for h in hist]
    assert all(b <= a + 1e-9 for a, b in zip(fits, fits[1:]))  # incumbent 单调不增
    assert fits[-1] < fits[0] - 1e-9                           # 代间严格改进
    assert res.km < res.metadata["baseline_km"] - 1.0          # 里程显著优于基线
    assert res.metadata["gens"] == 6


# ---------------------------------------------------------------------------
# 双种群容器: 可行 + 惩罚松弛
# ---------------------------------------------------------------------------


def test_two_population_containers(line, D):
    opt, res = _solve(line, D)
    assert 1 <= len(opt.feasible_pop) <= opt.pop_size
    assert len(opt.infeasible_pop) <= opt.pop_size
    assert opt.stats["created_feasible"] >= 1
    assert opt.stats["created_infeasible"] >= 1                # 松弛种群确实接纳过个体
    assert all(ind.cap_pen == 0.0 for ind in opt.feasible_pop)   # 可行种群零走廊违约
    assert all(ind.cap_pen > 0.0 for ind in opt.infeasible_pop)  # 松弛种群必有违约


# ---------------------------------------------------------------------------
# 可复现性
# ---------------------------------------------------------------------------


def test_same_seed_reproducible(line, D):
    """同种子 → Layer 1 日指派完全可复现.

    日内排序系 Layer 2 CP-SAT 精确重排域, 等优镜像链的取舍受墙钟影响,
    不在本优化器确定性契约内 — 故按 (总里程, 逐日成员集) 对账.
    """
    r1 = HGSR2Optimizer(pop_size=8, n_gens=4, ls_iters=8).solve(
        line, D, time_budget=30.0, seed=11)
    r2 = HGSR2Optimizer(pop_size=8, n_gens=4, ls_iters=8).solve(
        line, D, time_budget=30.0, seed=11)
    assert r1.km == r2.km
    assert {d: tuple(sorted(s)) for d, s in r1.days.items()} == \
           {d: tuple(sorted(s)) for d, s in r2.days.items()}
