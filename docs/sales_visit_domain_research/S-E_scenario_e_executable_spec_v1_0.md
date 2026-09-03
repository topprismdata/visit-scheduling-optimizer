# Scenario E — Rolling Replanning + Commitment/Lock + Execution History：Executable Specification (S-E v1.0)
## Phase B3 · 单维度验证：静态规划 → 动态决策的知识体系支撑力

> **文档标识**：`SE-ROLLING-REPLAN-EXESPEC-V1.0`  
> **所属阶段**：Phase B3（A ✅ C ✅ D ✅ → **E ◀** → B）  
> **验证目标（评审指令精确对齐）**：**不是新增业务概念、不是扩展 Domain**——验证当前 SVDE KB 能否表达 Rolling Replanning + Existing Commitment + Lock + Execution History，即**静态规划走向动态决策**。  
> **架构约束**：A03 v1.0.1 FROZEN 不动；DM-010 保持 Candidate；任何 Domain Change 须 Failure Evidence。  
> **评审预警落实**：动态变化失败时必须分类——A. Domain 缺失（可 DCR）vs B. Compiler/Planning Strategy 问题（不可 DCR）。

---

## 目录
1. [Business Reality 与 Decision Question](#1)
2. [Ontology Dependencies（预声明）](#2)
3. [Candidate Decision Models（含 DM-010 必要性判定实验）](#3)
4. [16 项模板（动态维度裁剪版）](#4)
5. [执行计划 TE-* 系列](#5)
6. [Failure Classification 框架（E 场景核心）](#6)
7. [Gate E 判定](#7)

---

# 1. Business Reality 与 Decision Question

**Business Reality**（评审要求：不是 Input Case，是业务现实）：
```
快消销售组织按 4 周周期排出拜访计划（S-A 世界）。第 2 周开始，现实持续偏离计划：
  • 业务员周二突发请假（资源扰动）
  • 客户 X 的周二承诺必须保住（Existing Commitment 生效中）
  • 上周客户 Y 漏访一次（ExecutionHistory 已记录）
  • 主管临时锁死明天的三连访顺序（SEQUENCE_LOCKED 新增）
  • 客户 Z 出现缺货信号（新增 OPTIONAL 需求注入）
每周一重排未来计划——但过去不可改、承诺不可破、漏访要补、锁定不可动。
```

**Decision Question**（单一、明确）：
> **在执行部分计划已成为事实、部分承诺已锁定、新事件不断注入的条件下，系统能否仅凭冻结 Domain 对象表达"最小破坏重排"所需的全部输入与约束，并输出可审计的重排结果？**

**不验证**（防扩散）：实时毫秒级响应（B）、多资源归属（D 已证）、路由优化（Phase 3）。

---

# 2. Ontology Dependencies（预声明）

| 动态能力 | 承载对象（冻结契约） | A/C/D 已验部分 | E 增量验证点 |
|---|---|---|---|
| **执行历史成为决策输入** | `ExecutionHistory.completed/missed` | S-A TA-HIST（单次抵扣） | **多轮累积**：周1完成→周2重排时抵扣窗口滚动；missed→COMMITTED 升级在滚动中持续生效 |
| **已发生事实不可逆** | `ExecutionHistory` + 时间单向性 | 未验 | 周度切片：past（只读）vs future（可排）边界由 horizon 与 history 联合表达 |
| **承诺保住** | `ExistingCommitment` + `CommitmentLock.DAY_LOCKED` | S-A TA-LOCK（存在性） | **重排扰动下的存活性**：请假/新需求注入后承诺仍不被移动 |
| **锁定升级** | `CommitmentLock.SEQUENCE_LOCKED / COMPLETELY_LOCKED` | 未用 | 主管临时锁——运行期新增 commitment（非初始装配） |
| **新需求注入** | `VisitDemand(SALES_SIGNAL/OUT_OF_STOCK, OPTIONAL)` | S-A 装配期存在 | **周2 动态注入**：原 Scenario 装配物 + 增量 demand 的合并表达 |
| **重排范围控制** | `PlanningPolicy.freeze_days_count + max_reassignment_ratio` | 未用（S-A 均 0/1.0） | freeze=2（过去+当周冻结）、ratio=0.3（未来仅 30% 可动） |
| **漏访补访节奏** | `ExecutionHistory.missed` → OccurrenceGenerator | 单次 | 滚动中 missed 的 eligible 前移 + COMMITTED 升级叠加 cadence 约束 |
| **重排审计** | Exception Audit Trace 四段链 | S-A TA-CAP | **重排差异审计**：哪些移了/哪些没移/为什么（新增 trace 维度，非新对象） |

---

# 3. Candidate Decision Models（含 DM-010 必要性判定实验）

**评审核心问题**：Replanning 是否需要独立 DM-010？还是 DM-006 VisitPlanning + DM-007 ExceptionHandling 已足够？

**判定实验设计**（本场景执行的核心输出之一）：

```
假设 H1: DM-010 独立必要
  论据: 重排有独特决策语义（最小破坏/冻结窗口/差异审计）——静态规划无这些概念

假设 H2: DM-006+007 可覆盖
  论据: 重排= 在收缩可行域上的再规划(006) + 扰动未满足项走异常链(007)

判据: 若 E 的全部决策输入/约束/输出可由 006/007 的 ontology_dependencies 无歧义表达
      且无 Failure Evidence 指出缺失 → H2 成立，DM-010 降级合并
      若出现"重排特有的、006/007 无法承载的决策输入"（如 freeze 窗口语义无处安放）→ H1 成立
```

| DM | E 中角色 | 验证内容 |
|---|---|---|
| DM-010 Replanning | **候选（判定实验对象）** | freeze/ratio/差异审计是否构成独立决策语义 |
| DM-006 VisitPlanning | 基线 | 收缩可行域（past 冻结+commitment 锁定）上的再规划 |
| DM-007 ExceptionHandling | 基线 | 扰动导致的未满足（如请假日 REQUIRED）走 DeferralPolicy 链 |
| DM-003 ReqGeneration | 回归 | missed→COMMITTED 升级 + carryover 在滚动窗口的持续计算 |
| DM-008 ExecutionMonitor | **E 主验** | LifecycleState IN_PROGRESS/COMPLETED/MISSED 首次实际流转 |

---

# 4. 16 项模板（动态维度裁剪版）

## §4.1 Business Inputs
```
E-Base  : S-A Standard 装配物（32 客户×1 业务员×4 周）为初始计划
E-Wk2   : 周一快照注入扰动包：
           • R001 周三 is_absent（新增 DayProfile）
           • 新 commitment: 客户 X 周四 DAY_LOCKED（运行期追加）
           • 主管锁: 周二三连访 SEQUENCE_LOCKED
           • ExecutionHistory 更新: 周1 全部完成 + Y 漏访 1 次
           • 新 demand: Z 缺货 OPTIONAL 注入
E-Wk3   : 周二快照（周2 重排结果的模拟执行 + 新扰动）
时态规则: 快照 t 时刻，ExecutionHistory 含全部 <t 已执行；PlanningPolicy.freeze_days=2
```

## §4.2 Policy Configuration
```
复用 S-A 四段 VisitPolicy + 新增：
  PlanningPolicy: mode=WEEKLY_ROLLING, freeze_days_count=2, max_reassignment_ratio=0.3
  DP-STD/DP-SLA 绑定不变（REQ-A-008/009）
  新 REQ-E-001 (COMPANY_POLICY, HARD): 已执行拜访为不可变事实，重排不得改动其记录
  新 REQ-E-002 (MANAGER_RULE, HARD): COMPLETELY_LOCKED/SEQUENCE_LOCKED 项目零移动
  新 REQ-E-003 (COMPANY_POLICY, SOFT): 重排移动率 ≤ max_reassignment_ratio
```

## §4.3–4.5 Expected Demand / Requirements / Boundaries
```
Wk2 快照后的 occurrence 期望:
  • 周1 已完成 A 类 8 家×2 = 16 次 → carryover 全额抵扣，其 eligible 区间后移
  • Y(missed) → 本周期内 eligible 前移 + COMMITTED
  • Z 新增 1 条 OPTIONAL demand（eligible=本周内）
  • 周1 已执行部分: 出现于 ExecutionHistory 而非重排输出（不可逆性）

Feasibility Boundaries:
  Normal    : 全部约束可满足，承诺保持，ratio 内完成重排
  Tight(TE-CAP2): 请假日恰逢承诺日 → 承诺日不可移+资源不可用 → 
                   STRUCTURAL conflict 显式暴露（承诺保住优先于 infeasible 报错？——
                   判定：HARD×HARD 冲突 → PROVEN_INFEASIBLE + 归因 REQ-E-002×availability）
  Ratio(TE-RATIO): 扰动超出 30% 可动比例 → 部分 OPTIONAL defer + DP 链 + 
                   超限移动被 ratio 约束拒绝（显式 shortfall 而非静默违反）
```

## §4.6–4.7 Expected Audit / Trace
```
重排差异审计（E 新增 trace 维度——非新 Domain 对象）:
  moved:    [{visit, from_day, to_day, reason: WEEKLY_ROLLING}]
  kept:     [{visit, reason: COMMITMENT_LOCKED | FREEZE_WINDOW | RATIO_BUDGET}]
  injected: [{demand: Z-缺货, class: OPTIONAL}]
  regen:    [{target: Y, trigger: MISSED, action: eligible 前移+COMMITTED}]
Exception 链回归: 请假日 REQUIRED 未满足 → R3→DP-STD→defer≤7d→absence
```

## §4.8–4.12 模板占位（Phase 3/4 锁定）
Formulations/Backends/GT/AC 见 §7 Gate；MM 蜕变：MM-E1 freeze 扩大→可移动集不增；MM-E2 ratio 放宽→kept 集不增；MM-E3 删除注入需求→既有解不变差；MM-E4 承诺增加→既有承诺仍保持。

## §4.13 Domain Coverage（E 增量）
| 对象 | E 主验点 |
|---|---|
| PlanningPolicy.freeze_days / max_reassignment_ratio | **首次非零使用**——语义是否足以控制重排范围 |
| CommitmentLock.SEQUENCE_LOCKED / COMPLETELY_LOCKED | **首次使用**——运行期新增锁定 |
| ExecutionHistory | **多轮滚动累积**——决策输入地位确立 |
| LifecycleState IN_PROGRESS→COMPLETED/MISSED | **首次实际流转**（DM-008 主验） |
| ExistingCommitment | **运行期追加**（非初始装配） |

## §4.15 Expected Failure Cases
| ID | 输入 | 期望 |
|---|---|---|
| FC-E-1 | 重排输出改动 ExecutionHistory 记录 | 违反 REQ-E-001 → 显式拒绝（不可逆性守卫） |
| FC-E-2 | 移动 COMPLETELY_LOCKED visit | 违反 REQ-E-002 → 显式拒绝 + 归因 |
| FC-E-3 | ratio=0.3 但扰动需移动 50% | 超 shortfall 显式报告（非静默违反 ratio） |
| FC-E-4 | missed 客户的补访落在 cadence 违反位置 | cadence HARD 优先 → 结构冲突归因 |

---

# 5. 执行计划 TE-* 系列

| ID | 测试 | 快照 | 断言 |
|---|---|---|---|
| TE-BASE | 初始计划→Wk2 重排 | Wk2 | 承诺保持/freeze 内零移动/missed 补访/ratio 内 |
| TE-COMMIT | 承诺存活性 | Wk2 | 请假日≠承诺日 → X 周四承诺日不变、executor 不变 |
| TE-LOCK-SEQ | 序列锁定 | Wk2 | 三连访顺序零改变（即使整体日期可移） |
| TE-HIST-CARRY | 多轮抵扣 | Wk3 | 周1+周2 完成累积抵扣，eligible 滚动后移 |
| TE-HIST-MISSED | 漏访滚动补 | Wk2→Wk3 | Y 补访成功且 COMMITTED；cadence 不因补访违反 |
| TE-INJECT | 新需求注入 | Wk2 | Z OPTIONAL 入候选、不挤占 REQUIRED、DP 链可解析 |
| TE-IRREV | 不可逆性 | Wk2 | 重排输出不含任何已执行 visit（只入 History） |
| TE-RATIO | 比例约束 | Wk2' | 需 50% 移动 vs ratio=30% → shortfall 报告 + 部分 defer |
| TE-INF-COMMIT | 承诺×资源硬冲突 | Wk2'' | 承诺日=请假日 → PROVEN_INFEASIBLE + 归因 E-002×availability |
| TE-DM010 | **DM-010 判定实验** | 全部 | 按 §3 判据输出 H1/H2 结论 + 证据 |

---

# 6. Failure Classification 框架（E 场景核心交付）

每个失败必须先分类（评审指令 §四.4）：

```
Class A — Domain 缺失
  判据: 冻结对象无法表达该业务语义（穷举现有通道失败，如 DOV 方法）
  后果: 可触发 DCR（附 Failure Evidence + Review）

Class B — Compiler / Planning Strategy 问题
  判据: 冻结对象可表达，但解释规则/编译规范/策略配置缺失
  后果: 入 CRR（如 CR-COMPILER-C-001 先例）；Domain 不动

Class C — 测试套件缺陷
  判据: 预期错误/fixture 错误（A/C/D 共 8 起先例）
  后果: 修套件，如实记录

预判高风险点 → 预登记分类假设:
  • freeze 窗口语义不明 → 疑似 B（PlanningPolicy 字段已有，缺解释规则）
  • 重排差异审计无对象 → 疑似 B（trace 维度，非 Domain 对象——若被判 A 则须 DCR 论证）
  • 运行期新增 commitment → 疑似无风险（ExistingCommitment 本就是 list，追加即表达）
```

---

# 7. Gate E 判定

```
Gate E1 — Immutability Gate
  已执行事实零改动（REQ-E-001）；ExecutionHistory 只读于重排。

Gate E2 — Commitment Survival Gate
  全部扰动下 DAY_LOCKED/SEQUENCE_LOCKED/COMPLETELY_LOCKED 项目零移动。

Gate E3 — Rolling History Gate
  多轮 carryover/missed 补访正确累积；DM-003 在滚动窗口持续成立。

Gate E4 — Injection Gate
  运行期新 demand/commitment 注入可表达；注入不破坏既有约束。

Gate E5 — Ratio/Freeze Governance Gate
  重排范围受 PlanningPolicy 控制；超限显式 shortfall（非静默）。

Gate E6 — DM-010 Adjudication Gate
  输出 H1/H2 判定 + 完整证据链（§3 判据）。

Gate E7 — Scenario Pass
  E1–E6 + TE-* 全过 + MM-E1..4 + Classification 全登记 + Change Log 状态如实。
```
