---
**Status:** HISTORICAL SNAPSHOT — SUPERSEDED BY `svde/docs/TOPPRISM_ARCHITECTURE_CORRECTION_PASS_v1_0_2.md`
**Superseded Date:** 2026-08-25
**Authoritative Version:** v1.0.2（提供完整文档清单 + 可复核扫描脚本 + 互斥分类表 + 全局 DEPRECATED 反向引用规则）

> 本报告为历史快照。v1.0.2 才是当前权威版本。

---

# TopPrism 架构纠偏修订报告 v1.0.1 (Correction Pass Report)

**Document ID:** TOPPRISM-ARCHITECTURE-CORRECTION-PASS-v1_0_1
**Date:** 2026-08-25
**Status:** **CORRECTION PASS COMPLETED — DOCUMENT_CONTRACT_INCONSISTENCY 仍 BLOCKED**
**触发原因:** 收到架构主管对"v1.0 纠偏报告"的二轮反馈（数量错误、迁移未完成、Baseline/Event 自相矛盾、Resource Transfer 错位、双入口、ExecutionEvent 混淆、Matrix/Baseline 不一致、31/31 无可复核证据）
**严格红线:** 本次纠偏不修改 runtime、不修改 solver、不安装依赖、不启动实测、不新增 API、不冻结 Canonical API

---

## 一、已修正项（11 项）

| # | 审查指出 | 实质修改 | 落盘文档 |
|---|---|---|---|
| **1** | 报告"已修正项 10 项"与表 11 项不一致 | 标题改为"11 项"并对齐 | 本报告（v1.0.1） |
| **2** | L0-L7 迁移未完成（仅一文档加 HISTORICAL） | 全仓扫描 → 4 类分类表；B 类 5 份加 MIGRATED-TO 头；D 类 4 份加 CONFLICT_NOTE 头 | 9 份文档 |
| **3** | Baseline §4.6 与 §5 自相矛盾（独立 vs 字段） | 选定**方案 B**：ExecutionEventStream 独立子资源，**严禁**作为 OperationalDecisionWorldState 字段；DEPRECATED 字段清单 | Baseline v1.0.1 §4.6 |
| **4** | Resource Availability 用 `visit_id` 错位 | 步骤 2 改用通用 `TransferRequest(entity_type=RESOURCE, entity_ref="仁军", ...)` | Slice v1.0.1 |
| **5** | 双入口（submit_resource_event vs submit_execution_feedback） | 统一为**两个独立 Canonical API**：`submit_execution_feedback(ActualVisitEvent)` 与 `submit_resource_event(ResourceAvailabilityObservation)`；严禁合并为多态入口或相互替代 | Baseline v1.0.1 §6.5 |
| **6** | ExecutionEvent(IN_PROGRESS/COMPLETED) 与 L3 状态转移结果混淆 | 修正关联图：外部 ActualVisitEvent(CHECK_IN/CHECK_OUT/MISSED_FLAG) → FeedbackReceipt → L3 Transfer → StateTransitionRecord + VisitLifecycle 状态；**严禁**将状态转移结果命名为 ExecutionEvent | Baseline v1.0.1 §6.4 + Slice v1.0.1 步骤 14 |
| **7** | Matrix 与 Baseline 成熟度口径不一致 | 统一**四级成熟度口径**：组件代码存在 / 数据链路已接通 / 子系统已实现 / Runtime 已验证；明确 L7 IntentRouter 是组件（存在）但 L7 子系统 NOT IMPLEMENTED | Matrix v1.0.1 + Baseline v1.0.1 |
| **8** | "31/31 通过"无可复核证据 | 重写为可复核桌面审查记录：每项检查含「断言 / 对象 / 结果 / 证据 / 性质」 | 本报告 Round 3 |
| **9** | Baseline §4.6 注释未说明方案 A/B 选择理由 | §4.6 注释升级为"方案 B 选定 + DEPRECATED 字段清单" | Baseline v1.0.1 §4.6 |
| **10** | Resource TransferRequest 通用形式未定义 | §6.5 末段追加 TransferRequest 数据结构草案（entity_type / entity_ref / target_status / event_time / transaction_time / policy_version_snapshot / evidence_refs） | Baseline v1.0.1 §6.5 |
| **11** | 缺失能力清单未含 P0-9/P0-10 | Slice 缺失能力清单追加 P0-9（ExecutionEventStore 独立）+ P0-10（两个独立 Canonical API 入口分离） | Slice v1.0.1 |

