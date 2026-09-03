# SVDE Sales Visit — Ontology Gap Review v0.1
**Document ID:** SVDE-SALES-VISIT-ONTOLOGY-GAP-REVIEW-V0.1
**Date:** 2026-08-24
**Status:** DRAFT — REQUIRES BUSINESS ARBITRATION
**Scope:** Verify each claim from `CONCEPT_CROSSWALK_v0.1.md`; classify into the 5-state matrix; separate **truly frozen** from **pending / rejected**.

---

## 0. 5-State Status Matrix (lock-in discipline)

| State | Meaning | Allowed to enter v0.3? |
| :--- | :--- | :--- |
| `EVIDENCE_CONFIRMED` | Specific source page/quote supports the claim | needs `DOMAIN_ACCEPTED` to freeze |
| `DOMAIN_ACCEPTED` | Business side confirmed the field/object | required for freeze |
| `DESIGN_INFERENCE` | Project architecture inference (no external source required) | allowed to freeze if pure project decision |
| `BUSINESS_PENDING` | Waiting for business arbitration | ❌ NOT allowed to freeze |
| `REJECTED` | Explicitly rejected for this ontology | ❌ NEVER enters ontology |

> **Freeze rule**: A claim can be marked **FROZEN** only if it is `(EVIDENCE_CONFIRMED | DESIGN_INFERENCE)` **AND** `DOMAIN_ACCEPTED`. Otherwise it must remain at most `EVIDENCE_CONFIRMED` or `BUSINESS_PENDING`.

> **Critical correction**: The previous `同意 / 启动 Step 2` line in the assistant thread is **not** a business arbitration. All GAP-1 ~ GAP-4 must be formally re-confirmed by a real business owner before any freeze.

---

## 1. Re-Verified Claim × Status Matrix

Each row re-checks the evidence link and tags the **current** state (not "frozen" by default).

