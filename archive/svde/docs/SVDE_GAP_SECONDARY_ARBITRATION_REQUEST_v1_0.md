# SVDE Sales Visit — GAP-3 / GAP-5 业务方二次裁决沟通
**Document ID:** SVDE-GAP-SECONDARY-ARBITRATION-REQUEST-V1.0
**Date:** 2026-08-24
**Status:** TEMPLATE — WAITING FOR BUSINESS OWNER
**Recipient:** Business Owner (Sales Visit domain) + IT Architect
**Purpose:** Re-clarify and collect binary arbitration on GAP-3 (`ApprovalRequest`) and GAP-5 (`BusinessCostPerDayPerCustomer`).
**Note:** GAP-1, GAP-2, GAP-4 already received clear answers and will not be re-asked.

---

## 0. 沟通原则（与 v1.0 一致）

- 本文档**不是**产品需求 / 业务变更 / 内部审查。
- 本文档**仅**用于业务方在 GAP-3 / GAP-5 上作出 binary 决定（是 / 否 / 推迟）。
- 业务方回复请**逐条**确认（**是 / 否 / 推迟**），不写开放意见——开放意见由另外的变更请求（CR）流程处理。
- 业务方对任意一条仍未明确勾选，**整个 v0.3 冻结流程继续 hold**，这是 v1.1 §5.3 的硬性约束。

---

## 1. GAP-3 二次澄清

### 1.1 业务问题（精确复述）
"延期 / 大改动 / 锁定释放"等是否进入销售拜访本体作为 `ApprovalRequest` 对象？

### 1.2 三个具体场景（业务方请逐条勾选哪些需要进入本体）

#### 场景 3-A：拜访延期审批
当一个 `PlannedVisit` 计划被推迟，**是否需要**业务主管在本体组件内审批？

- [ ] 需要进入本体（建模 `ApprovalRequest`，生命周期 `PROPOSED → APPROVED → LOCKED`）
- [ ] 不需要进入本体（由外部 ERP/OA 系统审批）
- [ ] 暂不明确，推迟裁决

#### 场景 3-B：临时大改路线审批
当 `RoutePlan` 因紧急事件需要大改（不是局部 2-opt 重排），**是否需要**业务主管在本体组件内审批？

- [ ] 需要进入本体
- [ ] 不需要进入本体
- [ ] 暂不明确，推迟裁决

#### 场景 3-C：锁定承诺释放审批
当 `Commitment.lifecycle_state == LOCKED` 的承诺需要释放或延期（如客户主动取消），**是否需要**业务主管在本体组件内审批？

- [ ] 需要进入本体
- [ ] 不需要进入本体
- [ ] 暂不明确，推迟裁决

### 1.3 业务方总答复（请勾选）
- [ ] **是** — `ApprovalRequest` 作为本体对象，统一支持 3-A / 3-B / 3-C（按业务方勾选的具体场景建模）
- [ ] **否** — 三类审批全部由外部系统承担，本体仅暴露 `requires_approval` 标志位，不建模审批流
- [ ] **推迟裁决** — 本期不纳入 v0.3，下一变更请求再处理

**业务方补充说明（如选"是"，请写明具体场景）：** ____________________________________________

**业务方签字：** __________________ **日期：** __________

---

## 2. GAP-5 二次澄清

### 2.1 业务问题（精确复述）
"业务代价（`BusinessCostPerDayPerCustomer`）"是否在 `DeferralPolicy` 内作为强制 / 可选 / 暂不引入字段？

### 2.2 三个具体场景（业务方请逐条勾选）

#### 场景 5-A：客户业务代价数据当前覆盖率
**业务方**对"延期业务代价"数据当前覆盖：

- [ ] 已有明确可量化数据（按天 / 按次 / 按合同条款）→ 选 **是**（强制字段）
- [ ] 部分客户有，部分为空 → 选 **否**（可选字段）
- [ ] 尚未开始量化任何客户的延期代价 → 选 **推迟**（v0.3 不引入此字段）

#### 场景 5-B：缺失代价字段时的系统行为
**业务方**期望缺失 `business_cost_per_day` 字段时：

- [ ] 缺失即硬约束违反 → SHACL 拒绝、决策器无法运行（配合 5-A "是" 选择）
- [ ] 缺失仅作 warning，可继续计算 → 配合 5-A "否" 选择
- [ ] 暂不明确 → 配合 5-A "推迟" 选择

#### 场景 5-C：行业普遍量化模型
**业务方**倾向于：

