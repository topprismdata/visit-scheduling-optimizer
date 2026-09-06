# 合同-相位本体重构实施计划（Contract-Cadence-Phase Implementation Plan）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 2026-09-06 数据考古钉死的"拜访合同-节拍-相位本体"（`docs/design/CONTRACT_CADENCE_MODEL.md`）落地，按**仓库解耦（Task 0）→ 语义层 → 数学层 → 算法层**的节奏推进，每层测试全绿才进下一层；最后完成旧账审计与合同口径重跑。

**Architecture:** 两件事，一条时间线：
1. **仓库增量解耦（Google 判据：变化耦合/所有权/Hyrum's Law）**：归档三代遗产（svde 等 33k 行）→ 实验脚本归置 + 公开 API 化 → 语义层立缝（`core/contract.py`）。**不做** big-bang 重构，`algos/` 内部分层明确推迟到合同重跑收口后。
2. **三层纪律各自独立测试**：语义层（本体=数据，精确重构）；数学层（模型=语义，暴力枚举可行集等价）；算法层（求解器=模型，确定性+复现+端到端三闸）。

**Tech Stack:** Python 3.10+ / numpy / OR-Tools (CP-SAT + GLOP) / pytest 9.1.1。

**关键背景数字（写死防漂移）：**
- 主线代码 = 6,862 行（data 133 + core 423 + algos 2,580 + tests 795 + 根脚本 2,931）；遗产 = 33k+ 行（svde 18,232 / validation 4,453 / 其他目录）。
- 全办 1,524 店零例外：周访 1,337 / 双周偶相位 88 / 双周奇相位 99；f 分布 {2:125, 3:62, 4:557, 5:780}；双周店 187 家是相位敏感人群。
- 基线 A：全办 4,144.3 km，09 线 326.6 km。旧终账（相位松弛口径）：全办 3,618.5 km，09 线 310.4 km。
- 7 月：周一/二 k=4，周三/四/五 k=5；7-01 = ISO 周 27；相位 = ISO 周 mod 2；`服务周` = ISO 周 mod 4。
- 旧管线参数（复现审计用）：`R2ALNS time_budget=150 × seeds (42,7,123,2026)` + `SP time_budget=300, rounds=1, sa_burst=10, r2_prime=True`，`dedupe_pool(top_k=8)`。

---

## File Structure

| 文件 | 动作 | 层 | 职责 |
|---|---|---|---|
| `archive/`（目录） | Create（git mv） | 解耦 | 三代遗产归档：svde/ validation/ src/ spec/ demo/ examples/ knowledge_base/ domain/ svde-bench/ + 根目录演示资产 |
| `experiments/`（目录） | Create（git mv） | 解耦 | 根目录 24 个实验脚本 + 2 个 .sh 归置；import 路径改写 |
| `algos/__init__.py` 等公开 API | Modify | 解耦 | `__all__` 声明；实验脚本仅可 import 公开符号（消除 Hyrum's Law 违例） |
| `core/contract.py` | Create | 语义 | 合同-相位本体：`phase_of` / `contract_of` / `contract_slot_dates` / `legal_date_map` / `check_contract`（+ 迁入 rhythm 松弛快筛） |
| `tests/test_semantic_contract.py` | Create | 语义 | 本体=数据：合成单元 + 15 行结构穷举 + 反例拒绝 + 1,524 店精确重构 + 服务周交叉验证 |
| `algos/sp_matheuristic.py` | Modify | 数学 | `_fw_table` / `_contract_pool_filter`；LP/IP `contract` 参数（池过滤 + 覆盖 RHS z 线性化）；定价 `legal` 剪枝 |
| `tests/test_mathmodel_sp_contract.py` | Create | 数学 | 模型=语义：部件单元 + RHS 可行模式穷举 + 3^9 暴力枚举等价 + LP≤IP + 09 线结构保证 |
| `algos/r2_alns.py` | Modify | 算法 | `move_candidates` 纯函数（contract/free 双模式）+ solve 接线 + `contract_ok` 元数据 |
| `tests/test_algorithm_contract.py` | Create | 算法 | 候选逻辑确定性 + free 模式缺陷存在性 + 同种子复现 + 09 线端到端三闸 |
| `core/base.py` | Modify（1 行） | 验收 | `AlgoResult.contract_ok` |
| `run_r2_ledger.py` | Modify | 实验 | days 落盘、`contract_viol`、`--legacy-free` 复现开关、合同账分文件 |
| `output/` 各 json | Create（产物） | 实验 | Phase B 审计账 / Phase C 合同账 |
| `docs/guides/ALGORITHM_GUIDE.md`、`AGENTS.md` §四、`docs/README.md` | Modify | 文档 | 附录 C / 新账 / 导航 |

---

### Task 0【解耦】归档遗产 + 实验归置 + 公开 API

**Files:**
- Create: `archive/`（含 `archive/README.md` 说明各层年代）、`experiments/`
- Modify: 被移动脚本的 import 路径（`sys.path` 前缀）、`algos/__init__.py`

- [ ] **Step 0.1: 归档三代遗产（git mv 保历史）**

```bash
cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer
mkdir -p archive
git mv svde archive/svde
git mv validation archive/validation
for d in src spec demo examples knowledge_base domain svde-bench __pycache__; do
  [ -e "$d" ] && git rm -r --cached "$d" 2>/dev/null; [ -d "$d" ] && mv "$d" archive/ 2>/dev/null
done
git mv "SH_Store_Insight_产品介绍_v1.0.pdf" "SH_Store_Insight_产品介绍_v1.0.pptx" \
       "SH_Store_Insight_产品介绍_v1.0_预览.png" "SH_Store_Insight_封面_QuickLook.png" \
       "SH_Store_Insight_第1页预览.png" archive/ 2>/dev/null
git mv "数据洞察与销售拜访本体构建_最佳实践与参考研究.md" \
       "方案B-仁军调整-0825.xlsx" "谋圣_售点洞察_产品定位与改进指导_v1.1.md" archive/ 2>/dev/null
rm -rf visit_scheduling_optimizer.egg-info __pycache__
```
Expected: `git status` 显示纯 rename；`python3 -c "import data.loader"` 不受影响；`ls` 根目录只剩主线文件

