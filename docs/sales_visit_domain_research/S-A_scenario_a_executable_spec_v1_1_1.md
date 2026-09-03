# Scenario A — FMCG 4 周周期覆盖：Executable Specification (S-A v1.1)
## Reference Scenario Spike · Scenario A: 16-Element Standard Template (Specification Correction)

> **文档标识**：`SA-FMCG-4W-PJP-EXESPEC-V1.1`  
> **所属阶段**：`Reference Scenario Spike`（A06 GATE 已解锁本阶段；生产代码重构保持 LOCKED）  
> **架构约束**：A03 `Domain-Contract-v1.0 FROZEN` / A05 `Reference-Architecture-v1.0 FROZEN`，**本规格不得新增领域概念**。  
> **本版性质**：Specification Correction + DCR 落地同步（DCR-SA-001-R 已批准并入 A03 v1.0.1；本文件 §2.2/§2.4/§2.7/§2.15/§2.17/§5 已同步）  
> **执行顺序**：A（本文件）→ C → D → E → B。  
> **变更规则**：任何架构变更必须由**可复现的 Scenario Failure** 驱动，以 `Domain Change Request` 形式提出，不得直接修改 A03。

---

## 目录
1. [场景定义与验证目标](#1-场景定义与验证目标)
2. [16 项标准模板](#2-16-项标准模板)
   - §2.1 Business Inputs
   - §2.2 Policy Configuration
   - §2.3 Expected VisitDemand / VisitOccurrence
   - §2.4 BusinessRequirement & Evidence
   - §2.5 Canonical Decision Objective（v1.1 新增前置定义）
   - §2.6 Feasibility Boundaries
   - §2.7 Expected Audit Result
   - §2.8 Candidate Mathematical Formulations（含 routing coupling 声明）
   - §2.9 Candidate Backends
   - §2.10 Ground-truth / Oracle（两层：GT-Micro + GT-Small）
   - §2.11 Acceptance Criteria
   - §2.12 Metamorphic Tests
   - §2.13 Benchmark Metrics
   - §2.14 Domain Coverage Matrix
   - §2.15 Compilation Trace Example
   - §2.16 Expected Failure Cases
   - §2.17 Architecture Change Log & DCR Register
3. [Expressibility Proofs（v1.1 新增）](#3-expressibility-proofs)
   - 3.1 PROOF-E1：RANGE fulfillment 分层表达（无 DCR）
   - 3.2 PROOF-E2：DeferralPolicy 绑定（含 DCR-SA-001 判定）
4. [第一批测试设计（8 类，v1.1 修订）](#4-第一批测试设计8-类)
5. [Gate A1–A5 判定标准（v1.1 状态）](#5-gate-a1a5-判定标准)

---

# 1. 场景定义与验证目标

**业务原型**：FMCG（美素佳儿/太古可口可乐式）销售代表 4 周（20 工作日）常态拜访周期覆盖。

**Scenario A 验证四件事**（不是验证"CG 好不好"）：

| # | 验证目标 | 判定物 |
|---|---|---|
| 1 | **冻结本体是否够用**：不修改 A03 即可完整表达本场景 | §2.14 Coverage + §3 Expressibility Proofs + §2.17 Change Log |
| 2 | **业务配置与数学模型是否真分开**：同一业务目标可被 ≥2 种 formulation 编译 | §2.5 canonical objective + §2.8 三候选 |
| 3 | **Backend 是否可替换**：≥2 个成熟 backend 在相同语义下一致 | §2.9 + Gate A3 |
| 4 | **验证体系是否工作**：两层 GT（Micro 穷举 / Small exact）可得已知最优 | §2.10 |

---

# 2. 16 项标准模板

## §2.1 Business Inputs

```
Instance Scale（v1.1 修订为四档）:
  GT-Micro   :  6 客户 × 1 业务员 × 2 周（10 工作日）→ 真正穷举 oracle
  GT-Small   : 10 客户 × 1 业务员 × 4 周            → 独立 exact model 求证 OPTIMAL
  Standard   : 32 客户 × 1 业务员 × 4 周            → 对齐南通仁军实际
  Stress     : 60 客户 × 2 业务员 × 4 周            → 多资源扩展（含独立 Ownership fixture，见 §2.2）

Facts & Signals 输入:
  • VisitTarget 清单: code, name, GeoLocation, territory_id,
    business_attributes.segment ∈ {KA, A, B, C}
  • TargetAvailability: WeeklyAvailabilityRule
    - 默认全工作日 08:00–18:00
    - 2 个 B 类客户仅周二/周四 14:00–18:00（验证周分化窗口）
  • ExecutionHistory: 上周期打卡记录（含 1 家 C 店 MISSED → 漏访重生）
  • SalesResource: R001 (GT/Standard), R001+R002 (Stress)
    ResourceAvailability 含:
    - 默认 BASE_DEPOT 出发
    - 1 天 is_absent=True（请假）

Travel & On-site Time 口径（v1.1 统一，禁止双重计入）:
  • On-site time = VisitPolicy.standard_service_duration_min（唯一进入容量/目标的店内时间）
  • ObservedStopTime(median 32.0 min, breakdown UNKNOWN) 仅作为
    service_duration 的校准证据登记于 ParameterRegistry，不参与加总。
  • Travel = L2 校准模型（区县速度），GT-Micro 路段成本由 Held-Karp 精确求值。
```

## §2.2 Policy Configuration（纯 A03 契约对象）

```
VisitPolicy ×4（v1.1：P4 补 neutral CadenceSpec；范围由 PolicyScope 声明）:

  Policy P1 [KA]
    scope: {segment == "KA"}
    FrequencySpec: EXACT, target=4, ref=28d, min=4, max=4
    CadenceSpec:   min=5d, max=9d
    standard_service_duration_min: 35

  Policy P2 [A]
    scope: {segment == "A"}
    FrequencySpec: EXACT, target=2, ref=28d, min=2, max=2
    CadenceSpec:   min=10d, max=16d
    standard_service_duration_min: 30

  Policy P3 [B]
    scope: {segment == "B"}
    FrequencySpec: RANGE, target=2, ref=28d, min=1, max=2
    CadenceSpec:   min=10d, max=18d
    standard_service_duration_min: 25
    (RANGE 的 fulfillment 分层表达见 §3.1 PROOF-E1)

  Policy P4 [C]
    scope: {segment == "C"}
    FrequencySpec: EXACT, target=1, ref=28d, min=1, max=1
    CadenceSpec:   min=1d, max=28d   ← v1.1 补 neutral cadence（单次拜访无间隔约束，跨度=全参考期）
    standard_service_duration_min: 20

PlanningPolicy:  mode=TACTICAL_PJP, freeze_days_count=0, max_reassignment_ratio=1.0
ObjectivePolicy: profile=BALANCED_STABILITY（canonical 层级见 §2.5）

Ownership（v1.1：Stress 独立 fixture）:
  GT-Micro / GT-Small / Standard:
    每客户 OwnershipPolicy.primary=(R001), allow_shared_pool=False
    SubstitutionPolicy.allow_backup=False; EligibilityPolicy 无门槛
  Stress（60×2）:
    30 客户 primary=(R001)、30 客户 primary=(R002)（按 territory 剖分）
    allow_shared_pool=True（验证共享池）；allow_backup=True, backup=同区另一 rep

DeferralPolicy ×2（DCR-SA-001-R 批准后：经 BusinessRequirement.exception_handling_policy_ref 绑定，A03 v1.0.1）:
  DP-STD: deferrable=True, max_deferral_days=7,
          escalation=NOTIFY_REGION_MANAGER, unmet_consequence=OPPORTUNITY_LOSS
  DP-SLA: deferrable=False, max_deferral_days=0,
          escalation=ESCALATE_TO_DIRECTOR, unmet_consequence=SLA_BREACH_REPORT
  绑定（Requirement 级）:
    R3 "B 类底线覆盖为运营承诺"  authority=COMPANY_POLICY → exception_handling_policy_ref="DP-STD"
    R4 "C 类含合同 SLA 巡检"     authority=CONTRACT     → exception_handling_policy_ref="DP-SLA"
  冲突解析: 本场景 ConflictResolutionStrategy = {order: [authority, strength]}
  （Scenario 级配置；A03 不定义全局排序——见 v1.0.1 patch 注释）

ExistingCommitment: 第 2 周周三 1 个 DAY_LOCKED 拜访（TA-LOCK）
```

## §2.3 Expected VisitDemand / VisitOccurrence

`OccurrenceGenerator(Policy + Horizon + ExecutionHistory) → occurrences`（v1.1 按 §3.1 分层表达）：

| segment | 客户数 | 需求生成（无 DCR 分层法） | occurrence 计数 |
|---|---|---|---|
| KA | 2 | 1 demand(REQUIRED)/店，EXACT(4) | 2×4 = 8 |
| A | 8 | 1 demand(REQUIRED)/店，EXACT(2) | 8×2 = 16 |
| B | 16 | **2 demand/店**：baseline(REQUIRED, EXACT 1) + stretch(OPTIONAL, EXACT 1)，metadata.policy_ref=P3，CadenceSpec 间隔约束在合并后生效（min=10d 施加于 baseline/stretch 任意两次之间） | 16×1 + 16×1 = 32（REQUIRED 底线 16，OPTIONAL 增量 16） |
| C | 6 | 1 demand(COMMITTED)/店，EXACT(1)；MISSED 店 eligible 前移 | 6×1 = 6 |

**容量设计**：总需求工时（service + travel 校准估计）与 20×480 min 比值 ≈ 0.85–0.95。

## §2.4 BusinessRequirement & Evidence（v1.1：REQ-A-002 改 HARD；新增 REQ-A-006/007）

| req_id | statement | strength | authority | parameter_refs | source_ref |
|---|---|---|---|---|---|
| REQ-A-001 | A 类门店每 28 天恰好拜访 2 次 | HARD | COMPANY_POLICY | param.freq_a=2, param.period=28d | SOP-FMCG-2026-014 |
| REQ-A-002 | 同店两次拜访间隔至少 10 天 | **HARD**（基线零违规；HARD→SOFT 降级留给 MM-5） | COMPANY_POLICY | param.gap_min_a=10d | SOP-FMCG-2026-014 |
| REQ-A-003 | 业务员单日工作不超过 8 小时 | HARD | LEGAL | param.daily_cap=480min | LABOR-LAW-CN-§36 |
| REQ-A-004 | 门店在店时间采用政策标准时长；ObservedStopTime 32min 为其校准证据（不叠加） | —(参数) | — | param.stop_time_evidence=32min(CALIBRATED, UNKNOWN breakdown) | 319 条打卡中位数 |
| REQ-A-005 | 锁定承诺不可移动 | HARD | MANAGER_RULE | — | commitment 记录 |
| **REQ-A-006** | 上周期 MISSED 的客户，本周期首次 eligible 日期前移且 fulfillment 升为 COMMITTED（漏访重生） | SOFT | COMPANY_POLICY | param.missed_priority_days | SOP-FMCG-2026-021 |
| **REQ-A-007** | 上周期已完成访问可抵扣本期 occurrence（历史抵扣：若上次访问距 horizon 起点 ≤ 抵扣窗口，本期减 1 次） | SOFT | COMPANY_POLICY | param.carryover_window_days | SOP-FMCG-2026-021 |
| **REQ-A-008 (R3)** | B 类底线覆盖未满足时按 DP-STD 处理（defer≤7d→RM 通知） | SOFT | COMPANY_POLICY | —（exception ref: DP-STD） | SOP-FMCG-2026-014 |
| **REQ-A-009 (R4)** | C 类合同 SLA 巡检未满足时按 DP-SLA 处理（立即升级总监） | HARD | CONTRACT | —（exception ref: DP-SLA） | CONTRACT-X-2026-88 |

## §2.5 Canonical Decision Objective（v1.1 新增；三 formulation 必须编译同一目标）

```
L1  所有 HARD requirements 可行（REQ-A-001/002/003/005）
L2  最大化 REQUIRED + COMMITTED fulfillment（满分 = 8+16+16+6 = 46 occurrence；
    B 类底线 16 计入 REQUIRED；C 类 6 计入 COMMITTED）
L3  最大化 OPTIONAL business value（B 类 stretch 16 次 × unit value 1.0；
    value 表由 Scenario 装配物给定，三 formulation 共享同一数值）
L4  cadence soft penalty + plan stability penalty
    （本场景无 prior plan → stability 项=0；MM/TA-LOCK 中按 §4 定义激活）
L5  最小化 total work time = Σ route travel(校准) + Σ service_duration

比较口径: lexicographic (L1 非可行即整体不可行; L2 → L3 → L4 → L5 依次最优)。
Reporting: 各 backend 输出五层元组 (L1_status, L2, L3, L4, L5)，Gate A3 按元组逐层比对。
```

## §2.6 Feasibility Boundaries（v1.1：TA-INF 反例修正为真不可行构造）

```
Structural Feasible（必须有解）:
  GT-Micro / GT-Small / Standard: 全部 EXACT + B 底线(RANGE min=1) 可满足。

Capacity Tight（优雅短缺，不得 INFEASIBLE）:
  TA-CAP: 工时压至 ~70% → B stretch（OPTIONAL）被 defer，
  输出 admitted/deferred + DeferralPolicy.unmet_consequence=OPPORTUNITY_LOSS。

Structural Infeasible（显式 PROVEN_INFEASIBLE + 归因）:
  TA-INF（v1.1 修正版）: KA 客户 EXACT(4) + CadenceSpec min=10d
    + TargetAvailability 仅周二可用。
    28 天内仅 4 个周二(间隔 7d < 10d)，任两访间隔 < min_gap
    → 4 次拜访在间隔约束下无合法组合 → PROVEN_INFEASIBLE，
      归因: REQ-A-002(cadence HARD) × availability 冲突。
  (v1.0 的 A 类示例实为可行——两个周二可隔 14d，已废弃。)
```

## §2.7 Expected Audit Result

```
frequency_compliance(EXACT + B 底线)  = 100%
cadence_violations(REQ-A-002 HARD)    = 0
capacity_violations(480min HARD)      = 0
availability_violations               = 0
committed_fulfillment                 = 1/1（锁定）+ 6/6（C 类 COMMITTED）
B stretch capture                     = 记录 captured/16（L3 指标，非违规）
TA-CAP: shortfall 报告（admitted/deferred 明细）             非 error
        且含 Exception Audit Trace 四段链:
        R3 → DP-STD → defer(≤7d) → reason=capacity_shortage
        R4 → DP-SLA → escalate → reason=capacity_shortage   （TA-CAP 下 R4 若未满足）
TA-INF: PROVEN_INFEASIBLE + 结构归因                        非 defer
```

## §2.8 Candidate Mathematical Formulations（v1.1：统一 routing coupling 声明）

**Joint 声明**：本 Spike 为 **schedule-first + exact route-evaluation coupled**：
1. 日期指派由各 formulation 决策；
2. 每个被选工作日的客户子集，其 route travel 由**同一 Held-Karp RoutingOracle（≤9 家精确）**求值；
3. route cost 作为该日容量约束与 L5 目标的组成部分**反馈进 formulation**（F2/F3 经 lazy day-cost 回填：先解 assign → 逐日 HK 评价 → 若容量/L5 变化超阈值则重解，至多 2 轮）；
4. 该耦合的近似性记入 `ApproximationDeclaration`（gap ≤ 第 2 轮阈值 ε_couple）。

| # | Formulation | 频次/间隔表达 | 容量/路线表达 | Model Size 特征 |
|---|---|---|---|---|
| F1 | **Pattern formulation** | 模式集 $P_i$（如 KA {W1..W4}，A {W1W3,W2W4}，B 底线+stretch 组合） + $\sum_{t\in D_w}x_{it}=\sum_p B_{ipw}y_{ip}$ | 日容量: $\sum_i s_i x_{it} \le cap$；travel 以 HK 评价回填日权重 | 变量最少；模式枚举可控 |
| F2 | **Date-index compact MIP** | $x_{it}\in\{0,1\}$；$\sum_t x_{it}=f_i$；$x_{it_1}+x_{it_2}\le 1,\ |t_2-t_1|<\Delta_{\min}$（**无 λ 列变量**） | 同 F1 的日容量 + travel 回填日系数 | 通用；N×T bool |
| F3 | **CP-SAT native** | 同 F2 语义，AddExactly/AddBoolOr 互斥链；可选 day interval | 整数容量不等式（×100 定点） | 离散传播强 |

**F2 明确修正**：v1.0 TRACE-3 混入的 $\lambda_{rt}$ 属列生成表达，已从 F2 移除；F2 的容量约束一律 date-index 形式。

## §2.9 Candidate Backends

| Backend | 角色 | 备注 |
|---|---|---|
| MathOpt → HiGHS / SCIP | F2 主力（LP/MIP + dual/bound） | |
| 原生 CP-SAT cp_model | F3 主力 | interval 原语（MathOpt 暂缺 #5144） |
| **GT 独立 exact model** | GT-Small oracle（CP-SAT 独立实现，求到 OPTIMAL+bound；非本套 F1/F2/F3） | 保证 oracle 独立性 |
| Held-Karp DP | RoutingOracle：所有日 route 精确成本 | 三 formulation 共用同一 oracle |
| GCG / Coluna | **候选 Spike，非必须** | compact 满足规模/时延/质量即保留简单方案 |
| VRPSolverEasy | 备选 oracle 交叉验证（R&D 定位不变） | |

## §2.10 Ground-truth / Oracle（v1.1：两层结构）

```
GT-Micro（6 客户 × 10 工作日）:
  • 真·穷举: 枚举全部 assignment（容量内），每日子集 route 由 Held-Karp 精确求值。
  • 产出: 全可行集 F* 与 canonical 目标五层元组的最优 obj*。
  • 用途: F1/F2/F3 各自 backend 的逐层语义一致性比对（A3 Gate 第一段）。

GT-Small（10 客户 × 20 工作日）:
  • 不做全枚举。由 §2.9 的独立 exact model 求到 status=OPTIMAL（附 bound/gap=0）。
  • 产出: oracle 参考解与目标元组。
  • 用途: A3 Gate 第二段（大规模下与 oracle 元组一致，容差 1e-4）。
```

## §2.11 Acceptance Criteria（v1.1 对齐 canonical objective）

```
AC-1  GT-Micro & GT-Small: F1/F2/F3 的 (L1..L5) 五层元组与 oracle 逐层一致
      （OPTIMAL 时；route 顺序不要求一致，L5 由同一 HK oracle 评估）。
AC-2  Standard: EXACT+B底线 100% 覆盖；cadence=0；HARD 工时=0；committed 全保。
AC-3  TA-CAP: admitted/deferred/shortfall+reason，无 INFEASIBLE 崩溃。
AC-4  TA-INF: PROVEN_INFEASIBLE + 归因 REQ-A-002×availability。
AC-5  TA-LOCK: 锁定 visit 日期/资源不变。
AC-6  编译零手改: 三 formulation 从同一 Scenario 装配物编译；业务对象未动；
      耦合近似已记入 ApproximationDeclaration(ε_couple)。
AC-7  Trace: §2.15 三链路在 DecisionTrace 机读可检索。
AC-8  口径唯一: 任何输出中 service 与 stop_time 不重复计入（审计断言）。
```

## §2.12 Metamorphic Tests（v1.1 语义锚定 canonical 元组）

| ID | 关系 | 断言（按 §2.5 层级） |
|---|---|---|
| MM-1 | 增加资源容量 | L2 未满足数不增；L3 捕获不减 |
| MM-2 | 放宽时间窗 | L1 可行性不降 |
| MM-3 | 删除 OPTIONAL（B stretch） | L2/L4/L5 各层指标不变差 |
| MM-4 | 延长规划时域 | 原 HARD 可行解仍存在 |
| MM-5 | REQ-A-002 HARD→SOFT | 不得 feasible→infeasible（L1 保持） |
| MM-6 | 锁定已满足 visit | 该 visit 资源/日期不变 |

## §2.13 Benchmark Metrics

```
Feasibility / Mandatory fulfillment / Committed fulfillment /
Optional value captured / Cadence violations / Travel time / Total work time /
Plan stability / Objective bound & gap（分层报告 L1..L5） /
Runtime(s) / Memory(peak) / Model build time / Solver time /
Compilation complexity / Proof level / Backend integration complexity
Model Size: variables / constraints /（列生成时:columns）（F1 时:patterns）
Coupling: HK evaluation rounds / ε_couple achieved
```

## §2.14 Domain Coverage Matrix（A03 对象使用清单，v1.1）

| A03 对象 | 使用 | 字段 | 备注 |
|---|---|---|---|
| VisitTarget | ✅ | location, territory_id, availability, business_attributes.segment | |
| TargetAvailability / WeeklyAvailabilityRule | ✅ | weekday_to_time_windows, blackout | 2 家 B 类周分化 |
| SalesResource / ResourceAvailability / ResourceDayProfile | ✅ | default_policy, date_profiles(请假), capacity_min | |
| VisitPolicy / PolicyScope / FrequencySpec / CadenceSpec | ✅ | 全字段；EXACT+RANGE；P4 neutral cadence | |
| VisitDemand / DemandReason / FulfillmentClass | ✅ | B 店 baseline(REQUIRED)+stretch(OPTIONAL) 双 demand | §3.1 |
| VisitOccurrence / ExecutionHistory | ✅ | 漏访重生（REQ-A-006）+ 抵扣（REQ-A-007） | |
| MergePolicy / VisitCandidate | ✅ | 同店 baseline+stretch 合并 1 candidate（间隔约束施加于合并后集合） | §3.1 |
| OwnershipPolicy / SubstitutionPolicy / EligibilityPolicy | ✅ | Stress 独立 fixture（R001/R002 剖分+共享池+backup） | §2.2 |
| DeferralPolicy | ✅ | DP-STD/DP-SLA；绑定关系见 §3.2 | |
| ExistingCommitment / CommitmentLock | ✅ | DAY_LOCKED ×1 | |
| LifecycleState | ✅ | PROPOSED→PLANNED | |
| BusinessRequirement / RequirementRegistry | ✅ | 7 条（§2.4） | |
| ParameterRegistry / ParameterDescriptor | ✅ | freq/gap/cap/stop_time_evidence/carryover | |
| PlanningPolicy / ObjectivePolicy / PlanningHorizon / WorkingCalendar | ✅ | TACTICAL_PJP；BALANCED_STABILITY→canonical §2.5 | |
| 未使用 | CAMPAIGN 等动态 reason、Route 层多数字段 | — | 属 B/E 范围 |

## §2.15 Compilation Trace Example（v1.1：F2 纯 date-index；含 L 层）

```
TRACE-1（频次，REQ-A-001）
  REQ-A-001 (A类 28d 恰 2 次, HARD, COMPANY_POLICY)
    → ParameterRegistry: param.freq_a=2, param.period=28d
    → F1: y_ip ∈ {W1W3, W2W4};  F2: Σ_t x_it = 2;  F3: AddExactly(2, [x_it])
    → ConstraintTag: PATTERN_SELECT_C{i}(F1) / COVERAGE_C{i}(F2/F3)
    → Result: L2 coverage = 16/16 (A 段)

TRACE-2（间隔，REQ-A-002）
  REQ-A-002 (同店间隔 ≥10d, HARD)
    → param.gap_min_a=10d
    → F1: 模式集预过滤(仅留合法组合);  F2: x_it1+x_it2≤1 ∀|t2-t1|<10;
       F3: AddBoolOr(¬x_it1, ¬x_it2) 链
    → ConstraintTag: GAP_C{i}_D{t1}_D{t2}
    → Result: cadence_violations=0

TRACE-3（容量，REQ-A-003）— v1.1 修正: 无 λ 变量
  REQ-A-003 (单日 ≤480min, HARD, LEGAL)
    → param.daily_cap=480min; on-site=service_duration(政策); stop_time 仅证据
    → F2: Σ_i (svc_i + hk_travel_coeff_t·x_it) ≤ 480   (hk 系数由耦合回填, §2.8)
       F3: 同语义整数式(×100)
    → ConstraintTag: DAY_CAPACITY_D{t}
    → Result: capacity_violations=0; ApproximationDeclaration 记录 ε_couple

TRACE-4（异常处理审计链，DCR-SA-001-R / v1.1 新增）
  REQ-A-008 (B 底线未满足, COMPANY_POLICY, exception_ref=DP-STD)
    → DeferralPolicy DP-STD (deferrable=True, max=7d, NOTIFY_RM)
    → Action: defer → reschedule in ≤7d
    → Reason: resource capacity shortage (TA-CAP)
    → DecisionTrace 四段链机读可检索: R3→DP-STD→defer→reason
```

## §2.16 Expected Failure Cases（v1.1）

| ID | 错误输入/冲突 | 期望行为 |
|---|---|---|
| FC-1 | 坐标越界 (95.0, 500.0) | 装配期 Semantic 拒绝，定位 target |
| FC-2 | KA EXACT(4)+仅周二+min_gap 10d（真不可行，=TA-INF） | PROVEN_INFEASIBLE + 归因 REQ-A-002×availability |
| FC-3 | ParameterRegistry 缺 param.stop_time_evidence | 编译期显式失败（禁止静默默认值） |
| FC-4 | PolicyScope 引用不存在属性 | PolicyScope.matches 校验失败 |
| FC-5 | DP-SLA(deferrable=False) 客户容量不足 | escalation=ESCALATE_TO_DIRECTOR（非 INFEASIBLE） |
| FC-6 | service 与 stop_time 在审计中双计 | AC-8 断言失败（口径守卫） |

## §2.17 Architecture Change Log & DCR Register

```
Change Log: [ EMPTY by default ]（规则同 v1.0：须挂可复现 Failure；"实现不方便"无效）

DCR Register:
  DCR-SA-001  — Scoped Deferral Policy Binding            [SUPERSEDED by -R]
  DCR-SA-001-R — Requirement-Level Exception Policy Binding [APPROVED 2026-08-22]
    变更: BusinessRequirement.exception_handling_policy_ref (可选, str|None)
    命名裁定: exception_handling（非 deferral 专属——defer/escalate/substitute/
              manual review/drop/transfer 皆由此承载）
    冲突解析: 不写死全局排序; Scenario 级 ConflictResolutionStrategy 配置
    审计要求: Exception Audit Trace 四段链(Unfulfilled Req → Applied Policy
              → Action → Reason) 必须入 DecisionTrace
    Patch 载体: A03 v1.0.1（经变更控制, 基线 v1.0 未被直接编辑）
    设计原则确立: Sales Visit Planning 核心对象是 Requirement Fulfillment;
                  Visit 只是满足 Requirement 的执行载体。
```

---

# 3. Expressibility Proofs

## 3.1 PROOF-E1：RANGE fulfillment 分层表达（结论：无需 DCR）

**命题**：`FrequencySpec(RANGE, min=1, max=2)` 的“第 1 次 REQUIRED、第 2 次 OPTIONAL”可用冻结契约无歧义表达，不依赖 metadata hack。

**表达法**（已写入 §2.2/§2.3）：
1. OccurrenceGenerator 为每个 B 店生成**两条 VisitDemand**：
   - `baseline`: DemandReason=COVERAGE_POLICY, FulfillmentClass=REQUIRED, FrequencySpec=EXACT(1)
   - `stretch`: DemandReason=COVERAGE_POLICY, FulfillmentClass=OPTIONAL, FrequencySpec=EXACT(1)
   - 两者 `metadata.policy_ref = P3`（作为**追溯指针**而非语义载体——语义完全由两个显式 demand 对象承载）
2. CadenceSpec(min=10d) 由 MergePolicy 在合并 baseline+stretch 为同一 VisitCandidate 后施加于“该店本周期全部被排 occurrence 集合”。
3. Trace 检验：REQ→demand(REQUIRED/OPTIONAL)→constraint→result 全链可机读，无隐式约定参与决策。

**结论**：✅ 可表达。语义不依赖 metadata（policy_ref 仅溯源用）；RANGE 语义编译规则 = “拆 N 条 EXACT demand，前 min 条 REQUIRED、余为 OPTIONAL”登记为 OccurrenceGenerator 的规范行为（属编译规范，不新增 A03 对象）。
→ **不提交 DCR**。

## 3.2 PROOF-E2：DeferralPolicy 绑定（结论：提交 DCR-SA-001）

**命题**：能否从冻结的 `SalesVisitPlanningScenario` 聚合中唯一确定“P3 适用 DP-STD、P4 适用 DP-SLA”？

**穷举现有绑定通道**：
| 候选通道 | 冻结契约中的依据 | 判定 |
|---|---|---|
| ① VisitPolicy 内嵌 deferral 字段 | VisitPolicy 无该字段 | ❌ |
| ② VisitDemand 携带 | VisitDemand 无 deferral 引用；若塞 metadata 则属 hack（语义藏在非语义字段） | ❌（违反“无 metadata hacks”判据） |
| ③ list 下标/顺序约定（scenario.deferral_policies[i] ↔ visit_policies[i]） | 契约未定义任何顺序语义；两条 list 长度可不等 | ❌（隐式代码约定，跨实现不可复现） |
| ④ PolicyScope 复用 | PolicyScope 是 VisitPolicy 的字段；DeferralPolicy 自身无 scope 字段，且 Scenario 聚合中无任何“DeferralPolicy→PolicyScope”关系定义 | ❌（无法从聚合推导） |

**失败证据（可复现）**：本场景装配 `visit_policies=[P1..P4], deferral_policies=[DP-STD, DP-SLA]` 后，任一合规编译器都无法从聚合唯一推导 P3→DP-STD、P4→DP-SLA——四种通道均需在契约外引入约定。

**结论**：❌ 冻结契约不可表达 → 原提交 DCR-SA-001；经 DOV 归属验证（MRE-1 证伪 a/b）与评审裁定，**由 DCR-SA-001-R 取代并已批准落地（A03 v1.0.1）**：

```
DCR-SA-001 — Scoped Deferral Policy Binding
  变更: 为 DeferralPolicy 增加绑定关系（最小改动，二选一，由评审裁定）:
    (a) DeferralPolicy.scope: PolicyScope  + DeferralPolicy.policy_id: str
    (b) VisitPolicy.deferral_ref: str  (引用 RequirementRegistry 风格的 registry 键)
  不引入新层次/新对象类型；完全复用既有 PolicyScope/引用模式。
  触发 Failure: FC-5/TA-CAP 中 P3 与 P4 的 deferral 行为无法从聚合确定。
  状态: PROPOSED（等待评审 sign-off；A03 保持 FROZEN 直至批准）
```

---

# 4. 第一批测试设计（8 类，v1.1 修订）

| ID | 测试 | 只允许改动 | 断言核心 |
|---|---|---|---|
| TA-BASE | 基线 28d/2 访 + 模式类策略 | — | occurrence 表（§2.3）逐行命中 |
| TA-POL | 28d/2 → 28d/3（A 类） | 仅 P2.FrequencySpec | Domain 零改动；occurrence=3/店 |
| TA-GAP | min_gap 10d → 12d（v1.1 替换 TA-DAY：preferred weekday 非冻结字段，场景 A 无此需求，不触发 DCR） | 仅 CadenceSpec | 配置级生效；cadence 仍 0 违规 |
| TA-RES | 请假 1 天 | 仅 ResourceAvailability.date_profiles | 当日无排班；其余满足 |
| TA-CAP | 工时 ~70% | 仅 capacity_min | admitted/deferred/shortfall（非 infeasible）；P4 走 DP-SLA escalation |
| TA-INF | FC-2 真不可行 | TargetAvailability+CadenceSpec | PROVEN_INFEASIBLE + 归因 |
| TA-HIST | 上周期提前完成 1 次 | 仅 ExecutionHistory | 抵扣后 occurrence 变化（REQ-A-007） |
| TA-LOCK | committed visit | 仅 ExistingCommitment | 锁定不破坏（连 MM-6） |

---

# 5. Gate A1–A5 判定标准（v1.1 状态）

```
Gate A1 — Domain Gate          [v1.1.1: PASS]
  PROOF-E1(RANGE) ✅ 无需 DCR；
  PROOF-E2 → DCR-SA-001-R 已批准并入 A03 v1.0.1（Requirement 级 exception_handling_policy_ref）。
  A1 关闭。

Gate A2 — Trace Gate           [v1.1.1: READY FOR EXECUTION]
  F2 trace 已修正（无 λ）；canonical objective 已定义（§2.5）；
  TRACE-1/2/3 + TRACE-4(异常审计链, DCR-SA-001-R) 待 Spike 验证;
  必须验证链: Requirement → Exception Policy → Formulation → Result。

Gate A3 — Semantic Equivalence [v1.1.1: 可开始；第一优先验证三 formulation 编译同一业务语义，而非 solver 速度]
  GT-Micro(穷举) + GT-Small(独立 exact) 两层比对五层目标元组。

Gate A4 — Reuse Gate           [保持：任何自写算法须先证成熟 backend 不满足]

Gate A5 — Scenario Pass        [NO；A1–A4 全过 + §4 八类 + MM-1..6 后放行]
```
