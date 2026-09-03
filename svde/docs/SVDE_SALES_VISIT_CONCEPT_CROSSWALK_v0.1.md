# SVDE Sales Visit — Concept Crosswalk v0.1
**Document ID:** SVDE-SALES-VISIT-CROSSWALK-V0.1
**Date:** 2026-08-24
**Status:** DRAFT — PENDING BUSINESS ARBITRATION
**Owner:** SVDE Core
**Scope:** Map every external concept into the Sales Visit ontology with explicit evidence level and freeze status.

---

## 0. Mapping Table (Primary Content)

| 外部概念 (External Concept) | 来源 (Source) | 业务含义 (Business Meaning) | 对应本体对象 (Ontology Object) | 证据等级 (Evidence Level) | 是否冻结 (Frozen?) | 备注 (Notes) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Visit Frequency** | [REF-001] OR Group; [REF-015] Kotler/Keller | 客户在周期内应被拜访的目标次数 | `CadenceSpec` | `DOMAIN_PRACTICE` | ✅ 冻结 | 不等于 `RouteStop`；不进入 `Customer` |
| **Min / Max Gap** (inter-visit interval) | [REF-001] OR Group; [REF-013] Johnston/Marshall | 同一客户相邻两次拜访的最小/最大间隔 | `CadenceSpec.min_interval_days` / `max_interval_days` | `DOMAIN_PRACTICE` | ✅ 冻结 | 属于周期层约束；**不**进 `RouteStop` |
| **Weekly Availability** | [REF-013] Johnston/Marshall; [REF-002] Salesforce | 客户允许被拜访的星期 + 时段 | `VisitPolicy.weekly_availability` + `time_window` | `PRODUCT_FACT` | ✅ 冻结 | 与锁定承诺共同构成 `hard_invariants` |
| **Service Goal / SLA Commitment** | [REF-002] Salesforce Field Service | 已承诺的拜访必须被如期履约，不可任意降级 | `Commitment.lifecycle_state == LOCKED` | `PRODUCT_FACT` | ✅ 冻结 | `must_not_override` 关系 |
| **Customer Tier (Strategic / Core / Development)** | [REF-011] Woodburn; [REF-018] Anderson/Stern | 客户商业价值分层 | `Customer.tier` | `DOMAIN_PRACTICE` | ✅ 冻结 | 影响 `ObjectiveProfile.business_value_objective` 权重 |
| **Territory Assignment** (region / rep / customer) | [REF-012] Zoltners; [REF-014] Shanahan; [REF-001] OR Group | 客户归属哪个代表负责 | `OwnershipPolicy` / `TerritoryAssignmentPlan` | `DOMAIN_PRACTICE` | ✅ 冻结 | **不**与单日路线折叠 |
| **Substitution Policy** (primary + substitute reps) | [REF-011] Woodburn; [REF-013] Johnston/Marshall | 替补代表关系 | `SubstitutionPolicy` | `DOMAIN_PRACTICE` | ✅ 冻结 | 独立于 `OwnershipPolicy` |
| **Eligibility Policy** (rep allowed customer tiers) | [REF-013] Johnston/Marshall | 代表资质筛选 | `EligibilityPolicy` | `DOMAIN_PRACTICE` | ✅ 冻结 | 独立于 `OwnershipPolicy` |
| **Resource Day Capacity** | [REF-002] Salesforce; [REF-001] OR Group | 代表某天可服务分钟数 | `ResourceDayProfile` | `PRODUCT_FACT` | ✅ 冻结 | 区别于 `Resource`（基线容量 vs 日级快照）|
| **Customer-Facing Time** (vs. travel time) | [REF-003] Nomadia | 实际有效面对客户的时间 | `ObjectiveProfile.distance_metric` (需 `customer_facing_time` 字段) | `EMPIRICAL_EVIDENCE` | ⏳ 待业务方确认加入 `ObjectiveProfile` | **必须**与 `distance_km` 分离 |
| **Route Stability / Disruption Cost** | [REF-004] Li & Sim 2016 | 滚动重排时的计划变动代价 | `ObjectiveProfile.stability_penalty` (v0.3 需补字段) | `MATHEMATICAL_THEORY` | ⏳ **v0.3 必须加** | 不可仅作为 Capability 内部 |
| **Travel Cost** (real-world matrix) | [REF-019] Dawson (system view) | 实际路网成本事实 | `TravelCostMatrix` | `EMPIRICAL_EVIDENCE` | ✅ 冻结 | 不可默认直线距离 |
| **Travel Cost Estimate** (on a route) | [REF-019] Dawson (system view) | 对某条路线的成本评估结果 | `TravelCostEstimate` | `EMPIRICAL_EVIDENCE` | ✅ 冻结 | 区分事实 vs 评估 |
| **Travel Cost Model** (estimator) | [REF-019] Dawson (system view) | 路网估算模型本身 | `TravelCostModel` | `DESIGN_INFERENCE` | ⏳ 待业务方确认 | 项目设计选择 |
| **Deferral Cost** (per customer per day) | [REF-001] OR Group | 未履约业务代价 | `DeferralPolicy.business_cost_per_day` | `DOMAIN_PRACTICE` | ✅ 冻结 | 必须显化 |
| **Approval Flow** (e.g. AP Route) | [GAP-3] 待业务方裁决 | 延期/大改动审批项 | 独立 `ApprovalRequest` 对象（候选） | 暂无 | ❓ 待业务方确认 | 是否进本体仍需裁决 |
| **TimeDeviation** (actual vs planned arrival) | [GAP-4] 待业务方裁决 | 实际 vs 计划时间偏差 | 独立对象（候选） | 暂无 | ❓ 待业务方确认 | 滚动重排需历史偏差数据 |
| **BusinessCostPerDayPerCustomer** | [GAP-5] 待业务方裁决 | 逾期业务代价量化 | `DeferralPolicy.business_cost_per_day` 已涵盖 | `DOMAIN_PRACTICE` | ✅ 冻结 | 已合并至 DeferralPolicy |
| **Product / SKU** (拜访货物) | [GAP-1] 待业务方裁决 | 拜访是否涉及商品交付 | 独立 `Product` 对象（候选） | 暂无 | ❓ 待业务方确认 | 视业务范围决定 |
| **Subsidiary / Region / Zone** | [GAP-2] 待业务方裁决 | 多层级销售组织管理 | 独立 `Subsidiary` 对象（候选） | 暂无 | ❓ 待业务方确认 | 多层级管理时需要 |
| **Sales Force Incentive / Quota** | [REF-012] Zoltners | 销售激励 | ❌ 拒绝 | `DOMAIN_PRACTICE` | ❌ **不冻结** | 与本体目标无关 |
| **Channel Hierarchy** (Kotler) | [REF-015] Kotler | 渠道层级 | ❌ 拒绝 | `DOMAIN_PRACTICE` | ❌ **不冻结** | 销售拜访本体不建模渠道结构 |
| **CRM Stage** (Discovery / Qualification) | [REF-011] Woodburn | 客户关系阶段 | ❌ 拒绝 | `DOMAIN_PRACTICE` | ❌ **不冻结** | 属于业务运营层，不是拜访本体 |
| **Column Generation / LNS / Tabu Search** | [REF-016] Ahuja et al. | 求解算法 | ❌ **拒绝进本体** | `MATHEMATICAL_THEORY` | ❌ **禁止** | 只能作为 `DailyRouteOptimization` Capability 内部实现 |
| **Big-M Penalty / Simplex / Shadow Price** | [REF-017] Hillier/Lieberman | LP/IP 内部概念 | ❌ **拒绝进本体** | `MATHEMATICAL_THEORY` | ❌ **禁止** | 只能作为 Capability 内部 |
| **Mega-Project CBA Methodology** | (Priemus, NEG) | 超大项目决策 | ❌ 拒绝 | `DESIGN_INFERENCE` | ❌ **不采用** | 与访销模式规模差异过大 |

