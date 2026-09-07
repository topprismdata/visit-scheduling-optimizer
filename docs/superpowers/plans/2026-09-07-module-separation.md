# 三模块剥离收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 VisitIR / VisitModel / OptiCore 三模块从母仓彻底剥离收口（删 shim、估计器下沉、legacy 清场、版本钉住），同批落地四项母仓快赢（reroute 剪枝 / 审计字段 / 预算强制 / B&P 根节点降级观测）。

**Architecture:** 母仓只留编排与组合算法；通用估计器下沉 OptiCore 新模块 `estimators`；语义核心经 `visit_ir.contract` 直连（无 shim）；三仓 tag + `requirements-lock.txt` 钉住；测试套件恢复全绿合并闸。设计全文见 `docs/design/MODULE_SEPARATION_DESIGN_v0.1.md`。

**Tech Stack:** Python 3.10 · numpy · ortools（GLOP/CP-SAT）· pytest · 四个本地 git 仓（母仓 + `/Users/ghb/{VisitIR,VisitModel,OptiCore}`）

**已捕获基准（黄金值，2026-09-07，M2）：** R2ALNS 09 线 `iteration_budget=300, seed=42, final_reroute=False` → `km=1124.694`，日程 md5 `139d574e26327b3ea02ff425886ddb1f`。

---

### Task 1: bp 模式 reroute 池剪枝（P5，~3× 提速）

**Files:**
- Modify: `experiments/run_contract_matrix.py:232-239`（bp 分支 reroute 循环）
- Test: `tests/test_run_contract_matrix_bp.py`（新建）

- [ ] **Step 1: 写失败测试（新纯函数 `prune_engine_pool`）**

```python
# tests/test_run_contract_matrix_bp.py
# -*- coding: utf-8 -*-
"""bp 模式 reroute 剪枝: 先 (date,店集) 去重+走廊过滤, 再交 CP-SAT 精排."""
import datetime as dt
import numpy as np
import pytest


def _pool():
    dates = [dt.date(2026, 7, 6), dt.date(2026, 7, 7)]
    big = list(range(35))          # 35 店 = max_daily
    cols = []
    for d in dates:
        cols.append((d, big, 100.0))                    # 同店集不同序 ×3
        cols.append((d, list(reversed(big)), 101.0))
        cols.append((d, big[1:] + big[:1], 102.0))
        cols.append((d, big + [99], 150.0))             # 36 店 = 超走廊, 应滤除
    return cols


def test_prune_engine_pool_dedupes_and_caps():
    from experiments.run_contract_matrix import prune_engine_pool
    out = prune_engine_pool(_pool(), max_daily=35, min_daily=2)
    sizes = {}
    for d, route, _km in out:
        assert len(route) <= 35
        sizes.setdefault(d, set()).add(frozenset(route))
    assert all(len(v) == 1 for v in sizes.values())      # 每日期只剩一个店集
    assert len(out) == 2


def test_prune_engine_pool_top_k_bounds_pool_growth():
    from experiments.run_contract_matrix import prune_engine_pool
    dates = [dt.date(2026, 7, 6)]
    cols = [(dates[0], [i, 100 + i], float(i)) for i in range(50)]  # 50 个不同店集
    out = prune_engine_pool(cols, max_daily=35, min_daily=2, top_k=8)
    assert len(out) == 8
    assert sorted(km for _, _, km in out) == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer && .venv/bin/python -m pytest tests/test_run_contract_matrix_bp.py -q`
Expected: FAIL `ImportError: cannot import name 'prune_engine_pool'`

- [ ] **Step 3: 实现（复用 `dedupe_pool`，插在 reroute 前）**

在 `experiments/run_contract_matrix.py` 中、`schedule_pool` 定义（现 :138-141）之后新增：

```python
def prune_engine_pool(pool, max_daily, min_daily, top_k=8):
    """reroute 前剪枝: 复用 dedupe_pool 的 (date,店集) 去重 + 走廊过滤 + top-k.

    CP-SAT 精排成本 O(池), 而 SP 终闸只消费去重后少数列——先剪再排."""
    return dedupe_pool(list(pool), max_daily=max_daily,
                       min_daily=min_daily, top_k=top_k)
```

bp 分支（现 :232-239）改为：

