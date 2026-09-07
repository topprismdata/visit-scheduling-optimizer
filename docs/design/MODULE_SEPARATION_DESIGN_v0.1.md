# 三模块剥离设计（VisitIR / VisitModel / OptiCore 收口）

> **状态**：v0.1 · 2026-09-07（依据 2026-09-06/07 三遍设计评审，评审证据见本文各节引用）
> **关系**：本设计是 `ALGORITHM_GUIDE.md` 附录 D"仓库三层抽离"裁定的**收口方案**——三层已立项（VisitIR / VisitModel / OptiCore 均已存在于 `/Users/ghb/` 且母仓经 editable install 消费），但抽离**未完成**：shim 残留、估计器双份维护、33k 行遗产在树、版本零钉住。本方案一次收口。
> **实施计划**：`docs/superpowers/plans/2026-09-07-module-separation.md`

---

## 1. 现状与问题（全部有证据）

| # | 问题 | 证据 |
|---|---|---|
| P1 | 语义/建模/引擎三仓外置但**零钉住**：母仓行为随三仓 HEAD 漂移而静默变化，换机即崩 | `core/contract.py:2-7` shim 自述；`.venv` 解析 `visit_ir → /Users/ghb/VisitIR`、`visitmodel → /Users/ghb/VisitModel`、`opticore → /Users/ghb/OptiCore`；三仓均无 tag |
| P2 | **估计器双份维护**：R2′ 的 2-NN 三件套（nn2 / removal_gain / insertion_cost）与 NN 链+2-opt 估价在 `r2_alns.py:66-140` 与 `branch_and_price.py:124-269`（`_randomized_schedule/_calendar_search` 内）近乎复制 | 两文件对照 |
| P3 | **legacy 在树**：`algos/pvrp_cg/`（二代项目）生产代码零引用，仅 7 个测试文件挂靠；其中 4 文件 16 用例全红（`counties`/`max_per_day` 关键字已不存在）+ `test_phase2_integration.py` import error | `grep pvrp_cg`：仅 tests/ 下 7 文件；全量 pytest 输出 |
| P4 | **shim 残留**：`core/contract.py` 纯转发 `visit_ir.contract`，11 个文件仍走旧路径 | `grep core.contract` 引用面 |
| P5 | bp 模式 reroute 随池规模线性爆炸（线 11：池 1,449 列逐列 CP-SAT，elapsed 1572s vs r2 同线 433s） | `run_contract_matrix.py:234-239` + 矩阵 JSON |
| P6 | bp 证书审计链断一环：引擎输出 `exact_pricing_calls` 未落盘 | jq 实证字段缺失 |
| P7 | `--alloc-budget` 双语义脚枪（秒 vs ×600 迭代），实战已咬人一次 | `run_contract_matrix.py:72-74,100-102` |
| P8 | B&P 根节点 CG 打满被静默丢弃：`root_lb` 丢失、无告警（线 11：`cg_iters=15, converge_attempts=0`） | `branch_and_price.py` `_solve_node_cg` 尾部 + 审计计数 |

## 2. 目标架构

```
┌─────────────────────────────────────────────────────────┐
│ 母仓 visit-scheduling-optimizer（编排层）                │
│  algos/（组合算法: r2_alns, branch_and_price, sp_matheuristic, sdr…）│
│  experiments/ · run_r2_ledger.py · docs/ · data/        │
└──────────┬──────────────────────┬───────────────────────┘
           │ import               │ import
┌──────────▼──────────┐  ┌────────▼────────┐
│ VisitModel          │  │ OptiCore        │
│ visitmodel.sp.      │  │ opticore.       │
│  formulation (SP/R2′│  │  heuristics     │
│  对偶语义)          │  │  estimators ←新 │
└──────────┬──────────┘  └─────────────────┘
           │ import               （零领域依赖：只认 D 矩阵与节点 id）
┌──────────▼──────────┐
│ VisitIR             │
│ visit_ir.contract   │
│ （合同-相位语义核心）│
└─────────────────────┘
```

**各仓职责与边界**：

| 仓 | 职责 | 禁止 |
|---|---|---|
| VisitIR | 合同/相位/频次本体、合法性判定（`contract_of/check_contract/contract_slot_dates/legal_date_map/…`） | 任何求解器 import、任何里程概念 |
| VisitModel | SP/R2′ 公式化与对偶语义（`sp_solve_lp/sp_solve_ip/_fw_table/weekday_dates`）、定价公式 | 启发式实现、数据加载 |
| OptiCore | 通用求解件：TSP 启发式/精确（`nn2opt_open/lkh`）、**新增** 2-NN 估计器与 NN 链+2-opt 估价（`estimators`） | 领域概念（合同/日期/频次） |
| 母仓 | 算法组合、实验编排、台账、文档；唯一持有业务数据与口径 | 再内嵌通用启发式/估计器（P2 类重复） |

**依赖方向**（单向，禁止回边）：母仓 → VisitModel → VisitIR；母仓 → OptiCore。OptiCore 与 VisitIR 互不依赖。

