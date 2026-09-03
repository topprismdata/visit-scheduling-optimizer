# SVDE 状态转移与演化引擎规范 v1.0 (State Transition Engine Specification)
**Document ID:** SVDE-STATE-TRANSITION-ENGINE-SPEC-v1.0  
**Date:** 2026-08-24  
**层级定位:** L3: 状态转移与演化控制层 (State Transition & Evolution Layer)  
**前置基础:** `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md` (L1)  
**核心原则:** 状态转移的可审计性、确定性与不可逆性。所有状态变更必须由合法事件显式驱动，严禁静默状态突变。

---

## 1. 状态转移核心数学形式化 (Mathematical State Transition Model)

运营决策世界模型的状态演化形式化为受控离散事件动态系统 (Discrete Event Dynamic System, DEDS):

$$\text{WorldState}_{t+1} = \delta\left(\text{WorldState}_t, \text{Event}_t, \text{Action}_t\right)$$

- $\text{WorldState}_t$: 当前时刻的世界状态不可变快照；
- $\text{Event}_t$: 外部发生的事实事件（如进店打卡、大仓缺货预警、代表请假）；
- $\text{Action}_t$: 决策系统采取的控制动作（如重排路线、委派替补、顺延周期）；
- $\delta(\cdot)$: 确定性状态转移函数（包含守卫条件 Guard 条件判定）。

---

## 2. 三大核心生命周期状态转移图 (Lifecycle Transition Graphs)

### 2.1 服务任务全生命周期状态机 (Task / Visit Lifecycle)

```
                    ┌────────────────────────┐
                    │       PROPOSED         │ (需求发起 / 意图生成)
                    └───────────┬────────────┘
                                │ [通过模式指派与容量校验]
                                ▼
                    ┌────────────────────────┐
                    │        PLANNED         │ (候选计划就绪，待审批)
                    └───────────┬────────────┘
                                │ [主管人工签署 / 外部确认]
                                ▼
                    ┌────────────────────────┐
                    │       COMMITTED        │ (生成承诺，锁定下发)
                    └───────────┬────────────┘
                                │ [执行日到达，Agent 进店打卡]
                                ▼
                    ┌────────────────────────┐
                    │      IN_PROGRESS       │ (现场作业中)
                    └───────┬────────┬───────┘
           [完成离店]       │        │        [未进店 / 中途脱访]
           ┌────────────────┘        └────────────────┐
           ▼                                          ▼
┌────────────────────────┐                  ┌────────────────────────┐
│       COMPLETED        │                  │         MISSED         │
│  (输出 ActualVisitFact)│                  │  (生成 MissedIncident) │
└────────────────────────┘                  └───────────┬────────────┘
                                                        │ [触发业务异常重排政策]
                                                        ▼
                                            ┌────────────────────────┐
                                            │ DEFERRED / RESCHEDULED │
                                            └────────────────────────┘
```

#### 状态转移合法性与守卫条件矩阵 (Transition Guard Matrix)
| 当前状态 (From) | 目标状态 (To) | 触发事件 (Triggering Event) | 守卫条件 (Guards) | 非法转移惩罚 |
| :--- | :--- | :--- | :--- | :--- |
| `PROPOSED` | `PLANNED` | `Event.PlanGenerated` | 存在合法时间槽且单日容量 $\le 6$ | 抛出 `CapacityOverloadError` |
| `PLANNED` | `COMMITTED` | `Event.HumanSignedOff` | 必须具备显式 `approver_id` | 抛出 `UnauthorizedPublishError` |
| `COMMITTED` | `IN_PROGRESS`| `Event.CheckInRecorded` | 打卡 GPS 距离门店 $\le 500\text{ m}$ | 标记 `GPS_DEVIATION_WARNING` |
| `IN_PROGRESS`| `COMPLETED` | `Event.CheckOutRecorded`| 在店时长 $\ge 10\text{ min}$ | 标记 `ABNORMAL_DURATION` |
| `COMMITTED` | `MISSED` | `Event.DayEnded` | 截至当天 23:59 未发生打卡事件 | 触发 `CriticalIncidentAlert` |
| `MISSED` | `DEFERRED` | `Event.ExceptionHandled` | 满足 DeferralPolicy 且未超出周期 | 允许重新进入 `PLANNED` 队列 |

---

### 2.2 客户归属所有权生命周期 (Ownership Lifecycle)
```
[UNASSIGNED] ──(InitialAssignment)──> [ACTIVE_EXCLUSIVE]
                                              │
                                              ├─(Reallocation)──> [REASSIGNED]
                                              │
                                              └─(OverlapDetected)─> [CONFLICT_FLAGGED]
```
- **冲突不覆盖原则**: 当检测到两个代表同时服务同一客户时，状态必须置为 `CONFLICT_FLAGGED`，记录冲突历史，严禁静默覆盖。

---

### 2.3 政策版本生命周期 (Policy Lifecycle)
```
[DRAFT] ──(Approved)──> [ACTIVE_CANONICAL] ──(Superseded)──> [SUPERSEDED_HISTORICAL]
```
- **不可变版本原则**: 任何政策变更必须递增版本号（如 `v2.0 -> v2.1`），历史决策保留指向旧版本政策的外键引用。

---

## 3. 反事实推演与分支演化机制 (Counterfactual What-If Scenario Rollout)

### 3.1 状态分叉机制 (State Forking & Branching)
为了评估潜在业务变更，引擎支持无副作用的状态分叉：

```python
def fork_scenario_branch(
    base_state: WorldStateSnapshot,
    scenario_id: str,
    perturbation_events: List[PerturbationEvent]
) -> WorldStateSnapshot:
    """
    1. 克隆 base_state 的不可变实体引用
    2. 生成全新的 Scenario Bitemporal 事务时间切片
    3. 依次应用 perturbation_events (如跨代表调店、突发大促)
    4. 返回独立沙箱分支 WorldStateSnapshot
    """
    pass
```

### 3.2 常见反事实情景清单
1. **调店情景 (Re-allocation Rollout)**: 将门店从代表 A 转移到代表 B，评估双方工时与路线变化；
2. **缺货应急插单情景 (OOS Urgent Insertion)**: 模拟当天突发插单，推演对后续承诺的影响；
3. **出勤中断情景 (Rep Absence / Capacity Shock)**: 模拟代表突发请假 3 天，推演未履约任务的最优延期策略。
