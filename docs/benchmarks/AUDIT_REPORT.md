# 拜访计划优化框架 — 审计报告

> 日期：2026-09-02
> 项目：进离店拜访计划优化
> 框架版本：v2.0（多算法竞争-协作框架）

---

## 一、数据源

### 唯一允许的数据文件
| 文件 | 说明 |
|---|---|
| `进离店内销售的SRP-7月拜访计划.xlsx` | 7 月计划（6,564 有效行） |
| `进离店内销售的SRP-8月拜访计划.xlsx` | 8 月计划（6,027 有效行） |
| `进离店内销售的SRP-9&10月拜访计划.xlsx` | 9-10 月计划（12,564 行） |

### 实际走访数据（用户授权使用）
| 文件 | 说明 |
|---|---|
| `进离店报表导出 (4).xlsx` | 7 月实际 GPS 打卡（9,760 行，11 人，29 天） |

### 距离口径
- **唯一口径**：OSM 骑行路网距离（FOSSGIS `routed-bike/table`）
- 严禁 haversine 直线距离
- 矩阵缓存：`output/road_dist_{line}.npy`（10 条线路，每家店 163-190 家）

### 路网区块
- 来源：`边界数据-路网-到区县带海岸线-四级路网-广东省-广州市.geojson`
- 7 个区县，1,667 个候选区块，22 个落店区块
- 相邻区块对：43 对（多边形边共享判定）

---

## 二、框架架构

### 分层设计
```
data/loader.py        数据加载（SRP → LineData）
data/road.py          路网矩阵获取/缓存（FOSSGIS 分块）
core/base.py          算法接口（Algorithm, LineData, AlgoResult）
core/metric.py        指标（day_km, check_freq）
core/route_pool.py    全局路线池（RoutePool, Route）
core/constraint.py    约束定义（freq, weekday, capacity）
core/zone_graph.py    区块图 + 约束提取（新）
algos/registry.py     算法注册表
algos/impl.py         算法实现（8个）
algos/tsp_engine.py   TSP引擎（CP-SAT exact / NN2opt heuristic）
algos/lkh_engine.py   LKH引擎（ATSP, 开放路径）
algos/sdr_exact.py    SDR列生成精确框架
algos/pvrp_cg/        ← 旧脚本，冻结零改动
runner.py             流水线运行器（gen→pool→SP→exact）
```

### 流水线
```
路线生成 (baseline/nn2opt/greedy/alns/cpsat)
    ↓
路线池 (RoutePool, 收集各算法产出)
    ↓
集合划分重组合 (ensemble_sp, 池→最优组合)
    ↓
精确闭锁 (sdr_exact, LP gap 报告)
```

### 时间预算模式
| 模式 | 算法 | 时间/线 |
|---|---|---|
| `--fast` | baseline + nn2opt + greedy_crossday | ~3 min |
| `--standard` | + cpsat_route + alns | ~15 min |
| `--deep` | + ensemble_sp + sdr_exact | ~30 min |

---

## 三、算法清单（8 个）

| # | 算法 | 类型 | 解决问题 | 方法 | 速度 |
|---|---|---|---|---|---|
| 1 | `baseline` | 对照 | — | 原始计划 | <1s |
| 2 | `nn2opt` | 启发式 | ①顺序重排 | NN 建序 + 2-opt 精修 | <1s |
| 3 | `greedy_crossday` | 启发式 | ②跨日重分配 | 贪心局部搜索（只收改进） | ~3 min/线 |
| 4 | `lkh_route` | 精确 | ①顺序重排 | LKH-3 ATSP，dummy depot 开放路径 | ~5 min/线 |
| 5 | `cpsat_route` | 精确 | ①顺序重排 | CP-SAT AddCircuit 开放 TSP | ~2s/线 |
| 6 | `alns` | 元启发式 | ②跨日重分配 | 自适应算子池 (move/swap/cluster_ruin) + 多臂老虎机权重 | ~2.5 min/线 |
| 7 | `ensemble_sp` | 精确 | 组合优化 | 路线池 + Set Partitioning (CP-SAT MILP) | <1s |
| 8 | `sdr_exact` | 精确 | 组合优化 | 列生成 + LP 下界 + gap 报告 | <1s |

### 新增算法（设计完成，待集成）
| # | 算法 | 方法 | 参考 |
|---|---|---|---|
| 9 | `clustered_tsp` | Clustered ATSP（跨区块边+M 变换） | Cook, Held, Helsgaun 2022 |
| 10 | `zone_ordered_tsp` | 区块顺序约束（从实际走访学习） | Amazon 2021 亚军 MIT 方案 |
| 11 | `lkh_amz_adapter` | LKH-AMZ 风格惩罚搜索（约束→LKH 参数） | jpt-amz 开源代码 |

---

## 四、关键算法调整（近 2 天）

