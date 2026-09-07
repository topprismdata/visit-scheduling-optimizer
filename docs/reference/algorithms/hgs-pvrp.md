# HGS-PVRP（混合遗传搜索）

> 类别：元启发式（种群） | 实现：`algos/hgs_pvrp.py` | 矩阵身份：独立机制行（多样性保留）

## 它解决什么

与 ALNS 同岗位的 Layer1 候选生产者，用**种群体制**（UHGS 血统：混合遗传搜索 + 偏差适应度选择 + 解距离多样性管理）探索日历+顺序联合空间。与 ALNS 的差异在搜索体制（population vs 单解轨迹），这正是研究矩阵保留它的理由——多样性，不是排名。

## 输入 / 输出

- 输入：`LineData`、`D`、`time_budget`、`seed`。
- 适配声明（代码头注）：每日**开放链**（无仓库往返）、每店出现次数多集合守恒、任意工作日可跨；单日容量硬约束 ≤ 原计划峰值。
- 输出：`AlgoResult(days=有序路线, km, capacity_ok, metadata)`。

## 机制

```
种子池:  nn2opt 起点 + 贪心热身(8% 预算) + 短 SA → base 个体；
         再深拷贝扰动 7 份 → 共 8 个体 (_Ind: tours + 逐店日期集向量 + km)
主循环 (pop_size=24):
  偏差适应度: rank(km) 与 rank(平均多样性) 加权 (S=6) → 锦标赛选父
  交叉:      日级均匀重组 —— child[dd] 50/50 取 p1 或 p2 的当日路线
  守恒兜底:  多退少补 —— 每店计数 vs 合同频次，多了按最小移除增量删，
             少了按最小插入增量补（含容量满时的最少店日兜底）
  教育:      v3 同款短促模拟退火（SA，Simulated Annealing）（hot=0.15，单代 ≤12% 剩余时间）
终局: 对 best 逐日 two_opt(30 轮)
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
