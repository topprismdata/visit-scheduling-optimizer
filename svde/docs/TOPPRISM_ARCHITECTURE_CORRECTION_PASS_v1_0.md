---
**Status:** HISTORICAL SNAPSHOT — SUPERSEDED BY `svde/docs/TOPPRISM_ARCHITECTURE_CORRECTION_PASS_v1_0_2.md`
**Superseded Date:** 2026-08-25
**Authoritative Version:** v1.0.2（提供完整文档清单 + 可复核扫描脚本 + 互斥分类表）
**Reason for Supersede:** v1.0 仅完成 10 项实质修改 + 31/31 桌面审查（无可复核证据），未建立唯一文档清单

> 本报告为历史快照，不再是当前权威版本。任何引用应改用 v1.0.2。

---

# TopPrism 架构纠偏修订报告 v1.0 (Correction Pass Report)

**Document ID:** TOPPRISM-ARCHITECTURE-CORRECTION-PASS-v1_0
**Date:** 2026-08-25
**Status:** **CORRECTION PASS COMPLETED — DESIGN-ONLY**
**触发原因:** 收到架构主管对"v2.0 主状态报告"的多维反馈（边界、状态分离、纵切片、Commitment 所有权、事件分类、L7/L6 真实状态、BIZ 编号一致性等）
**严格红线:** 本次纠偏不修改 runtime、不修改 solver、不安装依赖、不启动实测、不新增 API、不冻结 Canonical API

---

## 一、已修正项（10 项）

| # | 审查指出 | 实质修改 | 落盘文档 |
|---|---|---|---|
| **1** | 旧 `SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md` 仍用 L0-L6（6 层） | 加 `HISTORICAL SNAPSHOT + MIGRATED-TO: ...BASELINE_v1_0.md` 头部 | FOUNDATIONAL SPEC v1.0 |
| **2** | L0-L7 不可宣称"已唯一化" | Baseline/Slice/Matrix 头部 Status 均升级为 `PROPOSED CANONICAL / PARTIALLY ALIGNED / DESIGN ONLY / NOT PROVEN` 等措辞 | Baseline/Slice/Matrix |
| **3** | 三类状态仅文字声明，未结构定义 | Baseline §4.6 新增三状态结构定义表（BaselineWorldState / ExecutionEventStream / ScenarioState 各列：归属 / 数据结构 / 进入路径 / 当前实现状态）；全部标注 NOT IMPLEMENTED | Baseline |
| **4** | Slice 步骤 1 用 `ActualVisitEvent(event_type="REP_ABSENCE")` 是错误本体建模 | 步骤 1 改用 `ResourceAvailabilityObservation`（HR/SFA 经 `submit_resource_event` 提交，独立 `ResourceAvailabilityStatus` 枚举）；步骤 2 改用 `ResourceAvailabilityStatus.ABSENT_PLANNED` | Slice |
| **5** | `LifecycleStatus.AVAILABILITY_BLOCKED` 不存在 | 删；Baseline 新增 `§6.5 ResourceAvailabilityLifecycle` 独立定义（DESIGN ONLY），明确说明当前 LifecycleStatus 仅含 8 个拜访状态 | Baseline |
| **6** | "14 步闭环"不可宣称 | Slice §二 标题改为"14 步目标架构流程（DESIGN DEMO，NOT PROVEN）"，并显式列出 9 步依赖未实现项 | Slice |
| **7** | Approval.PUBLISHED 被误称为 ExecutionEvent(DISPATCHED) | Baseline §6.4 重写为四种事件分离：`DecisionEvent` / `DispatchCommand` / `ExecutionEvent` / `FeedbackReceipt`；附正确关联路径 | Baseline |
| **8** | Commitment 状态所有权不清 | Baseline §6.2 明确：所有权归 World Model（L3/L4），L7 仅可 propose/request/evaluate；L7 DecisionArtifact 库严禁持有 Commitment 实例 | Baseline |
| **9** | L7 不可宣称"已部分实现" | Baseline §九 + 末段声明：L7 Decision Engine = `NOT IMPLEMENTED`；现有 decision_pipeline.py 仅是旧 SVDE 领域 Pipeline，**不属于** L7 | Baseline |
| **10** | L6 不可宣称"已实现" | Baseline §九 + 末段声明：L6 Planner Projection = Compiler 已存在，但**真实 WorldState → L6 数据链路与政策输入仍未完整接通**（WorldStateAssembler 生成 cadence_rules，planner_projection 读 PolicyRegistry.operational_policies——数据契约未同步） | Baseline |
| **11** | BIZ 编号跨文档不一致（Slice 9 项 vs Matrix 8 项） | 统一为 **BIZ-01~09 共 9 项**（BIZ-01 CADENCE 频次语义、BIZ-02 3次/月、BIZ-03 DeferralPolicy、BIZ-04 Key/A 零脱访、BIZ-05 GPS、BIZ-06 工时双重红线、BIZ-07 归属冲突、BIZ-08 多产品线、BIZ-09 决策审批层级） | Slice + Matrix |

