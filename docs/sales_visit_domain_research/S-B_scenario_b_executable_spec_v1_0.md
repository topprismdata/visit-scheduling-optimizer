# Scenario B — Dynamic Opportunity + Intraday Emergency：Executable Specification (S-B v1.0)
## Phase 2 收官 · Opportunity-driven Decision 的最高级别 Domain Freeze 验证

> **文档标识**：`SB-DYNAMIC-OPPORTUNITY-EXESPEC-V1.0`  
> **所属阶段**：Phase 2 最后场景（A ✅ C ✅ D ✅ E ✅ → **B ◀**）  
> **验证目标（评审指令对齐）**：验证 Dynamic Opportunity + Intraday Emergency 能否由现有 **Ontology + Decision Model + Exception Handling + Execution History** 表达。  
> **最高级别冻结**：禁止因动态性新增 Entity；禁止因实时性新增 Domain；禁止因算法复杂新增 Decision Model。任何新增必须提交 Failure Evidence。  
> **评审三检查点**：Check-1 Opportunity 归属 / Check-2 Priority 归属 / Check-3 日内应急归属。

---

# 1. Business Reality 与 Decision Question

**Business Reality**：
```
业务员上午 8:30 已按今日计划出发（5 个 PlannedVisit，其中 V3 为 COMPLETELY_LOCKED 客户约定）。
运行中发生四类外部事件：
  E1 9:02 新机会门店 W 释放补货信号（SIGNAL opportunity——非既有 32 客户）
  E2 9:15 既有客户 M 打电话：紧急缺货，要求今天必须来（CUSTOMER_REQUEST 紧急）
  E3 9:40 营销部通知：区域 CAMPAIGN 临时任务，本周内完成即可（柔性机会）
  E4 10:00 V2 客户临时取消今日拜访（CANCELLED 事件）
系统须在"今天"内决策：接不接、插在哪、挤掉谁、记什么。
```

**Decision Question**：
> **外部事件产生的新需求（而非既有 Requirement 变化），能否仅凭冻结 Domain 完成从"事件→需求→候选→当日插入→异常处理→执行记录"的全链路表达，且不新增任何业务对象？**

**不验证**：实时响应延迟、多业务员协同（D 已证）、路由顺序（Phase 3）。

---

# 2. 评审三检查点：预注册判定实验

| Check | 问题 | 假设 | 判据 |
|---|---|---|---|
| **Check-1** | Opportunity 是 Requirement 来源还是新 Domain 对象？ | **H-A：来源**——`DemandReason` 枚举已含 SALES_SIGNAL/OUT_OF_STOCK/CAMPAIGN/CUSTOMER_REQUEST 四个动态来源；机会=带 reason 的 `VisitDemand` | 若机会语义（来源/时限/优先级含义）可由 VisitDemand+reason 无歧义表达 → 来源；若需要"机会独有字段无处安放"→ 才是新对象（须 Failure Evidence） |
| **Check-2** | Priority 是 Ontology 还是 Decision Policy？ | **H-策略**——`VisitCandidate.priority_score` 已是**派生字段**（由 FulfillmentClass×reason×recency 计算的决策策略产物），非实体 | 若所有优先级语义=score 计算+排序策略 → 归 DM-002；仅当需要"优先级实体间关系"才升 Ontology |
| **Check-3** | 日内应急是否独立于 Replanning/Exception？ | **H-复用**——E 已证 H2（重排=006+007 动态执行模式）；应急=窄窗口 REQUIRED demand 注入 + 被挤占项走 DeferralPolicy 链 | 若应急=注入+插入+挤占异常三段全部可由现有对象表达 → 复用；不设 Emergency DM |

**附加两判定**（评审指令 4/5）：
- **DM-008 门槛**：Execution Monitoring 是否有独立业务问题（"计划 vs 实际的偏离是什么"）且不可被 006（生成计划）/007（违反处理）承载？
- **DM-009 存在性**：Capacity Planning 是否存在独立于 DM-004 的**战略级**业务决策？（五场景全部战术级——若无场景证明独立 → 按 A5 预登记合并）

---

# 3. Ontology Dependencies（预声明）

