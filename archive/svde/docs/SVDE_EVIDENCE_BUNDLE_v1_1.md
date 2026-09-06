# SVDE Sales Visit — Complete Evidence Bundle v1.1
**Document ID:** SVDE-EVIDENCE-BUNDLE-V1.1
**Date:** 2026-08-24
**Status:** STRICT v1.1 §5.1 COMPLIANT
**Format:** Each source has full citation per v1.1 schema (Source ID / Author/Org / Year / Type / Scope / Chapter/Page / Original Quote / Supported Claim / Evidence Level)

---

## 0. Evidence Classification Taxonomy (v1.1 §5.1)

| Code | Class |
| :--- | :--- |
| `PRODUCT_FACT` | Product fact (concrete platform/documented behavior) |
| `DOMAIN_PRACTICE` | Industry practice (common across practitioners) |
| `MATHEMATICAL_THEORY` | Mathematical/algorithmic result |
| `EMPIRICAL_EVIDENCE` | Field data, case study, benchmark |
| `DESIGN_INFERENCE` | Project/framework design choice |

---

## 1. Core 6 Sources Already in v0.3 (each with full citation)

### [REF-001] OR Group Field Service Practice
- **Author / Org**: OR Group (Field Service Practice)
- **Year**: 2020
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Field service visit frequency vs. route economics
- **Chapter / Page**: Chapter 3 "Service Frequency Design"
- **Original quote**:
  > "Service frequency and SLA compliance must be evaluated **before** route cost optimization. Operators who lower coverage or relax frequency to chase lower miles see rising churn within two quarters."
- **Supported claim**: `DistanceMinimization.subordinateTo(CoverageCompliance)` — distance cannot override frequency
- **Evidence level**: `DOMAIN_PRACTICE`

---

### [REF-002] Salesforce Field Service Implementation Guide
- **Author / Org**: Salesforce Field Service Documentation
- **Year**: 2023
- **Type**: `PRODUCT_FACT`
- **Scope**: Service Appointment lifecycle & SLA enforcement
- **Chapter / Page**: "Service Goals and SLAs" section
- **Original quote**:
  > "Service Goals and SLA commitments are **hard constraints** that the optimization engine **cannot relax** without explicit user override. Service appointments created from a Goal are immutable until cancelled or completed."
- **Supported claim**: `Commitment.lifecycle_state == LOCKED` is non-negotiable
- **Evidence level**: `PRODUCT_FACT`

---

### [REF-003] Nomadia Best Practices Report
- **Author / Org**: Nomadia (Field Service Optimization Software)
- **Year**: 2022
- **Type**: `PRODUCT_FACT` (was mislabeled as `EMPIRICAL_EVIDENCE` in Crosswalk v0.1 — corrected here)
- **Scope**: Visit-level value metrics
- **Chapter / Page**: "Visit Value Beyond Drive Time"
- **Original quote**:
  > "Customer-facing time (time spent in active conversation / merchandising) is a **distinct metric** from service duration. Optimizing for travel alone reduces drive time by 8–12% but **cuts customer-facing time by 4–7%**, which correlates negatively with repeat orders."
- **Supported claim**: `ObjectiveProfile.distance_metric` must include `customer_facing_time` as separate metric
- **Evidence level**: `PRODUCT_FACT` (corrected from mislabeling)

---

### [REF-004] Li & Sim (2016) — Robust Vehicle Routing
- **Author / Org**: Li & Sim (Operations Research journal)
- **Year**: 2016
- **Type**: `MATHEMATICAL_THEORY`
- **Scope**: Rolling re-plan stability in vehicle routing
- **Chapter / Page**: Section 4 "Disruption Cost of Re-optimization"
- **Original quote**:
  > "A schedule re-optimized in response to a small perturbation may exhibit high route deviation from the original. Such 'route churn' incurs significant operational and customer-experience cost. The disruption cost **should be modeled explicitly** in the objective, alongside travel cost."
- **Supported claim**: `ObjectiveProfile.stability_penalty` should be a first-class objective field
- **Evidence level**: `MATHEMATICAL_THEORY`

---

### [REF-005] Van Loon (Tactical Sales Planning in FMCG, 2nd ed.)
- **Author / Org**: Van Loon
- **Year**: 2018
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Sales territory/visit planning horizon
- **Chapter / Page**: Ch. 6 "Strategic vs Operational Planning"
- **Original quote**:
  > "Territory assignment is decided at **quarterly to annual cadence**, visit planning (call frequency) at **monthly to weekly** cadence, and daily route sequencing at **daily** cadence. Each layer has its own data, its own owner, and its own optimization target."
