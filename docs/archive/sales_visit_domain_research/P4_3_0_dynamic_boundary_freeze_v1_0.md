# Phase 4.3-0 — Dynamic Decision Boundary Freeze v1.0
## 动态决策边界冻结 · 运行时状态模型 · 六工件扩展契约 · 变异分类法

> **文档标识**：`P43-0-DYNAMIC-BOUNDARY-FREEZE-V1.0`  
> **冻结日期**：2026-08-22  
> **阶段定位**：Phase 4.3-0 —— 动态配送调度决策编译器（Dynamic Fleet Route Logistics Decision Compiler）的启动前置边界冻结  
> **核心跃迁**：从静态计划编译（Static Decision Compilation）跃迁至 **动态在线自适应编译（Dynamic Runtime Adaptation）**。输入由单维快照扩展为 `State(t) + Event Stream → Decision Update(t+1)`。

---

## 1. 领域边界与负向知识界定（Boundary & Negative Knowledge）

```
                        Phase 4.3 Dynamic Delivery Decision Boundary
       ┌─────────────────────────────────────────────────────────────────────────────┐
       │ IN SCOPE (决策编译范围)                                                     │
       │  • 动态运单分配与车队路径重排 (Dynamic Fleet Dispatch & Re-routing)        │
       │  • 运行期事件驱动增量编译 (Event-driven Incremental Re-compilation)        │
       │  • 客户硬承诺时窗严格保持 (Commitment Survival: TIME_WINDOW_LOCKED)        │
       │  • 最小破坏重排预算 (Minimal Disruption Budget: max_reroute_ratio)          │
       │  • 动态安全底线后置验证 (Post-Event DSVL: 疲劳上限、冷链温控、装载超限)     │
       └─────────────────────────────────────────────────────────────────────────────┘
                                              ▲
                                              │ 严格边界隔离 (Strict Exclusion)
       ┌──────────────────────────────────────┴──────────────────────────────────────┐
       │ OUT OF SCOPE (严禁发散范围 —— 绝不构建全套产品系统)                         │
       │  • 自动驾驶与车辆底层底盘控制 (Autonomous Driving & Hardware Control)       │
       │  • 司机日常行为与薪酬绩效管理 (Driver Management & Payroll)                 │
       │  • 全套 TMS 运输结算与运费对账系统 (Full TMS, Freight Audit & Billing)      │
       │  • 商业地图导航渲染与高精地图底图产品 (Commercial Turn-by-Turn Navigation) │
       │  • 实时抢单撮合交易平台 (Real-time Crowdsourced Order Matching)             │
       └─────────────────────────────────────────────────────────────────────────────┘
```

**负向知识声明**：
> $\text{Dynamic Delivery Decision} \ne \text{导航与路径规划}$（不是寻找几何最短折线，而是动态事件下的运单与时间承诺重排）；  
> $\text{Dynamic Delivery Decision} \ne \text{TMS 全流程产品}$（不负责运费结算与履约开票）。

---

## 2. 动态内核扩展：运行时状态模型（Runtime State Model）

在标准静态 5 大工件基础上，SVDE Kernel 扩展出专用的 **工件 6: Runtime State Schema**，形式化定义动态世界的时间切片与事件流：

### 2.1 运单生命周期状态机（Order Lifecycle State Machine）
$$
\text{PENDING\_DISPATCH} \longrightarrow \text{ASSIGNED} \longrightarrow \text{IN\_TRANSIT} \longrightarrow \text{AT\_STOP} \longrightarrow \text{DELIVERED} \ / \ \text{FAILED}
$$

- **核心不可逆不变量（Immutability Invariant）**：
  - 处于 `AT_STOP` 与 `DELIVERED` 状态的运单属于已发生事实（Past Reality），在任何在线重规划中**绝对只读、严禁撤销、严禁篡改**。

### 2.2 车辆运行时状态（Vehicle Runtime State）
- 形式化为元组：$S_v(t) = \langle \text{loc}(t), \text{cur\_load}(t), \text{worked\_time}(t), \text{temp\_status}(t), \text{remaining\_stops}(t) \rangle$。
- 车辆机械故障（Breakdown）定义为 $S_v(t)$ 容量清零且不可移动。

---

## 3. 动态事件与变异分类法（Event Taxonomy: Data vs. Semantic Variation）

动态配送场景中，外部环境变化被严格区隔为两大类，决定系统是仅更新估算还是触发在线重新编译：

```
                                  Real-time Event Arrives
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
               Data Variation                               Semantic Variation
    (局部数据微调 · 零重新编译)                    (业务含义破坏 · 触发增量决策重编)
              │                                             │
              ├─ 轻度拥堵 (行程时间 +5%)                     ├─ 车辆突发机械故障 (Capacity 归零)
              ├─ 实际装卸轻微提前/滞后 (±3min)              ├─ 紧急特快件动态注入 (Hard Window 突发)
              └─ GPS 信号正常漂移                            └─ 客户时窗冲突变更 (Commitment Shift)
              │                                             │
              ▼                                             ▼
     更新 ETA 预测显示                             调用 SVDE Kernel 触发增量编译
     保持既有决策方案                               执行 Post-Event DSVL 验证
```

---

## 4. 动态决策六大标准工件规范（The 6-Artifact Suite for Phase 4.3）

Phase 4.3 将严格遵循扩展后的六大工件标准进行装配与验证：

1. `dynamic_delivery_semantic_contract_v1_0.yaml`：定义 3 辆车、10 订单、C1–C8 约束、I1–I4 不变量、规范目标（$L1$ 可行 $\to L2$ 准时履约 $\to L3$ 最小破坏 $\to L4$ 总行驶成本）。
2. `dynamic_delivery_constraint_type_registry_v1_0.yaml`：定义 `VehicleCapacity`, `TimeWindowHard`, `DriverHoursLimit`, `TimeWindowLock`, `ColdChainCompliance` 等强类型。
3. `dynamic_delivery_dsvl_rules_v1_0.yaml`：前置（Pre-Compile）+ 后置（Post-Event）双重决策可行性验证。
4. `dynamic_delivery_oracle_definition_v1_0.md`：独立 Exact CP-SAT Oracle，定义事件扰动下的标准基准。
5. `dynamic_delivery_trace_schema_v1_0.json`：因果追踪（含事件触发原因、为什么移动订单 X、为什么保留订单 Y）。
6. `dynamic_delivery_runtime_state_schema_v1_0.json`（**动态新增工件**）：定义 $t$ 时刻状态切片、事件流数据结构与已执行历史容器。

---

## 5. Phase 4.3 核心科学问题（Q1–Q4）

- **Q1 (Dynamic State Expression)**：SVDE 是否能完备表达运行期物理状态机与历史不可逆性？
- **Q2 (Semantic Re-compilation)**：外部突发事件能否确定性触发语义级增量重规划，而非简单启发式修补？
- **Q3 (Commitment Preservation)**：在车辆故障与急件插入扰动下，既有客户的锁定承诺（`LOCKED`）是否 100% 保持？
- **Q4 (Decision Explainability)**：Decision Trace 是否能够清晰解释“为什么改动某些路线，而坚决不改动某些承诺”？
