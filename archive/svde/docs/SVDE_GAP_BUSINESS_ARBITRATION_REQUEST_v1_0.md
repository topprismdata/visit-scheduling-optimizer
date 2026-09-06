# SVDE Sales Visit — GAP-1~GAP-5 业务方裁决沟通模板
**Document ID:** SVDE-GAP-BUSINESS-ARBITRATION-REQUEST-V1.0
**Date:** 2026-08-24
**Status:** TEMPLATE — WAITING FOR BUSINESS OWNER
**Recipient:** Business Owner (Sales Visit domain) + IT Architect
**Purpose:** Collect 5 binary arbitration decisions required before `prism-ontology` Phase 1 starts and SVDE ontology can be frozen at v0.3.

---

## 0. 模板使用说明（务必先读）

- 本文档**不是**产品需求 / 业务变更 / 内部审查。
- 本文档**仅**用于业务方在 5 个 GAP 上作出 binary 决定（纳入 / 不纳入）。任何未列入此模板的字段，**不在本次裁决范围**。
- 业务方回复请**逐条**确认（**是 / 否**），不写开放意见——开放意见由另外的变更请求（CR）流程处理。
- 业务方回复后，Agent 才能**根据回复**更新 ontology v0.3 草案，并执行 v1.1 规范的 5-state 生命周期 `BUSINESS_APPROVED → FROZEN` 流程。

---

## 1. GAP-1 — `Product` / SKU 是否进入销售拜访本体？

### 1.1 当前状态
- v0.3 本体草稿未包含 `Product` / `SKU` 对象。
- `[REF-018] Anderson/Stern` 提到渠道层级，但**未**证明销售拜访本体必须建模 SKU。
- `[GAP-1]` 在 `SVDE_SALES_VISIT_ONTOLOGY_GAP_REVIEW_v0.1.md` 标为 `BUSINESS_PENDING`。

### 1.2 业务问题
销售拜访是否包含商品交付 / 补退货 / 库存流转？如果是，拜访语义与"商品行"语义会折叠到同一对象，违反 v1.1 §4.2 不可折叠规则。

### 1.3 业务方答复（请勾选）
- [ ] **是** — `Product` / SKU 进入销售拜访本体，作为 `Customer` 的可选关联对象（可能为未来 SKU 拜访记录留位）。
- [ ] **否** — `Product` / SKU 不进入销售拜访本体；保持销售拜访与商品库存解耦。
- [ ] **推迟裁决** — 本期不纳入 v0.3，下一变更请求再处理。

**业务方签字：** __________________ **日期：** __________

---

## 2. GAP-2 — `Subsidiary` / `Region` / `Zone` 是否进入销售拜访本体？

### 2.1 当前状态
- v0.3 本体草稿未包含 `Subsidiary` / `Region` / `Zone` 对象。
- `[REF-014] Shanahan` 与 `[REF-005] Van Loon` 提到三层时间尺度（战略 / 战术 / 操作）分离，但**未**证明"销售拜访本体必须包含子公司层级"。
- `[GAP-2]` 标为 `BUSINESS_PENDING`。

### 2.2 业务问题
销售组织是否跨子公司 / 跨区域？若跨，拜访分配 / 频次 / 锁定承诺可能受子公司政策影响。

### 2.3 业务方答复（请勾选）
- [ ] **是** — `Subsidiary` / `Region` 进入本体，作为 `OwnershipPolicy` 与 `EligibilityPolicy` 的层级维度。
- [ ] **否** — 销售拜访本体保持单一层级；子公司信息视为外部系统参数。
- [ ] **推迟裁决** — 本期不纳入 v0.3，下一变更请求再处理。

**业务方签字：** __________________ **日期：** __________

---

## 3. GAP-3 — `ApprovalRequest` (AP Route) 是否进入销售拜访本体？

### 3.1 当前状态
- v0.3 本体草稿未包含 `ApprovalRequest` 对象。
- `DeferralPolicy.requires_approval` 字段暗示"存在审批"，但未具体建模"审批流"本体对象。
- `[GAP-3]` 标为 `BUSINESS_PENDING`。

