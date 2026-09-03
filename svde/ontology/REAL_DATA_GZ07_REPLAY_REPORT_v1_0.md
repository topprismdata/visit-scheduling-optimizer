# Real Data Replay #2 — 广州办 SFA 进离店报表 (2026-07) 端到端回放报告
**Version:** v1.0
**Date:** 2026-08-31
**数据源:** `进离店报表导出 (4).xlsx` (9,760 行 × 25 列; 华南区/广州/海珠荔湾; 2026-07-01 ~ 2026-07-31)
**驱动:** `shadow/replay_guangzhou_07.py` (rep=梁健满, max_stops=30)

## 1. 新增组件

| 组件 | 路径 | 职责 |
|---|---|---|
| `SFACheckinIngestor` | `real_data/sfa_checkin_ingestor.py` | 进离店打卡流水 → 规范 `OperationalDecisionWorldState` (L0 实例化 + R1-R4 清洗) |
| `planning_input` (v2 投影) | `shadow/planning_input.py` | `materialize_planned_frequency` (PolicyRegistry → CustomerEntity DTO 编译) + `project_for_replay_v2` (lifecycle 派生组合) |
| 契约回归测试 | `shadow/test_mvp_schema_compatibility.py` `tests/test_sfa_checkin_ingestor.py` | 防真实 MVP schema 与 Shadow 消费键再漂移; R1-R4 逐条契约 |

红线遵守: 源 xlsx 只读; MVP 主流程 (`vertical_slice_mvp.py`)、`runner.py`、`data_precheck.py`、`guard.py` 零修改; projection 注入走 runner 既有 `projection` 参数。

## 2. R1-R4 清洗结果 (全宇宙 9,760 事件)

| 规则 | 命中 | 说明 |
|---|---|---|
| R1 时长截断 | 51 | 在店 ≥120min 或自动离店 → service_duration 封顶, 挂机痕迹留 summary |
| R2 连批降权 | 1,250 | 同坐标 + 间隔≤5min + 在店≤2min → credit=0, 不进有效频次 |
| R3 GPS 不可信 | 1,224 | 偏差>100m → 事件保留, 坐标不参与门店定位 |
| R4 坐标漂移 | 23/2,632 店 | 同店可信坐标跨度>1km → 聚类质心; 391 店无可信坐标 → UNMAPPED 门禁 |

**可信率 83.0%** (8,096/9,760)。分 rep 名义→有效: 邝豪杰 63% / 马嘉洲 76% / 苏泳江 100% / 赵成毅 99% — 个体差异巨大, 是行为画像信号而非噪声。

## 3. 链路验证 (precheck=PASS, invariants=True)

- Snapshot 哈希 ⇆ manifest 一致; frozen 指纹闸门通过; 4 项 MVP 不变量成立。
- MVP 计划: 20 routes / 120 stops / 30 unique (Top-30 可规划店, freq 观测均值 4)。
- 对比: actual=376 → match_rate 0.080, **FAIL 如实输出** — 子宇宙按 solver 容量 (6 stops/日×20 日=120) 截断, 346 店的覆盖缺口不粉饰。
- 结构性发现: 该辖区真实 workload ~39 拜访/日/人, MVP 硬编码 `max_daily_stops=6` 与之差 6.5×; 名义拜访量中 ~17% 为不可信打卡 → 「日 40 拜访」本身即数据伪影。计划-观测双缺口互相印证。

## 4. 仁军 18D 悬案闭环 (2026-08-25 会话遗留)

`replay_renjun_18d.py` "A 策略注入不生效 / MVP 恒无 plan" 三层根因, 全部修复:

1. **注入对象错位**: policy 写入 `policies.operational_policies`, 但 bridge/solver 只读 `CustomerEntity.planned_frequency` (canonical 契约要求 source=PolicyRegistry, 缺编译步骤) → 新增 `materialize_planned_frequency` (v2.0)。
2. **注入被丢弃**: 对内存 ws 注入后 `run_replay(path)` 重读 fixture → 改经 `projection` 参数注入。
3. **metrics/compare 键名漂移**: 二者只读 `daily_routes`, 而 MVP `_summarize_plan` 实际产出 `daily_routes_summary`/`daily_routes_count`; 旧测试 fixture 恰用手写旧键 → 假绿。已双键兼容 + 契约回归测试钉死。

修复后 renjun 重放: materialized=36, lifecycle=107, **79 stops / 14 routes / 36 店, match_rate=1.0, 3 条业务规则 PASS** (频次比 0.98)。

## 5. 测试

- 全量回归: `shadow + tests` = 265 passed, 2 skipped (BIZ 冻结预期), 0 failed。
- 新增 10 项: ingestor 契约 8 (R1-R4/哈希/政策派生/缺列报错) + schema 兼容 2。