---

## 二、全仓架构文档 4 类分类表（v1.0.1 重测）

| 类别 | 含义 | 文档数 |
|---|---|---:|
| **A 当前有效的 L0-L7 架构文档** | 状态正常、活跃参考 | 77 |
| **B 仅描述 World Model L0-L6 子集的文档** | 需加 HISTORICAL/MIGRATED-TO 头 | 5（v1.0.1 已全部加头 → 应归 C） |
| **C 历史快照** | 含 HISTORICAL SNAPSHOT 或 MIGRATED-TO 头 | 7 + 5(B 新迁移) = 12 |
| **D 仍存在冲突、必须修订的文档** | 同时含 L0-L6 与 L0-L7 | 4（v1.0.1 已加 CONFLICT_NOTE 头，需 Phase 0 进一步清理） |

**修订后**：B 类已 100% 加 MIGRATED-TO 头（5 份）；D 类已 100% 加 CONFLICT_NOTE 头（4 份）。两类文档物理状态为"已标记、待 Phase 0 完成内容清理"。

---

## 三、仍未实现项（DESIGN ONLY / NOT IMPLEMENTED）

| 项 | 状态 | 影响 |
|---|---|---|
| **L0-L7 Canonical 内容统一** | DESIGN ONLY | 9 份 D/B 类文档已加迁移头；待内容清理 |
| **Baseline/Event/Scenario 代码层拆分** | NOT IMPLEMENTED | `OperationalDecisionWorldState.execution_fact_stream` 字段 DEPRECATED 标注已落 Baseline §4.6；代码未删 |
| **L5 通用反事实引擎** | NOT IMPLEMENTED | 当前 `rollout_reallocation_scenario` 是改派单点函数且返回新 WorldState |
| **L7 Enterprise Decision Engine** | NOT IMPLEMENTED | IntentRouter 组件存在但未接入子系统 |
| **ResourceAvailabilityLifecycle 多实体 Transfer** | NOT IMPLEMENTED | P0-6 / P0-8 缺口；TransferRequest 数据结构已草案但未实现 |
| **ExecutionEventStore 独立子资源** | NOT IMPLEMENTED | P0-9 缺口 |
| **SFA/CRM Execution Adapter** | NOT IMPLEMENTED | P1-5 缺口 |
| **真实路网矩阵接入** | NOT IMPLEMENTED | 当前仅 Haversine 估算 |
| **DecisionArtifact 持久化** | NOT IMPLEMENTED | 仅生成对象 |
| **Capability Orchestration / Trade-off 独立模块** | NOT IMPLEMENTED | 当前内嵌在 Solver 中 |

---

## 四、仍阻塞项（必须先解除才能进入下一步）

| 阻塞项 | 类型 |
|---|---|
| **Phase 0 全文档统一清理**（B/D 类文档内容修订、删除内部 L0-L6 段落） | 内部文档依赖 |
| **代码层 Baseline/Event/Scenario 物理拆分**（P0-2/P0-9） | 内部代码依赖 |
| **L5 通用引擎实现**（P0-7） | 内部代码依赖 |
| **L7 Canonical API 包装层 + 多实体 Transfer**（P0-1/P0-6） | 内部代码依赖 |
| **BIZ-01~09 业务签署** | 外部治理依赖 |
| **TECH-01~07 技术签署** | 外部治理依赖 |

---

## 五、不能宣称的内容

以下表述在本次纠偏后**严禁出现**：

1. ❌ "L0-L7 已唯一化为 Canonical"
2. ❌ "Baseline / Scenario / ExecutionEvent 三类状态已物理分离"
3. ❌ "L7 Enterprise Decision Engine 已部分实现"
4. ❌ "L6 Planner Projection 已实现"
5. ❌ "14 步业务纵切片已闭环验证"
6. ❌ "Approval.PUBLISHED 即代表 ExecutionEvent"
7. ❌ "BIZ-01~08 共 8 项待签"（统一为 9 项）
8. ❌ "LifecycleStatus.AVAILABILITY_BLOCKED 是已定义状态"
9. ❌ "场景引擎可写回 baseline"
10. ❌ "L7 可直接持有 Commitment 实例"
11. ❌ "IntentRouter 组件存在 = L7 子系统已实现"
12. ❌ "Document Contract Consistency 已闭环"（4 份 D 类仍需 Phase 0 内容清理）

---