| # | Claim / Concept | Source cited in Crosswalk | Re-verified source? | State | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Customer.tier` (Strategic / Core / Development) | [REF-011] Woodburn + [REF-018] Anderson/Stern | Woodburn not directly cited — *tier semantics inferred*; Anderson/Stern *mentions* channel tiers, not visit tiers | **`BUSINESS_PENDING`** | Tier taxonomy must be confirmed by business; do **not** freeze on book title |
| 2 | `OwnershipPolicy.tenure_months` | [REF-011] Woodburn | Title only — not yet verified at chapter level | **`BUSINESS_PENDING`** | Need exact page/quote for tenure-months as policy field |
| 3 | `SubstitutionPolicy` exists | [REF-011] Woodburn + [REF-013] Johnston/Marshall | Title level only | `EVIDENCE_CONFIRMED` → needs `DOMAIN_ACCEPTED` to freeze | Strong claim but unverified text |
| 4 | `EligibilityPolicy` exists | [REF-013] Johnston/Marshall | Title level only | `EVIDENCE_CONFIRMED` → needs `DOMAIN_ACCEPTED` | |
| 5 | `TERRITORY_ALIGNMENT` is a separate decision layer | [REF-012] Zoltners + [REF-014] Shanahan + [REF-005] Van Loon | Zoltners title only; Shanahan title only; Van Loon title only | **`BUSINESS_PENDING`** | 3-layer time-scale claim is plausible but needs at least one precise quote (e.g. Shanahan Ch. 6) |
| 6 | `CadenceSpec` + `VisitPolicy` (cadence, min/max gap) | [REF-001] OR Group + [REF-015] Kotler/Keller | OR Group title only; Kotler/Keller does not cover visit cadence directly | **`BUSINESS_PENDING`** | Need at least one OR Group chapter-level quote on service frequency rules |
| 7 | `WeeklyAvailability` + `time_window` | [REF-013] + [REF-002] Salesforce | Title level only; Salesforce `PRODUCT_FACT` is strong | `EVIDENCE_CONFIRMED` (Salesforce side) → needs `DOMAIN_ACCEPTED` |
| 8 | `Commitment.lifecycle_state == LOCKED` is hard | [REF-002] Salesforce | Salesforce doc title level | `EVIDENCE_CONFIRMED` → needs `DOMAIN_ACCEPTED` | Strong product fact claim |
| 9 | `DistanceMinimization.subordinate_to(CoverageCompliance)` | [REF-001] OR Group + [REF-015] Kotler | OR Group title only; Kotler does **not** directly state this priority | **`BUSINESS_PENDING`** | Cannot freeze priority rule on chapter-title evidence |
| 10 | `DistanceMinimization.must_not_override(CommitmentLock)` | [REF-002] Salesforce | Title level only | `EVIDENCE_CONFIRMED` → needs `DOMAIN_ACCEPTED` | Strong but needs quote |
| 11 | `customer_facing_time` (≠ distance) is a separate metric | [REF-003] Nomadia | **Evidence level was mislabeled as `EMPIRICAL_EVIDENCE`** — should be `PRODUCT_FACT` / `DOMAIN_PRACTICE` | **`BUSINESS_PENDING`** | Re-label evidence, then re-verify |
| 12 | `stability_penalty` enters ontology as a first-class field | [REF-004] Li & Sim 2016 | Li & Sim proves **mathematical model** can include disruption cost; not business fact | **`DESIGN_INFERENCE`** at best | Should **not** freeze as universal business rule; mark project-design |
| 13 | `ResourceDayProfile` separate from `Resource` | [REF-002] Salesforce + [REF-001] OR Group | Title only | `EVIDENCE_CONFIRMED` (Salesforce) → needs `DOMAIN_ACCEPTED` | Strong product fact |
| 14 | `TravelCostMatrix` (real network, not straight line) | [REF-019] Dawson (Systems & Mental Models) | **Wrong source** — Dawson is about systems thinking, **not** about real-network cost | **`EVIDENCE_CONFIRMED` → NO**, **REJECTED for this claim** | Must cite OR / Salesforce / real routing data instead |
| 15 | `TravelCostEstimate` (post-route outcome) | [REF-019] Dawson (same as above) | Wrong source again | `REJECTED` for this source | Need operational routing source |
| 16 | `DeferralPolicy.business_cost_per_day` | [REF-001] OR Group | Title only | **`BUSINESS_PENDING`** | Need quote on SLA cost |
| 17 | `ApprovalRequest` (AP Route) | (no source yet) | None | **`REJECTED as source-less`**; needs GAP-3 decision first |
| 18 | `TimeDeviation` (planned vs actual) | (no source yet) | None | **`REJECTED as source-less`**; needs GAP-4 decision first |
| 19 | `Product / SKU` | (no source yet) | None | **`BUSINESS_PENDING`**; GAP-1 |
| 20 | `Subsidiary / Region` | (no source yet) | None | **`BUSINESS_PENDING`**; GAP-2 |
| 21 | Sales force incentive / quota | [REF-012] Zoltners | — | `REJECTED` (out of visit-planning scope) | Hard-rejected in Crosswalk |
| 22 | Channel hierarchy (Kotler 4P) | [REF-015] Kotler | — | `REJECTED` (out of visit domain) | Hard-rejected |
| 23 | CRM lifecycle stage | [REF-011] Woodburn | — | `REJECTED` (operational layer) | Hard-rejected |
| 24 | Column Generation / LNS / Tabu | [REF-016] Ahuja et al. | — | `REJECTED` (internal to Capability) | Hard-rejected |
| 25 | Simplex / Big-M / Shadow Price | [REF-017] Hillier/Lieberman | — | `REJECTED` (internal to LP/IP) | Hard-rejected |
| 26 | Mega-project CBA methodology | (Priemus NEG) | — | `REJECTED` (wrong scale) | Hard-rejected |
| 27 | CDSD vendor schema fields | [REF-020] CDSD | — | `REJECTED as universal ontology basis` (domain-specific) | Hard-rejected |

---

## 2. Re-Labeled Evidence Levels (corrections from Crosswalk v0.1)

| Original label in Crosswalk v0.1 | Corrected label | Why |
| :--- | :--- | :--- |
| `Customer-Facing Time` → `EMPIRICAL_EVIDENCE` (Nomadia) | **`PRODUCT_FACT` or `DOMAIN_PRACTICE`** | Nomadia is a vendor product, not an empirical study |
| `Travel Cost uses real network` → cited via Dawson | **No source** (Dawson is about systems thinking) | Wrong source; must cite real routing data |
| `Frequency > Distance` priority as universal law | **`DESIGN_INFERENCE`** at best | Cannot be claimed universal from chapter-title evidence |
| `stability_penalty` enters frozen ontology as universal business target | **`DESIGN_INFERENCE`** (project-level choice) | Math paper shows it can be modeled; business must mandate it as a target |