---

## 1. Two Critical Crosswalks: Frozen v0.3 Changes (Pending Business OK)

### 1.1 `ObjectiveProfile` field changes (Required for v0.3)
Current v0.2 has only `distance_metric` (single). Evidence mandates:

| New field | Source | Evidence level | Reason |
| :--- | :--- | :--- | :--- |
| `customer_facing_time` (separate from `distance_km`) | [REF-003] Nomadia | `EMPIRICAL_EVIDENCE` | Distinct metric, optimization must consider both |
| `stability_penalty` | [REF-004] Li & Sim | `MATHEMATICAL_THEORY` | First-class objective in rolling re-plan |

→ **Business arbitration required**: confirm both fields are added before drafting v0.3.

### 1.2 `DeferralPolicy` completeness
Current v0.2 has `business_cost_per_day`. Evidence confirms this is sufficient, no extra field needed. ✅

---

## 2. Anti-Promotion Defense (locked)

These 8 categories **must never** be promoted into the frozen business ontology, regardless of evidence level:

| Forbidden concept | Why it cannot enter the frozen ontology |
| :--- | :--- |
| Algorithm primitives (Column Generation, LNS, Tabu) | Internal to `DailyRouteOptimization` |
| LP/IP math concepts (Simplex, Big-M, Shadow Price) | Internal to Capability solver |
| Vendor schema fields (Salesforce, CDSD) | Domain-specific, not universal |
| Channel hierarchy (Kotler 4P) | Not sales-visit domain |
| CRM lifecycle stage | Operational, not visit-planning |
| Sales force incentive/quota | Not related to visit planning |
| Mega-project CBA methodology | Wrong scale, wrong domain |
| Future theoretical papers' new "VRP-XYZ" variants | Solver implementation, not business object |

