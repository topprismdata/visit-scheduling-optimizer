# 进离店拜访计划优化框架 · 项目规则（AGENTS.md）

> 本文件替代原 `CLAUDE.md`（2026-09-04 迁移），是所有编码代理/维护者的项目宪法。
> 迁移时已将规则**更新为经代码与实测核验的真实现状**（性能核查见 `docs/PERFORMANCE_BENCHMARK.md`）。

## 数据源

- **Layer 1 规划唯一数据源**: `/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx`
- **Layer 2 实测数据源**（用户 2026-09-03 授权）: `/Users/ghb/Downloads/进离店报表导出 (4).xlsx` —— 实际打卡流水，仅用于"实际 vs Agent"对比，不反哺规划口径
- **距离口径**: OSM 骑行路网距离（FOSSGIS routed-bike/table）。
  ⚠ **已知违例**：`run_all_reps_actual_vs_agent.py` 在 FOSSGIS 429 限流时回退 `1.41×Haversine 校准矩阵` 并持久化缓存，实测约半数日级矩阵受污染（124/250，检测法：值是否恒为 3 位小数规则网格）。**对外交付前必须重刷回退缓存**：删除对应 `.npy` 重跑即可（脚本缓存命中优先）。**当前唯一已重核干净的线路：09（1,234.7→592.2 km 已入台账）；02~08/10/11 仍含部分回退，重刷待 FOSSGIS 配额恢复后执行**。详见 `docs/PERFORMANCE_BENCHMARK.md` §9
- 路网矩阵缓存：Layer 2 日级 `data/cache/dist_{line}_{date}_{n}.npy`；Layer 1 月度 `output/road_dist_{line}.npy`

## 业务概念

- 频次单位 = **周**；每店月总次数 = 计划表中出现行数（无"月频次"概念）
- 每家店锁定星期几（原始计划 100% 跨周不变）
- 不考虑服务时长
- 汇报时间口径：周六日一律剔除，只计 23 个法定工作日

## 框架架构（三层）

```
Layer 1   月度日程优化    algos/impl.py (注册算法) + algos/alns_v3.py
Layer 1.5 帕累托精修      algos/mo_alns_v4.py (MO-ALNS: NSGA-II+ALNS, 3 目标: 里程/相对base改动量/CV；原第 4 目标"跨区率"随 Clustered TSP 否决废弃)
Layer 2   单日动态调度    algos/agentic/ (SalesVisitDispatchAgent + CorridorDynamicInsertionTool)

data/loader.py         数据加载 (SRP → LineData)
data/road.py           路网矩阵获取/缓存 (Layer 1)
core/base.py           算法接口 (Algorithm, LineData, AlgoResult)
core/metric.py         指标 (day_km, total_km, check_freq)
core/route_pool.py     全局路线池 (RoutePool, Route)
core/constraint.py     约束定义 (freq, weekday, capacity)
algos/registry.py      算法注册表
algos/tsp_engine.py    TSP 引擎 (CP-SAT exact / NN2opt heuristic)
algos/lkh_engine.py    LKH 引擎 (ATSP, 开放路径)
algos/sdr_exact.py     SDR 列生成精确框架 (runner 导入时注册)
runner.py              流水线运行器 (gen→pool→SP→exact)
algos/pvrp_cg/         ← 旧脚本, 冻结零改动
```

### 已注册算法（registry 实测 9 个 + sdr_exact 随 runner 导入注册）

| 算法 | 说明 | 时间行为（2026-09-04 实测） |
|---|---|---|
| baseline | 原始计划对照 | 0.01 s |
| nn2opt | ① NN+2-opt 启发式顺序重排 | **0.01 s/线**（确定性） |
| greedy_crossday | ② 贪心跨日重分配 | 自然收敛 avg ~99 s |
| lkh_route | ① LKH 开放 TSP (ATSP) | 本次核查未纳入（非主力） |
| cpsat_route | ① CP-SAT 精确开放 TSP | **3.0 s/线**（0.13 s/天） |
| alns (v1) | ② ALNS 评估耦合 | 自然收敛 avg 145 s / max 221 s |
| ensemble_sp | 路线池 + 集合划分重组合 | **0.1 s**（池命中） |
| sdr_exact | 列生成 + LP 下界 gap 证书 | **0.9 s**（gap=0） |
| alns_v3 | ② 反馈耦合 ALNS（tour-carrying + regret-2 + SA）**主力** | **恒=预算**（生产 300 s / 快档 60 s） |
| mo_alns_v4 | MO-ALNS 三目标帕累托（base=上次规划结果） | **恒=预算**（无早停） |

> "恒=预算" = 墙钟精确撞满设定预算、不提前结束（SLA 可承诺、里程随预算单调改善）。详见 `docs/PERFORMANCE_BENCHMARK.md`。

### 运行模式与实测口径

- `--mode fast`: baseline + nn2opt + greedy_crossday（实测自然收敛 ≈ 1.7 min/线）
- `--mode standard`: + cpsat_route + alns（≈ 4 min/线）
- `--mode deep`: + ensemble_sp + sdr_exact（**实测 avg 4.1 / max 6.5 min/线**；旧口径"30 min"是预算总和，禁止对外使用）
- ⚠ **接线现状**（性能核查结论，勿当作已自动化）：runner MODES **不含** alns_v3 / mo_alns_v4；V3/V4 目前经研究脚本运行（`run_v3_all.py`、`run_mo_v4.py`、`run_all_reps_actual_vs_agent.py`）。V4 的 base=上次 V3 结果这条链是**手工拼接**，接入 runner 为待办。
- `rolling_horizon.py` / `lock_replan.py` 仅完成锁定与任务拆分**框架**，未接任何求解器（零调用方），对外禁止宣称"滚动重规划已实现"。

## 流水线

1. 路线生成（baseline, nn2opt, greedy, cpsat, alns）→ 路线池
2. 集合划分重组合（ensemble_sp，warm-start）
3. 精确闭锁（sdr_exact，gap 报告）
4. 每线/每算法结果 → 总账 CSV（含求解时间）
5. Layer 2：实际打卡 → SalesVisitDispatchAgent 走廊插单 → 台账 `output/all_reps_actual_vs_agent.csv`

## 可对外承诺的时间数字（唯一合法口径）

当天插单 ≤5 ms · 顺序重排 ≤1 s/线 · CP-SAT ≤5 s/线 · SP/SDR ≤5 s · 月度规划 ≤6 min/线 · 深度审计 ≈5 min/线（最慢 7）。
微调类（V3/V4）只能表述为"按设定预算交付"。PPT 引用其他数字前，先看 `docs/PERFORMANCE_BENCHMARK.md` §6 逐条判定。

## 铁律

1. `algos/pvrp_cg/` 旧脚本**冻结零改动**（含禁止向其内新增文件）
2. 新框架结果与旧脚本对账（baseline/nn2opt 零差异）
3. 每店总次数校验 `count_ok` 所有算法必经
4. 所有汇报时间数字必须来自实测并落在 `PERFORMANCE_BENCHMARK.md` / bench CSV 体系内，禁止引用旧版数字
5. 性能数据文件（`output/bench_*.csv` 等）带日期新增，**不覆盖历史文件**