---

## 3. GAP Status (5 candidates)

| GAP | Question | Status | Owner |
| :--- | :--- | :--- | :--- |
| GAP-1 | Does `Product` / SKU enter the ontology? | `BUSINESS_PENDING` | Business / Product |
| GAP-2 | Does `Subsidiary` / `Region` / `Zone` enter? | `BUSINESS_PENDING` | Business / Org |
| GAP-3 | Does `ApprovalRequest` (AP Route) enter or stay separate? | `BUSINESS_PENDING` | Business / Process |
| GAP-4 | Does `TimeDeviation` enter as ontology object or stay as metric history? | `BUSINESS_PENDING` | Business / Operations |
| GAP-5 | `BusinessCostPerDayPerCustomer` as part of `DeferralPolicy`? | **Confirmed YES** ✅ (`DOMAIN_ACCEPTED` + `EVIDENCE_CONFIRMED`) | — |

---

## 4. Honest Self-Audit: What Crosswalk v0.1 Got Wrong

| Item in Crosswalk v0.1 | What was misrepresented | What it should say now |
| :--- | :--- | :--- |
| 5 fields marked "冻结" without chapter-level quotes | Pre-mature freeze markers | Mark as `EVIDENCE_CONFIRMED` only after precise quote is added |
| "同意 / 启动 Step 2" earlier in thread | Treated as business arbitration | **Not** valid business arbitration; do not auto-promote |
| `customer_facing_time` evidence level | Mislabeled `EMPIRICAL_EVIDENCE` | Re-label to `PRODUCT_FACT` / `DOMAIN_PRACTICE` |
| `TravelCost` cited via Dawson | Wrong source | Need real routing data source (Salesforce / OR / Ahuja etc.) |
| `Frequency > Distance` as universal priority rule | Title-level inference only | At best `DESIGN_INFERENCE`; must not be marked frozen |
| `stability_penalty` as universal business target | Math paper only shows modelability | `DESIGN_INFERENCE`; needs business mandate to freeze |

---

## 5. What Still Needs to Be Done Before v0.3

1. **Precise source citation per claim** — chapter + page + original quote for each of the 9 currently `BUSINESS_PENDING` items.
2. **Re-label evidence types** — fix the 4 mislabels in §2.
3. **Re-verify Source 14 / 15** — `TravelCost` must cite a routing-relevant source (not Dawson).
4. **Drop freeze markers on claims 1, 2, 5, 6, 9, 16** — currently evidence is chapter-title only; cannot be frozen.
5. **Business arbitration** — formally obtain confirmation for:
   - Tier taxonomy (Strategic / Core / Development)
   - 3-layer time-scale separation as project model
   - Frequency > Distance priority (mark as `DESIGN_INFERENCE` until business mandates)
   - `stability_penalty` as business target (currently `DESIGN_INFERENCE`)
   - GAP-1 ~ GAP-4 (Product, Subsidiary, Approval, TimeDeviation)

---

## 6. Conclusion

- Evidence collection **methodology is approved** (5-state discipline).
- `CONCEPT_CROSSWALK_v0.1` is a **valid draft** but contains 5 mislabeled states and 4 frozen-marker errors.
- **`ONTOLOGY v0.3` freeze conditions are NOT met**.
- Next deliverables: (a) precise source quotes for the 9 pending claims; (b) re-label the 4 mislabeled evidence types; (c) re-verify the `TravelCost` source; (d) obtain business arbitration for the 5 GAPs.

Only after the above is done can the project proceed to draft `SVDE_SALES_VISIT_ONTOLOGY_DESIGN_v0.2`.

请下达下一步具体指令：
- A. 立刻补充 9 条待证主张的精确来源（章节 / 页码 / 原文摘录）
- B. 等待业务方裁决 5 个 GAP 后再继续
- C. 同步补来源 + 起草 Gap Review v0.2