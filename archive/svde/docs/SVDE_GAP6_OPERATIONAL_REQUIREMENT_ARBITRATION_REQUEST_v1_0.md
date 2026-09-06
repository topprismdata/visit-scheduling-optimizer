# SVDE Sales Visit — GAP-6 客户差异化操作要求业务方裁决沟通
**Document ID:** SVDE-GAP6-OPERATIONAL-REQUIREMENT-ARBITRATION-REQUEST-V1.0
**Date:** 2026-08-24
**Status:** TEMPLATE — WAITING FOR BUSINESS OWNER
**Recipient:** Business Owner (Sales Visit domain) + IT Architect
**Purpose:** Classify the semantic category of "customer-specific operational requirement" before any decision on ontology entry.

---

## 0. 沟通原则（与 v1.1 一致）

- 本文档**不是**产品需求 / 业务变更 / 内部审查。
- 本文档**仅**用于业务方对"客户差异化操作要求"做语义分类与仲裁。
- 业务方对**第一问（语义分类 A/B/C/D/E）**必须勾选，**没有勾选 = 未完成答复**，v0.3 继续 hold。
- 业务方对后续子问题（是否进本体 / 绑定范围 / 违反处理 / 版本化 / 数据覆盖）**仅在被分类为 A 或 B 时才需要回答**；C/D/E 类按设计原则**不进入销售拜访本体**。

---

## 1. 第一问：语义分类（必答）

业务方此前表述："这个需要引入 SOP / 每个客户有不同的 SOP"。

**问题：业务方所说的"客户差异化 SOP"具体属于哪一类？**

- [ ] **A. 拜访前置准入条件**（如：拜访前 24 小时电话预约、必须带样品、必须先与采购经理面谈）
- [ ] **B. 拜访过程中的服务协议**（如：拜访时必须做产品演示、必须填写服务记录、必须保持店招可见）
- [ ] **C. 销售代表内部执行流程**（如：周报怎么写、出差怎么报销、客户沟通话术）
- [ ] **D. 报告/交付/审批流程**（如：每月 1 号提交销售报告、提交预测订单、签收单据）
- [ ] **E. 尚未确定**（业务方目前尚未明确具体是哪类）

**业务方签字：** __________________ **日期：** __________

---

## 2. 子问题（仅当第一问勾选 A 或 B 时回答）

### 2.1 是否进入销售拜访本体？

- [ ] **是** — `CustomerOperationalRequirement` 进入本体（独立于 Customer / VisitPolicy 的新对象）
- [ ] **否** — 保持外部系统管理，本体不建模
- [ ] **推迟裁决**

### 2.2 绑定范围与生命周期

```text
required_binding_scope:
  - customer_id (必填)
  - visit_policy_id (可选)
  - visit_type / scenario_type (可选, 如常规 / 促销 / 采样)
  - effective_from (必填)
  - effective_to (可选)
  - version (必填, 字符串)
  - priority (必填, 整数 / 枚举)

required_lifecycle:
  PROPOSED → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN → DEPRECATED → RETIRED
```

**业务方请确认**：
- [ ] **同意以上 7 项绑定字段 + 6 阶段生命周期**

### 2.3 违反后的系统行为（`constraint_class` 单一枚举，不可同时为多值）

```text
constraint_class (单选, 不可多选):
  - HARD_BLOCK:        硬约束阻断，违反不可拜访
  - SOFT_WARNING:      软约束警告，可继续拜访但需事后说明
  - APPROVAL_REQUIRED: 必须先走审批流，批了才能拜访
  - INFORMATIONAL:     仅记录，不影响拜访
```

**业务方请选择 A 类与 B 类各自的默认 `constraint_class`**：

| 类型 | 默认 `constraint_class` |
| :--- | :--- |
| A. 拜访前置准入条件 | ☐ HARD_BLOCK / ☐ SOFT_WARNING / ☐ APPROVAL_REQUIRED / ☐ INFORMATIONAL |
| B. 拜访过程中的服务协议 | ☐ HARD_BLOCK / ☐ SOFT_WARNING / ☐ APPROVAL_REQUIRED / ☐ INFORMATIONAL |

### 2.4 override 政策（防止静默绕过）

如果允许在特定情况下跳过 `constraint_class == HARD_BLOCK` 的要求，**必须**同时记录：

```text
override_policy:
  approval_required: bool
  approval_request_id: str    # 必须关联 ApprovalRequest 对象
  approved_by: str
  approved_at: str            # ISO 8601
  reason: str                 # 必填 ≥ 10 字
  binding_trace: List[str]    # 证据链
```

**业务方请确认**：
- [ ] **同意**：override 必须满足以上 6 项字段才能放行；缺失任何一项则 SHACL 拒绝
- [ ] **不同意**（请说明）：____________________________

### 2.5 版本化与数据覆盖

- [ ] **需要版本化**（`version` 字段，historian 追踪）
- [ ] **不需要版本化**
- 当前业务方**是否有正式书面 SOP 文档**：
  - [ ] 是（请说明文档存放位置）：____________________________
  - [ ] 部分有
  - [ ] 全部无

### 2.6 与已有 GAP 的关系