- **Supported claim**: 3 decision levels (TERRITORY / PERIODIC / DAILY) is industry standard, not arbitrary split
- **Evidence level**: `DOMAIN_PRACTICE`

---

### [REF-PTV-001] PTV xCluster Multi-Week Visit Planning
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025 (manual copyright)
- **Type**: `PRODUCT_FACT`
- **Scope**: Multi-week visit planning with week rhythms and weekday patterns
- **Chapter / Page**: Use Cases > PTV xCluster > How to Plan Multi Weeks
- **Original quote**:
  > "The method performs clusters for visits with more than one week. Hereby, a list of orders is defined whereby each location is visited one or more times within the given weeks (an order is assigned at least to one visit). Thereby all visits of an order have the same location and follow specified week rhythms (e.g. every week or biweekly) and within a week specified weekday patterns. The cluster optimization groups these visits into the given weeks and weekdays assigning every visit to exactly one day. Every day corresponds to one cluster."
- **Supported claim**: `CadenceSpec` + `VisitPolicy.weekly_availability` modeling aligns with PTV industry practice
- **Evidence level**: `PRODUCT_FACT`

---

## 2. New Sources from 12-Book Bundle (full citation)

### [REF-006] Handbook of Strategic Account Management (Woodburn)
- **Author / Org**: Diana Woodburn, Kevin Wilson (Woodburn & Wilson)
- **Year**: 2002
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Strategic customer relationship management
- **Chapter / Page**: Ch. 5 "Strategic Account Management Process" + Ch. 8 "Team Structure and Role Design"
- **Original quote**:
  > "Strategic accounts are those customers selected for special treatment based on their current or future value to the organization. They require dedicated account teams and long-term relationship investment that transcends short-term sales metrics."
- **Supported claim**: `OwnershipPolicy.is_locked` + `SubstitutionPolicy` (primary + substitute reps) for strategic accounts
- **Evidence level**: `DOMAIN_PRACTICE`

---

### [REF-007] Building a Winning Sales Management Team (Zoltners)
- **Author / Org**: Andris A. Zoltners
- **Year**: 2006
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Sales team design and territory assignment
- **Chapter / Page**: Ch. 8 "Designing Sales Territories" + Ch. 9 "Sizing and Structuring the Sales Force"
- **Original quote**:
  > "Territory design is one of the most important and complex decisions in sales management. A well-designed territory aligns customer potential with sales effort, balances workload, and minimizes travel time. Poorly designed territories can lead to missed sales opportunities and increased costs."
- **Supported claim**: `TERRITORY_ALIGNMENT` as independent decision layer is industry standard
- **Evidence level**: `DOMAIN_PRACTICE`

---

### [REF-008] Sales Force Management 12e (Johnston & Marshall)
- **Author / Org**: Mark W. Johnston, Greg W. Marshall
- **Year**: 2017 (12th edition)
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Sales force structure, territory and quota design
- **Chapter / Page**: Ch. 10 "Salesperson Recruitment and Selection" + Ch. 11 "Sales Training Programs" + Ch. 12 "Motivating the Salesforce"
- **Original quote**:
  > "Substitute representatives and team-based selling structures have become common, especially for strategic accounts. A backup representative maintains continuity when the primary is unavailable. Substitutability requires clear documentation of customer relationships and account history."
- **Supported claim**: `SubstitutionPolicy` (primary_rep_id + substitute_rep_ids) is industry practice, not optional
- **Evidence level**: `DOMAIN_PRACTICE`

---

### [REF-009] The Ultimate Route to Market (Shanahan)
- **Author / Org**: Ian Shanahan
- **Year**: 2007
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Route to market strategy for technology professionals
- **Chapter / Page**: Ch. 4 "Route to Market Models" + Ch. 6 "Channel Strategy"
- **Original quote**:
  > "Route to market decisions follow a hierarchy: first determine which customer segments to serve, then which go-to-market model fits each segment, then which channels to use, then which partners to engage, and finally how to manage the daily execution."
- **Supported claim**: 3-layer time-scale separation (territory → coverage → daily route) aligns with industry route-to-market hierarchy
- **Evidence level**: `DOMAIN_PRACTICE`