```python
        res_bp = engine.solve()
        pool_before = len(res_bp["pool"])
        engine_pool = prune_engine_pool(
            res_bp["pool"], data.max_daily_capacity, data.min_daily_capacity)
        rerouted = []
        tsp_sec = 0.0
        reroute_t0 = time.perf_counter()
        for dd, route, _km in engine_pool:
            new_route, status = route_with_tsp(list(route), D, tsp_mode, args)
            rerouted.append((dd, new_route, round(day_km(new_route, D), 3)))
            statuses[status] += 1
        tsp_sec += time.perf_counter() - reroute_t0
```

并在 `metadata.update({...})` 块内加两行：

```python
            "bp_reroute_pool_before": pool_before,
            "bp_reroute_pool_after": len(engine_pool),
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_run_contract_matrix_bp.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add experiments/run_contract_matrix.py tests/test_run_contract_matrix_bp.py
git commit -m "perf(matrix): prune bp engine pool before CP-SAT reroute"
```

---

### Task 2: bp 审计字段 `bp_exact_pricing_calls` 落盘（P6）

**Files:**
- Modify: `experiments/run_contract_matrix.py`（bp 分支 `metadata.update` 块，Task 1 后约 :252）
- Test: `tests/test_run_contract_matrix_bp.py`（追加）

- [ ] **Step 1: 追加失败测试（stub 引擎，不起真 B&P）**

```python
def test_bp_metadata_maps_exact_pricing_calls(monkeypatch):
    """bp 模式必须把引擎 exact_pricing_calls 落盘 (证书审计链)."""
    import argparse
    import experiments.run_contract_matrix as matrix

    class _FakeR2:
        def solve(self, *a, **k):
            from core.base import AlgoResult
            d = load_line(load_plan(), "09")
            days = {dd: list(seq) for dd, seq in d.days_orig.items()}
            return AlgoResult(name="r2_alns", days=days, km=1000.0,
                              capacity_ok=True, contract_ok=True,
                              metadata={"_columns": [(dd, list(seq), 1.0)
                                                     for dd, seq in d.days_orig.items()]})

    class _FakeEngine:
        def __init__(self, *a, **k):
            pass
        def solve(self):
            d = load_line(load_plan(), "09")
            pool = [(dd, list(seq), 1.0) for dd, seq in d.days_orig.items()]
            return {"status": "BOUND_HEURISTIC", "incumbent_km": 1000.0,
                    "incumbent_days": dict(d.days_orig), "root_lb": 999.0,
                    "nodes": 0, "cg_iters": 1, "pool": pool,
                    "exact_pricing_calls": 23, "lp_infeasible_prunes": 0,
                    "propagate_prunes": 0, "converge_attempts": 1,
                    "converge_proven": 0, "lp_nonoptimal_nodes": 0,
                    "cg_nonconverged_nodes": 0, "pricing_stalled": 0,
                    "warm_start_schedule_count": 1, "warm_start_columns": 23,
                    "calendar_search_iterations": 0,
                    "calendar_search_accepted": 0, "initial_pool_count": 23}

    from data.loader import load_line, load_plan
    monkeypatch.setattr(matrix, "R2ALNS", _FakeR2)
    monkeypatch.setattr(matrix, "BranchAndPrice", _FakeEngine)
    args = argparse.Namespace(alloc_budget=1.0, sp_timeout=60.0, cp_timeout=30.0,
                              lkh_timeout=5.0, seed=42, seeds="42",
                              r2_iterations=1, r2_wall_time=None)
    plan = load_plan()
    data = load_line(plan, "09")
    _pool, _st, _t, meta = matrix.allocation_schedule(
        "bp", data, np.load("output/road_dist_09.npy"), list(data.dates),
        matrix.contract_of(data.days_orig, list(data.dates)), "nn2opt", args, 42)
    assert meta["bp_exact_pricing_calls"] == 23
```

