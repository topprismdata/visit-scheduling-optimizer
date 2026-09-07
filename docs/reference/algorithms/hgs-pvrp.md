# HGS-PVRP（混合遗传搜索）

> 类别：元启发式（种群） | 实现：`algos/hgs_pvrp.py` | 矩阵身份：独立机制行（多样性保留）

## 它解决什么

与 ALNS 同岗位的 Layer1 候选生产者，用**种群体制**（UHGS 血统：混合遗传搜索 + 偏差分解路由 crossover + 解距离多样性管理）探索日历+顺序联合空间。与 ALNS 的差异在搜索体制（population vs 单解轨迹），这正是研究矩阵保留它的理由——多样性，不是排名。

## 输入 / 输出

- 输入：`LineData`、`D`、`time_budget`、`seed`。
- 适配声明（代码头注）：每日**开放链**（无仓库往返）、每店出现次数多集合守恒、任意工作日可跨；单日容量硬约束 ≤ 原计划峰值。
- 输出：`AlgoResult(days=有序路线, km, capacity_ok, metadata)`。

## 机制

```
greedy_warm: v3 同款贪心跨日热身（双向走廊硬约束，two_opt 局部收口）
sa_improve:  v3 同款 SA 主循环（四算子 worst/cross/segment/random + 自适应权重）
种群层：  解距离多样性 _diversity（逐店日期集差异比例）管理子种群
crossover: 偏差分解路由（OXB 式）重组两个父代
```

- 数值件用 numpy 向量化（`_ins_deltas` 插入增量数组一次算全程）。
- 依赖 `algos.alns_v3` 的 `two_opt/best_insert/worst_edge`（同族共享几何件）。

## 复杂度与预算

- 墙钟驱动；种群规模与子代管理消耗内存（deepcopy 父代）。
- 机制剖面记录：代数/评估次数。

## 已知边界与陷阱

1. 同 ALNS：产出不保证 R2′/合同——必须过 Contract-SP 终闸（干净对照中实测 ≈ 基线的机制解释同 v3）。
2. 种群体制的确定性弱于单解 SLS（同一 seed 内部仍有 deepcopy/迭代序依赖）——复现档需按 §6.3 固定全部 worker/顺序。

## 引用论文

- Vidal et al. (2012)：UHGS 原始框架（PVRP 参考 SOTA）。
- Vidal (2022)：HGS 开源实现（CVRP）。
- Ropke & Pisinger (2006)：算子池来源。

## 相关文件与测试

- `algos/hgs_pvrp.py`；矩阵接入：`experiments/run_contract_matrix.py`（`hgs_pvrp` 模式）
