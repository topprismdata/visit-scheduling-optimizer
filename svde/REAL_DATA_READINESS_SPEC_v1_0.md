# SVDE Core Framework — 真实数据就绪与受控验证规范
**Document ID:** SVDE-REAL-DATA-READINESS-V1.0  
**Date:** 2026-08-24  
**Classification:** Real Data Ingestion & Pre-flight Gate Specification  
**Status:** **26 Core Tests + 121 Bench Tests = 147 Tests PASS / 进入受控真实数据验证阶段**

---

## 1. 测试数量精确核对（Test Count Correction）

- **SVDE Core 独立测试集**：`svde/tests/` 共 **26 个测试**（新增 3 个真实数据预检与边矩阵严格性测试）
- **SVDE-Bench 基准测试集**：`svde-bench/` 共 **121 个测试**
- **全库总测试数**：**147 个测试（100% 真实执行通过）**

---

## 2. 真实数据导入两项关键缺陷闭环（Pre-flight Code Hardening）

| # | 发现的缺陷 | 修复措施与代码实现 | 验证测试 |
| :--- | :--- | :--- | :--- |
| **1** | **缺失边矩阵时自动使用 10.0 名义通行时间**（隐式默认值导致真实数据虚假可行） | `svde/verification/__init__.py:121-135` 彻底移除了 `transit_cost = 10.0` 兜底。若路由结构存在但 `edge_matrix` 为空，审计器直接记录物理违约并判定 `solution_feasible = False`（Fail-Closed，禁止隐式默认时间）。 | `test_missing_edge_matrix_fails_closed_in_auditor` |
| **2** | **`DEFAULT` 边格式缺少数值校验**（非法嵌套触发裸 `TypeError`） | 在 `DecisionAuditor` 中严格校验 `edge_matrix["DEFAULT"]` 必须为非布尔数值类型（`int`/`float`），否则显式记录物理违约；同时增加对各边权重的数值校验。 | `test_invalid_non_numeric_default_in_edge_matrix_caught_by_auditor` |

---

## 3. 真实数据预检校验器 (`DataPrecheckValidator`)

针对进入真实数据测试阶段的要求，在 `svde/verification/data_precheck.py` 中实现了独立的预检工具，提供数据导入前的 6 项硬性检查：

1. **实体 ID 唯一性与非空性**：严格拒绝重复的车辆/代表/订单/客户 ID。
2. **容量与需求数值合法性**：校验 `capacity`、`demand` 为非负数值类型（拒绝字符串与负数）。
3. **时间窗逻辑合法性**：断言 `tw_early <= tw_late`。
4. **边矩阵完整性**：路由算例必须提供明确的 `edge_matrix`，拒绝缺失边数据。
5. **起终点场站存在性**：时序路径算例必须包含有效 `depot_ids`。
6. **禁止隐式默认通行时间**：若使用 `DEFAULT` 兜底必须显式声明且为数值。

---

## 4. 运行模式与使用范围边界（Usage Boundary Protocol）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SVDE 真实数据运行模式准入表                           │
├────────────────────────┬──────────┬─────────────────────────────────────────┤
│ 运行模式               │ 准入状态 │ 准入前置条件                            │
├────────────────────────┼──────────┼─────────────────────────────────────────┤
│ 真实历史数据离线回放   │ ✅ 准入   │ 必须通过 DataPrecheckValidator 预检     │
│ 影子模式（与现有排班对比）│ ✅ 准入   │ 必须具备完整真实边矩阵，不依赖默认时间  │
│ 自动写回生产排班/决策  │ ⛔ 暂缓   │ 需完成影子模式差异分析与人工审批闭环    │
│ 未提供边矩阵的路由数据 │ ⛔ 暂缓   │ 必须补齐实际路网通行矩阵后方可准入      │
└────────────────────────┴──────────┴─────────────────────────────────────────┘
```

---

## 5. 当前准确结论

系统正式定位于：**“147/147 全量通过，具备完整的预检拦截能力，可进入受控真实数据验证阶段；尚未达到无需数据预检即可生产自动决策的程度。”**
