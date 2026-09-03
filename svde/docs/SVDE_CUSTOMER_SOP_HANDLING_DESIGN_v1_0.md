# SVDE Sales Visit — 客户差异化 SOP 处理方案设计
**Document ID:** SVDE-CUSTOMER-SOP-HANDLING-DESIGN-V1.0
**Date:** 2026-08-24
**Status:** DESIGN PROPOSAL — REQUIRES BUSINESS ARBITRATION
**Scope:** Design proposal for handling per-customer differentiated Standard Operating Procedures (SOPs) within SVDE Sales Visit ontology.

---

## 0. 设计原则

> **重要前提**：本设计**仅是技术方案建议**。在 v1.1 §5.3 规范下，本设计的**任何字段**（如 `CustomerSOP` / `SOPPolicy` / `SOPBinding` 等对象）**都不能**自行被 Agent 标为 `FROZEN`。
> 
> 必须先由业务方在 `GAP-3 SECONDARY` 或新增 `GAP-6` 沟通模板中明确勾选 "是" / "否" / "推迟"，才能进入 `BUSINESS_APPROVED → FROZEN` 状态。

---

## 1. 业务问题精确定义

业务方原话："这个需要引入 SOP"——核心含义是**"每个客户有不同的标准操作流程"**（per-customer differentiated SOPs）。

**典型场景举例**：
- 客户 A：拜访前 24 小时必须电话预约
- 客户 B：每月 1 号必须提交上月销售报告
- 客户 C：拜访时必须穿防护服 + 带 5 个样品
- 客户 D：必须先与采购经理面谈 30 分钟才能进入店面

这些**不是**通用 SOP，而是**按客户绑定的特殊操作要求**。

---

## 2. 三种实现方案对比

### 方案 A：客户级 SOP 字段直接挂在 `Customer` 上（**简单**）

```text
Customer {
  id: str
  sop_id: str           # 指向 SOPPolicy
  sop_constraints: List[str]  # 适用于本客户的具体 SOP 要求
}
```

- **优点**：实现简单，单层引用
- **缺点**：**违反 v1.1 §4.2 不可折叠规则**——把 SOP 直接绑到 Customer 上会折叠两个不同的语义层
- **适用场景**：仅当 SOP 极简单（1-2 条规则）

### 方案 B：独立 `SOPPolicy` + `CustomerSOPBinding`（**推荐**）

```text
SOPPolicy {
  id: str
  name: str
  description: str
  constraints: List[SOPConstraint]  # 时间、物品、流程等
  applicable_customer_tier: str
}

CustomerSOPBinding {
  customer_id: str
  sop_policy_id: str
  binding_date: str       # SOP 生效时间
  expiration_date: str   # SOP 失效时间（如有）
  version: str            # SOP 版本号（业务方常更新 SOP）
  override_allowed: bool  # 是否允许代表特殊情况下跳过
}

SOPConstraint {
  type: Enum             # TIME | EQUIPMENT | PAPERWORK | APPROVAL | OTHER
  description: str
  is_hard: bool          # 硬性：违反 SOP 不可拜访
  is_soft: bool          # 软性：违反 SOP 需事后说明
}
```

- **优点**：满足 v1.1 §4.2 不折叠规则；支持 SOP 版本化与客户差异化
- **缺点**：需新增 3 个本体对象
- **适用场景**：**多数业务方**（推荐）

### 方案 C：SOP 链接到 `VisitPolicy` 而非 `Customer`（**最严格**）

```text
VisitPolicy {
  customer_id: str
  cadence_spec_id: str
  sop_policy_id: str      # SOP 绑在拜访政策上
  ...
}

SOPPolicy { ... }
SOPConstraint { ... }
```

- **优点**：SOP 随拜访政策生命周期自动管理（如 VIP 客户 SOP 失效时仍可拜访）
- **缺点**：客户换政策时 SOP 会跟着走，可能不是业务方期望
- **适用场景**：SOP 与拜访政策强绑定

---

## 3. v1.1 规范对齐检查

