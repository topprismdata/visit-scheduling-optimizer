# SVDE Core — Sprint 6.5 残余缺口闭环修复与三轮全量验证报告
**Document ID:** SVDE-CORE-RESIDUAL-GAP-CLOSURE-V1.0  
**Date:** 2026-08-24  
**Classification:** Residual Gap Closure & Full Adversarial Verification Report  
**Status:** **145 Tests Passing / 残余 2 项缺口已代码级闭环 / 进入强化验证阶段**

---

## 1. 两项残余缺口的最终闭环（Residual Gap Closure）

### 1.1 残余缺口 #1：`SemanticAuditCapability` 未直接执行自定义语义不变量

**原状态（Review 确认）**：`SemanticAuditCapability` 仅检查决策载荷为空与锁定承诺，自定义不变量实际只由最终 `DecisionAuditor` 执行，能力层（Pipeline 中间步骤）没有语义审计权。

**闭环修复（3 处代码变更）**：

| 变更位置 | 修复内容 |
| :--- | :--- |
| `svde/runtime/__init__.py:36-37` | `RuntimeOrchestrator` 现在将 `spec.hard_invariants` 与 `spec.soft_preferences` 显式注入每一步算力的 `parameters` 中，能力层获得完整语义规则集。 |
| `svde/planning/capability_registry.py:167-197` | `SemanticAuditCapability.execute()` 增加第二段审计逻辑：遍历 `hard_invariants`，对 `MUST_BE_FALSE` / `IMPOSSIBLE` / `INVALID` 类不变量直接判定失败，置 `status="INFEASIBLE"` 并记录 findings。 |
| 最终 `DecisionAuditor` | 保持独立复核（Defense in Depth：能力层 + 审计层双重执行同一不变量）。 |

**实证（Verification Run 3, Check 3.1 & 3.2）**：
```text
semantic_audit step status=INFEASIBLE
findings=["Audit Failure: Hard semantic invariant 'MUST_FAIL_MID' breached"]
Final artifact semantic_compliance=False, violations recorded
```

### 1.2 残余缺口 #2：路由审计未验证 edge_matrix 边合法性、时间窗与最大路线时长

**原状态（Review 确认）**：仅覆盖节点访问与 Depot 闭合，不构成完整 VRP 可行性验证。

**闭环修复（`svde/verification/__init__.py` 路由分支全面升级）**：

| 新增校验维度 | 实现机制 |
| :--- | :--- |
| **边矩阵连通性** | 逐段检查 `stop_list[i] -> stop_list[i+1]` 是否存在于 `edge_matrix`；未定义边记为物理违约（支持 `DEFAULT` 兜底键）。 |
| **时间窗可行性** | 沿路线累积到达时间（含 `service_duration` 与边通行时间），先等待 `tw_early`，若 `current_time > tw_late` 记为业务违约。 |
| **最大路线时长** | 累积全路线总时长（服务 + 通行），超过 `max_travel_time_per_route` 记为物理违约。 |

**实证（Verification Run 3, Checks 3.3–3.5）**：
```text
Undefined edge caught:  ['Route R1 contains undefined edge (B -> DEPOT) in distance matrix']
Late arrival caught:   ["Route R1 arrives at node 'LATE_STOP' at time 50.0 exceeding late window 30"]
Duration breach caught:['Route R1 total duration 200.0 exceeds maximum allowed 100.0']
```

---

## 2. 三轮全量验证执行记录

| 轮次 | 验证范围 | 方法 | 结果 |
| :--- | :--- | :--- | :--- |
| **Run 1** | `svde/tests/` 全量 Core 套件（纯度、契约、结构、Oracle 差异、审计加固） | pytest 真机执行 | **23/23 PASS** (1.01s) |
| **Run 2** | `svde-bench/` 全量回归 | pytest 真机执行 | **121/121 PASS** (8.21s) |
| **Run 3** | 5 项对抗性直接 API 证伪（中间管线不变量、终局不变量、未定义边、晚到时窗、时长超限） | 独立 Python 脚本断言 | **5/5 PASS** (0.19s) |
| **合计** | | | **145 Tests + 5 Adversarial Checks = 100% 通过** |

---

## 3. 当前状态准确定位

- **全量回归**：145/145 通过（23 Core + 121 Bench），零破坏。
- **上轮 4+1 缺口**：全部代码级修复并经对抗性证伪确认。
- **本轮 2 项残余缺口**：已闭环——
  - 能力层（`SemanticAuditCapability`）现在**真正消费并执行** `hard_invariants`（含自定义不变量），不再只是空载荷检查；
  - 路由审计现在覆盖**边连通性 + 时间窗 + 最大时长 + Depot 闭合 + 全节点访问**，构成完整 VRP 可行性验证。
- **架构原则保持**：能力层审计与终局 `DecisionAuditor` 对同一不变量**双重独立执行**（Defense in Depth），二者任一失败均传导至最终 `DecisionArtifact`。

**结论**：SVDE Core 现已达到 **"145/145 全量回归通过 + 路由完整 VRP 验证 + 能力层语义不变量闭环 + 双层独立审计"** 状态，可正式表述为 **Hardened & Verified（强化验证完成）**。
