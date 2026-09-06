# TopPrism L7 企业决策引擎详细规范 v1.0 (Enterprise Decision Engine Spec)

**Document ID:** TOPPRISM-L7-DECISION-ENGINE-SPEC-v1.0  
**Version:** **v1.0-draft.2 (Phase 6 Detailed Specification - Corrected)**  
**Date:** 2026-08-24  
**Status:** **DETAILED SUBSYSTEM SPECIFICATION (NOT YET FROZEN)**  
**上游约束:** 
- `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md`
- `DECISION_ENGINE_BOUNDARY.md`
- `WORLD_MODEL_DECISION_ENGINE_CONTRACT.md` (v1.0-draft.5.2)
- `CANONICAL_TYPE_REGISTRY.md` (类型权威登记)

---

## 一、L7 企业决策引擎的核心定位与架构责任

L7 企业决策引擎（Prism Decision Engine）是 **TopPrism 决策智能产品家族的“行动、优化与审批统筹中枢”**。
它的核心职责不是维护世界事实，而是**在不可变的世界模型之上，统筹业务意图、调度运筹求解能力、评估多目标权衡、执行严格三维独立审计、落实人机协同审批、并最终下发不可变的决策产物（DecisionArtifact）**。

---

## 二、字典序多目标层级规范 (Aligned with S-A §2.5 & World Model)

决策引擎在评估候选方案优劣时，严格遵循以下五级字典序目标（Lexicographic Objective Hierarchy）：

$$\operatorname{LexMin} \quad \mathbf{Z} = \left( Z_0, Z_1, Z_2, Z_3, Z_4 \right)$$

- **Level 0 (物理可行性与硬约束守卫)**: 单日容量 $\le 6$ 家、单日工时 $\le 480\text{ min}$ (或长途日弹性上限)、起终点闭环、无子回路；
- **Level 1 (业务价值与客户覆盖质量)**: `REQUIRED` 核心大店 0 脱访、全网频次达成率最大化；
- **Level 2 (交通在途时间与空间损耗)**: 全月从 Depot 往返与城际通勤总耗时绝对极小化（消除跨区折返）；
- **Level 3 (拜访节奏稳定性与平滑度)**: 1A 严格同周几等距（7天/14天/28天）偏离度极小化；
- **Level 4 (每日工作负荷均衡度)**: 工作日间拜访数量方差极小化（次级偏好，不为追求过度均衡而牺牲空间紧凑性）。

---

## 三、DecisionArtifact 发布与 WorldModel 状态提交的事务契约 (Two-Phase Commit / Saga Protocol)

为了确保“决策库发布”与“世界模型状态锁定”不出现分布式不一致，决策引擎必须遵循以下三阶段预留与提交协议：

```
L7 Decision Engine                                  World Model L3 / L4 Store
       │                                                      │
       │ 1. reserve_plan_commitment(candidate_plan_id)       │
       ├─────────────────────────────────────────────────────>│
       │                                                      │ 校验承诺冲突并生成锁定令牌
       │ 2. 返回 (success=True, commit_token="TKN_xxx")       │
       │<─────────────────────────────────────────────────────┤
       │                                                      │
       │ 3. 写入不可变 DecisionArtifact 到决策库             │
       │                                                      │
       │ 4. commit_plan_transition(commit_token)              │
       ├─────────────────────────────────────────────────────>│
       │                                                      │ 正式将相关拜访状态置为 COMMITTED
       │ 5. 返回 TransitionResult                             │
       │<─────────────────────────────────────────────────────┤
       │                                                      │
       │ ─── 若步骤 3 或 4 失败触发补偿 ───────────────────── │
       │ 6. abort_plan_commitment(commit_token)               │
       ├─────────────────────────────────────────────────────>│ 释放预留锁定
```

### 3.1 事务实现级约束

| 约束项 | 规则 |
| :--- | :--- |
| **幂等键** | `reserve_plan_commitment(candidate_plan_id, idempotency_key)` — 同一 `idempotency_key` 重复调用返回首次 `commit_token`，不重复锁定 |
| **commit_token 有效期** | 默认 300 秒（可通过配置调整）；超时后 WorldModel 自行将预留状态从 `RESERVED` 回退为 `AVAILABLE` |
| **预留锁超时** | WorldModel 后台巡检进程每 30 秒扫描过期 `RESERVED` 记录并自动释放 |
| **补偿写入审计** | `abort_plan_commitment` 必须在 `execution_fact_stream` 中写入一条 `TransitionEvent`（含 `failure_reason`），确保补偿操作本身可审计 |
| **重复产物防护** | DecisionArtifact 存储以 `candidate_plan_id` 为唯一键；若已存在则返回已有 `artifact_id` 而非重复写入 |
| **WorldModel 先提交、产物存储失败** | WorldModel 已 COMMITTED 但 DecisionArtifact 写入失败时：系统进入 `PENDING_PUBLISH` 状态，由重试队列补偿写入（最长重试 24h，超时告警） |
| **产物先写入、WorldModel 提交失败** | DecisionArtifact 已写入但 WorldModel COMMIT 失败时：系统自动调用 `abort_plan_commitment` 补偿，DecisionArtifact 标记为 `ROLLED_BACK` |
| **重试语义** | 全流程幂等可重试；任何步骤失败后调用方可携带相同 `idempotency_key` 重试，不会产生重复锁定或重复产物 |

---

## 四、核心数据结构规范（权威引用）

本引擎消费与产出的全部领域类型的**唯一权威定义**在 `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md`：

| 类型 | 权威章节 |
| :--- | :--- |
| `PlanningIntent` | §26 |
| `PlannedStop` | §27 |
| `PlannedDailyRoute` | §28 |
| `CandidatePlan` | §29 |
| `PlanAuditReport` | §31 |
| `DecisionArtifact` | §32 |

（依据《Canonical Types 规范》定义来源铁律第 3 条：其他规范文档只允许引用，严禁重复定义。）

---

## 五、阶段状态声明

- **规范版本**: `v1.0-draft.2`
- **状态**: 修正完成，作为 Phase 6 详细规范沉淀，**等待 Phase 1 业务语义签署完成后与整体 API 共同冻结**。
