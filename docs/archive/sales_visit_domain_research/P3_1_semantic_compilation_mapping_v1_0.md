# Phase 3.1 — Semantic Compilation Mapping v1.0
## Decision → Mathematical Formulation 三形态映射（F1 Pattern / F2 compact-MIP / F3 CP-SAT）
## 首个数学层执行单元 · 契约 v0_2 Part 5 为唯一入口 · Guard 1/2/3 全程生效 · KG Gate 已签署

> **文档标识**：`P31-SEMANTIC-COMPILATION-MAPPING-V1.0`  
> **执行日期**：2026-08-22  
> **前置门槛**：KG Integrity Review PASS（KB-GOV-011）+ Contract v0_2（11 契约含 backend_binding）  
> **编译范围**：nature=optimization 五决策（BDC-01/02/04/05/06）+ BDC-07 数学面托管声明；BDC-03/08 不编译（generation/monitoring）；NDC-01/02/03 门控出（P6/G-5）  
> **规范目标基准**：S-A §2.5 五级字典序（Frozen——三形态必须编译同一目标，输出 (L1..L5) 五层元组）  
> **形态基础**：S-A §2.8 三 formulation 预注册（本文件扩展至五决策并补元素级溯源）  
> **纪律**：数学元素 100% 溯源冻结对象；F2 无 λ 列变量（§2.8 修正维持）；routing 按 §2.8 Joint 声明（schedule-first + HK oracle 耦合）

---

## 0. Guard 执法声明

| Guard | 本文件执法体现 |
|---|---|
| Guard 1 单向 | 每个数学元素带 `←` 溯源列；§6 Change Log = 0 DCR（无公式驱动概念新增） |
| Guard 2 语义等价 | §5 验证要求全部按契约 validation_requirement；runtime 指标零出现（归 3.4/RMAP-P4） |
| Guard 3 数学优先 | §7 失败处理预登记（失败→Pattern/formulation 检查→三类分类→仅 Class A 穷举失败 DCR；禁词不作为第一反应） |

---

## 1. 共享数学基础（Shared Ground）——五决策共用符号字典

符号是 Domain 对象的**投影**，不是新概念。

### 1.1 集合与索引
| 符号 | 定义 | ← Domain |
|---|---|---|
| $T$ / $R$ / $D$ | 客户集 / 资源集 / 工作日集 | VisitTarget / SalesResource / WorkingCalendar × PlanningHorizon |
| $P_t$ | 目标 t 候选模式集（如 {W1W3, W2W4}） | VisitPolicy × WorkingCalendar 派生（MP-07 形态 a） |
| $O$ | occurrence 集 | VisitOccurrence |

### 1.2 参数（编译期只读）
| 符号 | 语义 | ← Domain |
|---|---|---|
| $f_t$ / $[f^{lo}, f^{hi}]$ | 频次 EXACT / RANGE | FrequencySpec |
| $\Delta^{min/max}_t$ | 间隔边界 | CadenceSpec |
| $s_t$ | 服务时长（**AC-8：stop_time 证据不入**） | VisitOccurrence.expected_service_min |
| $cap_{rd}$ | 日容量 | ResourceAvailability/ResourceDayProfile |
| $w_{td}$ | 目标可用掩码（含例外日） | TargetAvailability/WeeklyAvailabilityRule |
| $u_{trd}$ | 指派可行掩码（三段派生后） | Ownership∪pool∪backup → Eligibility → Availability（S-D） |
| $\ell_t$/$lock(t)$ | 承诺日与锁级 | ExistingCommitment/CommitmentLock |
| $N_{fr}, \rho$ | 冻结天数 / 重排预算 | PlanningPolicy |
| $v_t$ / $c_t$ | OPTIONAL 价值 / 未安排成本 | 装配件 value 表 / DeferralPolicy.unmet_consequence（BE-005） |
| $\bar{x}_{td}$ | 重排前既有解 | PlannedVisit（滚动输入） |

