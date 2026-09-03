# SVDE 运营决策世界模型技术规范 v1.0 (Operational Decision World Model Specification)
**Document ID:** SVDE-OPERATIONAL-DECISION-WORLD-MODEL-SPEC-v1.0  
**Date:** 2026-08-24  
**Status:** **ARCHITECTURAL BASELINE SPECIFICATION (跨行业对齐的运营决策世界模型规范)**  
**理论与工业基准:**
1. **ISO 23247**: 制造业数字孪生框架 (Digital Twin Framework for Manufacturing)
2. **NASA MDS**: 喷气推进实验室任务数据系统 (State-Based & Goal-Oriented Control Architecture)
3. **Autonomous Driving World Models**: 状态转移预测与未来情景演化 (State Transition & Rollout)
4. **W3C PROV-O**: 数据溯源与证据链规范 (Provenance Data Model)
5. **Bitemporal Data Architecture**: 双时态数据建模 (Valid Time vs Transaction Time, Snodgrass 1999)

---

## 1. 认知体系重构：七大核心范畴的严格边界

为了彻底根除“历史观察与政策混淆”、“推断估计与物理实体混淆”，世界模型将企业全域事实严格划分为七个正交认知范畴：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        SVDE 七大核心认知范畴及其因果流向                                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. 事实观测 (OBSERVATION)  ──> 客观世界发生过什么 (打卡记录、陈列拍照、GPS打点、历史频次)│
│                                                                                        │
│ 2. 派生推断 (DERIVED)      ──> 系统根据观测推断出什么 (商圈质心、常驻城市、动作耗时分布)│
│                                                                                        │
│ 3. 业务政策 (POLICY)       ──> 企业管理层期望应该怎样 (拜访频率要求、单日容量红线、SLA) │
│                                                                                        │
│ 4. 履约承诺 (COMMITMENT)   ──> 已经与外部达成的锁定承诺 (大客户固定时段、已排定不可撤回)│
│                                                                                        │
│ 5. 规划意图 (PLAN_INTENT)  ──> 决策者打算如何行动 (下月排班意图、大促攻坚、长途专场)   │
│                                                                                        │
│ 6. 执行事实 (EXEC_EVENT)   ──> 意图下发后一线实际执行了什么 (是否线内、准点率、陈列达标)│
│                                                                                        │
│ 7. 反事实推演 (SCENARIO)   ──> 如果改变决策世界会怎样 (What-if 仿真、跨代表划转影响)    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 范畴隔离铁律
- **铁律 1 (No Observation-as-Policy)**: 严禁将历史打卡记录中的频次或日期，直接当成未来的业务政策；
- **铁律 2 (No Derived-as-Ground-Truth)**: 几何质心推断的 Depot 必须显式标记为 `DERIVED_ESTIMATE`，绝不可冒充物理存在的办事处；
- **铁律 3 (No Silent Assumption)**: 未经供应链实测校准的大仓配送日，必须显式标记为 `UNCALIBRATED_HYPOTHESIS`。

---

## 2. 双时态状态快照 (Bitemporal WorldStateSnapshot)

借鉴金融核心系统与 NASA MDS 状态架构，每一个状态切片都必须具备两套独立的时间维度：

```python
from dataclasses import dataclass
import datetime

@dataclass(frozen=True)
class BitemporalPeriod:
    """双时态时间戳"""
    valid_from: datetime.datetime      # 业务事实在真实世界中生效的开始时间 (Valid Time)
    valid_to: datetime.datetime        # 业务事实在真实世界中失效的结束时间
    transaction_from: datetime.datetime # 该事实被记录/写入本系统的时刻 (Transaction Time)
    transaction_to: Optional[datetime.datetime] = None # 该事实在系统中被更新/废弃的时刻
```

- **Valid Time (生效时间)**: 描述真实世界的业务周期（如 2026年6月1日至6月30日）；
- **Transaction Time (系统记录时间)**: 描述数据入库与决策生成时刻（如 2026年8月24日 17:30:00），确保任何历史决策可在任意时刻**100% 确定性回放（Deterministic Replay）**。

---

## 3. 显式状态转移机 (State Transition Lifecycle)