## 3. 迁移清单

### 3.1 估计器下沉（P2 → OptiCore）
- 新模块 `OptiCore/src/opticore/estimators.py`：`nn2(c, members, D)`、`removal_gain(c, members, D)`、`insertion_cost(c, members, D)`（空集返回 None）、`nn_chain(members, D)`、`two_opt(route, D)`、`nn_chain_2opt(members, D)`、`open_km(route, D)`。
- 契约：**纯函数、确定性**（距离平局按节点 id 升序破）；`D` 为 numpy 矩阵，节点为任意可排序 id。
- 母仓改造：`r2_alns.py` 搜索层闭包改为薄委托；`branch_and_price.py` 删除 `_calendar_search` 内嵌 nn2/removal_gain/insertion_cost/day_km_est 副本，改 import。行为等价由黄金值测试钉死（§5）。

### 3.2 shim 清除（P4）
- 删除 `core/contract.py`；全仓 11 处 `from core.contract import …` 改 `from visit_ir.contract import …`（含 `core/metric.py`、`run_r2_ledger.py`、测试）。**不留兼容别名**（干净切断）。

### 3.3 legacy 处置（P3）
- `git rm -r algos/pvrp_cg` + 删除 7 个挂靠测试（`test_alns_validity/test_calibration/test_constraints/test_solver_adapter/test_phase2_integration/test_travel/test_planning`）。git 历史即归档；如需快照另出 `archive/pvrp_cg-<date>.tgz` 一次性包。
- 验收：`pytest tests/` 全绿成为合并闸。

### 3.4 母仓快赢（P5/P6/P7/P8，与剥离同批落地防二次冲突）
- **P5**：bp 模式 reroute 前先 `dedupe_pool(engine_pool, max_daily, min_daily, top_k=8)`（复用现有函数），CP-SAT 只精排进 SP 候选集的列；落盘 `bp_reroute_pool_before/after`。
- **P6**：bp 元数据补 `bp_exact_pricing_calls` 映射。
- **P7**：`validate_budget_args(args)`——r2_alns/bp 模式下 `--r2-iterations` 与 `--r2-wall-time` 至少显式给一个，否则 CLI 报错退出（默认 `--alloc-budget` 不再静默换算）。
- **P8**：`_solve_node_cg` 迭代打满时不再返回 None 丢弃——记录 `root_lp_unconverged`（命名诚实：未收敛 RMP LP **不是**有效下界，不得写入 `root_lb`）与 `cg_degraded_nodes` 计数，节点仍不分支（不污染剪枝语义）。

## 4. 版本钉住机制（P1）

- 三仓各打 tag：`v0.1.0`（VisitIR @625bfee、VisitModel @ffbca43、OptiCore @41b4bed 为基线，剥离合并时更新）。
- 母仓根新增 `requirements-lock.txt`（`<repo绝对路径> <tag或commit>` 三行）+ `scripts/sync_libs.sh`（checkout 锁定版 + `pip install -e`）+ `scripts/check_libs.sh`（HEAD ≠ 锁 → exit 1，作为流水线 preflight/月度重算前置闸）。
- 三仓改动流程：先在子仓提交/tag → 母仓更新 lock → 母仓跑全绿 → 母仓提交。禁止母仓内直接改子仓代码。

## 5. 测试策略与绿灯闸

- **黄金值等价**：R2ALNS（09 线，`iteration_budget=300, seed=42, final_reroute=False`）改造前后 km/days 逐位一致——重构前先跑一次把值写进测试常量；B&P 微型实例 7 用例继续全绿。
- 各仓自带单测（OptiCore estimators 黄金值、VisitIR 语义、VisitModel 公式化），母仓只测编排与算法组合。
- 合并闸 = `pytest tests/` 全绿 + `scripts/check_libs.sh` 通过 + 09 线 bp 冒烟（`--r2-iterations 5000` 档 `contract_viol=0`）。

## 6. 与优化路线的衔接

- 本计划**不含** ESPPRC 精确定价（评审 2.2，B&P 从证书工具升级为质量工具的唯一路径）——其归属 VisitModel（labeling 公式）+ OptiCore（通用件），待本剥离落地后**另立计划**，避免两件大工程互相踩。
- seed 经济学（6/8 seed 边际）、CV 次级目标实验：剥离后按附录 E 节奏排期，不在本计划。

## 7. 风险与回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| 估计器下沉引入行为漂移 | 黄金值测试前置钉死；两算法各自测试守门 | revert 母仓单 commit |
| 删 pvrp_cg 误伤仍需能力 | grep 证生产零引用；归档 tgz 留底 | `git revert` + tgz |
| 三仓锁定后需要紧急热修 | 子仓 hotfix tag → 更新 lock 单行 | lock 指回旧 tag |
| B&P 降级返回改变树行为 | 不分支、不写 root_lb、只加观测字段；PROVEN 判据不变 | revert 单 commit |
