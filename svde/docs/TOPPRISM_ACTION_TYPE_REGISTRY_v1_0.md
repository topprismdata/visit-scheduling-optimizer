# TopPrism Action Type 注册表 (v1.0-draft)

**Document ID:** TOPPRISM_ACTION_TYPE_REGISTRY_v1_0
**Version:** v1.0-draft
**Date:** 2026-08-27
**Status:** **DESIGN ONLY** — 非冻结规范，随 Action Type 工程化逐步增补

**设计依据:** TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md 建议 1
**Palantir 对照:** Action Types = "the verbs of the enterprise" (参数 + 规则 + 提交标准 + 副作用)

---

## 一、注册表结构

每条 Action Type 记录含：

| 字段 | 说明 |
|---|---|
| **Action ID** | 全局唯一标识（如 `ACTION-DEFER-VISIT`） |
| **名称** | 业务操作名称（如 `拜访顺延`） |
| **参数** | 该动作所需的输入参数（类型、约束） |
| **规则** | 执行该动作必须满足的业务规则（引用 BIZ-xx） |
| **提交标准** | 谁在什么条件下可以执行（角色、状态、时间窗口） |
| **副作用** | 执行后触发的连锁动作（通知、写回、重算触发） |
| **读对象** | 该动作读取哪些 Canonical 类型 |
| **写对象** | 该动作创建/修改哪些 Canonical 类型 |
| **写回系统** | 该动作写回哪些外部系统（如 ERP） |

---

## 二、首批 Action Type

### ACTION-DEFER-VISIT `拜访顺延`

**业务语义:** 经理将某次已排定的拜访顺延到另一日期，受 `DeferralPolicy` 约束。

**参数:**
```python
{
    "visit_id": str,           # 待顺延的拜访标识
    "deferral_policy_id": str, # 顺延政策（引用 DeferralPolicy.policy_id）
    "new_date": date,          # 目标日期
    "reason_code": str,        # 原因代码（如 "CUSTOMER_CANCEL" / "WEATHER" / "REP_UNAVAILABLE"）
    "approved_by": str,        # 审批人（BIZ-08）
}
```

**规则:**
- `deferral_policy_id` 必须引用 `DeferralPolicy` 中 state=ACTIVE 的记录 (BIZ-02)
- 当月已顺延次数不得超过 `max_deferrals_per_month` (BIZ-02)
- 新日期必须在 `allowed_deferral_window_days` 内 (BIZ-02)
- Key/A 级门店顺延须经理审批 (BIZ-03/BIZ-08)

**提交标准:**
- 角色: `REP_MANAGER` 或以上
- 状态: 目标拜访 `current_status` 必须为 `PLANNED` 或 `COMMITTED`
- 时间窗口: 原拜访日期前 24h 内不可顺延（紧急情况走例外审批）

**副作用:**
- 通知: 原日期路线受影响的其他门店负责人
- 写回: 更新 `OperationalVisitLifecycleRecord` 状态 → `DEFERRED`
- 触发: 可选增量重算（若目标日期已有超过上限的拜访）

**读对象:** `OperationalVisitLifecycleRecord` (§12), `DeferralPolicy` (§8)
**写对象:** `OperationalVisitLifecycleRecord` (status → DEFERRED), `PolicyAmendment` (§37)

---

### ACTION-TRANSFER-OWNERSHIP `归属转移`

**业务语义:** 将某门店的拜访归属从一代表转移到另一代表。

**参数:**
```python
{
    "store_code": str,
    "from_rep_id": str,
    "to_rep_id": str,
    "effective_date": date,
    "reason_code": str,      # "TERRITORY_REBALANCE" / "CONFLICT_RESOLUTION" / "REP_DEPARTURE"
    "approved_by": str,
}
```

**规则:**
- 目标门店必须同时存在于 `from_rep_id` 与 `to_rep_id` 的 `assigned_store_codes` 中 (BIZ-06)
- 若因归属冲突裁决，必须引用 `OwnershipConflictRecord` 的裁决结果 (BIZ-06)
- `effective_date` 不得早于当前日期 - 7 天（追溯限制）