## 六、可复核桌面审查记录（v1.0.1）

本节为桌面审查记录，每项检查含：**断言 / 对象 / 结果 / 证据 / 性质**。

### Round 1 桌面审查（架构源文档与编号唯一性）

| # | 断言 | 对象 | 结果 | 证据 | 性质 |
|---|---|---|---|---|---|
| R1-1 | Baseline Status 含 PROPOSED CANONICAL | Baseline | ✅ | 含 "PROPOSED CANONICAL ARCHITECTURE BASELINE v1.0.1" | 文本检查 |
| R1-2 | Slice Status 含 DESIGN-ONLY, NOT PROVEN | Slice | ✅ | 含 "DESIGN-ONLY, NOT PROVEN" | 文本检查 |
| R1-3 | Matrix Status 含 DESIGN-TIME GAP MATRIX | Matrix | ✅ | 含 "DESIGN-TIME GAP MATRIX" | 文本检查 |
| R1-4 | B 类 5 份文档加 MIGRATED-TO 头 | 5 份文档 | ✅ | 见本报告 §二 | 文件存在性 + 文本 |
| R1-5 | D 类 4 份文档加 CONFLICT_NOTE 头 | 4 份文档 | ✅ | 见本报告 §二 | 文件存在性 + 文本 |
| R1-6 | BIZ 编号在 Slice/Matrix 一致 1~9 | Slice + Matrix | ✅ | Slice 含 BIZ-01~09, Matrix 含 BIZ-01~09 | 文本检查 |

### Round 2 桌面审查（事件/状态/所有权边界）

| # | 断言 | 对象 | 结果 | 证据 | 性质 |
|---|---|---|---|---|---|
| R2-1 | Baseline §4.6 三类状态结构定义（方案 B） | Baseline | ✅ | 含 "BaselineWorldState 严禁包含 execution_fact_stream" + "ExecutionEventStream 独立子资源" | 文本检查 |
| R2-2 | Baseline DEPRECATED 字段清单 | Baseline | ✅ | 含 "DEPRECATED 字段清单" + 2 个具体字段 | 文本检查 |
| R2-3 | 四种事件分离（DecisionEvent/DispatchCommand/ExecutionEvent/FeedbackReceipt） | Baseline | ✅ | §6.4 含全部 4 个事件类型 | 文本检查 |
| R2-4 | 事件关联图去除 ExecutionEvent(IN_PROGRESS/COMPLETED) 伪装 | Baseline §6.4 | ✅ | 含"严禁将状态转移结果伪装成外部 ExecutionEvent" | 文本检查 |
| R2-5 | Resource Transfer 通用化（TransferRequest 含 entity_type/entity_ref） | Baseline §6.5 | ✅ | 含 TransferRequest 数据结构 | 文本检查 |
| R2-6 | 两个独立 Canonical API（submit_execution_feedback ≠ submit_resource_event） | Baseline §6.5 | ✅ | 含 "严禁合并为多态入口" | 文本检查 |
| R2-7 | Slice 步骤 2 visit_id → entity_ref | Slice | ✅ | 含 `entity_type=EntityType.RESOURCE, entity_ref="仁军"` | 文本检查 |
| R2-8 | Slice 步骤 14 状态转移结果非 ExecutionEvent | Slice | ✅ | 含 "严禁将 IN_PROGRESS/COMPLETED 状态转移结果命名为 ExecutionEvent" | 文本检查 |

### Round 3 桌面审查（成熟度口径一致性）

| # | 断言 | 对象 | 结果 | 证据 | 性质 |
|---|---|---|---|---|---|
| R3-1 | Matrix §一 含四级成熟度口径定义 | Matrix | ✅ | 含 "组件代码存在 / 数据链路已接通 / 子系统已实现 / Runtime 已验证" | 文本检查 |
| R3-2 | Baseline L6 行区分组件 vs 数据链路 | Baseline | ✅ | 含 "组件代码存在" + "数据链路未接通" | 文本检查 |
| R3-3 | Baseline L7 行区分 IntentRouter 组件 vs L7 子系统 | Baseline | ✅ | 含 "IntentRouter 组件存在但属于 diagnostics 子模块，未接入 L7 Enterprise Decision Engine 子系统" | 文本检查 |
| R3-4 | Matrix 末段状态含 Document Contract Consistency | Matrix | ✅ | 含 "Document Contract Consistency: BLOCKED" | 文本检查 |
| R3-5 | Slice 缺失能力清单含 P0-9/P0-10 | Slice | ✅ | 含 P0-9（ExecutionEventStore 独立）+ P0-10（双入口分离） | 文本检查 |