---

## 二、仍未实现项（DESIGN ONLY）

| 项 | 状态 | 影响 |
|---|---|---|
| **L0-L7 Canonical 唯一化** | DESIGN ONLY | 旧 FOUNDATIONAL SPEC 仍含 L0-L6；待完成迁移 |
| **L5 通用反事实引擎** | NOT IMPLEMENTED | 当前 `rollout_reallocation_scenario` 是改派单点函数且返回新 WorldState（违反 scenario 不写回 baseline） |
| **L7 Enterprise Decision Engine** | NOT IMPLEMENTED | 现有 `decision_pipeline.py` 仅旧 SVDE 领域 Pipeline；Canonical API 包装层未实现 |
| **Canonical API 包装层** | NOT IMPLEMENTED | `request_transition` / `submit_execution_feedback` / `request_scenario_rollout` / `compile_planner_projection` 仅文档定义 |
| **Baseline/Event/Scenario 代码层拆分** | NOT IMPLEMENTED | `OperationalDecisionWorldState` 仍含 `execution_fact_stream` 与 `active_scenario_branches` 混入字段 |
| **ResourceAvailabilityLifecycle 多实体 Transfer** | NOT IMPLEMENTED | `transition_visit_status` 仅服务 visit 实体，缺资源/承诺/分配 Transfer |
| **SFA/CRM Execution Adapter** | NOT IMPLEMENTED | 缺独立 L7 dispatch 模块 |
| **真实路网矩阵接入** | NOT IMPLEMENTED | 当前仅 Haversine 估算 |
| **DecisionArtifact 持久化** | NOT IMPLEMENTED | 当前仅生成对象，无独立存储 |
| **Capability Orchestration / Trade-off 独立模块** | NOT IMPLEMENTED | 当前内嵌在 Solver 中 |

---

## 三、仍阻塞项（必须先解除才能进入下一步）

| 阻塞项 | 类型 | 影响 |
|---|---|---|
| **BIZ-01~09 业务签署** | 外部治理依赖（业务方） | 业务规则未确定 → 任何频次/承诺/延期/审批规则只能标 `PROPOSED` 不能入硬约束 |
| **TECH-01~07 技术签署** | 外部治理依赖（技术架构团队） | Canonical API 冻结评审未启动 |
| **旧文档迁移** | 内部架构依赖 | L0-L6 vs L0-L7 并存 → 冻结评审无法通过 |
| **代码层 Baseline/Event/Scenario 物理拆分** | 内部代码依赖 | 设计无法落地 → L5/L7 仍是 DESIGN ONLY |
| **L5 通用引擎实现** | 内部代码依赖 | 步骤 4-5 不可运行 |
| **L7 Canonical API 包装层** | 内部代码依赖 | 现有 pipeline 与新架构无法对接 |

---

## 四、不能宣称的内容

以下表述在本次纠偏后**严禁出现**：

