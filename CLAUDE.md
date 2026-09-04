# 进离店拜访计划优化框架

## 数据源
- **唯一允许的数据文件**: `/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx`
- 距离口径: **OSM 骑行路网距离** (FOSSGIS routed-bike/table), 严禁 haversine 直线距离
- 路网矩阵缓存 (Layer2 动态): `data/cache/dist_{line}_{date}_{n}.npy`

## 业务概念
- 频次单位 = 周, 每店月总次数 = 计划表中出现行数
- 每家店锁定星期几 (100% 跨周不变)
- 不考虑服务时长
- 09 线路仅一人 (梁健满)

## 框架架构（三层）

```
Layer 1  月度日程优化   algos/impl.py (8 注册算法) + algos/alns_v3.py + algos/mo_alns_v4.py
Layer 1.5 稳定化精修    algos/mo_alns_v4.py (MO-ALNS, NSGA-II+ALNS, 4 目标帕累托)
Layer 2  单日动态调度   algos/agentic/ (SalesVisitDispatchAgent + CorridorDynamicInsertionTool)

data/loader.py         数据加载 (SRP → LineData)
data/road.py           路网矩阵获取/缓存 (Layer1)
core/base.py           算法接口 (Algorithm, LineData, AlgoResult)
core/metric.py         指标 (day_km, total_km, check_freq)
core/route_pool.py     全局路线池 (RoutePool, Route)
core/constraint.py     约束定义 (freq, weekday, capacity)
algos/registry.py      算法注册表
algos/tsp_engine.py    TSP引擎 (CP-SAT exact / NN2opt heuristic)
algos/lkh_engine.py    LKH引擎 (ATSP, 开放路径)
algos/sdr_exact.py     SDR列生成精确框架
runner.py              流水线运行器 (gen→pool→SP→exact)
algos/pvrp_cg/         ← 旧脚本, 冻结零改动
```

### 已注册算法 (9个)
| 算法 | 说明 | 时间预算 |
|---|---|---|
| baseline | 原始计划对照 | 10s |
| nn2opt | ① NN+2-opt 启发式顺序重排 | 10s |
| greedy_crossday | ② 贪心跨日重分配 | 180s |
| lkh_route | ① LKH 精确开放 TSP (ATSP) | 300s |
| cpsat_route | ① CP-SAT 精确开放 TSP | 300s |
| alns | ② ALNS 自适应算子池 + 聚簇破坏 | 300s |
| ensemble_sp | 路线池 + 集合划分重组合 (warm-start) | 300s |
| sdr_exact | 列生成精确框架 (LP下界 + gap报告) | 600s |
| alns_v3 | 反馈耦合 ALNS (tour-carrying + regret-2 + SA) | 300s |
| mo_alns_v4 | MO-ALNS 多目标帕累托 (NSGA-II, 4 目标) | 60s |

### 运行模式
- `--mode fast`: baseline + nn2opt + greedy_crossday (~3 min/线)
- `--mode standard`: + cpsat_route + alns (~15 min/线)
- `--mode deep`: + ensemble_sp + sdr_exact (~30 min/线)
- 求解时间在 CSV 中 `sec` 列保留

## 流水线
1. 路线生成 (baseline, nn2opt, greedy, cpsat, alns) → 路线池
2. 集合划分重组合 (ensemble_sp with warm-start)
3. 精确闭锁 (sdr_exact, gap报告)
4. 每线/每算法结果 → 总账 CSV (含求解时间)

## 铁律
- `algos/pvrp_cg/` 旧脚本冻结零改动
- 新框架跑出结果与旧脚本对账 (baseline/nn2opt 零差异)
- 每店总次数校验 (count_ok) 所有算法必经