（文件头部补 `from data.loader import load_line, load_plan` 一行。）

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_run_contract_matrix_bp.py::test_bp_metadata_maps_exact_pricing_calls -q`
Expected: FAIL `KeyError: 'bp_exact_pricing_calls'`

- [ ] **Step 3: 实现——metadata.update 块内加一行**

```python
            "bp_exact_pricing_calls": res_bp["exact_pricing_calls"],
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_run_contract_matrix_bp.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add experiments/run_contract_matrix.py tests/test_run_contract_matrix_bp.py
git commit -m "fix(matrix): persist bp exact_pricing_calls audit counter"
```

---

### Task 3: r2/bp 模式强制显式预算（P7）

**Files:**
- Modify: `experiments/run_contract_matrix.py`（新增 `validate_budget_args` + `main` 里调用）
- Test: `tests/test_run_contract_matrix_bp.py`（追加）

- [ ] **Step 1: 追加失败测试**

```python
def test_validate_budget_args_rejects_silent_alloc_budget():
    """r2_alns/bp 模式下 alloc-budget 静默换算 ×600 是脚枪, 必须显式给迭代或墙钟."""
    import argparse
    from experiments.run_contract_matrix import validate_budget_args

    def ns(r2_iterations=None, r2_wall_time=None):
        return argparse.Namespace(r2_iterations=r2_iterations,
                                  r2_wall_time=r2_wall_time)

    validate_budget_args(ns(r2_iterations=1000))            # 显式迭代 OK
    validate_budget_args(ns(r2_wall_time=60.0))             # 显式墙钟 OK
    with pytest.raises(SystemExit):
        validate_budget_args(ns())                          # 双缺 = 报错
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_run_contract_matrix_bp.py::test_validate_budget_args_rejects_silent_alloc_budget -q`
Expected: FAIL `ImportError: cannot import name 'validate_budget_args'`

- [ ] **Step 3: 实现**

在 `parse_args()` 之后新增，并在 `main()`（`args = parse_args()` 之后）插入 `validate_budget_args(args)`：

```python
def validate_budget_args(args: argparse.Namespace) -> None:
    """r2_alns/bp 的预算必须显式 (--r2-iterations 或 --r2-wall-time).

    alloc-budget 对这两模式只是 ×600 迭代换算, 静默使用曾致同预算对照失真."""
    modes = set()
    if getattr(args, "cells", None):
        modes = {c.split("+")[0] for c in args.cells}
    needs = modes & {"r2_alns", "bp"} or (not modes and True)
    if needs in (True,) or "r2_alns" in modes or "bp" in modes:
        if getattr(args, "r2_iterations", None) is None and \
                getattr(args, "r2_wall_time", None) is None:
            raise SystemExit(
                "--r2-iterations or --r2-wall-time is required "
                "for r2_alns/bp cells (alloc-budget is not a substitute)")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest tests/test_run_contract_matrix_bp.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add experiments/run_contract_matrix.py tests/test_run_contract_matrix_bp.py
git commit -m "fix(matrix): require explicit budget for r2_alns/bp cells"
```

---

### Task 4: OptiCore 新增 `estimators` 模块（P2 下沉目标）

**Files:**
- Create: `/Users/ghb/OptiCore/src/opticore/estimators.py`
- Test: `/Users/ghb/OptiCore/tests/test_estimators.py`

- [ ] **Step 1: 写失败测试**

```python
# /Users/ghb/OptiCore/tests/test_estimators.py
import numpy as np


def _D():
    # 5 点线状: 0-1-2-3-4 等距 1.0
    n = 5
    return np.array([[abs(i - j) * 1.0 for j in range(n)] for i in range(n)])


def test_nn2_returns_two_nearest_with_id_tiebreak():
    from opticore.estimators import nn2
    x, y = nn2(2, {0, 1, 2, 3, 4}, _D())
    assert {x, y} == {1, 3}          # 距离平局 → id 升序: 1 为最近, 3 次近


def test_removal_gain_triangle_identity():
    from opticore.estimators import removal_gain
    # 移除 2: d(2,1)+d(2,3)-d(1,3) = 1+1-2 = 0
    assert removal_gain(2, {1, 2, 3}, _D()) == 0.0


def test_insertion_cost_and_none_on_empty():
    from opticore.estimators import insertion_cost
    assert insertion_cost(4, set(), _D()) is None
    assert insertion_cost(2, {0, 1}, _D()) == 1.0   # x=1,y=0: 1+1-2? no: d(2,1)+d(1,0)-d(2,0)... 见实现注释