| 检查项 | 状态 |
| :--- | :--- |
| 不折叠业务对象（§4.2） | ✅ SOP 与 Customer / VisitPolicy 独立 |
| 生命周期完整（§8） | ✅ `CustomerSOPBinding` 可独立演化为 `DEPRECATED` / `EXPIRED` |
| 证据等级（§5.1） | ⚠️ "客户差异化 SOP"目前仅业务方口头表达，**无具体证据来源** |
| 五状态门禁（§5.3） | ⚠️ 须经业务方勾选 `BUSINESS_APPROVED` 才能冻结 |
| 算法概念防升格（§6.1） | ✅ SOP 不是算法，是业务规则 |

---

## 4. 必须由业务方裁决的 5 个具体问题

### Q1：SOP 是否进入本体？

- [ ] **是** — `SOPPolicy` + `CustomerSOPBinding` + `SOPConstraint` 三个新对象进入本体（**方案 B 推荐**）
- [ ] **是** — 但仅 `Customer.sop_id` 简单字段进本体（**方案 A**）
- [ ] **否** — SOP 保持外部系统管理，本体不建模
- [ ] **推迟** — 本期不处理，下一变更请求再处理

### Q2：SOP 与 Customer 的绑定方式？

- [ ] **客户级绑定**（SOP 跟随客户生命周期）— 方案 B
- [ ] **拜访政策级绑定**（SOP 跟随 VisitPolicy 生命周期）— 方案 C
- [ ] **暂不明确**

### Q3：违反 SOP 的系统行为？

- [ ] **硬性拒绝** — 违反 SOP 不可拜访该客户
- [ ] **软性警告** — 违反 SOP 需事后说明，可继续拜访
- [ ] **不区分** — 全部软性

### Q4：SOP 是否需版本化？

- [ ] **需要** — SOP 随业务调整需支持版本号与历史追踪
- [ ] **不需要** — 一次定义不变更

### Q5：SOP 数据的当前覆盖？

- [ ] **已有书面 SOP** — 业务方已有正式版本化 SOP 文档
- [ ] **部分有** — 仅有部分客户/部分场景
- [ ] **全部无** — 暂未开始撰写

---

## 5. 关联说明（与 GAP-3 / GAP-5 的关系）

| 关联 GAP | 关系 |
| :--- | :--- |
| **GAP-3 (ApprovalRequest)** | 违反 SOP → 是否进入 `ApprovalRequest`（需业务方裁决）？|
| **GAP-5 (BusinessCostPerDayPerCustomer)** | SOP 失败成本是否进入 `BusinessCostPerDayPerCustomer`？|
| **GAP-1 (Product/SKU)** | SOP 是否要求携带特定 SKU / 样品？|

> **注意**：本设计建议**不**将 SOP 草稿直接合并进 GAP-3 / GAP-5 的裁决流程，避免一次裁决过多对象。**应新增独立 `GAP-6 (SOPPolicy)` 仲裁流程**。

---

## 6. 当前真实状态

```
v1.1 规范：Design Baseline
GAP-1 (Product)  : BUSINESS_APPROVED
GAP-2 (Region)   : BUSINESS_APPROVED
GAP-3 (Approval) : PENDING_ESCALATION
GAP-4 (TimeDev)   : BUSINESS_APPROVED
GAP-5 (BizCost)   : PENDING_ESCALATION
GAP-6 (SOP)       : PROPOSED (本设计建议)
v0.3 冻结        : 仍 HOLD（需 GAP-3/5 裁决 + 新增 GAP-6 沟通）
prism-ontology  : 未启动 Phase 0
```

---

## 7. 下一步建议（请选 1 项）

| 选项 | 操作 | 推进度 |
| :--- | :--- | :--- |
| **A. 仅将业务方原话"需要 SOP"作为 `BUSINESS_OWNER_OBSERVATION` 归档，不展开 GAP-6** | ✅ 合规 + 不引入新对象 + v0.3 仍 hold 等 GAP-3/5 | 最小 |
| **B. 立即起草 GAP-6 沟通模板** | 按本设计 §4 的 5 个问题，参照 v1.0 / v1.1 模板起草 | 推荐 |
| **C. 等 GAP-3 / GAP-5 二次答复后再决定是否启动 GAP-6** | 严格按 v1.1 §5.3 + §9 推进 | 最保守 |
| **D. 同时启动 GAP-3 / GAP-5 二次澄清 + GAP-6 沟通** | 业务方一次面对三轮沟通 | 激进 |

**我推荐 B 或 C**——B 更积极（业务方已表达 SOP 需求），C 更保守（按 v1.1 严格推进）。

请下达下一步具体指令。