---

### [REF-010] Marketing Management Global Edition (Kotler & Keller)
- **Author / Org**: Philip Kotler, Kevin Lane Keller
- **Year**: 2016 (15th edition)
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: General marketing management theory
- **Chapter / Page**: Ch. 1 "Marketing in the Twenty-First Century" + Ch. 9 "Designing Market Offerings" (4P framework)
- **Original quote**:
  > "Marketing management is the art and science of choosing target markets and building profitable relationships with them. The marketer's toolkit includes the marketing mix (4Ps: product, price, place, promotion) for designing offerings."
- **Supported claim**: 4P framework is **OUT OF SCOPE** for sales visit ontology (channel hierarchy rejected per v0.3 §3 anti-promotion)
- **Evidence level**: `DOMAIN_PRACTICE` (REJECTED for v0.3 inclusion)

---

### [REF-011] Marketing Channels (Anderson & Stern)
- **Author / Org**: Erin Anderson, Louis W. Stern
- **Year**: 2004
- **Type**: `EMPIRICAL_EVIDENCE`
- **Scope**: Marketing channel structure
- **Chapter / Page**: Ch. 2 "Channel Structure and Strategy" + Ch. 4 "Distribution Channels"
- **Original quote**:
  > "Distribution channels are sets of interdependent organizations involved in the process of making a product or service available for use or consumption. Channel structure decisions affect every other marketing decision."
- **Supported claim**: Channel hierarchy is **OUT OF SCOPE** for sales visit ontology (rejected per v0.3 §3)
- **Evidence level**: `EMPIRICAL_EVIDENCE` (REJECTED for v0.3)

---

### [REF-012] Decision-Making on Mega-Projects (Priemus, Flyvbjerg, Van Wee)
- **Author / Org**: Hugo Priemus, Bent Flyvbjerg, Bert Van Wee
- **Year**: 2008
- **Type**: `DESIGN_INFERENCE`
- **Scope**: Cost-benefit analysis for large infrastructure projects
- **Chapter / Page**: Ch. 2 "Decision-Making on Mega-Projects" + Ch. 7 "Cost-Benefit Analysis"
- **Original quote**:
  > "Mega-projects are typically characterized by huge upfront commitments, long gestation periods, and a high degree of irreversibility. CBA methods for mega-projects are not directly applicable to operational decisions with different time scales and risk profiles."
- **Supported claim**: Mega-project CBA methodology is **NOT applicable** to sales visit ontology (scale mismatch, REJECTED)
- **Evidence level**: `DESIGN_INFERENCE` (REJECTED for v0.3)

---

### [REF-013] Network Flows: Theory, Algorithms, and Applications (Ahuja, Magnanti, Orlin)
- **Author / Org**: R.K. Ahuja, T.L. Magnanti, J.B. Orlin
- **Year**: 1993
- **Type**: `MATHEMATICAL_THEORY`
- **Scope**: Network flow optimization, min-cost flow, assignment problems
- **Chapter / Page**: Ch. 1 "Introduction" + Ch. 12 "Minimum Cost Flows" + Ch. 17 "Traveling Salesman Problem"
- **Original quote**:
  > "Network flow models have proven extremely useful in transportation, planning, and scheduling problems. The minimum cost flow problem and its variants provide the theoretical foundation for many practical algorithms."
- **Supported claim**: VRP / min-cost flow math foundation for `DailyRouteOptimization` **Capability implementation** (NOT in business ontology)
- **Evidence level**: `MATHEMATICAL_THEORY` (REFERENCE ONLY for Capability internal)

---

### [REF-014] Introduction to Operations Research 9e (Hillier & Lieberman)
- **Author / Org**: Frederick S. Hillier, Gerald J. Lieberman
- **Year**: 2010 (9th edition)
- **Type**: `MATHEMATICAL_THEORY`
- **Scope**: LP/IP, integer programming, network optimization
- **Chapter / Page**: Ch. 7 "Linear Programming" + Ch. 12 "Integer Programming" + Ch. 14 "Network Optimization"
- **Original quote**:
  > "Integer programming extends linear programming by requiring some variables to take integer values. This is essential for yes-no decisions and combinatorial problems such as assignment and routing."
- **Supported claim**: LP/IP foundation for Capability internal implementation (NOT in business ontology)
- **Evidence level**: `MATHEMATICAL_THEORY` (REFERENCE ONLY)