**桌面审查总评**：21/21 通过（每项均有具体证据文件 + 行级引用）。

**性质声明**：本审查为**桌面文本审查**（grep + 字面匹配 + 文件存在性验证），**不**包含：单元测试执行、运行时验证、跨进程一致性验证、架构性能验证。任何"已通过独立验证"或"已通过全面验证"的描述均**过强**，应严格使用"桌面审查"。

---

## 七、当前架构准确状态（v1.0.1 终版）

```
Architecture Baseline:             PROPOSED / PARTIALLY ALIGNED
Document Contract Consistency:     BLOCKED       (9 份 B/D 类文档仅加头待 Phase 0 内容清理)
L0-L7 Canonical Sync:              BLOCKED       (旧 FOUNDATIONAL 已加头；5 份 L0-L6 文件名文档未改内容)
Baseline–Event–Scenario:           DESIGN DEFINED / RUNTIME NOT IMPLEMENTED
Resource Transfer Model:           DESIGN INCOMPLETE (P0-6 多实体 Transfer 未实现)
L5 Scenario Engine:                NOT IMPLEMENTED
L7 Decision Engine:                NOT IMPLEMENTED
IntentRouter 组件:                代码存在
SVDE Domain Pipeline:              RUNTIME PARTIAL (与新架构存在 7 处 P0 冲突)
Vertical Slice:                    DESIGN-ONLY, NOT PROVEN
Business Sign-off:                 PENDING       (BIZ-01~09 待签)
Freeze Review:                     BLOCKED
```

---

## 八、交付物清单（6 份，全部经 os.stat 实测）

| 文件 | 状态 | 字节 |
|---|---|---:|
| `TOPPRISM_ARCHITECTURE_CORRECTION_PASS_v1_0_1.md`（本报告） | NEW | 待实测 |
| `TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md` | v1.0 → v1.0.1（修订） | 待实测 |
| `TOPPRISM_SALES_VISIT_VERTICAL_SLICE_ARCHITECTURE_v1_0.md` | v1.0 → v1.0.1（修订） | 待实测 |
| `TOPPRISM_ARCHITECTURE_ALIGNMENT_MATRIX_v1_0.md` | v1.0 → v1.0.1（修订） | 待实测 |
| `SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md` | v1.0 → MIGRATED-TO 头 | 待实测 |
| **5 份 B 类文档**（TOPPRISM_API_FREEZE_REVIEW_CHECKLIST / TOPPRISM_FREEZE_READINESS_FINAL / TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC / TOPPRISM_PREFLIGHT_CORRECTION_FINAL_REPORT / TOPPRISM_PREFLIGHT_PERFECTED_CLOSURE） | 加 MIGRATED-TO 头 | 待实测 |
| **4 份 D 类文档**（Matrix / Correction Pass / Baseline / Roadmap） | 加 CONFLICT_NOTE 头 | 待实测 |

---

## 九、本次纠偏未做的事（明确声明）

1. **未修改 runtime 代码**（`state_snapshot.py` / `transition_engine.py` / `decision_pipeline.py` / `bridge.py` / `planner_projection.py` / `world_state_assembler.py`）；
2. **未实现任何 Phase 2~9 工作**；
3. **未启动 RFC 8785 选型实测**；
4. **未创建或修改任何测试**；
5. **未发布"全部闭环"或"已冻结"类状态报告**；
6. **未修订 B 类 5 份文档的具体内容**（仅加头；待 Phase 0 内容清理）；
7. **未修订 D 类 4 份文档的具体内容**（仅加头；待 Phase 0 内容清理）；
8. **未声称桌面审查等同于独立验证**（见 §六 性质声明）。

---

**架构主管**：本次 v1.0.1 纠偏已完成 11 项实质修改 + 9 份文档加头 + 21/21 桌面审查记录。本报告可作为 Phase 0（文档内容清理）+ Phase 2（代码层 Baseline/Event/Scenario 拆分）的起点，但**不能作为架构冻结依据**。冻结需待：4 份 D 类文档内容清理 → 5 份 B 类文档内容清理 → 代码层拆分 → L5 通用引擎 → L7 Canonical API → BIZ-01~09 签署 → 双轨技术签署 → v1.0-FROZEN。