| 动态能力 | 承载对象（冻结） | B 增量验证点 |
|---|---|---|
| 机会事件→需求 | `VisitDemand.reason∈{SALES_SIGNAL,CAMPAIGN,CUSTOMER_REQUEST}` | **新目标 W 的机会 demand 生成**（非既有 Requirement 变化） |
| 紧急插入 | `VisitDemand(CUSTOMER_REQUEST, REQUIRED, 当日 DateRange)` | 窄窗口 REQUIRED 的 eligible 表达 |
| 优先级 | `VisitCandidate.priority_score + FulfillmentClass` | score 派生策略 + 排序（无 Priority 实体） |
| 被挤占处理 | `DeferralPolicy` 四段链 | OPTIONAL 被紧急插入挤占 → defer 显式落盘 |
| 取消事件 | `LifecycleState.CANCELLED` | 运行期 PlannedVisit 状态流转（**首次**） |
| 锁定保护 | `CommitmentLock.COMPLETELY_LOCKED` | 挤占决策不得动锁定项 |
| 执行监测 | `ExecutionHistory + LifecycleState IN_PROGRESS/COMPLETED/MISSED` | 当日状态机 + 偏离检测（DM-008 主验） |
| 容量判定 | `ResourceAvailability.capacity_min` 战术口径 | 当日剩余容量 → 插入可行性（DM-004 口径） |

---

# 4. 执行计划 TB-* 系列

| ID | 测试 | 断言 |
|---|---|---|
| TB-OPP-NEW | 新门店 W 机会（SIGNAL） | VisitDemand(reason=SALES_SIGNAL) 生成→occurrence→candidate 全链路；W 无既有 VisitPolicy 也能以 demand 直入 |
| TB-OPP-CAMPAIGN | CAMPAIGN 柔性任务 | OPTIONAL + 本周窗口；不挤占 REQUIRED |
| TB-EMERG-INSERT | 紧急 M 当日插入 | REQUIRED 窄窗口 eligible=today；插入成功；容量口径判定 |
| TB-EMERG-DISPLACE | 挤占走 DP 链 | 被挤 OPTIONAL → defer≤7d 四段落盘；**锁定项零移动** |
| TB-CANCEL | V2 取消 | LifecycleState→CANCELLED 流转；容量释放反映到后续插入 |
| TB-PRIORITY | 优先级=策略派生 | priority_score 计算规则可解释；排序=DM-002 策略；**无 Priority 实体** |
| TB-MONITOR-LIFE | 当日状态机 | PROPOSED→PLANNED→IN_PROGRESS→COMPLETED/MISSED/CANCELLED 全态可达且单调 |
| TB-MONITOR-DEV | 偏离检测 | MISSED/CANCELLED 与计划 diff → 触发 regen（DM-003）与 DP 链（DM-007）输入 |
| TB-CAPACITY | 容量判定口径 | 当日剩余容量=capacity−已完成−已锁；插入判定用此口径（DM-004，无战略对象） |
| TB-DM008 | DM-008 门槛判定 | 独立业务问题/独立输入/006-007 不可承载 三判据输出 |
| TB-DM009 | DM-009 存在性判定 | 五场景全战术级证据汇总 → 独立/合并结论 |
| TB-FREEZE | 冻结守卫 | 全部 TB 执行后 A03 对象数 47 不变；零新实体引用 |

# 5. Failure Classification（同 E 三类框架）

预判：机会时限语义（"今天必须"）→ 疑似无风险（DateRange 即表达）；取消恢复策略 → 疑似 B；其余按实登记。

# 6. Gate B 判定

```
B1 Opportunity Gate      — Check-1 判定 + 证据
B2 Priority Gate         — Check-2 判定 + 证据
B3 Emergency Gate        — Check-3 判定 + 证据（不设 Emergency DM）
B4 Lifecycle Gate        — 全状态机 + 取消/偏离
B5 DM Adjudication Gate  — DM-008 独立性 + DM-009 存在性 双裁定
B6 Freeze Gate           — 47 对象零新增 · 零 DCR 或 DCR 提交
B7 Scenario Pass         — TB-* 全过 + Classification 全登记
```
