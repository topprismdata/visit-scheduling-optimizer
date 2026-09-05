# Scenario D — 多资源 + Ownership/Eligibility/Substitution：Executable Specification (S-D v1.0)
## Phase 2 · 16-Element Standard Template（单维度验证：组织关系边界）

> **文档标识**：`SD-MULTIRES-OWNERSHIP-EXESPEC-V1.0`  
> **所属阶段**：Phase 2 Scenario Specification Validation（A ✅ → C ✅ → **D ◀** → E → B）  
> **架构约束**：A03 `Domain-Contract-v1.0.1 FROZEN`；不修改 A03/A05、不进入数学、不设计 Solver、不新增 Domain Entity。  
> **单维度原则**：本场景**只验证组织关系四概念分离**——柔性节奏属 C（已证）、滚动锁定属 E、动态属 B。  
> **评审预警（本场景最高风险）**：严禁出现 `Owner == Assigned Rep` 隐藏假设；D 被预判为**最可能产生真实 DCR 的场景**。

---

## 目录
1. [场景定义与四概念分离目标](#1-场景定义与四概念分离目标)
2. [16 项标准模板](#2-16-项标准模板)
3. [执行计划（TD-* 系列 + MRE-D 系列）](#3-执行计划)
4. [Gate D 判定标准](#4-gate-d-判定标准)
5. [Domain Change Log](#5-domain-change-log)

---

# 1. 场景定义与四概念分离目标

**业务原型**：苏州/常州式多业务员辖区——客户有固定归属关系，但存在请假替补、区域共享池与资质门槛。

**Scenario D 只验证一个维度——组织关系四分离**：

| 概念 | 回答的问题 | 承载对象（冻结契约） | 严禁混淆 |
|---|---|---|---|
| **Ownership** | 谁拥有这个客户关系？ | `OwnershipPolicy.primary_resource_ids` | ≠ 执行人 |
| **Eligibility** | 谁具备执行资格？ | `EligibilityPolicy.required_qualifications/tags` | ≠ 有空 |
| **Availability** | 谁现在有时间？ | `ResourceAvailability/ResourceDayProfile` | ≠ 有资格 |
| **Assignment** | 这次计划实际给谁？ | `PlannedVisit.resource_id`（输出物） | ≠ Owner 必然 |

**四概念关系式**（本场景核心断言）：
```
eligible_resources(target, date) = Ownership(primary ∪ shared_pool ∪ backup) 
                                   → filtered by Eligibility(qualifications, territory)
                                   → filtered by Availability(day_profile)
assignment = 规划输出，从 eligible 中选择（Phase 3 优化决策）
审计: assignment ≠ owner 时必须可追溯（substitute 经由 / shared via / backup via）
```

---

# 2. 16 项标准模板

## §2.1 Business Inputs

```
实例规模:
  D-STD : 20 客户 × 3 业务员（R001/R002/R003）× 4 周
  D-MRE : 最小反例实例（见 §2.5）

资源画像（三员差异化，验证 Eligibility/Availability 分离）:
  R001 "资深代表": qualifications={cold_chain: true}, 全勤, BASE_DEPOT
  R002 "标准代表": qualifications={}, 全勤除第 2 周周三请假（is_absent）
  R003 "共享池员": qualifications={cold_chain: true}, 仅周二/周四工作（部分日）

客户分群:
  10 家 primary=R001（其中 3 家 cold_chain 资质门槛）
  6 家 primary=R002
  4 家 shared_pool=True（无固定 primary）
```

## §2.2 Policy Configuration

```
VisitPolicy: 复用 A 场景四段制（KA/A/B/C），cadence 标准值——本场景不测节奏（C 已证）

OwnershipPolicy ×20:
  14 家: primary=(R001|R002), allow_shared_pool=False
  3 家: primary=(R001), required cold_chain（经 EligibilityPolicy 表达，不塞 Ownership）
  4 家: primary=(), allow_shared_pool=True   ← 共享池：primary 为空 + pool 开关
  2 家(高价值): 增 SubstitutionPolicy(allow_backup=True, backup=(R003), 
                conditions={trigger: PRIMARY_ABSENT, same_territory: true})

EligibilityPolicy（独立于 Ownership 表达）:
  3 家: required_qualifications={cold_chain: true}
  全部: required_territory_tags={any: [NT-03]}（三员均持 NT-03）

时间窗: 全部 FULL（本场景不测时窗——C 已证）；资源差异化日历见 §2.1
```

## §2.3 Expected VisitDemand / VisitOccurrence

```
Occurrence 生成与 A 同构（本场景不重测计数），重点在 eligible_resource_ids 派生:

对每 occurrence:
  pool = Ownership.primary ∪ (shared_pool ? all_resources : ∅) ∪ (backup, 若触发)
  eligible = {r ∈ pool | r 满足 Eligibility.qualifications ∧ tags ∧ r.DayProfile(date) 可用}

预期派生结果（关键断言）:
  cold_chain 客户: eligible ⊆ {R001, R003}（R002 无资质被滤除）
  R002 请假日: 该日 eligible ∌ R002（有归属≠可用）
  共享池客户: eligible = {R001, R002, R003}（无 primary 约束）
  backup 客户(R001 缺勤日): eligible = {R003}（substitution 触发）
```

## §2.4 BusinessRequirement & Evidence

| req_id | statement | strength | authority | exception_ref |
|---|---|---|---|---|
| REQ-D-001 | 客户归属关系变更须经主管审批（Owner 变更是管理事件，非规划输出） | HARD | COMPANY_POLICY | — |
| REQ-D-002 | 冷链资质门槛不可绕过（无资质者不得执行） | HARD | LEGAL（食品安全） | DP-ESC（升级总监） |
| REQ-D-003 | 替补执行须可追溯（assignment≠owner 时审计链强制） | HARD | COMPANY_POLICY | — |
| REQ-D-004 | 共享池客户服务等级不低于专属客户 | SOFT | COMPANY_POLICY | DP-STD |

## §2.5 最小反例（MRE-D 系列，评审指令要求）

### MRE-D-1：Owner ≠ Executor（核心反例）
```
客户 X: OwnershipPolicy(primary=(R001), allow_shared_pool=False)
        SubstitutionPolicy(allow_backup=True, backup=(R002),
                           conditions={trigger: PRIMARY_ABSENT})
R001: 第 2 周周三请假（ResourceDayProfile.is_absent=True）
R002: 该日可用且具备资格

系统必须能同时表达并审计:
  • Ownership 不变: X 仍是 R001 的客户（关系归属未转移）
  • 该日 eligible = {R002}（substitution 触发派生）
  • 若 assignment=R002: 审计链 "X assigned R002 via SUBSTITUTION (primary R001 absent)"
  • 三者各自独立记录，无任一推导自另一的隐式假设
```

### MRE-D-2：有归属 ≠ 有资格
```
客户 Y: primary=(R001)，required_qualifications={cold_chain}
新员工 R004 加入 primary（管理误配）: qualifications={}

断言: R004 ∈ Ownership.primary 但 R004 ∉ eligible（Eligibility 独立过滤）
     系统显式暴露"归属与资格矛盾"而非静默放行或静默改归属
```

### MRE-D-3：有空 ≠ 被授权
```
R003（共享池员）周二空闲。
客户 Z: primary=(R002), allow_shared_pool=False, backup=∅

断言: R003 该日 available=true 但 eligible(Z)=∅（无授权路径）
     可用性不产生执行权
```

## §2.6 Expected Audit Result

```
ownership_immutable_during_plan : true（规划期归属零变更——REQ-D-001）
qualification_violations        : 0
substitution_traceability       : 每次 assignment≠owner 均含 via-reason
shared_pool_service_level       : 记录比对（REQ-D-004 SOFT）
```

## §2.7 Audit Trace（本场景链路）

```
TRACE-D1（替补审计）:
  MRE-D-1 assignment: PlannedVisit.resource_id=R002
    → 审计: {owner: R001, executor: R002, via: SUBSTITUTION, 
             trigger: PRIMARY_ABSENT, policy_ref: SubstitutionPolicy(backup=(R002))}
    → Tag: ASSIGN_VIA_SUB_T{X}_D{date}
    → 断言: 该链四要素齐全，缺任一 = Gate D3 FAIL

TRACE-D2（资质过滤）:
  cold_chain 客户: R002 ∈ pool 但 ∉ eligible
    → Tag: ELIG_FILTER_T{Y}_R{R002}_REASON{missing:cold_chain}
    → 拒绝原因显式，非静默
```

## §2.8–2.12 模板占位（Phase 3/4 锁定）

```
§2.8 Formulations : [占位——Phase 3]
§2.9 Backends     : [占位——Phase 4]
§2.10 GT          : [占位——Phase 3]
§2.11 AC          : 见 §4 Gate D
§2.12 MM          : MM-D1 增加资源 → 既有客户 eligible 集不缩
                    MM-D2 放开资质要求 → eligible 集不缩
                    MM-D3 撤销 shared_pool → 该客户 eligible 集不增
                    MM-D4 backup 名单扩大 → 触发日 eligible 集不缩
```

## §2.13 Domain Coverage Matrix（D 场景专用增量）

| A03 对象 | D 中角色 | 增量验证点（A/C 未覆盖） |
|---|---|---|
| OwnershipPolicy | **主用 ✅✅** | 多 primary、空 primary+pool 开关、**规划期不可变性** |
| SubstitutionPolicy | **主用 ✅✅** | conditions 触发语义、backup 派生路径、审计 via-reason |
| EligibilityPolicy | **主用 ✅✅** | qualifications 独立过滤、与 Ownership 矛盾显式暴露 |
| ResourceAvailability（多资源差异化） | 主用 | 三员异构日历（请假/部分日/全勤）交叉 |
| derive_eligible_resources 派生 | **主用 ✅✅** | 四概念关系式端到端（A03 §2.6 组合语义） |
| LifecycleState | 未增（assignment 属输出） | — |

## §2.14 Compilation Trace Example：见 §2.7

## §2.15 Expected Failure Cases

| ID | 输入 | 期望 |
|---|---|---|
| FC-D-1 | Ownership.primary 引用不存在资源 | 装配期显式失败 |
| FC-D-2 | backup 资源不满足 Eligibility | 派生时显式排除 + 原因标签（非静默） |
| FC-D-3 | shared_pool=True 但全员无 NT-03 tag | eligible=∅ + 结构报告（而非崩溃） |

## §2.16 Architecture Change Log

```
[ EMPTY by default ]
（评审预判：D 是最可能产生真实 DCR 的场景——若四概念关系式无法由冻结对象
 无歧义表达，如实记录 Failure 并提交 DCR，禁止 workaround。）
```

---

# 3. 执行计划（TD-* 系列 + MRE-D 系列）

| ID | 测试 | 只改动 | 断言 |
|---|---|---|---|
| TD-BASE | 20 客户 × 3 资源基线 | — | eligible 派生全表命中 §2.3 预期 |
| TD-OWN-1 | 客户 primary R001→R002 | 仅 OwnershipPolicy | 归属变更生效；**REQ-D-001 提示：规划期变更需审批标记** |
| TD-ELIG-1 | cold_chain 客户 × R002 | — | R002 恒被滤除（MRE-D-2） |
| TD-ELIG-2 | 撤除冷链门槛 | 仅 EligibilityPolicy | R002 进入 eligible（MM-D2） |
| TD-AVAIL-1 | R002 请假日 | 仅 date_profiles | 该日 R002 出局、其余不变 |
| TD-AVAIL-2 | R003 部分日（仅 Tue/Thu） | 仅 ResourceDayProfile | 周一 R003 出局（MRE-D-3 变体） |
| TD-POOL-1 | 共享池客户 | — | eligible={三员} |
| TD-POOL-2 | shared_pool→False | 仅 OwnershipPolicy | eligible 收缩至 primary（MM-D3） |
| TD-SUB-1 | **MRE-D-1 完整链** | R001 请假 + backup 配置 | owner 不变 / executor=R002 / via=SUBSTITUTION 四要素审计 |
| TD-SUB-2 | backup 名单 +R002 | 仅 SubstitutionPolicy | 触发日 eligible 扩（MM-D4） |
| TD-ADD-1 | 新增 R004 全资质 | 仅 resources 列表 | 既有 eligible 不缩（MM-D1） |
| TD-TRACE | 审计链完整性 | — | 每次 via-assignment 四要素机读可检 |

---

# 4. Gate D 判定标准

```
Gate D1 — Four-Concept Separation Gate
  Ownership/Eligibility/Availability/Assignment 四者独立表达；
  无任一概念从另一概念隐式推导（MRE-D-1/2/3 三反例全证）。

Gate D2 — Derivation Integrity Gate
  eligible 派生 = pool → elig → avail 三段过滤；
  每次过滤的排除项带显式原因标签（TRACE-D2）。

Gate D3 — Substitution Audit Gate
  MRE-D-1: owner≠executor 时 {owner, executor, via, trigger, policy_ref} 五要素齐全。

Gate D4 — Immutability Gate
  规划期 Ownership 零隐式变更（REQ-D-001）；显式变更留审批标记。

Gate D5 — Scenario Pass
  D1–D4 + TD/MRE 全过 + MM-D1..4 + Change Log 状态如实。
```

---

# 5. Domain Change Log

见 §2.16（EMPTY by default；若评审预判成真，如实提交 DCR）。