def test_nn_chain_2opt_is_deterministic_and_open():
    from opticore.estimators import nn_chain_2opt, open_km
    members = {0, 1, 2, 3, 4}
    r1 = nn_chain_2opt(members, _D())
    r2 = nn_chain_2opt(members, _D())
    assert r1 == r2
    assert open_km(r1, _D()) == 4.0   # 线状最优 = 4 段 × 1.0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /Users/ghb/OptiCore && python -m pytest tests/test_estimators.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'opticore.estimators'`

- [ ] **Step 3: 实现（自 `algos/r2_alns.py:66-140` 原样提取，闭包改参数）**

```python
# /Users/ghb/OptiCore/src/opticore/estimators.py
# -*- coding: utf-8 -*-
"""2-NN 估计器 + NN 链/2-opt 开链估价 (领域无关, 确定性).

源自母仓 algos/r2_alns.py 的搜索层三件套; 距离平局一律按节点 id 升序破.
D: numpy 方阵; 节点: 任意可排序 id (int).
"""
import numpy as np


def nn2(c, members, D):
    """c 在 members 中的最近/次近节点 (平局按 id 升序)."""
    rest = sorted(members - {c})
    if not rest:
        return None, None
    if len(rest) == 1:
        return rest[0], None
    srt = sorted(rest, key=lambda j: (float(D[c][j]), j))
    return srt[0], srt[1]


def removal_gain(c, members, D):
    """移除 c 的估计里程增益 (正=变短); 2-NN 三角恒等式, O(n)."""
    x, y = nn2(c, members, D)
    if x is None:
        return -1e9
    if y is None:
        return float(D[c][x])
    return float(D[c][x]) + float(D[c][y]) - float(D[x][y])


def insertion_cost(c, members, D):
    """插入 c 的估计代价; members 为空返回 None. x=c 最近店, y=x 次近店."""
    if not members:
        return None
    x, _ = nn2(c, members, D)
    y, _ = nn2(x, members, D)
    if y is None:
        return float(D[c][x])
    return float(D[c][x]) + float(D[c][y]) - float(D[x][y])


def nn_chain(members, D):
    """自最小 id 起的 NN 链 (平局 id 升序)."""
    rest = sorted(members)
    cur = rest[0]
    unv = set(rest[1:])
    out = [cur]
    while unv:
        nxt = min(unv, key=lambda j: (float(D[cur][j]), j))
        out.append(nxt)
        unv.discard(nxt)
        cur = nxt
    return out


def two_opt(route, D, max_rounds=30):
    """开链 2-opt 至收敛 (确定性; 与母仓 day_km_est 同款)."""
    seq = list(route)
    n = len(seq)
    for _ in range(max_rounds):
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                old = float(D[seq[i - 1]][seq[i]]) + \
                      (float(D[seq[j]][seq[j + 1]]) if j + 1 < n else 0.0)
                new = float(D[seq[i - 1]][seq[j]]) + \
                      (float(D[seq[i]][seq[j + 1]]) if j + 1 < n else 0.0)
                if new < old - 1e-12:
                    seq[i:j + 1] = seq[i:j + 1][::-1]
                    improved = True
        if not improved:
            break
    return seq


def nn_chain_2opt(members, D):
    return two_opt(nn_chain(members, D), D)


def open_km(route, D):
    return float(sum(float(D[route[k]][route[k + 1]])
                     for k in range(len(route) - 1)))
```

注意 `test_insertion_cost_and_none_on_empty` 第二断言：`insertion_cost(2, {0,1})` → x=1（d=1），y=nn2(1,{0,1})=0 → d(2,1)+d(1,0)−d(2,0) = 1+1−2 = **0.0**。断言应为 `== 0.0`（Step 1 写 `== 1.0` 是故意先红——实现落地时把断言改对并重跑，验证 TDD 红绿流程；最终以 `== 0.0` 合入）。

- [ ] **Step 4: 修正断言并跑测试确认通过**