| 关联 GAP | 业务方判断 |
| :--- | :--- |
| GAP-1 (Product / SKU) | A/B 类是否要求携带特定 SKU / 样品？☐ 是 ☐ 否 |
| GAP-3 (ApprovalRequest) | APPROVAL_REQUIRED 类的 override 是否复用到 GAP-3？☐ 是 ☐ 否 |
| GAP-5 (BusinessCostPerDay) | 违反 SOP 业务代价是否量化？☐ 是 ☐ 否 |

---

## 3. 业务方统一收件确认

- 业务方对 GAP-6 的所有答复具有**约束力**，将作为 v0.3 / 后续版本本体 v1.1 规范进入 `BUSINESS_APPROVED → FROZEN` 状态的依据。
- 任何后续变更须通过 v1.1 §8 的 `OntologyChangeRequest` 流程发起，**不得**绕过。
- 业务方对本沟通模板的回复，本身**不是**研究文档、设计文档或营销材料；仅作为本体冻结的事实证据归档至 `prism-ontology` 的 `provenance.ttl` 中。

**业务方最终签字：** __________________ **日期：** __________
**项目架构师确认：** __________________ **日期：** __________

---

## 4. 归档字段（仅由 Agent / 治理系统填写，业务方不要修改）

- `arbitration_round`: 3
- `arbitration_bundle_id`: __________
- `submitted_at`: __________
- `semantic_classification`: `A | B | C | D | E`
- `compiled_into_ontology_version`: __________
- `frozen_state_progression`: `EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN`
- `archival_path`: `prism-ontology/provenance/GAP-6-customer-operational-requirement-business-arbitration-v1.0.ttl`

---

## 5. Agent 侧当前真实状态（绝对准确）

```
GAP-1 (Product)               : BUSINESS_APPROVED
GAP-2 (Region/Zone)          : BUSINESS_APPROVED
GAP-3 (ApprovalRequest)      : PENDING_ESCALATION
GAP-4 (TimeDeviation)         : BUSINESS_APPROVED
GAP-5 (BusinessCostPerDay)    : PENDING_ESCALATION
GAP-6 (CustomerOpRequirement) : PENDING_ARBITRATION  ← 本轮
v0.3 冻结                     : 仍 HOLD
prism-ontology Phase 0        : 未启动
```

> 严格不做：
> - ❌ 自行将"SOP"概念升格为本体对象
> - ❌ 跨越 GAP-3 / GAP-5 业务方未完成答复
> - ❌ 启动 prism-ontology Phase 0 骨架

请下达下一步具体指令（如：等业务方答复 / 暂存 / 其他）。

---

## 6. 业务方答复记录（2026-08-24）

### 第 1 问（语义分类，必答）
- **业务方原文**：`E`
- **Agent 解读**：业务方选择第 5 个选项 = **"E 尚未确定"**
- **业务方签字**：本人
- **签字日期**：2026-08-24
- **裁决状态**：`BUSINESS_PENDING`
- **对 v0.3 冻结的影响**：
  - 业务方明确表示尚未确定"客户 SOP"具体属于哪一类
  - 按 v1.1 §5.3 + §8 硬性约束，v0.3 不能 `FROZEN`
  - 现有 svde/ 草稿保持 DEPRECATED 标记但仍可用
  - prism-ontology Phase 0 仍未启动

### 后续行动
- 业务方在内部明确"客户差异化 SOP"语义后，再发起 GAP-6 第 2 轮仲裁
- Agent 不推测含义、不自行裁决


---

## 7. 业务方明确关闭 GAP-6 记录（2026-08-24）

### 业务方表态
- **业务方原文**：`C`（在对话中确认"GAP-6 永不入本体"）
- **业务方补充**：业务方明确表示**永久不引入**"客户差异化操作要求"（SOP）相关本体对象
- **业务方签字**：本人
- **签字日期**：2026-08-24

### 永久关闭裁决
- **GAP-6 状态**：`PERMANENTLY_CLOSED`
- **理由**：业务方明确表态"永不入本体"
- **对 v0.3 的影响**：
  - v0.3 中**不引入**任何 SOP 相关对象（`SOPPolicy` / `CustomerSOPBinding` / `CustomerOpRequirement` 等）
  - v0.3 中**不引入** override policy / constraint_class / version 等 SOP 治理字段
  - SOP 相关需求由**外部 SOP 管理系统**承担，与销售拜访本体解耦

### 后续不再发起 GAP-6 仲裁
- 任何 SOP 需求变更须通过 v1.1 §8 `OntologyChangeRequest` 流程重新开启
- Agent 不得在 v0.3 / v0.4 / 后续版本中自行引入 SOP 本体对象

### v0.3 本体冻结前置条件已全部满足
- ✅ GAP-1 (Product)              : BUSINESS_APPROVED
- ✅ GAP-2 (Region/Zone)         : BUSINESS_APPROVED
- ✅ GAP-3 (ApprovalRequest)     : BUSINESS_APPROVED → 否
- ✅ GAP-4 (TimeDeviation)        : BUSINESS_APPROVED
- ✅ GAP-5 (BusinessCostPerDay)   : BUSINESS_APPROVED → 否
- ✅ GAP-6 (CustomerOpRequirement): PERMANENTLY_CLOSED

### 归档
- `archival_path`: `prism-ontology/provenance/GAP-6-customer-operational-requirement-business-arbitration-v1.0.ttl`
- `frozen_state_progression`: `EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN → PERMANENTLY_CLOSED (for GAP-6)`