---

## 3. Open Business Arbitration (5 GAPs)

These must be resolved before ontology v0.3 can be drafted:

| GAP | Question | Decision-maker |
| :--- | :--- | :--- |
| GAP-1 | Does `Product` (SKU) enter ontology? | Business / Product |
| GAP-2 | Does `Subsidiary` / `Region` / `Zone` enter ontology? | Business / Org |
| GAP-3 | Does `ApprovalRequest` (AP Route) enter or stay as separate system? | Business / Process |
| GAP-4 | Does `TimeDeviation` enter as ontology object or as metric history? | Business / Operations |
| GAP-5 | Does `BusinessCostPerDayPerCustomer` stay embedded in `DeferralPolicy`? | **Confirmed yes** ✅ |

---

## 4. Evidence-Claim Decision Table

| Claim | Evidence | Confidence | Current ontology coverage | Action |
| :--- | :--- | :--- | :--- | :--- |
| Frequency > Distance | [REF-001] [REF-015] | High | Present (v0.2) | Keep |
| Locked commitment > Distance | [REF-002] [REF-013] | High | Present (v0.2) | Keep |
| Plan stability is first-class | [REF-004] | High | **Missing field** | **v0.3 add** |
| Customer-facing time ≠ distance | [REF-003] | High | **Missing field** | **v0.3 add** |
| 3-layer time-scale separation | [REF-014] [REF-012] [REF-005] | High | Present (v0.2) | Keep |
| Deferral cost quantified | [REF-001] | Medium | Present (v0.2) | Keep |
| Travel cost uses real network | [REF-019] (Dawson) | Medium | Present (v0.2 `TravelCostMatrix`) | Keep |
| Sales force incentive | [REF-012] | High | n/a | **Reject** (not visit-planning) |
| Channel hierarchy | [REF-015] | High | n/a | **Reject** (not visit domain) |
| Mega-project CBA | (Priemus NEG) | High | n/a | **Reject** (wrong scale) |

---

## 5. Open Questions

1. **GAP-1 ~ GAP-4**: please confirm whether each candidate concept enters the frozen ontology.
2. **`customer_facing_time` and `stability_penalty` in `ObjectiveProfile`**: please confirm addition to v0.3.
3. **`TravelCostModel`**: is it `DESIGN_INFERENCE` (project-internal) or should it be left out entirely?

Once business arbitration is complete, the next deliverable is **`SVDE_SALES_VISIT_ONTOLOGY_GAP_REVIEW_v0.1.md`** (formalize the 5 GAPs) → then v0.3 ontology revision draft.

请下达下一步具体指令：
- A. 等业务方裁决 5 个 GAP 后再继续
- B. 立即生成 `ONTOLOGY_GAP_REVIEW_v0.1.md` 把 GAP 正式化
- C. 同步起草 v0.3 本体（不推荐，GAP 还没裁决）