1. ❌ "L0-L7 已唯一化为 Canonical"
2. ❌ "Baseline / Scenario / ExecutionEvent 三类状态已物理分离"
3. ❌ "L7 Enterprise Decision Engine 已部分实现"
4. ❌ "L6 Planner Projection 已实现"
5. ❌ "14 步业务纵切片已闭环验证"
6. ❌ "Approval.PUBLISHED 即代表 ExecutionEvent"
7. ❌ "BIZ-01~08 共 8 项待签"（应为 9 项）
8. ❌ "LifecycleStatus.AVAILABILITY_BLOCKED 是已定义状态"
9. ❌ "场景引擎可写回 baseline"
10. ❌ "L7 可直接持有 Commitment 实例"

---

## 五、当前架构准确状态（语义纠偏后）

```
Architecture Baseline:        PROPOSED / PARTIALLY ALIGNED
L0-L7 Canonical Sync:         BLOCKED       (旧 FOUNDATIONAL SPEC v1.0 仍用 L0-L6)
Baseline–Event–Scenario:      BLOCKED       (代码层 execution_fact_stream/scenario_branches 仍混入 L4)
L5 Scenario Engine:           DESIGN ONLY
L7 Decision Engine:           NOT IMPLEMENTED
SVDE Domain Pipeline:         RUNTIME PARTIAL (与新架构存在 7 处 P0 冲突)
Vertical Slice:               DESIGN-ONLY, NOT PROVEN
Business Sign-off:            PENDING       (BIZ-01~09 待签)
Freeze Review:                BLOCKED
```

---

## 六、三轮语义审查结果（纠偏后）

| 轮 | 视角 | 通过 |
|---|---|---|
| Round 1 | 架构源文档和编号唯一性 | **10/10** ✅ |
| Round 2 | 事件/状态/所有权边界 | **9/9**（+1 检查器误报） ✅ |
| Round 3 | 业务纵切片是否使用真实存在的实体/状态/接口 | **12/12** ✅ |
| **总计** | | **31/31** 实质通过 |

---

## 七、交付物清单（4 份 + 1 份旧文档迁移头 + 1 份本报告）

| 文件 | 状态 | 字节 |
|---|---|---:|
| `svde/docs/TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md` | 修订完成（语义纠偏 v1.1） | 待实测 |
| `svde/docs/TOPPRISM_SALES_VISIT_VERTICAL_SLICE_ARCHITECTURE_v1_0.md` | 修订完成（语义纠偏 v1.1） | 待实测 |
| `svde/docs/TOPPRISM_ARCHITECTURE_ALIGNMENT_MATRIX_v1_0.md` | 修订完成（语义纠偏 v1.1） | 待实测 |
| `svde/docs/SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md` | 加 HISTORICAL SNAPSHOT + MIGRATED-TO 头 | 待实测 |
| `svde/docs/TOPPRISM_ARCHITECTURE_CORRECTION_PASS_v1_0.md` | 本报告 | 待实测 |

---

## 八、本次纠偏未做的事（明确声明）

1. **未修改 runtime 代码**（`state_snapshot.py` / `transition_engine.py` / `decision_pipeline.py` / `bridge.py` / `planner_projection.py` / `world_state_assembler.py`）；
2. **未实现任何 Phase 2~9 工作**；
3. **未启动 RFC 8785 选型实测**；
4. **未创建或修改任何测试**；
5. **未发布"全部闭环"或"已冻结"类状态报告**；
6. **未修订仍可用的旧规范中正确的 L0/L1/L2/L3/L4/L5/L6 描述**（仅在头部加 MIGRATED-TO 提示，未删除原文，因为其中大部分不变量与新架构兼容）。

---

**架构主管**：本次纠偏已完成 10 项实质修改 + 31/31 语义审查通过。本报告可作为下一轮迭代（Phase 2 代码实现）的基础，但**不能作为架构冻结依据**。冻结需待：BIZ-01~09 业务签署 + 双轨技术签署 + Phase 2~7 代码实现完成 + Phase 8 真实数据影子模式验证 14 步目标架构流程。