### 3.2 业务问题
延期 / 大改动是否需要进入本体的 `ApprovalRequest` 对象？还是保持与外层审批系统集成（OA / BPM）？

### 3.3 业务方答复（请勾选）
- [ ] **是** — `ApprovalRequest` 作为本体对象，承载 `deferral / route_change / commitment_release` 三类请求的生命周期（`PROPOSED → APPROVED → LOCKED`）。
- [ ] **否** — 审批保持外部系统集成；本体不建模审批。
- [ ] **推迟裁决** — 本期不纳入 v0.3，下一变更请求再处理。

**业务方签字：** __________________ **日期：** __________

---

## 4. GAP-4 — `TimeDeviation`（实际 vs 计划时间偏差）是否进入销售拜访本体？

### 4.1 当前状态
- v0.3 本体草稿未包含 `TimeDeviation` 对象。
- `[REF-001] OR Group` 提到 SLA 与频次跟踪，但**未**具体说明"实际 vs 计划时间偏差"是本体对象还是指标历史。
- `[GAP-4]` 标为 `BUSINESS_PENDING`。

### 4.2 业务问题
滚动重排（`ROLLING_REPLAN`）需要"实际 vs 计划时间偏差"作为输入信号。该信号应该是本体对象（带生命周期）还是仅作为运行时度量历史？

### 4.3 业务方答复（请勾选）
- [ ] **是** — `TimeDeviation` 进入本体，作为 `ActualVisit` 的衍生对象（记录 `actual_arrival - planned_arrival` 与 `source_signal`）。
- [ ] **否** — `TimeDeviation` 保留为运行时度量历史（数据仓库），不进本体。
- [ ] **推迟裁决** — 本期不纳入 v0.3，下一变更请求再处理。

**业务方签字：** __________________ **日期：** __________

---

## 5. GAP-5 — `BusinessCostPerDayPerCustomer` 是否在 `DeferralPolicy` 内？

### 5.1 当前状态
- v0.2 草稿在 `DeferralPolicy` 中已有 `business_cost_per_day` 字段。
- `SVDE_SALES_VISIT_CONCEPT_CROSSWALK_v0.1.md` 中 [REF-001] 提到 SLA 代价，证据等级 `DOMAIN_PRACTICE`。
- v0.2 / Crosswalk 已经隐式确认该字段应嵌入 `DeferralPolicy`。

### 5.2 业务问题
延期业务代价是否**必须**作为 `DeferralPolicy` 的强制字段？

### 5.3 业务方答复（请勾选）
- [ ] **是** — `BusinessCostPerDayPerCustomer` 强制嵌入 `DeferralPolicy`，所有延期计算必须包含此字段。
- [ ] **否** — 该字段可选；延期计算可不使用业务代价。
- [ ] **推迟裁决** — 本期不纳入 v0.3，下一变更请求再处理。

**业务方签字：** __________________ **日期：** __________

---

## 6. 业务方统一收件确认

- 业务方对以上 5 个 GAP 的所有答复具有**约束力**，将作为 v0.3 本体 v1.1 规范进入 `BUSINESS_APPROVED → FROZEN` 状态的依据。
- 任何后续变更须通过 v1.1 §8 的 `OntologyChangeRequest` 流程发起，**不得**绕过。
- 业务方对本沟通模板的回复，本身**不是**研究文档、设计文档或营销材料；仅作为本体 v0.3 冻结的事实证据归档至 `prism-ontology` 的 `provenance.ttl` 中。

**业务方最终签字：** __________________ **日期：** __________
**项目架构师确认：** __________________ **日期：** __________

---

## 7. 归档字段（仅由 Agent / 治理系统填写，业务方不要修改）

- `arbitration_bundle_id`: __________
- `submitted_at`: __________
- `compiled_into_ontology_version`: __________
- `frozen_state`: `EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → BUSINESS_APPROVED → FROZEN`
- `archival_path`: `prism-ontology/provenance/GAP-1..5-business-arbitration-v1.0.ttl`