- [ ] 客单价损失模型（按客户日均价值估算）
- [ ] 合同违约赔偿（按合同条款查找）
- [ ] 综合模型（按客户分级 + 合同条款 + 历史价值）
- [ ] 暂不明确 / 暂不引入

### 2.3 业务方总答复（请勾选）
- [ ] **是** — `BusinessCostPerDayPerCustomer` 作为 `DeferralPolicy` 的强制字段，缺失即 SHACL 拒绝
- [ ] **否** — 作为可选字段，缺失仅 warning，可继续计算
- [ ] **推迟裁决** — 本期不纳入 v0.3，下一变更请求再处理

**业务方补充说明（如选"是"，请写明量化模型偏好）：** ____________________________________________

**业务方签字：** __________________ **日期：** __________

---

## 3. 业务方统一收件确认

- 业务方对 GAP-3 / GAP-5 的答复具有**约束力**，将作为 v0.3 本体 v1.1 规范进入 `BUSINESS_APPROVED → FROZEN` 状态的依据。
- 任何后续变更须通过 v1.1 §8 的 `OntologyChangeRequest` 流程发起，**不得**绕过。
- 业务方对本沟通模板的回复，本身**不是**研究文档、设计文档或营销材料；仅作为本体 v0.3 冻结的事实证据归档至 `prism-ontology` 的 `provenance.ttl` 中。

**业务方最终签字：** __________________ **日期：** __________
**项目架构师确认：** __________________ **日期：** __________

---

## 4. 归档字段（仅由 Agent / 治理系统填写，业务方不要修改）

- `arbitration_round`: 2
- `arbitration_bundle_id`: __________
- `submitted_at`: __________
- `compiled_into_ontology_version`: __________
- `frozen_state_progression`: `EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN`
- `archival_path`: `prism-ontology/provenance/GAP-3-and-5-secondary-business-arbitration-v1.0.ttl`


---

## 8. 业务方第 1 轮快速答复记录（2026-08-24）

### GAP-3 答复
- **业务方原文**：`1`
- **Agent 解读**：业务方勾选 GAP-3 第 1 个选项 = **"否"**（不走本体 `ApprovalRequest`，走 SOP 流程）
- **业务方签字**：本人（业务方）
- **签字日期**：2026-08-24
- **裁决状态**：`BUSINESS_APPROVED` → v0.3 不引入 `ApprovalRequest` 对象
- **关联影响**：
  - GAP-5（业务代价）继续 PENDING
  - GAP-6（客户差异化操作要求）若选 A/B 仍可包含 override_policy 字段

### GAP-5 / GAP-6 状态
- GAP-5 仍 PENDING（待答复"是/否/推迟"）
- GAP-6 仍 PENDING（待答复 A/B/C/D/E）

### Agent 承诺
- v0.3 冻结仍 hold，等 GAP-5 + GAP-6 完成答复
- prism-ontology Phase 0 仍未启动
- 现有 svde/ 草稿保持 DEPRECATED 但可用

---

归档路径：`prism-ontology/provenance/GAP-3-and-5-secondary-business-arbitration-v1.0.ttl`


---

## 9. 业务方第 2 轮快速答复记录（2026-08-24）

### GAP-5 答复
- **业务方原文**：`否`
- **Agent 解读**：业务方选择 GAP-5 第 2 个选项 = **"否"**（`BusinessCostPerDayPerCustomer` 作为可选字段，缺失仅 warning）
- **业务方签字**：本人
- **签字日期**：2026-08-24
- **裁决状态**：`BUSINESS_APPROVED` → v0.3 中 `DeferralPolicy.business_cost_per_day` 为可选字段

### GAP-6 答复
- **业务方原文**：`E`
- **Agent 解读**：业务方选择 GAP-6 第 5 个选项 = **"E 尚未确定"**
- **业务方签字**：本人
- **签字日期**：2026-08-24
- **裁决状态**：`BUSINESS_PENDING` → v0.3 不引入 SOP 相关本体对象

### 第 2 轮总答复记录
- **GAP-3** 答复 = 否 → `BUSINESS_APPROVED`
- **GAP-5** 答复 = 否 → `BUSINESS_APPROVED`
- **GAP-6** 答复 = E（尚未确定）→ `BUSINESS_PENDING`

### v0.3 本体冻结状态推进
- 已完成 GAP 业务方裁决：GAP-1 / GAP-2 / GAP-3 / GAP-4 / GAP-5
- 仍未裁决：GAP-6（业务方明确说"尚未确定"）
- 按 v1.1 §8 规范，v0.3 不能进入 `FROZEN` 状态
- 等 GAP-6 裁决前，v0.3 保持 `BUSINESS_APPROVED` 状态