### 3.1 拜访生命周期状态机 (Visit Lifecycle State Machine)
任何一次拜访（Visit）在世界模型中经历严格的状态流转：

```
                    ┌────────────────────────┐
                    │       PROPOSED         │ (意图生成 / 需求提出)
                    └───────────┬────────────┘
                                │ [通过合规审计与模式指派]
                                ▼
                    ┌────────────────────────┐
                    │        PLANNED         │ (候选排班完成)
                    └───────────┬────────────┘
                                │ [业务主管人工签署 / 外部确认]
                                ▼
                    ┌────────────────────────┐
                    │       COMMITTED        │ (锁定承诺 / 下发终端)
                    └───────────┬────────────┘
                                │ [到达执行日 / 代表进店打卡]
                                ▼
                    ┌────────────────────────┐
                    │      IN_PROGRESS       │ (现场作业中)
                    └───────┬────────┬───────┘
           [完成离店]       │        │        [未进店 / 异常中断]
           ┌────────────────┘        └────────────────┐
           ▼                                          ▼
┌────────────────────────┐                  ┌────────────────────────┐
│       COMPLETED        │                  │         MISSED         │
│  (生成 ActualVisitFact) │                  │  (生成 MissedIncident) │
└────────────────────────┘                  └───────────┬────────────┘
                                                        │ [触发异常处理]
                                                        ▼
                                            ┌────────────────────────┐
                                            │ DEFERRED / RESCHEDULED │
                                            └────────────────────────┘
```

---

## 4. 规划器专属投影视角 (PlannerStateProjection)

规划求解器（Solvers）绝不直接读取庞杂的全量世界模型，而是通过专用的**投影契约（Projection Contract）**获取精简、确定、无歧义的数学载荷：

```python
@dataclass(frozen=True)
class PlannerStateProjection:
    """规划器专用的确定性状态投影切片"""
    projection_id: str
    target_rep_id: str
    planning_horizon: BitemporalPeriod
    
    # 纯数学节点拓扑
    node_matrix_index: Dict[str, int]               # store_code -> 矩阵索引
    travel_cost_matrix: List[List[float]]           # 真实通勤耗时 (分钟)
    travel_distance_matrix: List[List[float]]       # 真实通行距离 (公里)
    
    # 纯业务约束载荷
    candidate_pattern_space: Dict[str, List[List[Tuple[int, int]]]] # 严格模式空间
    locked_commitments: Dict[Tuple[int, int], List[str]]           # 已锁定拜访
    service_duration_vector: List[float]            # 动作合成在店时长
    daily_stop_capacity: int = 6                    # 单日门店上限
    daily_workload_budget_min: float = 480.0        # 工时预算
    
    # 投影元数据
    is_projection_clean: bool = True
    projection_warnings: List[str] = field(default_factory=list)
```

---

## 5. 反事实推演与状态预演契约 (What-if Scenario Rollout)

世界模型必须支持向未来推演决策影响（Rollout Simulation）：

$$\text{WorldState}_{t+1} = \operatorname{StateTransition}\left(\text{WorldState}_t, \text{DecisionArtifact}, \text{EnvironmentStochasticEvents}\right)$$

### 5.1 反事实推演能力清单
1. **调店情景 (Re-allocation Rollout)**: 如果将通州的 2 家门店从仁军划转给佳佳，两人的工时方差、总在途耗时会发生什么确定性变化？
2. **缺货冲击情景 (Out-of-Stock Spike)**: 如果某 Key 店突发缺货插入应急拜访，现有的周三严格节奏如何最小扰动重排？
3. **大仓改期情景 (DC Rescheduling)**: 如果爱婴室嘉善大仓由周二配送改为周三配送，终端门店巡检应如何自动对齐？

---

## 6. 实施演进路线图

1. **Step 1: 代码层实现双时态与全范畴 WorldStateSnapshot** (`world_state_snapshot.py`)；
2. **Step 2: 建立显式 StateTransitionEngine 状态转移机**；
3. **Step 3: 实现 PlannerStateProjection 投影编译器**；
4. **Step 4: 编写全链路双时态与反事实推演测试套件**。