### 1.3 决策变量（三形态共享语义）
| 符号 | 语义 | F1 | F2 | F3 |
|---|---|---|---|---|
| $x_{tdr}$ | t 于日 d 由 r 执行 | $y_{tp}$ 投影 | $\{0,1\}$ | Bool + channeling |
| $y_{tp}$ | 模式选择 | 核心 $\{0,1\}$ | 无（λ 修正） | 无 |
| $z_t$ / $d_t$ / $chg_{td}$ | OPTIONAL 准入 / 短缺 / 变动 | 模式值携带 | $\{0,1\}$ | Bool/Int |

### 1.4 规范目标（S-A §2.5 逐字绑定——三形态唯一目标）
```
L1 ∀ HARD 可行            ← BusinessRequirement(HARD)
L2 max Σ REQUIRED+COMMITTED 履行 ← FulfillmentClass
L3 max Σ v_t·z_t          ← OPTIONAL value
L4 min (cadence 软罚 + stability 罚) ← CadenceSpec(软) + 滚动 plan
L5 min Σ_d travel + Σ s_t·x ← RouteOracle(HK) + expected_service_min
lexicographic；输出五层元组——Gate 逐层比对（AC-1）
```

### 1.5 Routing 耦合（§2.8 Joint 声明维持）
schedule-first：日指派由 formulation 决策 → 选中日子集 route 由**同一 Held-Karp RoutingOracle（≤9 家精确）**求值 → 回填容量与 L5（F2/F3 lazy ≤2 轮，gap 记 ApproximationDeclaration $\varepsilon_{couple}$）。三形态共用 oracle 保证 L5 可比。

---

## 2. 逐决策三形态映射（契约 Part 5 × KBC backend_binding 对齐）

### 2.1 BDC-01 Coverage（允 MP-02/06/07 · 禁 MP-05 · F1/F2→KBC-02/08 · F3→KBC-01）

| 数学元素 | F1 Pattern | F2 compact-MIP | F3 CP-SAT | ← 溯源 |
|---|---|---|---|---|
| 频次 EXACT | $\sum_p B_{tpw} y_{tp}$（模式周计数） | $\sum_d x_{td}=f_t$ | AddExactly | FrequencySpec |
| 频次 RANGE | baseline+stretch 双模式列 | $f^{lo}\le\sum_d x_{td}\le f^{hi}$ | AddAtLeast/AtMost | FrequencySpec（PROOF-E1 分层） |
| 最小间隔 | 模式构造期剪枝 | $x_{td_1}+x_{td_2}\le 1,\ |d_2-d_1|<\Delta^{min}$ | 成对 AddBoolOr(¬x₁,¬x₂) | CadenceSpec.min_gap（MP-07 形态 b） |
| 最大间隔 | 模式剪枝 | 滑窗 $\sum_{d\in W}x_{td}\ge 1$ | AddAtLeastOne(滑窗) | CadenceSpec.max_gap |
| **禁项执法** | 无路径变量 | 无路径变量 | 无路径变量 | MP-05 禁——零 Circuit/route 元素 |

**验证**：Requirement Fulfillment 等价（fulfillment 矩阵逐 Requirement 比对；Scenario A 基准）。

### 2.2 BDC-02 Prioritization（允 MP-06/09/02 · 禁 MP-04 · F1/F2→KBC-02/08 · F3→KBC-01）

| 数学元素 | F1 | F2 | F3 | ← 溯源 |
|---|---|---|---|---|
| OPTIONAL 准入 | stretch 模式选/不选 | $z_t\in\{0,1\}$；$z_t\le\sum_d x_{td}$ | Bool + implication | FulfillmentClass.OPTIONAL |
| L3 价值 | 模式值累加 | $\max\sum v_t z_t$ | 同 F2 | 装配件 value 表 |
| 短缺显式 | 不选即缺 | $d_t=1-z_t$（REQUIRED 入 L2 不可行；OPTIONAL 入 L3 罚） | Bool + channeling | DeferralPolicy（BE-005） |
| 字典序 | 模式枚举序 | **分层求解序列（L1→L5）** | 多解序列 | S-A §2.5（MP-09 形态 d 同构） |

