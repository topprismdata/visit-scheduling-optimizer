# ALNS v3（反馈耦合自适应大邻域搜索）

> 类别：元启发式——自适应大邻域搜索（ALNS，Adaptive Large Neighborhood Search）族 | 实现：`algos/alns_v3.py` | 矩阵身份：独立机制行（实测 ≈ 基线，作对照与多样性保留）

## 它解决什么

与 R2 同岗位的 Layer1 候选日历生产者，但走**通用 ALNS 路线**：destroy–repair 多算子 + 自适应权重 + 模拟退火分段降温，同时**携带每日 tour**（"把 TSP 当眼睛"：增量 2-opt、tour-informed destroy、regret 插入），而不是每次候选用 TSP 重新当秤（那是 v1，已淘汰）。

## 输入 / 输出

- 输入：`LineData`、`D`、`time_budget`、`seed`、`weekday_lock`（仅同星期几槽位互挪的旧口径开关）。
- 输出：`AlgoResult(days=每日完整有序路线, km, capacity_ok, metadata{iters})`。

## 机制

```
暖身：每日 nn2opt + ≤30 轮贪心跨日（双向走廊约束；12% 预算）
温度：以平均边长为基的分段降温 T0→T1→T2→T3（Kirkpatrick 式模拟退火，SA：Simulated Annealing）
  算子池 ['worst', 'cross', 'segment', 'random']
    worst:    移除"最差边"关联店（Shaw 式 related removal 变体）
    cross:    跨日移动
    segment:  段迁移
    random:   随机移除
  repair = best_insert（regret/最佳插入）
  权重自适应：成功 +score，失败权重衰减 ≥0.2
终局：对 best 逐日 two_opt(30 轮) 收尾
```

- 纯几何件（`two_opt / best_insert / worst_edge`）已下沉 `opticore.heuristics`，本模块 re-export 兼容。

## 复杂度与预算

- 墙钟驱动（time_budget，秒），非显式迭代预算——**与 R2 的预算协议不同**，研究矩阵中按"机制剖面"记录自身 iters。
- 无显式合同枚举：`weekday_lock=False` 时移动可能产生合同/R2′ 违例 → 靠下游过滤，这是它在干净对照中 ≈ 基线的机制解释。

## 已知边界与陷阱

1. 产出不保证 R2′/合同合法——必须过 Contract-SP 终闸 + `check_contract`；v3 矩阵口径下"合法质量"以终闸结果为准。
2. 8-worker CP-SAT 等求解器不可进搜索期（确定性红线）。
3. 与 hgs_pvrp 共享 SA 骨架与算子件，属同族机制（对照实验中用于归因"为什么同族 ≈ 基线"）。

## 引用论文

- Ropke & Pisinger (2006)：ALNS 原始框架。
- Shaw (1998)：related removal（worst 算子思想）。
- Pisinger & Ropke (2010)：ALNS 统一框架与 PVRP 应用。
- Kirkpatrick et al. (1983)：SA 接受准则与分段降温。

## 相关文件与测试

- `algos/alns_v3.py`；`OptiCore/src/opticore/heuristics.py`（two_opt/best_insert/worst_edge 真身）
