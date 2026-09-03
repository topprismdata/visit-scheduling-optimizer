# SVDE Sales Visit — GAP-7 / GAP-8 业务方裁决沟通
**Document ID:** SVDE-GAP7-8-ARBITRATION-REQUEST-V1.0
**Date:** 2026-08-24
**Status:** TEMPLATE — WAITING FOR BUSINESS OWNER
**Recipient:** Business Owner (Sales Visit domain)
**Source**: PTV xCluster/xTerritory Evidence Bundle [REF-PTV-001 ~ REF-PTV-006]

---

## 0. 沟通原则

- 只勾选"是 / 否 / 推迟"。
- 证据来源是 PTV xServer 产品手册（`PRODUCT_FACT` 级）。
- 不勾选 = v0.3 维持现状不修改。

---

## 1. GAP-7：`visitSplits`（一天内多次拜访同一客户）

### 背景
PTV xCluster 支持把一次拜访拆成同一天内的多个片段（如上午样品配送 + 下午订单确认）。v0.3 当前不支持。

### 场景
客户 A 需要一天内被拜访 2 次：上午送样品（30 分钟），下午签合同（45 分钟）。

### 业务方勾选

- [ ] **是** — 引入 `VisitSplit` 对象，支持一天内多次拜访
- [ ] **否** — 不支持，一天最多拜访一次
- [ ] **推迟**

**签字：** __________ **日期：** __________

---

## 2. GAP-8：`CustomerGroup`（预定义客户组）

### 背景
PTV xTerritory 支持把多个 location 预定义为同一组，强制它们分配到同一辖区。v0.3 当前无客户组概念。

### 场景
连锁药店 A 有 5 家门店，业务要求必须由同一个销售代表负责全部 5 家。

### 业务方勾选

- [ ] **是** — 引入 `CustomerGroup` 对象，支持"必须同辖区"约束
- [ ] **否** — 不支持客户组，每个客户独立分配
- [ ] **推迟**

**签字：** __________ **日期：** __________

---

## 归档字段

- `arbitration_round`: 4
- `submitted_at`: 2026-08-24
- `evidence_source`: PTV xCluster/xTerritory Manual [REF-PTV-001 ~ 006]
- `archival_path`: prism-ontology/provenance/GAP-7-8-ptv-arbitration-v1.0.ttl


---

## 业务方答复记录（2026-08-24）

### GAP-7 (visitSplits) 答复
- **业务方原文**：`B`
- **解读**：**否** — 不引入 `VisitSplit` 对象，一天最多拜访同一客户一次
- **签字**：本人（业务方）
- **日期**：2026-08-24
- **状态**：`BUSINESS_APPROVED → 否`

### GAP-8 (CustomerGroup) 答复
- **业务方原文**：`C`
- **解读**：**推迟** — 本期不处理，下一变更请求再裁决
- **签字**：本人（业务方）
- **日期**：2026-08-24
- **状态**：`BUSINESS_PENDING（DEFERRED）`

### v0.3 影响
- GAP-7 = 否 → v0.3 不引入 VisitSplit，无需修改
- GAP-8 = 推迟 → v0.3 不引入 CustomerGroup，待未来 OntologyChangeRequest
- **v0.3 FROZEN 状态不受影响**（两个 GAP 均不新增对象）