**验证**：Objective Tuple 等价（五层元组逐层）。

### 2.3 BDC-04 ResourceAlloc（允 MP-03/06 · 禁 MP-05 · F1/F2→KBC-02/08 · F3→KBC-01）

| 数学元素 | F1 | F2 | F3 | ← 溯源 |
|---|---|---|---|---|
| 日容量 | $\sum_{t,p} s_t B_{tpd} y_{tp}\le cap_{rd}$ | $\sum_t s_t x_{tdr}\le cap_{rd}$ | 整数不等式（×100 定点） | ResourceAvailability/DayProfile |
| 可用掩码 | 模式仅含可用日 | $x_{tdr}\le u_{trd}$ | 变量禁用 | ResourceAvailability（缺勤） |
| 可行性 | 解存在性 | **LP 松弛可行域（对偶=容量边际——BE-023 语义通道）** | 传播失败=INFEASIBLE+冲突集 | REQ-A-005；S-B 240min 口径 |
| 优雅短缺 | stretch 不选 | $d_t$ 显式+罚（TA-CAP 不得崩溃） | 同 F2 | DeferralPolicy |

**验证**：Feasibility 等价（可行/短缺/不可行三态 + TA-INF 归因 REQ-A-002×availability）。

### 2.4 BDC-05 Assignment（允 MP-01/06 · 禁 MP-04/05 · F1/F2→KBC-02/08 · F3→KBC-01 partial）

| 数学元素 | F1 | F2 | F3 | ← 溯源 |
|---|---|---|---|---|
| 指派唯一 | 列互斥 | $\sum_r x_{tdr}\le 1$ | AddAtMostOne | PlannedVisit.resource_id |
| 三段掩码 | 列构造期过滤 | $x_{tdr}\le u_{trd}$（pool→elig→avail 三段合成掩码） | 同 F2 | Ownership/Substitution/Eligibility/Availability（MRE-D-1..3） |
| 单资源退化 | 掩码恒真 | 同左 | 同左 | S-A 单人 |
| 审计链 | 列=五要素记录 | (owner, executor, via, trigger, policy_ref) 解后重建 | 同 F2 | S-D 五要素 |

**验证**：Requirement Fulfillment 等价（三段排除集 + 指派记录一致）。

### 2.5 BDC-06 VisitPlanning（允 MP-04/05/06/07/08——联合主战场 · F1/F2→KBC-02 · F3→KBC-01 · oracle=HK）

基础三形态 = S-A §2.8 预注册维持（F1 模式列 / F2 date-index 无 λ / F3 CP-SAT 原生）。扩展面（E/B 维度，全部溯源）：

| 扩展面 | F1 | F2 | F3 | ← 溯源 |
|---|---|---|---|---|
| 日内时序 | 无（schedule-first） | 无 | **interval + no-overlap + sequence（MP-04 本体）** | TimeWindow/WeeklyAvailabilityRule |
| 行程（单日） | HK 回填 | HK lazy 回填 | HK 回填 | MP-05 单日腿（≤9 家） |
| DAY_LOCKED | 模式锁定含承诺日 | $x=\bar{x}$ 常数固定 | literal 固定 | ExistingCommitment |
| SEQUENCE_LOCKED | 模式含序 | 顺序布尔传递闭包 | **AddCircuit/顺序链** | CommitmentLock.SEQUENCE_LOCKED |
| COMPLETELY_LOCKED | 全锁 | 日+资源双固定 | 双固定 | CommitmentLock |
| 冻结窗口 | 模式前 $N_{fr}$ 日同 $\bar{x}$ | $x_{tdr}=\bar{x}_{tdr}\ \forall d<N_{fr}$ | 同 F2 | PlanningPolicy.freeze_days |
| 重排预算 | 模式差计数 | $\sum chg_{td}\le\rho|future|$（超限→shortfall 显式） | 同 F2 | PlanningPolicy.ratio（TE-RATIO） |
| 扰动注入 | 追加模式列 | 追加 $x$ 行 | 追加 Bool | VisitDemand 注入（TE-INJECT） |
| 漏访重生成 | 模式重构 | eligible 重算新约束 | 同 F2 | ExecutionHistory.missed |
| 历史不可逆 | 模式不含已执行日 | $x_{td}=0\ \forall d\in executed$ | 同 F2 | ExecutionHistory（REQ-E-001） |

