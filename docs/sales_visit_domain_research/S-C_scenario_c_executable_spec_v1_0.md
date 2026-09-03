# Scenario C — 柔性 Cadence + Time Window：Executable Specification (S-C v1.0)
## Phase 2 · 16-Element Standard Template（单维度验证：柔性约束表达力）

> **文档标识**：`SC-FLEX-CADENCE-TIMEWINDOW-EXESPEC-V1.0`  
> **所属阶段**：Phase 2 Scenario Specification Validation（A ✅ → **C ◀** → D → E → B）  
> **架构约束**：A03 `Domain-Contract-v1.0.1 FROZEN`；不修改 A03/A05、不进入数学、不设计 Solver、不新增 Domain Entity。  
> **单维度原则**（评审警示）：本场景**只证明柔性约束表达**，不做大而全——动态调整属 Scenario B，多资源属 Scenario D。  
> **变更规则**：任何失败 → Scenario Failure 记录 → DCR Review；禁止 workaround。

---

## 目录
1. [场景定义与单维度验证目标](#1-场景定义与单维度验证目标)
2. [16 项标准模板](#2-16-项标准模板)
3. [执行计划（TA-C 系列测试）](#3-执行计划ta-c-系列测试)
4. [Gate C 判定标准](#4-gate-c-判定标准)
5. [Domain Change Log](#5-domain-change-log)

---

# 1. 场景定义与单维度验证目标

**业务原型**：高价值母婴/保健品连锁客户群——拜访节奏与到店时段均有柔性但非任意（如"距上次 7–30 天内再访""仅周二/周四下午可接待"）。

**Scenario C 只验证一个维度**：

| # | 验证目标 | 判定物 |
|---|---|---|
| C-1 | **CadenceSpec 语义边界**：min/max spacing 何者是强制、何者是偏好、语义是否无歧义 | §2.2 + §2.4 + 语义边界表 |
| C-2 | **TimeWindow 来源分离**：门店营业 vs 客户预约 vs 资源工作时段，不同来源不同对象，不塞进 VisitPolicy | §2.1 + §2.2 装配审查 |
| C-3 | **Frequency vs Cadence 生命周期关系**：频次（每周期几次）与节奏（间隔多远）独立演化，互不牵连 | §3 TC-CAD 系列 |
| C-4 | Requirement Fulfillment + Audit Trace 在柔性约束下保持四段链 | §2.7 |

**明确不在本场景验证**（防扩散）：动态重排（B）、多业务员归属（D）、滚动锁定（E）、任何 formulation/backend。

---

# 2. 16 项标准模板

## §2.1 Business Inputs

```
实例规模:
  C-Micro : 8 客户 × 1 业务员 × 4 周（20 工作日）→ 解释层验证
  C-Var   : 变体若干（见 §3），每变体只改一个对象

Facts & Signals:
  • 8 家 VisitTarget，全部 segment="FLEX"（本场景专用段，验证 scope 表达力）
  • TimeWindow 来源三类（关键审查点 C-2）:
    - 门店营业窗口 → TargetAvailability.WeeklyAvailabilityRule
      (4 家: 周二/周四 14:00–18:00 —— 周分化窗口)
    - 客户指定窗口 → 同上对象但经 date_exceptions 覆盖
      (2 家: 第 2 周仅周三上午 09:00–12:00)
    - 资源工作窗口 → ResourceAvailability.ResourceDayProfile
      (业务员: 默认 08:00–18:00，第 3 周周三仅下午)
  • ExecutionHistory: 4 家有上次访问记录（7–40 天前不等，驱动 cadence eligible 计算）
```

## §2.2 Policy Configuration

```
VisitPolicy P-FLEX（唯一政策，验证柔性表达）:
  scope: {segment == "FLEX"}
  FrequencySpec: RANGE, target=2, ref=28d, min=1, max=2
  CadenceSpec:   min_spacing_days=7, max_spacing_days=30   ← 核心审查对象
  standard_service_duration_min: 30

CadenceSpec 语义边界声明（C-1 核心交付）:
┌───────────────────┬────────────────┬──────────────────────────────────┐
│ 字段               │ 语义性质        │ 违反后果                          │
├───────────────────┼────────────────┼──────────────────────────────────┤
│ min_spacing_days  │ 强制（HARD）    │ 违反 = cadence violation，       │
│                   │                │ 属 REQ-C-002（结构不可满足时       │
│                   │                │ → PROVEN_INFEASIBLE）            │
│ max_spacing_days  │ 强制（HARD）    │ 同上（防"扎堆周期初/遗忘周期末"）  │
│ preferred_weekday │ 不存在于冻结契约 │ 本场景不引入（TA-DAY 教训）；     │
│                   │ （A03 无此字段）│ 若业务需要 → DCR 通道            │
└───────────────────┴────────────────┴──────────────────────────────────┘
  关键: 两个 spacing 皆是业务规则的 Rule Enforcement Strength 表达，
       由 BusinessRequirement.strength 承载（本场景均为 HARD）；
       软偏好版本留给 MM 变体（HARD→SOFT 降级测试）。

TimeWindow 归属审查表（C-2 核心交付）:
┌──────────────────┬───────────────────────────────┬─────────────────┐
│ 来源             │ 归属对象（冻结契约）            │ 严禁塞入         │
├──────────────────┼───────────────────────────────┼─────────────────┤
│ 门店营业时间      │ TargetAvailability            │ VisitPolicy     │
│                  │  .WeeklyAvailabilityRule      │                 │
│ 客户指定时段      │ 同上 + date_exceptions        │ VisitDemand     │
│ 销售政策指定      │ （本场景不涉及；如出现 → DCR） │ —               │
│ 业务员工作时段    │ ResourceAvailability          │ TargetAvail.    │
│                  │  .ResourceDayProfile          │                 │
└──────────────────┴───────────────────────────────┴─────────────────┘

PlanningPolicy: TACTICAL_PJP, freeze=0
ObjectivePolicy: BALANCED_STABILITY（解释层不实例化目标）
Ownership: 每客户 primary=(R001)（D 场景维度，此处恒真退化）
DeferralPolicy: DP-FLEX (deferrable=True, max=10d, NOTIFY_RM, OPPORTUNITY_LOSS)
  绑定: REQ-C-003 (COMPANY_POLICY) → exception_handling_policy_ref="DP-FLEX"
```

## §2.3 Expected VisitDemand / VisitOccurrence

```
OccurrenceGenerator 输出（RANGE 分层，同 PROOF-E1 规范）:
  8 客户 × [1 REQUIRED(底线) + 1 OPTIONAL(stretch)] = 8 + 8

eligible_date_range 计算（cadence × history × availability 三源交汇）:
  对有历史访问的客户 i (last_visit = L):
    eligible = [max(horizon_start, L + min_gap), min(horizon_end, L + max_gap)]
             ∩ TargetAvailability 开放日
  对无历史客户:
    eligible = [horizon_start, horizon_start + max_gap] ∩ 开放日
  → 这是解释层日期集合计算（非优化）：只产出 eligible 区间，不选日期。
```

## §2.4 BusinessRequirement & Evidence

| req_id | statement | strength | authority | parameter_refs | exception_ref |
|---|---|---|---|---|---|
| REQ-C-001 | FLEX 段客户每 28 天底线 1 次、至多 2 次 | HARD | COMPANY_POLICY | param.freq_flex_min=1, max=2 | — |
| REQ-C-002 | 两次拜访间隔不早于 7 天、不晚于 30 天 | **HARD** | COMPANY_POLICY | param.gap_flex=[7,30] | — |
| REQ-C-003 | FLEX 段覆盖未满足时按 DP-FLEX 延期 | SOFT | COMPANY_POLICY | — | **DP-FLEX** |
| REQ-C-004 | 客户指定时段（date_exceptions）具有门店营业同级效力 | HARD | CONTRACT | — | — |

## §2.5 Feasibility Boundaries

```
Feasible  : 标准实例——所有客户在 [7,30] 窗 + 时窗限制下存在合法日期组合。
Tight     : TC-CAP——容量压至仅容底线 → stretch 全 defer + DP-FLEX 链。
Infeasible: TC-INF——min_gap=25d + EXACT(2) + 客户仅第 2 周周三上午开放
            （一个 28 天周期内该窗口仅 1 个可用日 → 2 次拜访无合法组合，
             且两次须隔 ≥25d 而仅 1 日可用）→ PROVEN_INFEASIBLE
             归因: REQ-C-002 × REQ-C-004 联合冲突。
```

## §2.6 Expected Audit Result

```
cadence_violations(HARD)      = 0（正常实例）
availability_violations       = 0（含 date_exceptions 尊重）
exception_trace(降级测试时)   : REQ-C-003 → DP-FLEX → defer≤10d → capacity shortage
eligible_range 完整性         : 每个 occurrence 的 eligible 区间可回溯到
                                (history.L, min_gap, max_gap, availability) 四源
```

## §2.7 Audit Trace（本场景链路）

```
TRACE-C1（柔性节奏 eligible 推导）:
  REQ-C-002 (gap ∈ [7,30] HARD)
    → param.gap_flex=[7,30]
    → eligible = [L+7, L+30] ∩ 开放日        ← 解释层日期集合运算
    → Tag: ELIGIBLE_OCC_{occ_id}（记录四源输入）
    → Result: 8 客户 eligible 区间全部非空（正常实例）

TRACE-C2（时窗来源分离）:
  REQ-C-004 (客户指定时段, CONTRACT)
    → TargetAvailability.WeeklyAvailabilityRule.date_exceptions[日期X]=(09:00,12:00)
    → Tag: AVAIL_OVERRIDE_T{target}_D{X}
    → Result: 资源窗口(08-18) ∩ 门店(14-18) ∩ 客户(09-12) = 空时 → 该组合日排除
              （三源独立、交集判定、无一源吞并另一源）
```

## §2.8–2.12 模板占位（Phase 3 锁定，本阶段不实例化）

```
§2.8 Candidate Formulations : [占位——Phase 3；本阶段禁止生成]
§2.9 Candidate Backends     : [占位——Phase 4]
§2.10 Ground Truth          : [占位——Phase 3；C-Micro 穷举同 A 规范]
§2.11 Acceptance Criteria   : 见 §4 Gate C（解释层专用 AC 列于 Gate）
§2.12 Metamorphic Tests     : MM-C1 放宽 max_gap → eligible 集不缩
                              MM-C2 收紧 min_gap → eligible 集不增
                              MM-C3 HARD→SOFT 降级 REQ-C-002 → 不致 infeasible
                              MM-C4 date_exceptions 增加例外日 → 可行性不降
```

## §2.13 Domain Coverage Matrix（C 场景专用增量）

| A03 对象 | C 中角色 | 增量验证点（A 未覆盖） |
|---|---|---|
| CadenceSpec | **主用 ✅✅** | min/max 双边界语义、与 history 交互（eligible 推导） |
| WeeklyAvailabilityRule.date_exceptions | **主用 ✅✅** | 客户指定时段覆盖机制（A 未用） |
| WeeklyAvailabilityRule（周分化多窗口） | 主用 | 4 家 Tue/Thu-PM（A 仅 2 家，扩样本） |
| ResourceDayProfile（部分日时段） | 主用 | 第 3 周周三仅下午（A 仅全日请假） |
| FrequencySpec(RANGE)+分层 | 回归 | 与 cadence 独立演化（TC-CAD-3） |
| exception_handling_policy_ref | 回归 | 新 binding REQ-C-003→DP-FLEX |

## §2.14 Compilation Trace Example：见 §2.7（TRACE-C1/C2 即本阶段交付）

## §2.15 Expected Failure Cases

| ID | 输入 | 期望 |
|---|---|---|
| FC-C-1 | min_gap > max_gap（CadenceSpec 内部矛盾） | 装配期显式校验失败 |
| FC-C-2 | date_exception 日期 blackout 同时声明 | 显式冲突报告（异常与禁止互斥） |
| FC-C-3 | REQ-C-003 引用不存在 DP | KeyError（同 A 的 FC 回归） |

## §2.16 Architecture Change Log

```
[ EMPTY by default ]
规则同前：须挂可复现 Failure + 契约无法表达论证。
```

---

# 3. 执行计划（TA-C 系列测试）

| ID | 测试 | 只改动 | 断言 |
|---|---|---|---|
| TC-BASE | 8 客户基线 | — | occurrence=8 REQ+8 OPT；eligible 区间四源可溯 |
| TC-CAD-1 | min_gap 7→14 | 仅 CadenceSpec | eligible 起点后移；结构仍可行 |
| TC-CAD-2 | max_gap 30→21 | 仅 CadenceSpec | eligible 终点前移；不改变 Frequency 语义 |
| TC-CAD-3 | freq RANGE→EXACT(2) | 仅 FrequencySpec | cadence 边界不动——两轴独立 |
| TC-TW-1 | 门店时窗 Tue/Thu-PM → Mon/Wed-AM | 仅 WeeklyAvailabilityRule | 可行性重算，无对象新增 |
| TC-TW-2 | 增 1 家客户指定 date_exception | 仅 date_exceptions | 该日窗口=客户时段∩门店∩资源 |
| TC-TW-3 | 资源第 3 周三仅下午 | 仅 ResourceDayProfile | 三源交集判定正确 |
| TC-CAP | 容量仅容底线 | 仅资源容量 | stretch defer + REQ-C-003→DP-FLEX 四段链 |
| TC-INF | min_gap=25 + EXACT(2) + 仅 1 可用日 | CadenceSpec+Freq+Availability | PROVEN_INFEASIBLE + 归因 REQ-C-002×004 |
| TC-HIST | 上次访问 3 天前 vs 35 天前 | 仅 ExecutionHistory | eligible 分别推迟/前移（7 天规则） |

---

# 4. Gate C 判定标准

```
Gate C1 — Cadence Semantics Gate
  min/max spacing 语义边界表（§2.2）成立且测试一致；
  无"偏好星期"类未冻结字段被引入。

Gate C2 — TimeWindow Source-Separation Gate
  三源（门店/客户/资源）各自对象承载；
  交集判定无源吞并；VisitPolicy/VisitDemand 零时窗字段。

Gate C3 — Independence Gate
  Frequency 与 Cadence 变更互不影响（TC-CAD-3 双向）。

Gate C4 — Trace Gate
  ELIGIBLE_OCC 与 AVAIL_OVERRIDE 标签可机读回溯四源。

Gate C5 — Scenario Pass
  C1–C4 + TC 全过 + MM-C1..4 + Change Log EMPTY。
```

---

# 5. Domain Change Log

见 §2.16（EMPTY by default；执行报告将如实记录）。