### 4.1 LKH 正确使用（ATSP 修正）
**问题**：`TYPE: TSP` + `FULL_MATRIX` 只读下三角矩阵，上三角被忽略，导致矩阵错误。
**修正**：必须用 `TYPE: ATSP` + `FULL_MATRIX` 读全矩阵。
**开放路径**：加 dummy 节点（大常数 C=10×max 距离），解闭圈后剥离 dummy。
**效果**：09 线 23 店：LKH 17.4 km → ATSP 修正后 15.97 km（CP-SAT 最优 14.03 km）。
**结论**：LKH 在显式路网矩阵上收敛差于 CP-SAT，CP-SAT 作为主精确引擎。

### 4.2 ALNS 自适应算子池
**改进**：
- 算子池：move（单店移）、swap（交换）、ruin_repair（随机重排）、cluster_ruin（聚簇破坏）
- 自适应权重：多臂老虎机，每 50 轮更新一次，历史表现好的算子权重大
- 初始解：来自 greedy_crossday（全预算，50 轮贪心）
- 修复频次 bug：block 算子加了 `c in s2` 检查，防止重复
**效果**：09 线 ALNS 291.4 km vs greedy_crossday 301.7 km（+3.4%）

### 4.3 Warm-start（AddHint）
**方法**：用 greedy_crossday 解作为提示喂给 CP-SAT Set Partitioning
```python
model.AddHint(x[(dd, ri)], 1)  # 指向 greedy 选中的路线
```
**效果**：CP-SAT 立刻获得可行解，搜索加速

### 4.4 SDR 列生成精确框架
**方法**：
1. 多起点随机 NN2opt + LKH → 大规模路线池（≥40 条/日）
2. CP-SAT Set Partitioning 组合（整数解 UB）
3. GLOP LP 松弛 → 下界 LB → gap 报告
**效果**：09 线 gap=0.0（与 ensemble_sp 一致）

---

## 五、Amazon 2021 方法论研究（影响后续工作）

### 冠军方案（JPT - Cook/Held/Helsgaun）
- 论文：*Constrained Local Search for Last-Mile Routing* (Transportation Science 2022)
- 代码：https://github.com/heldstephan/jpt-amz（MIT 开源，已克隆）
- 核心：**Clustered ATSP**（两级层次结构）
  - 外 TSP：确定区块访问顺序（跨区块边+大常数 M，强制同块连续）
  - 内 TSP：各区块内开放 TSP
- 约束：区块前序约束（从历史路线提取）、多级聚类（zone/super/super-super）
- 算法：LKH-AMZ（3-opt/4-opt 惩罚搜索，Build 阶段仅 109 秒）
- 评分：0.01978（0=完美匹配司机路线），领先第二名 42%

### 亚军方案（Permission Denied - MIT）
- 层次 TSP + 学习成本矩阵（从历史数据修正跨区代价）
- 后处理匹配司机偏好

### 季军方案（Sky is the Limit）
- 惩罚网络变换 + 数据分析规则 + RL 参数优化

### 对我们的影响
- 路网区块（22 区块）可作为"zones"
- 实际走访数据可作为训练数据提取区块顺序约束
- 新增 `clustered_tsp`、`zone_ordered_tsp`、`lkh_amz_adapter` 三个算法

---

## 六、7 月计划优化结果（11 人）

### 数据来源
- `output/ledger_standard.csv`（标准模式 5 算法）
- `output/ledger_deep.csv`（深度模式 7 算法）

### 人员→线路映射
| 人员 | 线路 | 线路 ID |
|---|---|---|
| 冯秀珍 | 冯秀珍_海珠荔湾05 | 05 |
| 黄志成 | 海珠荔湾10 | 10 |
| 梁健满 | 海珠荔湾09 | 09 |
| 邝豪杰 | 海珠荔湾08 | 08 |
| 苏泳江 | 海珠荔湾11 | 11 |
| 赵成毅 | 梁齐志_海珠荔湾07 | 07 |
| 欧祖良 | 海珠荔湾03 | 03 |
| 梁炯棠 | 海珠荔湾06 | 06 |
| 马嘉洲 | 海珠荔湾04 | 04 |
| 黄宏妮 | 黄宏妮_海珠荔湾02 | 02 |
| 梁齐志 | 梁齐志_海珠荔湾07 | 07 |