**提交标准:**
- 角色: `DISTRICT_MANAGER` 或以上
- 状态: 被转移门店当前无 `ACTIVE` 的 `OwnershipAssignment` 冲突

**副作用:**
- 写回: 创建 `OwnershipAssignment` (status=ACTIVE), 旧 assign 置为 `SUPERSEDED`
- 通知: 两位代表及其区域经理

**读对象:** `OwnershipConflictRecord` (§35.9), `OperationalResource` (§5)
**写对象:** `OwnershipAssignment` (§38)

---

### ACTION-APPROVE-PLAN `审批计划`

**业务语义:** 经理审批/驳回某次计划版本，将其从 `reviewed` 推进到 `published` 或退回 `draft`。

**参数:**
```python
{
    "plan_version_id": str,
    "decision": str,          # "APPROVE" / "REJECT" / "REVISE"
    "comments": str,
    "approved_by": str,
}
```

**规则:**
- 计划版本必须处于 `reviewed` 状态（审批前置）
- Key/A 级门店占比 > 50% 的计划须总监级审批 (BIZ-08)
- 驳回时须填写 `comments`（原因说明）

**提交标准:**
- 角色: `MANAGER` 或以上（Key 占比高时 → `DIRECTOR`）
- 时间窗口: 计划生效日至少 3 个工作日前

**副作用:**
- 写回: `PlanVersion.status` → `published` (APPROVE) / `draft` (REJECT/REVISE)
- 通知: 计划所属代表（批准时推送，驳回时附原因）
- 触发: 若 REJECT 且 `plan_version.solver_run_id` 存在，标记求解器运行记录为 `OVERRIDDEN`

**读对象:** `PlanVersion` (algos/pvrp_cg), `PlannedVisit[]`, `OperationalCustomer` (§4)
**写对象:** `PlanVersion` (status)

---

### ACTION-ADJUST-FREQUENCY `调整频次`

**业务语义:** 业务经理调整某门店的拜访频次（触发 `PolicyAmendment` 记录）。

**参数:**
```python
{
    "policy_id": str,
    "store_code": str,
    "new_frequency_per_month": int,
    "reason_code": str,      # "DEMAND_CHANGE" / "PROMOTION" / "PERFORMANCE_ADJUST"
    "effective_from": date,
    "approved_by": str,
}
```

**规则:**
- `new_frequency_per_month` 必须在合法频次集中（1/2/4，**禁止 3**，对齐 BIZ-01 方案B 事实）
- 生效日期不得早于当前日期
- 频次调整涉及 Key/A 级门店需要经理审批 (BIZ-03)

**提交标准:**
- 角色: `DATA_STEWARD` 或以上
- 状态: 目标门店 `OperationalCustomer` 状态为 active

**副作用:**
- 写回: 创建 `PolicyAmendment` (field_name=target_frequency_per_month)
- 通知: 对应代表的区域经理

**读对象:** `OperationalVisitPolicy` (§7), `OperationalCustomer` (§4)
**写对象:** `PolicyAmendment` (§37), `OperationalVisitPolicy` (target_frequency_per_month 更新)

---

## 三、实现路径

| 阶段 | 动作 | 依赖 |
|---|---|---|
| Phase 1 | 注册表冻结（本文档进入 REVIEW） | 无（规范层） |
| Phase 2 | Action Type 的 Canonical 参数类型定义（冻结 dataclass） | Canonical Types 规范 |
| Phase 3 | Action Type 执行引擎（L7 决策引擎） | 双轨签署、L7 代码实现 |
| Phase 4 | 副作用引擎（通知/写回） | 外部系统集成 |

---

## 四、成熟度声明

```
本文档: DESIGN ONLY (注册表草案)
参数类型: 未实现 (待 Canonical 类型登记)
执行引擎: 未实现 (L7 决策引擎)
副作用: 未实现
```