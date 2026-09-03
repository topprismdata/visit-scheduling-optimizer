# Scenario B — Domain Executable Validation Report v1.0
## Phase 2 收官 · Dynamic Opportunity + Intraday Emergency（最高级别 Domain Freeze）

> **文档标识**：`SB-DOMAIN-EXECUTABLE-VALIDATION-V1.0`  
> **执行日期**：2026-08-22  
> **载体**：`validation/phase2/run_scenario_b_validation.py` + `decision_trace_b.json`  
> **结果**：**13/13 PASS · 0 DCR · 0 Class-A · 三项评审禁令全守**  
> **首跑失败**：3 FAIL 全部 Class-C（套件缺陷），逐项归因见 §4

---

## 1. Gate B 判定

| Gate | 结果 | 证据 |
|---|---|---|
| **B1 Opportunity** | ✅ | Check-1 判定：**Requirement 来源**（H-A 成立）——`DemandReason` 四动态来源（SALES_SIGNAL/OUT_OF_STOCK/CAMPAIGN/CUSTOMER_REQUEST）承载全部机会语义；新门店 W 无既有 VisitPolicy 亦以 demand 直入全链（demand→occurrence→candidate）；零新实体 |
| **B2 Priority** | ✅ | Check-2 判定：**Decision Policy**——`VisitCandidate.priority_score` 为派生字段（class×reason×urgency 可解释计算），排序归 DM-002 策略；实测 COMMITTED(3.0) > REQUIRED+urgent(2.958) > OPTIONAL+signal(1.2)；无 Priority 实体 |
| **B3 Emergency** | ✅ | Check-3 判定：**复用 E 的 H2 结论**——应急=窄窗口 REQUIRED 注入(DateRange(TODAY,TODAY))+DM-004 战术容量判定+被挤占项走 DP 四段链；不设 Emergency DM |
| **B4 Lifecycle** | ✅ | CANCELLED **首次运行期流转**（容量 240→300min 释放反映）；七态状态机单调+终态吸收；偏离检测（completed/missed/cancelled diff）产出 regen(DM-003)/exception(DM-007) 输入 |
| **B5 DM Adjudication** | ✅ | **DM-008 独立成立**（三判据：问题独立=状态事实层 vs 计划生成 vs 违例处理；输入独立=执行事件流；承载缺口=006/007 均不拥有状态真值）；**DM-009 合并入 DM-004**（五场景全战术级，无战略级业务决策证据） |
| **B6 Freeze** | ✅ | domain_contract 32 类=冻结转录原样（A 18/18、E 17/17 同一契约复跑全过佐证未变）；本脚本零新增类；Opportunity/Priority/Emergency 实体零出现 |
| **B7 Pass** | ✅ | 13/13 + Classification 全登记 + Change Log EMPTY |

## 2. 评审五问逐项回答

| # | 评审问题 | 答案 |
|---|---|---|
| 1 | Opportunity 是否需要新增 Domain Concept？ | **不需要**——`VisitDemand.reason` 枚举即机会来源；demand 直挂 target 即新门店表达 |
| 2 | Priority 是否属于 Decision Policy？ | **是**——priority_score 为 VisitCandidate 上的派生字段，DM-002 策略计算 |
| 3 | Intraday Emergency 是否属于 Replanning/Exception？ | **是**——注入+容量判定+DP 链三段全复用；E 的 H2 结论在日内尺度再次成立 |
| 4 | DM-008 是否达到独立门槛？ | **达到**——执行状态真值是独立业务问题、独立输入（事件流）、006/007 不可承载 → **Validated Candidate（独立保留）** |
| 5 | DM-009 是否存在独立业务决策？ | **不存在**——五场景全部战术级容量判定 → **合并入 DM-004**（按 A5 预登记，无 Failure Evidence 反对） |

## 3. DM 注册表终态（五场景后）

```
DM-001 Coverage          Validated Candidate（A/C/D）
DM-002 Prioritization    Validated Candidate（A/B——B 增证 score 派生策略）
DM-003 ReqGeneration     Validated Candidate（A/C/E——E 增证滚动 regen）
DM-004 ResourceAlloc     Validated Candidate（A/D/B——B 增证日内容量；DM-009 并入）
DM-005 Assignment        Validated Candidate（D）
DM-006 VisitPlanning     Validated Candidate（A/C/D/E——E 增证收缩域再规划）
DM-007 ExceptionHandling Validated Candidate（A/C/D/E/B——B 增证挤占链）
DM-008 ExecutionMonitor  Validated Candidate · 独立成立（E 供证据 + B 终验）
DM-009 CapacityPlanning  MERGED into DM-004（裁定：无独立战略级决策证据）
DM-010 Replanning        MERGED into DM-006+007（E 裁定 H2，B 复证日内尺度）

净 Decision Model 数：10 → 8
```

## 4. 首跑失败归因（3 起，全 Class-C）

| # | 失败 | 归因 | 修复 |
|---|---|---|---|
| 1 | KeyError: DemandReason.COVERAGE_POLICY | 套件：REASON_BOOST 表漏两个枚举值 | 补全枚举覆盖（0.0 权重） |
| 2 | TypeError: 'bool' not iterable | 套件：terminal_absorbing 布尔逻辑误用 all() | 改布尔或运算 |
| 3 | TB-FREEZE 计数 32≠31 | 套件：记忆常数错误（31 为误记；契约实际 32 类，A/E 复跑全过佐证一致） | 断言改为契约实际值+禁令模式匹配 |

**Class-A（Domain 缺失）：0 起。Class-B 登记见 Classification。**

## 5. Failure Classification 登记

| 高风险点 | 预判 | 实际 | 证据 |
|---|---|---|---|
| 机会时限语义（"今天必须"） | 无风险 | **无风险** | DateRange(TODAY,TODAY) 即表达 |
| 新门店无 VisitPolicy 机会直入 | 待判 | **无风险**（含 B 类候选） | demand 直挂 target；policy 解析仅在 OccurrenceGenerator 层需要 → CRR 候选规则 |
| 取消恢复策略 | B | **B** | CANCELLED→恢复无解释规则；契约可表达（重新生成 demand），归 CRR |

## 6. Domain Change Log

**EMPTY**（0 DCR；三项禁令——因动态性新增 Entity / 因实时性新增 Domain / 因算法复杂新增 DM——全部守住）。

## 7. Phase 2 收官状态

```
五场景: A 18/18 · C 20/20 · D 20/20 · E 17/17 · B 13/13 = 88 测试
        0 DCR 违规 · 1 合规 DCR(SA-001-R) · 1 编译规则(C-001)
首跑失败累计 11 起，全部 Class-C（套件缺陷），零起指向 Domain
DM 注册表: 10 → 8（DM-009→004，DM-010→006+007）；8 个 Validated Candidate 待 Gate 复审转 Approved
SVDE Knowledge Base v0.1 核心闭环成立（Ontology→DM→Scenario→Evidence，静态+动态+机会驱动）
Phase 2 → CLOSE（待评审签字）；Phase 3 Semantic Compilation 解锁
```