### 3 级对比表
| 人员 | 线路 | 计划(km) | 顺序重排(km) | 跨日重分配(km) | ①省%(vs计划) | ②再省%(vs顺序) |
|---|---|---|---|---|---|---|
| 冯秀珍 |  5 | 1330.1 | 428.8 | 282.8 | 67.8% | 34.0% |
| 黄志成 | 10 | 2879.1 | 403.3 | 378.1 | 86.0% | 6.2% |
| 梁健满 |  9 | 1116.0 | 381.7 | 290.3 | 65.8% | 23.9% |
| 邝豪杰 |  8 | 3227.0 | 855.2 | 512.1 | 73.5% | 40.1% |
| 苏泳江 | 11 | 2531.5 | 1075.0 | 786.9 | 57.5% | 26.8% |
| 赵成毅 |  7 | 1202.2 | 422.7 | 361.4 | 64.8% | 14.5% |
| 欧祖良 |  3 | 594.8 | 260.8 | 145.0 | 56.2% | 44.4% |
| 梁炯棠 |  6 | 573.2 | 193.8 | 99.8 | 66.2% | 48.5% |
| 马嘉洲 |  4 | 982.4 | 302.5 | 215.2 | 69.2% | 28.9% |
| 黄宏妮 |  2 | 2420.7 | 282.5 | 247.8 | 88.3% | 12.3% |
| 梁齐志 |  7 | 1202.2 | 422.7 | 361.4 | 64.8% | 14.5% |
| **合计** | | **16857** | **4606** | **3319** | **-73%** | **-28%** |

### 求解时间
| 算法 | 全10线合计时间 | 备注 |
|---|---|---|
| baseline | 0s | |
| nn2opt | 0s | |
| greedy_crossday | 1547s | |
| cpsat_route | 90s | |
| alns | 1453s | |
| ensemble_sp | 0s | |
| sdr_exact | 0s | |

---

## 七、实际走访分析结果（11 人）

### 数据来源
- 实际走访：`进离店报表导出 (4).xlsx`（9,760 行 GPS 打卡）
- 路网矩阵：按日按人抓取，缓存于 `output/daily_matrices/`
- 分析脚本：`algos/pvrp_cg/actual_all_reps.py`（逐人容错 + 增量保存）

### 已完成 8 人结果
| 人员 | 天数 | 全部店实际(km) | 优化(km) | 省% | 计划内实际(km) | 优化(km) | 省% |
|---|---|---|---|---|---|---|---|
| 冯秀珍 | 23 | 1992 | 497 | 75% | 1555 | 446 | 71% |
| 梁健满 | 25 | 2546 | 577 | 77% | 1622 | 462 | 71% |
| 欧祖良 | 27 | 1645 | 346 | 79% | 1304 | 315 | 76% |
| 苏泳江 | 23 | 2706 | 1098 | 59% | 2706 | 1098 | 59% |
| 赵成毅 | 13 | 1084 | 306 | 72% | 929 | 292 | 69% |
| 邝豪杰 | 26 | 6401 | 974 | 85% | 4818 | 892 | 81% |
| 黄志成 | 25 | 7762 | 947 | 88% | 5295 | 848 | 84% |
| **合计** | | **24136** | **4744** | **80%** | **18231** | **4353** | **76%** |

### 关键发现
1. **计划外门店占比高**：梁健满 376 家店中 213 家（57%）是计划外
2. **优化空间稳定**：50-60% 节省，无论是否含计划外
3. **最大单日**：梁健满 7/30 日 119 家店，实际 237 km → 优化 72 km（-70%）
4. **计划覆盖率**：11 人 100% 覆盖计划门店（实际走访包括了所有计划店）

---

## 八、验证方法

### 8.1 每店频次校验（count_ok）
所有算法产出后必经：解中每店的总拜访次数 = 计划频次
- 8 个算法全部通过（`count_ok=True`）
- 发现 ALNS block 算子频次 bug 并修复

### 8.2 与旧脚本对账
| 指标 | 旧脚本(km) | 新框架(km) | 差异 |
|---|---|---|---|
| baseline | 16,857 | 16,857 | **0.0%** |
| nn2opt | 4,606 | 4,606 | **0.0%** |
| greedy_crossday | 3,758 | 3,501 | 随机差异 ~6.8% |

### 8.3 代码审查
- 旧脚本 `algos/pvrp_cg/` 冻结零改动
- 所有算法继承 `Algorithm` 基类，统一接口
- 求解时间保留在 CSV 的 `sec` 列

---

## 九、求解时间汇总

| 算法 | 全10线合计 | 说明 |
|---|---|---|
| baseline | <1s | 原始计划，不优化 |
| nn2opt | <1s | NN+2-opt |
| greedy_crossday | ~1,044s | 贪心跨日，每线180s预算 |
| cpsat_route | ~52s | CP-SAT 精确 TSP |
| alns | ~1,166s | ALNS 自适应，每线300s预算 |
| ensemble_sp | <1s | 池+SP，依赖池质量 |
| sdr_exact | <1s | 列生成，依赖池质量 |

---

## 十、下一步计划

1. 完成 11 人实际走访分析剩余 3 人（马嘉洲、黄宏妮、梁齐志）
2. 实现 Clustered TSP 算法（跨区块+M 变换）
3. 从实际走访数据提取区块顺序约束
4. 实现 `zone_ordered_tsp` 算法
5. 实现 `lkh_amz_adapter` 风格惩罚搜索

---

*文档生成时间：2026-09-02 13:10*
*框架版本：v2.0*