**MP-08 编排注记**（契约 mp08_note 对齐）：RollingHorizon 是 **orchestration pattern 非 solver pattern**——单期实例由 MP-04/06 承载，滚动编排在 DecisionModelCompiler 层实现（冻结/预算/承诺在各形态中的上表执法即为编译层职责）。

**验证**：全四指标（锁零移动/注入不挤占/冻结零移动/预算显式——S-A/C/E 联合基准）。

### 2.6 BDC-07 ExceptionHandling（policy——不独立编译）
托管声明：$d_t$ 与 L4 软罚**内嵌 BDC-02（L2/L3 边界）与 BDC-06（L4）**；四段异常链为解后解释层输出。验证=策略链回归（S-A/S-E），不入 GT-Micro 目标函数。

---

## 3. Trace 要求（AC-7）
每形态输出机读 DecisionTrace，三元组 `(Domain object → Math element → Solver binding)` 逐元素可检索（例：`CadenceSpec.min_gap → x_td1+x_td2≤1 → CP-SAT AddBoolOr`）。三形态 trace 同构，仅 binding 列不同。

## 4. 规模档位（S-A §2.1 维持）
GT-Micro 6×1×2周（穷举）/ GT-Small 10×1×4周（独立 exact）/ Standard 32×1×4 / Stress 60×2×4。**本文件为零代码映射——实施验证归 3.2/3.3。**

## 5. 等价验证汇总（契约 × 五决策）
| 决策 | 验证类型 | GT-Micro 投影 |
|---|---|---|
| BDC-01 | Requirement Fulfillment | fulfillment 矩阵 |
| BDC-02 | Objective Tuple | (L1..L5) 逐层 |
| BDC-04 | Feasibility | 三态判定+归因 |
| BDC-05 | Requirement Fulfillment | 三段排除集+指派记录 |
| BDC-06 | 全四指标 | 四守卫断言 |
| BDC-07 | 策略链回归（托管） | 解后解释输出 |

## 6. Domain Change Log
**EMPTY**——0 DCR；全部数学元素溯源冻结对象（§1/§2 ← 列）。Guard 1 执法记录：零公式驱动概念新增。

## 7. 失败处理预登记（Guard 3）
1. 查 Pattern 选型（契约 allowed/forbidden 误用？）；2. 查 formulation 表达力（F1 模式构造 / F2 线性化 / F3 原语缺失）；3. 三类分类（A Domain/B Compiler→CRR/C 套件）；4. 仅 Class A 穷举失败 → DCR（附 Failure Evidence）。禁词（DynamicXXX/ExceptionXXX/OptimizationXXX）不作第一反应。

## 8. 状态推进
```
Phase 3.0 契约 v0_2          ✅（KG Gate 签署 + 11 backend_binding）
Phase 3.1 本映射 v1.0        ✅（五决策三形态 + 元素级溯源 + 0 DCR）
Phase 3.2 GT-Micro Oracle    ← 下一（穷举 + KBC-05 第四方仲裁）
Phase 3.3 F1/F2/F3 等价      ← 3.2 后
Phase 3.4 Performance        ← =RMAP P4（runtime 自此才入视野）
```