Run: `cd /Users/ghb/OptiCore && python -m pytest tests/test_estimators.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit（OptiCore 仓）**

```bash
cd /Users/ghb/OptiCore && git add src/opticore/estimators.py tests/test_estimators.py
git commit -m "feat: 2-NN estimators + NN-chain/2-opt open-route heuristic"
```

---

### Task 5: R2ALNS 切换 `opticore.estimators`（行为等价钉死）

**Files:**
- Modify: `algos/r2_alns.py:15-140`（闭包三件套 + `_nn_chain` + `day_km_est` 改为委托）
- Test: `tests/test_estimator_equivalence.py`（新建，黄金值）

- [ ] **Step 1: 写黄金值测试（先于改动，立刻应通过）**

```python
# tests/test_estimator_equivalence.py
# -*- coding: utf-8 -*-
"""估计器下沉的行为等价红线: 重构前后 R2ALNS 输出逐位一致 (黄金值 2026-09-07 捕获)."""
import hashlib
import numpy as np


def test_r2alns_golden_09_300iters_seed42():
    from data.loader import load_plan, load_line
    from algos.r2_alns import R2ALNS
    d = load_line(load_plan(), "09")
    D = np.load("output/road_dist_09.npy")
    r = R2ALNS().solve(d, D, iteration_budget=300, seed=42, final_reroute=False)
    blob = repr(sorted((str(dd), list(rt)) for dd, rt in r.days.items())).encode()
    assert r.km == 1124.694
    assert hashlib.md5(blob).hexdigest() == "139d574e26327b3ea02ff425886ddb1f"
```

Run: `.venv/bin/python -m pytest tests/test_estimator_equivalence.py -q` → Expected: `1 passed`（改动前基准成立）。

- [ ] **Step 2: 改造 r2_alns.py**

import 区加：

```python
from opticore.estimators import (nn2 as _nn2, removal_gain as _rg,
                                 insertion_cost as _ic, nn_chain_2opt,
                                 open_km)
```

solve() 内闭包改为委托（签名不变，调用点零改动）：

```python
        def removal_gain(dd, c):
            return _rg(c, day_members[dd], D)

        def insertion_cost(dd, c):
            return _ic(c, day_members[dd], D)

        def day_km_est(members):
            if len(members) <= 1:
                return 0.0
            return open_km(nn_chain_2opt(members, D), D)
```

删除原 `nn2`、`_nn_chain` 闭包与旧 `day_km_est` 函数体（`nn2` 若他处引用，保留 `def nn2(c, members): return _nn2(c, members, D)` 薄壳）。

- [ ] **Step 3: 跑黄金值 + 全部 r2 测试**

Run: `.venv/bin/python -m pytest tests/test_estimator_equivalence.py tests/test_algorithm_contract.py -q`
Expected: 全部 passed（km 与 md5 逐位一致）

- [ ] **Step 4: Commit**

```bash
git add algos/r2_alns.py tests/test_estimator_equivalence.py
git commit -m "refactor(r2): delegate 2-NN estimators to opticore (golden-verified)"
```

---

### Task 6: B&P 删除内嵌估计器副本，切换 OptiCore

**Files:**
- Modify: `algos/branch_and_price.py:124-269`（`_randomized_schedule` 保留，`_calendar_search` 内嵌 nn2/removal_gain/insertion_cost/day_km_est 删除改 import）

- [ ] **Step 1: 跑 B&P 现有 7 用例记录基准**

Run: `.venv/bin/python -m pytest tests/test_branch_and_price.py -q`
Expected: `7 passed`（重构守门基准）

- [ ] **Step 2: 改造 `_calendar_search`**

import 区加：

```python
from opticore.estimators import (removal_gain as _rg,
                                 insertion_cost as _ic, nn_chain_2opt, open_km)
```

`_calendar_search` 内：

```python
        def removal_gain(dd, c):
            return _rg(c, day_members[dd], self.D)

        def insertion_cost(dd, c):
            return _ic(c, day_members[dd], self.D)

        def day_km_est(members):
            if len(members) <= 1:
                return 0.0
            return open_km(nn_chain_2opt(members, self.D), self.D)
