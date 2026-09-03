# SVDE Sales Visit — Concept Crosswalk v1.1
**Document ID:** SVDE-CONCEPT-CROSSWALK-V1.1
**Date:** 2026-08-24
**Status:** STRICT v1.1 §5.4 COMPLIANT (after Evidence Bundle v1.1)
**Source**: SVDE_EVIDENCE_BUNDLE_v1.1 (REF-001 ~ REF-020)

---

## 0. Mapping Table (per v1.1 §5.4)

| External Concept | Source(s) | Business Meaning | Maps to v0.3 Object | Evidence Level | Frozen? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Visit Frequency | [REF-001] [REF-017] | 周期内目标拜访次数 | `CadenceSpec` | `DOMAIN_PRACTICE` + `PRODUCT_FACT` | ✅ | visits_per_week, tolerance_days |
| Week rhythm | [REF-PTV-001] | 客户按周次拜访的节奏 | `CadenceSpec.weekly_availability` | `PRODUCT_FACT` | ✅ | weekly weekday patterns |
| Service Goal / SLA | [REF-002] | 已承诺的拜访必须被如期履约 | `Commitment.lifecycle_state == LOCKED` | `PRODUCT_FACT` | ✅ | hard constraint |
| Substitutability | [REF-008] [REF-006] | 替补代表关系 | `SubstitutionPolicy` | `DOMAIN_PRACTICE` | ✅ | primary + substitute reps |
| Eligibility | [REF-008] | 代表资质筛选 | `EligibilityPolicy` | `DOMAIN_PRACTICE` | ✅ | rep capability matching |
| Fixed territory center | [REF-016] [REF-005] | 客户归属锁定 | `OwnershipPolicy.is_locked` | `PRODUCT_FACT` + `DOMAIN_PRACTICE` | ✅ | rep-customer binding |
| Tour period estimate | [REF-019] | 路线时长估算（非求解） | `DISTANCE_TIME_TRADEOFF` capability | `PRODUCT_FACT` | ⚠️ PLANNED | estimator ≠ solver |
| Time window | [REF-018] [REF-002] | 拜访时窗约束 | `Commitment.time_window` | `PRODUCT_FACT` | ✅ | hard constraint |
| Customer-facing time | [REF-003] | 实际有效面对客户时间 | `ObjectiveProfile.distance_metric` (separate field) | `PRODUCT_FACT` | ✅ | distinct from distance |
| Disruption cost | [REF-004] | 计划变动代价 | `ObjectiveProfile.stability_penalty` | `MATHEMATICAL_THEORY` | ✅ | first-class objective |
| Channel hierarchy | [REF-010] [REF-011] | 营销渠道层级 | (REJECTED) | `DOMAIN_PRACTICE` + `EMPIRICAL_EVIDENCE` | ❌ | per v0.3 §3 anti-promotion |
| Sales incentive | [REF-007] | 销售激励 | (REJECTED) | `DOMAIN_PRACTICE` | ❌ | per v0.3 §3 anti-promotion |
| CRM lifecycle | [REF-006] | 客户关系阶段 | (REJECTED) | `DOMAIN_PRACTICE` | ❌ | operational layer |
| LP/IP / VRP math | [REF-013] [REF-014] | 求解算法 | (REFERENCE ONLY) | `MATHEMATICAL_THEORY` | ⚠️ | Capability internal only |
| Mega-project CBA | [REF-012] | 大型项目决策 | (REJECTED) | `DESIGN_INFERENCE` | ❌ | wrong scale |
| CDSD vendor format | [REF-020] | 厂商数据格式 | (REJECTED) | `PRODUCT_FACT` | ❌ | vendor-specific |
| Systems thinking | [REF-015] | 系统思维 | `ObjectiveProfile.lexicographic_levels` | `DESIGN_INFERENCE` | ✅ | design rationale |

---

## 1. Anti-Promotion Defense (per v0.3 §3)

| Refused Promotion | Source | v0.3 §3 Reason | Status |
| :--- | :--- | :--- | :--- |
| Channel hierarchy | [REF-010] [REF-011] | Different domain | ❌ NOT IN v0.3 |
| Sales force incentive | [REF-007] | Different scope | ❌ NOT IN v0.3 |
| CRM lifecycle | [REF-006] | Operational layer | ❌ NOT IN v0.3 |
| Algorithm concept (Column Gen, LNS, Tabu, Simplex, Big-M) | [REF-013] [REF-014] | Internal to Capability | ❌ NOT IN v0.3 |
| Mega-project CBA | [REF-012] | Wrong scale/domain | ❌ NOT IN v0.3 |
| CDSD vendor format | [REF-020] | Vendor-specific | ❌ NOT IN v0.3 |
| SOP-related object | GAP-6 PERMANENTLY CLOSED | Business owner closure | ❌ NEVER |

---

## 2. Claim × Evidence Audit

| Claim | Supported by | Confidence | Current v0.3 Coverage | Action |
| :--- | :--- | :--- | :--- | :--- |
| Coverage > Distance | [REF-001] [REF-017] | High | `PR-001` (PR-001) | Keep |
| Locked commitment is hard | [REF-002] [REF-018] | High | `Commitment.lifecycle_state == LOCKED` | Keep |
| Frequency / week rhythm modeling | [REF-001] [REF-PTV-001] | High | `CadenceSpec` | Keep |
| Substitution pattern | [REF-008] [REF-006] | High | `SubstitutionPolicy` | Keep |
| Territory is independent layer | [REF-016] [REF-005] [REF-007] [REF-009] | High | `TERRITORY_ALIGNMENT` decision layer | Keep |
| Customer-facing time ≠ travel time | [REF-003] | High | `ObjectiveProfile.distance_metric` (separate field) | Keep |
| Disruption cost is first-class | [REF-004] | Medium-High | `ObjectiveProfile.stability_penalty` | Keep |
| Channel hierarchy | [REF-010] [REF-011] | High (but REJECTED) | NOT IN v0.3 | Per §3 anti-promotion |
| Sales incentive | [REF-007] | High (but REJECTED) | NOT IN v0.3 | Per §3 anti-promotion |
| Mega-project CBA | [REF-012] | High (but REJECTED) | NOT IN v0.3 | Wrong scale |

---

## 3. Open Questions for v0.3 (resolved by 6 GAP arbitrations)

All 6 GAPs previously raised have been adjudicated:
- GAP-1: BUSINESS_APPROVED (Product in v0.3)
- GAP-2: BUSINESS_APPROVED (Region in v0.3)
- GAP-3: BUSINESS_APPROVED → NO (走 SOP)
- GAP-4: BUSINESS_APPROVED
- GAP-5: BUSINESS_APPROVED → NO (optional field)
- GAP-6: PERMANENTLY CLOSED (SOP never enters)
- GAP-7: BUSINESS_APPROVED → NO (no visitSplits)
- GAP-8: DEFERRED (CustomerGroup pending)
