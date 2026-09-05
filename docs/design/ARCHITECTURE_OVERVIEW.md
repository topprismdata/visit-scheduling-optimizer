# 多算法竞争-协作框架设计

## 目标
同一线路数据 + 同一路网矩阵，跑任意多个算法，输出统一对比表（含求解时间）。
算法即插即用，适应不同 VRP 场景。

## 调研依据
- **Amazon 2021 冠军** (Cook/Held/Helsgaun): 层次聚类 + 带顺序约束的 TSP 变体 + 组合优化
- **菜鸟/美团**: ALNS 自适应算子池 + 多算法并存
- **论文① van Montfort 2026**: fragment 基表述, 时间依赖约束
- **论文② Paradiso 2020**: ESF 列生成下界 + 结构枚举 + 分支切割
- **论文③ Villegas 2025**: 路线池 + 集合划分重组合 (+0.5% 平均, 构造+SP 达 4.26%)

## 设计决策
1. **TSP 引擎层**: CP-SAT 精确 (≤35 店 0.7s 证最优) / NN2opt 启发式 / LKH (ATSP)
2. **流水线**: 路线生成 → 池 → SP 重组合 → 精确闭锁
3. **Warm-start**: 启发式解 → CP-SAT AddHint, 加速搜索
4. **时间预算**: fast/standard/deep/all 模式, 每算法独立预算

## LKH 正确用法 (踩坑记录)
- `TYPE: TSP` + `FULL_MATRIX` 只读下三角 → 矩阵错误
- 必须用 `TYPE: ATSP` + `FULL_MATRIX` 读全矩阵
- 开放路径: 加 dummy 节点 (大常数 C=10*max), 闭圈剥离
- LKH 在显式路网矩阵上收敛差于 CP-SAT, 作为备选引擎

## 关键指标
- count_ok: 每店总次数校验 (所有算法必经)
- day_km: 开放链路网里程 (无仓库往返)
- sec: 求解时间保留