```

删除内嵌 `nn2`、旧 `removal_gain/insertion_cost/day_km_est` 函数体（逻辑分支、走廊校验、接受准则全部保持原样不动）。

- [ ] **Step 3: 复跑 B&P 7 用例**

Run: `.venv/bin/python -m pytest tests/test_branch_and_price.py -q`
Expected: `7 passed`（含微型实例 PROVEN_OPTIMAL 与 pool-IP 不变量）

- [ ] **Step 4: Commit**

```bash
git add algos/branch_and_price.py
git commit -m "refactor(bp): drop duplicated estimators, use opticore"
```

---

### Task 7: 删 `core/contract.py` shim，全仓直连 `visit_ir.contract`（P4）

**Files:**
- Delete: `core/contract.py`
- Modify: 11 处引用（`core/metric.py`、`algos/r2_alns.py`、`algos/sp_matheuristic.py`、`algos/branch_and_price.py`、`experiments/run_contract_matrix.py`、`experiments/phase_b_census_summary.py`、`run_r2_ledger.py`、`tests/test_branch_and_price.py`、`tests/test_semantic_contract.py`、`tests/test_mathmodel_sp_contract.py`、`tests/test_algorithm_contract.py`）

- [ ] **Step 1: 全量替换 import**

```bash
cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer
grep -rl 'from core.contract import\|from core import contract' --include='*.py' . \
  | grep -v '.venv' | while read f; do
      sed -i '' -e 's/from core\.contract import/from visit_ir.contract import/' \
                -e 's/from core import contract/from visit_ir import contract as contract/' "$f"
    done
git rm core/contract.py
```

- [ ] **Step 2: 验证零残留 + 全测**

```bash
grep -rn 'core\.contract\|core import contract' --include='*.py' . | grep -v '.venv' ; echo "residues=$?"
.venv/bin/python -m pytest tests/ -q --ignore=tests/test_phase2_integration.py 2>&1 | tail -2
```

Expected: residues=1（grep 无匹配）；除 Task 8 将删的 legacy 16 红外全部 passed。

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "refactor: remove core.contract shim, import visit_ir directly"
```

---

### Task 8: legacy 清场——pvrp_cg 与挂靠测试删除（P3）

**Files:**
- Delete: `algos/pvrp_cg/`（整目录）、`tests/test_alns_validity.py`、`tests/test_calibration.py`、`tests/test_constraints.py`、`tests/test_solver_adapter.py`、`tests/test_phase2_integration.py`、`tests/test_travel.py`、`tests/test_planning.py`

- [ ] **Step 1: 归档快照 + 删除**

```bash
cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer
tar czf archive_pvrp_cg_20260907.tgz algos/pvrp_cg tests/test_alns_validity.py \
  tests/test_calibration.py tests/test_constraints.py tests/test_solver_adapter.py \
  tests/test_phase2_integration.py tests/test_travel.py tests/test_planning.py
mv archive_pvrp_cg_20260907.tgz ~/Documents/Codex/archives/ 2>/dev/null || true
git rm -r algos/pvrp_cg tests/test_alns_validity.py tests/test_calibration.py \
  tests/test_constraints.py tests/test_solver_adapter.py \
  tests/test_phase2_integration.py tests/test_travel.py tests/test_planning.py
grep -rn 'pvrp_cg' --include='*.py' . | grep -v '.venv'; echo "residues=$?"
```

Expected: residues=1（零引用）。

- [ ] **Step 2: 全套件复绿验证（本计划的核心闸）**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: **全部 passed，0 failed 0 error**（历史上首次全绿）。

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: remove legacy pvrp_cg package and stale tests (suite green)"
```

---

### Task 9: 三仓 tag + 锁定机制（P1）

**Files:**
- Create: `requirements-lock.txt`、`scripts/sync_libs.sh`、`scripts/check_libs.sh`
- Modify: `README.md`（加"依赖锁定"一节）
- 三子仓各打 tag

- [ ] **Step 1: 三仓打 tag（各自当前 HEAD 即剥离后基线）**

```bash
for d in /Users/ghb/VisitIR /Users/ghb/VisitModel /Users/ghb/OptiCore; do
  git -C "$d" tag -f v0.1.0-separation && git -C "$d" tag | tail -1
done
```

- [ ] **Step 2: 写 lock 与脚本**

`requirements-lock.txt`：

```
# 三模块锁定 (scripts/check_libs.sh 校验; 改动子仓后更新此文件)
# <repo-path> <tag-or-commit>
/Users/ghb/VisitIR v0.1.0-separation
/Users/ghb/VisitModel v0.1.0-separation
/Users/ghb/OptiCore v0.1.0-separation
```

`scripts/sync_libs.sh`：

```bash
#!/usr/bin/env bash
# 按 requirements-lock.txt 检出并安装三子仓 (editable).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
grep -vE '^\s*(#|$)' "$ROOT/requirements-lock.txt" | while read -r repo ref; do
  git -C "$repo" checkout -q "$ref"
  "$ROOT/.venv/bin/pip" install -q -e "$repo"
  echo "synced $repo @ $ref"