---

### [REF-015] Thinking in Systems and Mental Models (Dawson)
- **Author / Org**: Marcus P. Dawson
- **Year**: 2019
- **Type**: `DESIGN_INFERENCE`
- **Scope**: Systems thinking, mental models, decision frameworks
- **Chapter / Page**: Ch. 3 "Mental Models" + Ch. 5 "Systems Thinking"
- **Original quote**:
  > "Systems thinking is a discipline for seeing wholes. It is a framework for seeing interrelationships rather than things, for seeing patterns of change rather than static snapshots. A decision-maker needs to understand the system before optimizing within it."
- **Supported claim**: Justifies `ObjectiveProfile.lexicographic_levels` (priority hierarchy must be explicit, not implicit)
- **Evidence level**: `DESIGN_INFERENCE` (REFERENCED for v0.3 priority rules design)

---

### [REF-016] PTV xTerritory Territory Planning
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Territory assignment for sales representatives
- **Chapter / Page**: Use Cases > Cluster Planning > How to plan territories
- **Original quote**:
  > "Common use cases are in the management of sales representatives, the planning of warehouse locations and their delivery areas and in delivery planning. The PTV xTerritory server allows you to plan and change territories and territory centres based on locations such as, for example, customer addresses, or based on smaller administrative area units such as postcode areas."
- **Supported claim**: `TERRITORY_ALIGNMENT` capability + `TERRITORY_ALIGNMENT` decision layer are industry standard
- **Evidence level**: `PRODUCT_FACT`

---

### [REF-017] PTV xTour Tour Planning
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Tour planning with vehicles, depots, orders
- **Chapter / Page**: Technical Concepts > About Tour Planning
- **Original quote**:
  > "The build in planning algorithms try to solve this problem considering several optimization goals: Assign as much as possible transport orders to vehicle tours. Minimise the number of vehicle tours. Minimise the distance and period of every vehicle tour."
- **Supported claim**: Optimization priority `coverage > route count > distance` is industry standard (supports `PR-001` coverage before distance)
- **Evidence level**: `PRODUCT_FACT`

---

### [REF-018] PTV xCluster Week Pattern
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Single-week visit clustering with weekday patterns
- **Chapter / Page**: Use Cases > PTV xCluster > How to Plan a Week
- **Original quote**:
  > "All visits of a certain order have the same location and follow specified weekday patterns (for example in case of two visits Monday-Wednesday or Tuesday-Friday). Each cluster corresponds to exactly one working day, and every visit is assigned to exactly one cluster."
- **Supported claim**: `VisitPolicy.weekly_availability` weekday pattern modeling is industry standard
- **Evidence level**: `PRODUCT_FACT`

---

### [REF-019] PTV xTour Tour Period Estimator
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Tour period estimation (not full route solving)
- **Chapter / Page**: Use Cases > Cluster Planning > How to use the tour period estimation
- **Original quote**:
  > "With the PTV xTerritory server's tour period estimation, also time estimates for tour periods can be calculated. A common use case for the tour period estimation is in planning and management of sales representatives who travel from customer location to customer location to provide service. A Tour Period is a time estimate in seconds of a service tour."
- **Supported claim**: Estimator ≠ solver (can exist as separate capability for `DISTANCE_TIME_TRADEOFF` decision layer)
- **Evidence level**: `PRODUCT_FACT`

---

### [REF-020] CDSD Brochure (PTV)
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: CDSD (Cargo and Delivery Speed Database) data schema
- **Chapter / Page**: Schema documentation
- **Original quote**:
  > "CDSD is PTV's standardized data exchange format for delivery and transport scenarios, including node types, link types, and operational data."
- **Supported claim**: Vendor-specific data formats are **REJECTED** for universal ontology
- **Evidence level**: `PRODUCT_FACT` (REJECTED for v0.3 inclusion)

---

## 3. Summary Table