- [ ] **Step 0.2: 写归档说明**

`archive/README.md`：

```markdown
# 历史归档（非主线代码）

| 目录 | 年代 | 内容 | 状态 |
|---|---|---|---|
| svde/ | 2026 上半年 | 售点洞察/本体构建（prism_ontology、world_model） | 已被主线优化器取代 |
| validation/ | svde 末期 | phase3/4 基准（gt_micro_oracle、warehouse_slotting） | 随 svde 归档 |
| src/ spec/ demo/ examples/ knowledge_base/ domain/ svde-bench/ | 早期 | 各阶段沉积 | 归档 |
| *.pptx *.pdf *.xlsx *洞察*.md | 早期 | 演示与研究资产 | 归档 |

主线 = data/ core/ algos/ tests/ experiments/ run_r2_ledger.py。归档目录禁止 import（不在 sys.path）。
```

- [ ] **Step 0.3: 实验脚本归置 + sys.path 修正**

```bash
mkdir -p experiments
git mv bench_feedback_ablation.py bench_layer1_calendar.py bench_layer2_tsp.py \
       bench_perf_20260904.py build_all_days_comparison.py exp_09_rep.py exp_09_tracks.py \
       gen_v3_09.py refetch_fallback_matrices.py run_4months.py run_all_lines_capacity_sp.py \
       run_all_reps_actual_vs_agent.py run_mo_v4.py run_r2_repeat.py run_r2prime_all.py \
       run_sp_experiment.py run_v3_all.py run_v4_03.py run_v4_greedy_revert.py \
       run_v4_refine_03.py run_v4_scan.py runner.py tools_sp_summary.py \
       run_deep_wave.sh run_sp_all.sh experiments/
```
每个移动脚本的 `sys.path.insert(0, ".")` 改为：

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```
（一次 sed 批量 + 逐文件检查：`grep -l 'sys.path.insert(0, ".")' experiments/*.py`）

Run: `cd experiments && python3 exp_09_rep.py --help 2>&1 | head -2 || python3 -c "import run_mo_v4" 2>&1 | head -2`
Expected: import 正常（路径修正生效）

- [ ] **Step 0.4: 公开 API 声明（堵 Hyrum's Law）**

`algos/tsp_engine.py`、`algos/alns_v3.py`、`algos/hgs_pvrp.py`、`algos/sp_matheuristic.py` 头部加 `__all__`，把被实验脚本引用的符号转正为公开（加下划线别名保留期一版）：

```python
# algos/tsp_engine.py
__all__ = ["exact_open_tsp", "nn2opt_open"]
exact_open_tsp = _exact_open_tsp      # 公开名; _旧名保留一版过渡
nn2opt_open = _nn2opt_open
```
（`alns_v3`: `two_opt/best_insert/worst_edge` 已无下划线，只需 `__all__`；`hgs_pvrp`: `sa_improve/greedy_warm/diversity/counts` 同法转正；`sp_matheuristic`: `check_r2prime/dedupe_pool/sp_solve_ip/sp_solve_lp/column_generate/SPMatheuristic` 入 `__all__`。）

Run: `python3 -c "from algos.tsp_engine import exact_open_tsp; from algos.hgs_pvrp import sa_improve; print('ok')"`
Expected: `ok`

- [ ] **Step 0.5: 回归 + 提交**

```bash
python3 -m pytest tests/ -q 2>&1 | tail -2
git add -A && git commit -m "refactor: archive three legacy generations; move experiments out of root; public solver API (Hyrum's law fix)"
```
Expected: 既有 7 个测试文件全绿；仓库根目录只剩主线 + 文档 + 配置

---

### Task 1【语义层】core/contract.py + 语义层测试

**Files:**
- Create: `core/contract.py`（新语义模块——三层纪律的第一道物理缝；`core/metric.py` 里的 `rhythm_*`/`slot_index_map`/`legal_slot_sets` 等 v2 松弛原语一并迁入，metric.py 只留距离与容量）
- Test: `tests/test_semantic_contract.py`

- [ ] **Step 1.1: 写语义层失败测试**

创建 `tests/test_semantic_contract.py`：

```python
# -*- coding: utf-8 -*-
"""语义层测试: 合同-相位本体 == SRP 数据 (docs/design/CONTRACT_CADENCE_MODEL.md).
定稿标准: 精确重构(集合相等), 不只是"不违例"; 反例必须被拒绝."""
import sys
import datetime as dt
from collections import Counter
from datetime import date

import pytest

sys.path.insert(0, ".")

SRP = "/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx"
LINES = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']


def _july_workdays():
    d0 = date(2026, 7, 1)
    return [d0 + dt.timedelta(days=i) for i in range(31)
            if (d0 + dt.timedelta(days=i)).weekday() < 5]


# ---------- 1. 相位锚定 ----------

def test_phase_of_iso_week_parity():
    from core.contract import phase_of
    assert phase_of(date(2026, 7, 1)) == 1    # ISO 27 奇
    assert phase_of(date(2026, 7, 8)) == 0    # ISO 28 偶
    assert phase_of(date(2026, 7, 15)) == 1   # ISO 29 奇
    assert phase_of(date(2026, 7, 6)) == 0    # 周一 ISO 28 偶
    assert phase_of(date(2026, 7, 13)) == 1   # 周一 ISO 29 奇


# ---------- 2. 合同槽位集: 15 行结构穷举 ----------

def test_slot_sets_exhaustive_15_row_table():
    from core.contract import contract_slot_dates
    dates = _july_workdays()
    wd = {w: [d for d in dates if d.weekday() == w] for w in range(5)}
    for w, ds in wd.items():                       # 周访 = 全部槽位
        assert contract_slot_dates("W", None, ds) == set(ds)
    for w in (0, 1):                               # k=4 双周: 两相位都 2 次
        assert len(contract_slot_dates("B", 0, wd[w])) == 2
        assert len(contract_slot_dates("B", 1, wd[w])) == 2
    for w in (2, 3, 4):                            # k=5: 偶 2 次, 奇 3 次 (f=3 真身)
        even = contract_slot_dates("B", 0, wd[w])
        odd = contract_slot_dates("B", 1, wd[w])
        assert len(even) == 2 and len(odd) == 3
        assert even | odd == set(wd[w]) and not (even & odd)
    assert contract_slot_dates("B", 1, wd[2]) == \
        {date(2026, 7, 1), date(2026, 7, 15), date(2026, 7, 29)}


# ---------- 3. 合同反推 + 验收: 反例必须拒绝 ----------

def test_contract_of_weekly_and_biweekly():
    from core.contract import contract_of
    dates = _july_workdays()
    mon = [d for d in dates if d.weekday() == 0]
    wed = [d for d in dates if d.weekday() == 2]
    days = {mon[0]: [0], mon[1]: [0], mon[2]: [0], mon[3]: [0],
            wed[0]: [1, 2], wed[2]: [1, 2], wed[4]: [1, 2],
            wed[1]: [2], wed[3]: [2]}
    ct = contract_of(days, dates)
    assert ct[0] == ("W", None)
    assert ct[1] == ("B", 1)
    assert ct[2] == ("W", None)


def test_check_contract_rejects_all_counterexamples():
    from core.contract import check_contract
    dates = _july_workdays()
    wed = [d for d in dates if d.weekday() == 2]
    thu = [d for d in dates if d.weekday() == 3]
    ct = {7: ("B", 1), 8: ("W", None)}
    good = {**{d: [7, 8] for d in (wed[0], wed[2], wed[4])},
            **{d: [8] for d in thu}}
    assert check_contract(good, ct, dates) == []
    assert 7 in check_contract({wed[1]: [7], wed[3]: [7],
                                **{d: [8] for d in thu}}, ct, dates)          # 反例1 相位翻转
    bad2 = dict(good); bad2[wed[0]] = [8]; bad2[thu[0]] = [7, 8]
    assert 7 in check_contract(bad2, ct, dates)                                # 反例2 星期几分裂
    bad3 = {wed[0]: [7, 8], wed[2]: [7, 8], wed[4]: [8], **{d: [8] for d in thu}}
    assert 7 in check_contract(bad3, ct, dates)                                # 反例3 缺访
    bad4 = dict(good); bad4[wed[1]] = [7, 8]
    assert 7 in check_contract(bad4, ct, dates)                                # 反例4 多访
    bad5 = dict(good); bad5[thu[0]] = []
    assert 8 in check_contract(bad5, ct, dates)                                # 反例5 周访漏一天


# ---------- 4. 真实数据: 精确重构 1,524 店 ----------

def test_real_data_exact_reconstruction_all_lines():
    from data.loader import load_plan, load_line
    from core.contract import contract_of, contract_slot_dates, check_contract
    pv = load_plan()
    f_dist, ct_dist, total = Counter(), Counter(), 0
    for lid in LINES:
        d = load_line(pv, lid)
        dates = list(d.dates)
        ct = contract_of(d.days_orig, dates)
        assert check_contract(d.days_orig, ct, dates) == []
        sched = {}
        for dd, seq in d.days_orig.items():
            for c in seq:
                sched.setdefault(c, set()).add(dd)
        for c, (k, p) in ct.items():                # 集合相等, 强于"不违例"
            ds = sched[c]
            w = next(iter(ds)).weekday()
            wd_dates = [t for t in dates if t.weekday() == w]
            assert ds == contract_slot_dates(k, p, wd_dates), \
                f"线{lid} 店{c}: 重构不等"
        for c, (k, p) in ct.items():
            ct_dist[(k, p)] += 1
            f_dist[len(sched[c])] += 1
        total += len(ct)
    assert total == 1524
    assert dict(ct_dist) == {("W", None): 1337, ("B", 0): 88, ("B", 1): 99}
    assert dict(f_dist) == {2: 125, 3: 62, 4: 557, 5: 780}


# ---------- 5. 服务周字段交叉验证 (ISO 周 mod 4) ----------

def test_service_week_field_is_iso_week_mod4():
    import pandas as pd
    df = pd.read_excel(SRP, sheet_name="Sheet1")
    df = df[df["计划是否有效标识"] == "有效"]
    bad = sum(1 for _, r in df.iterrows()
              if str(int(r["服务周"])) != str(pd.to_datetime(r["拜访日期"]).date().isocalendar()[1] % 4))
    assert bad == 0, f"服务周 != ISO周 mod4 的行数: {bad}"
```

- [ ] **Step 1.2: 运行确认失败**

Run: `cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer && python3 -m pytest tests/test_semantic_contract.py -v 2>&1 | tail -4`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.contract'`

- [ ] **Step 1.3: 创建 core/contract.py**

新文件 `core/contract.py`（语义层单一职责：拜访合同本体；从 `core/metric.py` 迁入 v2 松弛原语并在 metric.py 删除，`core/metric.py` 顶部加一行 `from core.contract import *  # 兼容旧 import` 过渡）：

```python
# -*- coding: utf-8 -*-
"""语义层: 拜访合同-节拍-相位本体 (2026-09-06 定稿).

docs/design/CONTRACT_CADENCE_MODEL.md:
- 合同 ∈ {周访 W, 双周访 B}; 双周带相位 φ ∈ {0,1} = ISO 自然周 mod 2 (跨月延续);
- 月内次数与日期集完全由 (合同, φ, σ) 决定, f 是派生量;
- 数据铁证: 全办 1,524 店零例外 (15 行结构表).
零求解器依赖 (业务建模层).
"""
import itertools
import math
from collections import defaultdict


# ---- v2 均匀节拍松弛快筛 (合法集 ⊃ 合同版, 只能证伪不能证真) ----

def slot_index_map(dates):
    """{date: (weekday, 周序 idx)}; 同星期几按序编号 (7 月: 周一/二 k=4, 其余 k=5)."""
    by_wd = defaultdict(list)
    for dd in sorted(dates):
        by_wd[dd.weekday()].append(dd)
    return {dd: (w, i) for w, ds in by_wd.items() for i, dd in enumerate(ds)}


def slots_per_weekday(dates):
    n = defaultdict(int)
    for dd in dates:
        n[dd.weekday()] += 1
    return dict(n)


def _ok_gaps(k, f):
    return set(range(1, k + 1)) if f <= 1 else {k // f, -(-k // f)}


def rhythm_ok_dates(ds, slot_of, spw):
    """单店日期集 R2'(单一星期几) + 均匀节拍(松弛)."""
    ds = list(ds)
    if not ds:
        return True
    ws = {slot_of[d][0] for d in ds}
    if len(ws) > 1:
        return False
    w = ws.pop()
    k, idx = spw[w], sorted(slot_of[d][1] for d in ds)
    f = len(idx)
    ok = _ok_gaps(k, f)
    gaps = [idx[i + 1] - idx[i] for i in range(f - 1)] + [idx[0] + k - idx[-1]]
    return all(g in ok for g in gaps)


def check_rhythm(days, slot_of, spw):
    """全月解节奏松弛验收 (返回违例店列表, 空=通过松弛)."""
    shop = defaultdict(list)
    for dd, seq in days.items():
        for c in seq:
            shop[c].append(dd)
    return [c for c, ds in shop.items() if not rhythm_ok_dates(ds, slot_of, spw)]


# ---- 合同-相位本体 (定稿) ----

def phase_of(d):
    """ISO 自然周 mod 2 (跨月自动延续的相位锚)."""
    return d.isocalendar()[1] % 2


def contract_of(days_orig, dates):
    """从原计划反解每店合同: {store_idx: ("W", None) | ("B", phi)}.
    月内次数 == 该星期几槽位数 → 周访; 否则双周, 相位 = 首日期 ISO 周 mod 2."""
    spw = slots_per_weekday(dates)
    sched = defaultdict(set)
    for dd, seq in days_orig.items():
        for c in seq:
            sched[c].add(dd)
    ct = {}
    for c, ds in sched.items():
        w = next(iter(ds)).weekday()
        ct[c] = ("W", None) if len(ds) == spw[w] else ("B", phase_of(next(iter(ds))))
    return ct


def contract_slot_dates(kappa, phi, wd_dates):
    """合同 × 相位 × 星期几槽位 → 合法日期集. 周访=全槽位; 双周=相位匹配槽位."""
    s = set(wd_dates)
    if kappa == "W":
        return s
    return {d for d in s if phase_of(d) == phi}


def legal_date_map(contracts, dates):
    """{store_idx: 全月合法日期集} = ∪_w contract_slot_dates (池过滤/定价剪枝用)."""
    by_wd = defaultdict(list)
    for dd in sorted(dates):
        by_wd[dd.weekday()].append(dd)
    return {c: set().union(*(contract_slot_dates(k, p, by_wd[w]) for w in by_wd))
            for c, (k, p) in contracts.items()}


def check_contract(days, contracts, dates):
    """合同验收(第五闸): 每店日期集必须精确等于其 (合同,相位,σ) 合同槽位集.
    返回违例 store_idx 列表(空=通过). 蕴含 R2' (星期几分裂必违例)."""
    sched = defaultdict(set)
    for dd, seq in days.items():
        for c in seq:
            sched[c].add(dd)
    by_wd = defaultdict(list)
    for dd in sorted(dates):
        by_wd[dd.weekday()].append(dd)
    bad = []
    for c, (k, p) in contracts.items():
        ds = sched.get(c, set())
        if not ds or len({d.weekday() for d in ds}) != 1:
            bad.append(c); continue
        if ds != contract_slot_dates(k, p, by_wd[next(iter(ds)).weekday()]):
            bad.append(c)
    return bad
```

同时 `core/metric.py`：删除已迁走的 rhythm 段（`slot_index_map`~`check_rhythm`，即 metric.py 第 43~115 行），顶部加：

```python
from core.contract import (slot_index_map, slots_per_weekday, rhythm_ok_dates,  # noqa: F401
                           check_rhythm)  # 兼容旧 import 的过渡再导出
```

- [ ] **Step 1.4: 运行语义层测试全绿**

Run: `cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer && python3 -m pytest tests/test_semantic_contract.py -v 2>&1 | tail -10`
Expected: `7 passed`（1,524 店精确重构 + 服务周交叉验证约 8 秒；**失败=本体被推翻，停下重查语义，禁止改断言迁就实现**）

- [ ] **Step 1.5: 旧 import 兼容回归 + 提交**

Run: `python3 -c "from core.metric import check_rhythm, day_km; print('compat ok')" && python3 -m pytest tests/ -q 2>&1 | tail -2`
Expected: `compat ok` + 全绿

```bash
git add core/contract.py core/metric.py tests/test_semantic_contract.py
git commit -m "feat(semantic): core/contract.py ontology module; exact reconstruction verified on 1524 stores"
```

---

### Task 2【数学层】SP 合同模式 + 数学层测试

**Files:**
- Modify: `algos/sp_matheuristic.py`
- Test: `tests/test_mathmodel_sp_contract.py`

- [ ] **Step 2.1: 写数学层失败测试**

创建 `tests/test_mathmodel_sp_contract.py`（合成实例：3 店 × 9 日期，已知最优 12.6；含一条相位非法列证明两模型分叉点）：

```python
# -*- coding: utf-8 -*-
"""数学层测试: SP 合同模式的可行集 == 语义合法集.
部件单元 + RHS 可行模式穷举 + 3^9 暴力枚举等价 + LP≤IP + 真实 09 线结构保证."""
import sys
import itertools
import json
from datetime import date

import pytest

sys.path.insert(0, ".")

MON = [date(2026, 7, 6), date(2026, 7, 13), date(2026, 7, 20), date(2026, 7, 27)]
WED = [date(2026, 7, 1), date(2026, 7, 8), date(2026, 7, 15), date(2026, 7, 22), date(2026, 7, 29)]
DATES = sorted(MON + WED)


def _contracts():
    """3 店: 0=周访, 1=双周偶(合法 m1,m3,w2,w4), 2=双周奇(合法 m2,m4,w1,w3,w5)."""
    from core.contract import contract_of
    days = {m: [0] for m in MON}
    days[WED[1]] = [1]; days[WED[3]] = [1]
    days[WED[0]] = [2]; days[WED[2]] = [2]; days[WED[4]] = [2]
    return contract_of(days, DATES)


def _pool():
    """每日期 3 列, 走廊[1,2]. 已知最优 12.6 = (σ0=mon 全 [0]) + (m2,m4 [2]) + (w2,w4 [1]).
    另含一条相位非法列 (w1 上的店1, km=1.5) 供两模型分叉验证."""
    p = []
    for m in MON:
        p.append((m, [0], 1.0))
        if m in (MON[0], MON[2]):
            p += [(m, [1], 2.0), (m, [0, 1], 2.8)]
        if m in (MON[1], MON[3]):
            p += [(m, [2], 2.5), (m, [0, 2], 3.3)]
    for w in WED:
        p.append((w, [0], 1.0))
        if w in (WED[1], WED[3]):
            p += [(w, [1], 2.0), (w, [0, 1], 2.8)]
        if w in (WED[0], WED[2], WED[4]):
            p += [(w, [2], 2.5), (w, [0, 2], 3.3)]
    p.append((WED[0], [1], 1.5))          # 相位非法: 店1 出现在奇相位周三
    return p


# ---------- 1. 部件单元 ----------

def test_fw_table_matches_contract_counts():
    from algos.sp_matheuristic import _fw_table, weekday_dates
    from core.contract import contract_slot_dates
    ct = _contracts()
    wd_g = weekday_dates(DATES)
    fw = _fw_table(ct, wd_g)
    assert fw[0] == {0: 4, 2: 5}          # 周访: k4/k5
    assert fw[1] == {0: 2, 2: 2}          # 双周偶
    assert fw[2] == {0: 2, 2: 3}          # 双周奇: k5 → 3 次 (f=3 真身)
    for c, tbl in fw.items():
        for w, f in tbl.items():
            assert f == len(contract_slot_dates(*ct[c], wd_g[w]))


def test_pool_filter_drops_exactly_illegal():
    from algos.sp_matheuristic import _contract_pool_filter
    from core.contract import legal_date_map
    ct = _contracts()
    out, drop = _contract_pool_filter(_pool(), legal_date_map(ct, DATES))
    assert drop == 1 and (WED[0], [1], 1.5) not in out
    legal = legal_date_map(ct, DATES)
    assert all(d in legal[c] for d, r, _ in out for c in r)


# ---------- 2. RHS 线性化可行模式穷举 (双周奇店) ----------

def test_linearized_rhs_admits_exactly_legal_patterns():
    from ortools.sat.python import cp_model
    from algos.sp_matheuristic import _fw_table, weekday_dates
    fw = _fw_table(_contracts(), weekday_dates(DATES))[2]     # 店2 (B,1)
    feasible = []
    for mon_dates in [()] + [c for k in (2,) for c in itertools.combinations(MON, k)]:
        for wed_dates in [()] + [c for k in (3,) for c in itertools.combinations(WED, k)]:
            if not mon_dates and not wed_dates:
                continue
            m2 = cp_model.CpModel()
            cols = {**{m: i for i, m in enumerate(MON)}, **{w: 4 + i for i, w in enumerate(WED)}}
            x = {i: m2.NewBoolVar(f"x{i}") for i in cols}
            z = {w: m2.NewBoolVar(f"z{w}") for w in (0, 2)}
            m2.AddExactlyOne(list(z.values()))
            on = [i for i, d in cols.items() if d in mon_dates + wed_dates]
            m2.Add(sum(x[i] for i in on) == sum(fw[w] * z[w] for w in (0, 2)))
            for i, d in cols.items():
                m2.Add(x[i] <= z[d.weekday()])
            if cp_model.CpSolver().Solve(m2) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                feasible.append((mon_dates, wed_dates))
    assert set(feasible) == {((), (WED[0], WED[2], WED[4])), ((MON[1], MON[3]), ())}


# ---------- 3. 暴力枚举等价 ----------

def _brute_force(contract_mode=True):
    from core.contract import legal_date_map, check_contract
    ct = _contracts()
    legal = legal_date_map(ct, DATES)
    by_date = {}
    for d, r, km in _pool():
        by_date.setdefault(d, []).append((r, km))
    best = None
    for combo in itertools.product(*(by_date[d] for d in DATES)):
        sched = {c: set() for c in ct}
        ok = True
        for d, (r, _) in zip(DATES, combo):
            for c in r:
                if contract_mode and d not in legal[c]:
                    ok = False
                sched[c].add(d)
        if not ok:
            continue
        days = {d: list(r) for d, (r, _) in zip(DATES, combo)}
        if contract_mode and check_contract(days, ct, DATES):
            continue
        if any(not v for v in sched.values()):
            continue
        km = sum(k for _, k in combo)
        best = km if best is None else min(best, km)
    return best


def test_ip_optimum_equals_bruteforce_semantic_opt():
    from algos.sp_matheuristic import sp_solve_ip
    ct = _contracts()
    k_c = {0: 4, 1: 2, 2: 3}
    km, days = sp_solve_ip(DATES, k_c, _pool(), timeout_s=30, contract=ct)
    assert km == pytest.approx(_brute_force(True), abs=1e-6) == pytest.approx(12.6, abs=1e-6)
    km_legacy, _ = sp_solve_ip(DATES, k_c, _pool(), timeout_s=30)
    assert km_legacy == pytest.approx(_brute_force(False), abs=1e-6)
    assert km_legacy < km, "legacy(无相位约束)必须严格更优 — 两模型恰在非法集分叉"


def test_lp_le_ip_on_synthetic():
    from algos.sp_matheuristic import sp_solve_lp, sp_solve_ip
    ct = _contracts()
    k_c = {0: 4, 1: 2, 2: 3}
    lp, _ = sp_solve_lp(DATES, k_c, _pool(), timeout_s=30, contract=ct)
    ip, _ = sp_solve_ip(DATES, k_c, _pool(), timeout_s=30, contract=ct)
    assert lp is not None and lp <= ip + 1e-6


# ---------- 4. 真实 09 线结构保证 ----------

def test_09_baseline_only_pool_structure_guarantee():
    import numpy as np
    from data.loader import load_plan, load_line
    from core.contract import contract_of, check_contract, legal_date_map
    from core.metric import day_km
    from algos.tsp_engine import _exact_open_tsp
    from algos.sp_matheuristic import sp_solve_ip, sp_solve_lp, _contract_pool_filter
    pv = load_plan()
    d = load_line(pv, "09")
    D = np.load("output/road_dist_09.npy")
    dates = list(d.dates)
    ct = contract_of(d.days_orig, dates)
    k_c = {c: sum(1 for dd, seq in d.days_orig.items() if c in seq) for c in ct}
    pool = []
    for dd, seq in d.days_orig.items():
        seq_opt = _exact_open_tsp(list(seq), D, time_limit=30)
        pool.append((dd, list(seq_opt), round(day_km(seq_opt, D), 3)))
    pool2, drop = _contract_pool_filter(pool, legal_date_map(ct, dates))
    assert drop == 0, "原始计划零例外, 基线A 列不应被合同过滤误伤"
    km, days = sp_solve_ip(dates, k_c, pool2, timeout_s=60, contract=ct)
    baseA = json.load(open("output/cpsat_plan_baselines.json"))["09"]
    assert abs(km - baseA) < 0.1, f"结构保证破坏: {km} vs {baseA}"
    assert check_contract(days, ct, dates) == []
    lp, _ = sp_solve_lp(dates, k_c, pool2, timeout_s=60, contract=ct)
    assert lp is not None and lp <= km + 1e-6
```

- [ ] **Step 2.2: 运行确认失败**

Run: `cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer && python3 -m pytest tests/test_mathmodel_sp_contract.py -v 2>&1 | tail -4`
Expected: FAIL — `ImportError: cannot import name '_fw_table'`

- [ ] **Step 2.3: 实现 SP 合同模式**

`algos/sp_matheuristic.py` 五处修改（与文件现状逐行对应）：

(1) `_z_open`（第 79 行）之后加：

```python
def _contract_pool_filter(pool, legal):
    """合同池过滤: 剔除任何 (店,日期) 非法成员关系的列. 返回 (pool, n_dropped)."""
    out, drop = [], 0
    for date, route, km in pool:
        if any(c in legal and date not in legal[c] for c in route):
            drop += 1
            continue
        out.append((date, route, km))
    return out, drop


def _fw_table(contracts, wd_groups):
    """派生频次表 {c: {w: f(c,w)}}: f = |合同槽位集| (周访=k_w, 双周=相位计数)."""
    from core.contract import contract_slot_dates
    return {c: {w: len(contract_slot_dates(k, p, ds)) for w, ds in wd_groups.items()}
            for c, (k, p) in contracts.items()}
```

(2) `sp_solve_lp`（第 81 行）：签名加 `contract=None`；`solver = ...` 后插池过滤；覆盖约束段合同模式跳过；z 段替换（强制建 z + RHS 线性化 `sum(x[i] for i in cols) == sum(fw[c][w] * zc[w] for w in ws)`；合同模式下 z 开放集 = 全部星期几）。`duals["store"]` 从线性化覆盖约束取对偶（语义=该店合同覆盖影子价）。

(3) `sp_solve_ip`（第 198 行）：同构改造，API 换 CP-SAT（`m.AddExactlyOne` / `m.Add(sum(xv) == sum(fw·z))`）。

(4) `price_columns`（第 121 行）：签名加 `legal=None`；`start_c` 循环体首与内层候选循环 `if c in in_day:` 后各加 `if legal is not None and dd not in legal.get(c, ()): continue`。

(5) `column_generate`（第 168 行）与 `SPMatheuristic.solve`（第 250 行）：签名各加 `contract=None`；透传 LP/IP/定价（定价传 `legal=legal_date_map(contract, dates) if contract else None`）。

- [ ] **Step 2.4: 运行数学层测试全绿**

Run: `cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer && python3 -m pytest tests/test_mathmodel_sp_contract.py -v 2>&1 | tail -10`
Expected: `6 passed`（合成毫秒级；09 结构保证约 40 秒）

- [ ] **Step 2.5: 提交**

```bash
git add algos/sp_matheuristic.py tests/test_mathmodel_sp_contract.py
git commit -m "feat(math): SP contract mode; feasible set proven equal to semantic set by brute force"
```

---

### Task 3【算法层】r2_alns 合同化 + 算法层测试

**Files:**
- Modify: `algos/r2_alns.py`
- Test: `tests/test_algorithm_contract.py`

- [ ] **Step 3.1: 写算法层失败测试**

创建 `tests/test_algorithm_contract.py`：

```python
# -*- coding: utf-8 -*-
"""算法层测试: MOVE 候选纯逻辑(确定性) + free 模式缺陷存在性 + 同种子复现 + 09 端到端三闸."""
import sys
import random
from datetime import date

sys.path.insert(0, ".")

MON = [date(2026, 7, 6), date(2026, 7, 13), date(2026, 7, 20), date(2026, 7, 27)]
WED = [date(2026, 7, 1), date(2026, 7, 8), date(2026, 7, 15), date(2026, 7, 22), date(2026, 7, 29)]


def test_move_candidates_contract_mode_deterministic_and_legal():
    from algos.r2_alns import move_candidates
    contracts = {5: ("B", 1)}
    sched = {WED[0], WED[2], WED[4]}
    seen = set()
    for seed in range(20):                       # 与 rng 无关
        cands = move_candidates(5, sched, {0: MON, 2: WED}, contracts, "contract",
                                random.Random(seed))
        assert all(ds == {MON[1], MON[3]} for w, ds in cands), "奇相位周一=第2/4个, 唯一候选"
        seen.add(tuple(sorted(w for w, _ in cands)))
    assert seen == {(0,)}, "原星期几(周三)候选=原集合, 必被跳过"


def test_move_candidates_free_mode_can_be_illegal():
    """free(旧口径)随机全组合可产生相位非法集 — v1 缺陷存在性, 审计复现口径的依据."""
    from algos.r2_alns import move_candidates
    from core.contract import contract_slot_dates
    contracts = {5: ("B", 1)}
    sched = {WED[0], WED[2], WED[4]}
    legal_wed = contract_slot_dates("B", 1, WED)
    seen_illegal = False
    for seed in range(200):
        cands = move_candidates(5, sched, {0: MON, 2: WED}, contracts, "free",
                                random.Random(seed))
        if any(w == 2 and ds != legal_wed for w, ds in cands):
            seen_illegal = True
    assert seen_illegal, "200 种子内必须见过相位非法候选"


def test_r2alns_same_seed_reproducible_and_gated():
    import numpy as np
    from data.loader import load_plan, load_line
    from core.contract import contract_of, check_contract
    from algos.r2_alns import R2ALNS
    from algos.sp_matheuristic import check_r2prime
    pv = load_plan()
    d = load_line(pv, "09")
    D = np.load("output/road_dist_09.npy")
    dates = list(d.dates)
    ct = contract_of(d.days_orig, dates)
    r1 = R2ALNS().solve(d, D, time_budget=30, seed=42)
    r2 = R2ALNS().solve(d, D, time_budget=30, seed=42)
    assert r1.km == r2.km, "同种子必须逐位复现 (若抖动: 加大预算重试, 不许删断言)"
    assert r1.capacity_ok and check_r2prime(r1.days) == []
    viol = check_contract(r1.days, ct, dates)
    assert viol == [], f"合同违例 {len(viol)}: {viol[:10]}"
    assert r1.metadata["contract_ok"] is True
```

- [ ] **Step 3.2: 运行确认失败**

Run: `cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer && python3 -m pytest tests/test_algorithm_contract.py -v 2>&1 | tail -4`
Expected: FAIL — `ImportError: cannot import name 'move_candidates'`

- [ ] **Step 3.3: 实现 move_candidates + solve 接线**

`algos/r2_alns.py`：

(1) 第 18 行后加：`from core.contract import contract_of, contract_slot_dates, check_contract`

(2) `@register` 前加模块级纯函数：

```python
def move_candidates(c, sched_dates, wd_g, contracts, combo_mode, rng):
    """MOVE 候选生成 (纯函数, 确定性可测).
    contract: 每目标星期几恰一个合同槽位集 (v1 全组合=C(k,f) 是月频次错误, 已废);
    free: 旧口径随机全组合 (仅供 Phase B 旧账复现审计). 返回 [(weekday, 新日期集)]."""
    old = set(sched_dates)
    out = []
    kappa, phi = contracts[c]
    for w2, slots in wd_g.items():
        if combo_mode == "contract":
            new_ds = contract_slot_dates(kappa, phi, slots)
        else:
            f = len(old)
            if f > len(slots):
                continue
            new_ds = set(rng.choice(list(itertools.combinations(slots, f)))) \
                if len(slots) > f else set(slots)
        if new_ds and new_ds != old:
            out.append((w2, new_ds))
    return out
```

(3) `solve` 签名（第 28 行）加 `combo_mode="contract"`；第 35 行前加 `contracts = contract_of(data.days_orig, dates)`。

(4) 主循环候选段（原第 84~93 行）替换为：

```python
            c = rng.choice(stores)
            old_dates = sorted(sched[c], key=str)
            best_ev = None
            for w2, new_ds in move_candidates(c, sched[c], wd_g, contracts, combo_mode, rng):
                new_dates = sorted(new_ds, key=str)
```

（第 96 行起走廊校验与估价不动。）

(5) 返回 metadata 加：`"contract_ok": len(check_contract(days, contracts, dates)) == 0,`

- [ ] **Step 3.4: 运行算法层测试全绿**

Run: `cd /Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer && python3 -m pytest tests/test_algorithm_contract.py -v 2>&1 | tail -6`
Expected: `3 passed`（端到端约 70 秒）

- [ ] **Step 3.5: 提交**

```bash
git add algos/r2_alns.py tests/test_algorithm_contract.py
git commit -m "feat(algorithm): MOVE on contract slot sets; deterministic + reproducibility + gates tests"
```

---

### Task 4: 验收闸 + ledger 落盘与开关

**Files:**
- Modify: `core/base.py:39`、`run_r2_ledger.py`

- [ ] **Step 4.1: `AlgoResult` 第 39 行 `capacity_ok` 后加**：`contract_ok: bool = True  # 合同-相位守恒 (第五闸)`

- [ ] **Step 4.2: `run_r2_ledger.py`**——第 23 行后加 `LEGACY_FREE = '--legacy-free' in sys.argv` 与 `from core.contract import contract_of, check_contract`；输出名合同模式改 `sp_contract_ledger_{lid}.json`（防覆盖旧账，旧账先备份 `output/backup_ledger_20260906/`）；R2ALNS 调用加 `combo_mode=("free" if LEGACY_FREE else "contract")`；SP 调用合同模式传 `contract=contracts`；rec 加 `contract_viol`/`mode` 字段；终解 days 落盘 `output/sp_r2_days_{lid}.json`

- [ ] **Step 4.3: 冒烟**

```bash
mkdir -p output/backup_ledger_20260906 && cp output/sp_r2_ledger_??.json output/backup_ledger_20260906/
python3 run_r2_ledger.py 09 2>&1 | tail -2
```
Expected: `违R2'=0`；`output/sp_contract_ledger_09.json` 中 `contract_viol==0`、`structure_guarantee==true`；SP ∈ [310.4, 326.6]

- [ ] **Step 4.4: 全量回归 + 提交**

```bash
python3 -m pytest tests/ -q 2>&1 | tail -2
git add core/base.py run_r2_ledger.py output/sp_contract_ledger_09.json output/sp_r2_days_09.json
git commit -m "feat: contract gate; ledger days dump + audit fields + legacy-free switch; 09 smoke"
```

---

### Task 5: Phase B —— 旧账相位污染审计

- [ ] **Step 5.1** `nohup python3 run_r2_ledger.py 02 03 04 05 06 07 08 09 10 11 --legacy-free > output/legacy_free_rerun.log 2>&1 &`（约 2.5 h；各线 sp_km 须与备份旧账一致，容差 ±0.5 km）
- [ ] **Step 5.2** 汇总 `output/contract_audit_r2_ledger.json`（十线 `contract_viol` + 总数 / 187 双周店）；结论三分支：0 → 旧账转正；≤20 → 记录收拢成本；>20 → Task 6 为正式账
- [ ] **Step 5.3** `git add` 审计产物 + commit `"bench: phase-B contract violation census"`

---

### Task 6: Phase C —— 合同口径十线重跑（Windows 主力）

- [ ] **Step 6.1** 同步 `core/ algos/ run_r2_ledger.py` 到 `ghb@192.168.31.188:C:/Users/ghb/bench09/`（sshpass；遇限流 `sleep 30`）
- [ ] **Step 6.2** schtasks 模式跑 `run_r2_ledger.py 02..11`（`cmd /c ... ^> contract10.log`；禁裸 `start /b`）
- [ ] **Step 6.3** 回收合并 `output/sp_contract_ledger_all.json`；打印：合同口径 vs 基线 A 降幅、vs 旧松弛 3,618.5 的相位代价、十线 contract_viol 全 0
- [ ] **Step 6.4** commit `"bench: contract-mode 10-line final account"`

---

### Task 7: 文档收口

- [ ] **Step 7.1** `ALGORITHM_GUIDE.md` 附录 C：三次语义教训（月频次→均匀节拍→合同-相位）+ 方法论（"零违例只证规则≥数据，重构相等才是定稿"）+ 解耦决定（Google 判据、Hyrum's Law 证据、增量不 big-bang）
- [ ] **Step 7.2** `AGENTS.md` §四 换合同账（`sp_contract_ledger_all.json`，新增 contract_viol 列全 0），删口径警示块
- [ ] **Step 7.3** `docs/README.md` 导航收录本体/REPLAN/本计划；路径 B 插入本体文档
- [ ] **Step 7.4** 全量回归 + commit `"docs: appendix C + constitution refresh + nav"`

---

## Self-Review（写完自查）

1. **覆盖**：解耦=Task 0；语义=Task 1；数学=Task 2；算法=Task 3；闸与实验=Task 4~6；文档=Task 7。REPLAN Phase A↔Task 0~4、B↔Task 5、C↔Task 6、D↔Task 7。
2. **层间依赖**：contract.py（T1）← SP 合同模式（T2）← r2_alns 端到端（T3）；每层测试独立可跑，红绿分明。
3. **占位符**：无；所有代码完整；命令带期望输出/容差。
4. **类型一致性**：`contract_of → {c:(κ,φ)}` 贯穿 `contract_slot_dates(kappa,phi,wd_dates)`、`legal_date_map(contracts,dates)`、`check_contract(days,contracts,dates)`、SP `contract=/legal=`、`move_candidates(c,sched_dates,wd_g,contracts,combo_mode,rng)`。
5. **防再错锚点**：f=3 真身、ISO mod 2/mod 4、1,524 精确重构全部固化为断言；legacy/free 双口径隔离防审计污染。