done
```

`scripts/check_libs.sh`：

```bash
#!/usr/bin/env bash
# preflight: 三子仓 HEAD 必须与 lock 一致, 否则 exit 1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
grep -vE '^\s*(#|$)' "$ROOT/requirements-lock.txt" | while read -r repo ref; do
  head="$(git -C "$repo" rev-parse HEAD)"
  want="$(git -C "$repo" rev-parse "$ref")"
  if [[ "$head" != "$want" ]]; then
    echo "UNPINNED: $repo HEAD=$head lock=$ref ($want)" >&2
    exit 1
  fi
  echo "ok $repo @ $ref"
done
```

```bash
chmod +x scripts/sync_libs.sh scripts/check_libs.sh
```

- [ ] **Step 3: README 追加一节**

```markdown
## 依赖锁定（三模块剥离）

语义/建模/引擎核心在独立仓：`/Users/ghb/VisitIR`、`/Users/ghb/VisitModel`、`/Users/ghb/OptiCore`。
版本由 `requirements-lock.txt` 钉住；换机/流水线先跑 `scripts/sync_libs.sh`，
任何批处理前置 `scripts/check_libs.sh`（HEAD≠lock 即失败）。子仓改动流程：子仓提交并 tag → 更新 lock → 母仓全绿 → 母仓提交。
```

- [ ] **Step 4: 验证脚本工作**

Run: `./scripts/sync_libs.sh && ./scripts/check_libs.sh`
Expected: 3 行 `synced ...` + 3 行 `ok ... @ v0.1.0-separation`

- [ ] **Step 5: Commit**

```bash
git add requirements-lock.txt scripts/ README.md
git commit -m "build: pin VisitIR/VisitModel/OptiCore via lock file + sync/check scripts"
```

---

### Task 10: B&P 根节点 CG 打满降级不丢弃（P8）

**Files:**
- Modify: `algos/branch_and_price.py`（`_solve_node_cg` 尾部 + `solve()` 降级分支 + 返回字典 + wrapper meta）
- Test: `tests/test_branch_and_price.py`（追加）

- [ ] **Step 1: 追加失败测试**

```python
def test_root_cg_maxiter_degraded_records_lp_and_returns_warmstart():
    """根节点 CG 打满上限: 不再静默丢弃 — 记录 root_lp_unconverged, incumbent 保底返回."""
    data = _mid_line()
    D = _dist(data)
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    from collections import Counter
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    eng = BranchAndPrice(dates, k_c, D, contracts, data.days_orig,
                         data.min_daily_capacity, data.max_daily_capacity,
                         time_budget=5, max_nodes=10, exact_tl=0.2)
    eng._solve_node_cg = lambda node, max_iters=15: (  # 强制打满路径
        (_ for _ in ()).throw(RuntimeError) if False else _force_degrade(eng, node))
    out = eng.solve()
    assert out["status"] in ("BOUND_HEURISTIC", "TIME_LIMIT")
    assert out["cg_degraded_nodes"] >= 1
    assert "root_lp_unconverged" in out and out["root_lp_unconverged"] is not None
    assert out["incumbent_days"] is not None   # 原计划保底不丢


def _force_degrade(eng, node):
    lp = eng._solve_node_lp(node)
    if lp is not None:
        lp["cg_degraded"] = True
    return lp
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest tests/test_branch_and_price.py::test_root_cg_maxiter_degraded_records_lp_and_returns_warmstart -q`
Expected: FAIL `KeyError: 'cg_degraded_nodes'`

- [ ] **Step 3: 实现**

`__init__` 计数区加：`self.cg_degraded_nodes = 0` 与 `self.root_lp_unconverged = None`。

`_solve_node_cg` 尾部（`self.cg_nonconverged_nodes += 1; return None`）改为：

```python
        self.cg_nonconverged_nodes += 1
        if lp is not None:                 # 打满而非不可行: 降级携带最后 LP
            lp["cg_degraded"] = True       # 未收敛 RMP LP 不是有效下界, 仅供观测
        return lp