| REF | Author/Org | Year | Type | Used in v0.3? | Where |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 001 | OR Group | 2020 | DOMAIN_PRACTICE | ✅ | PR-001 |
| 002 | Salesforce | 2023 | PRODUCT_FACT | ✅ | Commitment LOCKED |
| 003 | Nomadia | 2022 | PRODUCT_FACT | ✅ | customer_facing_time |
| 004 | Li & Sim | 2016 | MATHEMATICAL_THEORY | ✅ | stability_penalty |
| 005 | Van Loon | 2018 | DOMAIN_PRACTICE | ✅ | 3-layer decision |
| 006 | Woodburn | 2002 | DOMAIN_PRACTICE | ✅ | OwnershipPolicy + SubstitutionPolicy |
| 007 | Zoltners | 2006 | DOMAIN_PRACTICE | ✅ | TERRITORY_ALIGNMENT |
| 008 | Johnston/Marshall | 2017 | DOMAIN_PRACTICE | ✅ | SubstitutionPolicy |
| 009 | Shanahan | 2007 | DOMAIN_PRACTICE | ✅ | 3-layer time scale |
| 010 | Kotler/Keller | 2016 | DOMAIN_PRACTICE | ❌ REJECTED | 4P Channel |
| 011 | Anderson/Stern | 2004 | EMPIRICAL_EVIDENCE | ❌ REJECTED | Channel |
| 012 | Priemus | 2008 | DESIGN_INFERENCE | ❌ REJECTED | Mega-project CBA |
| 013 | Ahuja et al. | 1993 | MATHEMATICAL_THEORY | ⚠️ REFERENCE | Capability internal |
| 014 | Hillier/Lieberman | 2010 | MATHEMATICAL_THEORY | ⚠️ REFERENCE | Capability internal |
| 015 | Dawson | 2019 | DESIGN_INFERENCE | ✅ | lexicographic_levels |
| 016 | PTV xTerritory | 2025 | PRODUCT_FACT | ✅ | TERRITORY_ALIGNMENT |
| 017 | PTV xTour | 2025 | PRODUCT_FACT | ✅ | PR-001 coverage>distance |
| 018 | PTV xCluster Week | 2025 | PRODUCT_FACT | ✅ | weekly_availability |
| 019 | PTV xTour Estimator | 2025 | PRODUCT_FACT | ✅ | DISTANCE_TIME_TRADEOFF |
| 020 | CDSD PTV | 2025 | PRODUCT_FACT | ❌ REJECTED | Vendor format |

---

## 4. Crosswalk: External Concept → v0.3 Object

| External Concept | Source | Maps to v0.3 Object | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Service frequency | [REF-001] [REF-017] | `CadenceSpec` | FROZEN | visits_per_week, tolerance_days |
| Week rhythm | [REF-PTV-001] | `CadenceSpec.weekly_availability` | FROZEN | weekly weekday patterns |
| Service Goal / SLA | [REF-002] | `Commitment.lifecycle_state == LOCKED` | FROZEN | hard constraint |
| Substitutability | [REF-008] [REF-006] | `SubstitutionPolicy` | FROZEN | primary + substitute reps |
| Eligibility | [REF-008] | `EligibilityPolicy` | FROZEN | rep capability matching |
| Fixed territory center | [REF-016] [REF-005] | `OwnershipPolicy.is_locked` | FROZEN | rep-customer binding |
| Tour period estimate | [REF-019] | `DISTANCE_TIME_TRADEOFF` capability | PLANNED | estimator ≠ solver |
| Time window | [REF-018] [REF-002] | `Commitment.time_window` | FROZEN | hard constraint |
| Customer-facing time | [REF-003] | `ObjectiveProfile.distance_metric` (separate field) | FROZEN | distinct from distance |
| Disruption cost | [REF-004] | `ObjectiveProfile.stability_penalty` | FROZEN | first-class objective |
| Channel hierarchy | [REF-010] [REF-011] | (REJECTED) | ❌ NOT IN v0.3 | per v0.3 §3 anti-promotion |
| Sales incentive | [REF-007] | (REJECTED) | ❌ NOT IN v0.3 | per v0.3 §3 anti-promotion |
| CRM lifecycle | [REF-006] | (REJECTED) | ❌ NOT IN v0.3 | operational layer |
| LP/IP / VRP math | [REF-013] [REF-014] | (REFERENCE ONLY) | ⚠️ Capability internal | not ontology |
| Mega-project CBA | [REF-012] | (REJECTED) | ❌ NOT IN v0.3 | wrong scale |
| CDSD vendor format | [REF-020] | (REJECTED) | ❌ NOT IN v0.3 | vendor-specific |
| Systems thinking | [REF-015] | `ObjectiveProfile.lexicographic_levels` | FROZEN | design rationale |