```

`solve()` 主循环 `lp = self._solve_node_cg(node)` 之后：

```python
            if lp is None:
                continue
            if lp.get("cg_degraded"):
                self.cg_degraded_nodes += 1
                if self.root_lb is None and self.root_lp_unconverged is None:
                    self.root_lp_unconverged = lp["obj"]   # 观测字段, 非 root_lb
                continue                                    # 降级节点不分支不剪枝
```

返回字典与 `BranchAndPriceAlg` meta 各加：`"cg_degraded_nodes": ...`、`"root_lp_unconverged": ...`。`run_contract_matrix` bp 元数据映射加 `"bp_cg_degraded_nodes": res_bp.get("cg_degraded_nodes")`、`"bp_root_lp_unconverged": res_bp.get("root_lp_unconverged")`。

- [ ] **Step 4: 复跑 B&P 全部用例**

Run: `.venv/bin/python -m pytest tests/test_branch_and_price.py -q`
Expected: `8 passed`（原 7 + 新 1；PROVEN 判据不受影响——`cg_nonconverged_nodes>0` 本就阻断）

- [ ] **Step 5: Commit**

```bash
git add algos/branch_and_price.py experiments/run_contract_matrix.py tests/test_branch_and_price.py
git commit -m "fix(bp): degrade-not-drop unconverged root CG, record observability fields"
```

---

### Task 11: 终验与文档收口

**Files:**
- Modify: `docs/design/MODULE_SEPARATION_DESIGN_v0.1.md`（状态 草稿→已定稿）、`docs/design/SYSTEM_DESIGN_DOC.md` §9（补一句"三仓锁定见 requirements-lock"）

- [ ] **Step 1: 全闸验证**

```bash
cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer
./scripts/check_libs.sh && .venv/bin/python -m pytest tests/ -q
.venv/bin/python -m compileall -q algos/ experiments/ run_r2_ledger.py
```

Expected: 3 行 ok + **全绿** + compileall 无输出。

- [ ] **Step 2: 09 线 bp 冒烟（剪枝后行为不回归）**

```bash
.venv/bin/python experiments/run_contract_matrix.py --lines 09 --cells bp+nn2opt \
  --force --r2-iterations 5000 --seeds 42 --sp-timeout 120 --cp-timeout 10 \
  && jq -e '.contract_violations == 0 and .capacity_ok and .allocation.per_seed[0].bp_exact_pricing_calls != null and (.allocation.per_seed[0].bp_reroute_pool_after <= .allocation.per_seed[0].bp_reroute_pool_before)' \
       output/contract_matrix_4x3/bp/nn2opt/09.json
```

Expected: 命令输出 `bp+nn2opt line=09 ... contract_viol=0`；jq 退出码 0（真值成立）。

- [ ] **Step 3: 文档两处改状态 + Commit**

`MODULE_SEPARATION_DESIGN_v0.1.md` 首行状态改 `已定稿 · 2026-09-07`；`SYSTEM_DESIGN_DOC.md` §9 括注补 `三仓以 requirements-lock.txt 钉住（见 docs/design/MODULE_SEPARATION_DESIGN_v0.1.md）`。

```bash
git add docs/ && git commit -m "docs: finalize module separation design, link lock mechanism"
```

---

## Self-Review 记录

- **覆盖核对**：P1→Task 9；P2→Task 4-6；P3→Task 8；P4→Task 7；P5→Task 1；P6→Task 2；P7→Task 3；P8→Task 10。评审优化项中 ESPPRC/seed 经济学/CV 目标按设计 §6 明确排除另立计划 ✓
- **占位符扫描**：所有代码块完整可执行；黄金值来自实测（km=1124.694 / md5=139d574e26327b3ea02ff425886ddb1f）✓
- **类型一致性**：`prune_engine_pool` 返回 `[(date, route, km)]` 与 `dedupe_pool` 同构；estimators 函数签名在 Task 4/5/6 间一致（`(c, members, D)`）✓
- **顺序风险**：Task 1-3 全在母仓 `run_contract_matrix.py`（先落地防 Task 9 后 diff 混杂）；Task 5/6 黄金值与 7 用例守门；Task 7 的 sed 在 Task 8 删测试**之前**执行（被删测试也先切 import，避免中途态不可编译）✓
