# SRP 4.0 三层架构设计文档
## Semantic → Mathematical → Solver:接口定义、类型系统与层间契约

> **Document Status**: Draft v0.2 (2026-09-20) — 落实 GPT 评审 3×P0 修正
> **Author**: TopPrism Algorithm Engineering
> **Prerequisite**: CONTRACT_CADENCE_MODEL.md (v3 合同-相位本体定稿) · SYSTEM_DESIGN_DOC.md v3.2 · AGENTS.md §五(三层设计红线)
> **GPT Review**: Round 1 评分 8.2/10; Round 2 落实 P0 修正后进入 Phase A
> **v0.1 → v0.2 变更**: ① L3 不再主动违反 L2 硬约束,改为 Escalation → Recompile; ② VisitMathIR 拆为不可变 IR + SolveRuntimeState; ③ 新增 SourceMap + MathValidator + API contracts 包; ④ LineData 拆为四个不可变边界对象; ⑤ 新增 PlanningHorizon / ObjectivePolicy / typed ExceptionGrant / Decision Episode envelope

---

## 1. Goals

### 1.1 解决的问题

当前 SRP 代码库中,三层(语义/数学/求解器)的边界靠开发者纪律维持,而非代码结构。具体表现:

1. `algos/r2_alns_v2_backup.py` 直接调用 `contract_of()` / `check_contract()`(Layer 3 泄漏到 Layer 1)
2. `LineData.__post_init__` 从 `days_orig` 推导 `K_min/K_max`(业务推断政策隐藏在数据结构构造器里)
3. `LineData.freq` 独立存在,与 `contract_of()` 推导的 `f_c` 形成双真相
4. `SPMatheuristic.solve()` 内部从 `days_orig` 计算 `k_c`(Layer 3 知道 Layer 1 的事)
5. `check_r2prime()` 定义在 `algos/` 里(Layer 1 业务语义在算法层)
6. `column_generate()` 直接调用 `legal_date_map()`(Layer 3 偷偷调 Layer 1 编译器)

### 1.2 设计目标(G1-G6)

| # | 目标 | 说明 |
|---|---|---|
| G1 | Semantic → Math 完备性 | 每条有效 L1 规则必须能证明自己被 L2 编译了(No orphan semantic rule) |
| G2 | Math → Semantic 可追溯性 | 每条 L2 constraint/objective 必须知道来源于哪条 semantic rule(No orphan mathematical constraint) |
| G3 | Solver 独立验证 | L3 不自证合法;由 L2 MathValidator 独立验解 |
| G4 | 可复现性 | 同一 SemanticSpec + MathIR + SolverConfig 必须可重演,并留 hash/version |
| G5 | 类型安全边界 | 跨层传递对象禁止裸 dict/list;使用 frozen dataclass + tuple/frozenset |
| G6 | 授权显式化 | 每条规则例外必须经过 ExceptionGrant,不允许代码内 `if special_case` 逃逸 |

### 1.3 Non-Goals

- 不在本轮更换 ALNS 算法本身
- 不在本轮引入服务时长/班次可行性(老板裁定出范围)
- 不在本轮做全国 572 线的完整迁移(芜湖 3 线试点先行)
- 不在本轮实现 Decision Memory 完整数据模型(预留 Decision Episode envelope)
- 不设计通用 optimization IR(VisitPlanningInstance 只服务 recurring field visit scheduling)
- 不解决跨进程/跨语言 RPC(先解决 Python 内部架构;serialization 后续设计)
- **不使用通用 optimization IR 命名**——VisitPlanningInstance 保留 visit scheduling 数学结构

---

## 2. Invariants(跨层不变量,分层响应)

五条不变量在任何一层都不可被**同层**违反;但 L3 不可行时**不自行修**,而是 **Escalate → L2 Recompile**。

### 2.1 义务守恒方程(取代简单频次守恒)

$$\text{Completed}_c + \text{FutureScheduled}_c + \text{OpenMakeupDebt}_c = \text{ContractObligation}_c$$

客户取消 ≠ 义务消失,而是产生 `MakeupDebt`,由 L2 Reconcile 吸收。

### 2.2 五条不变量的分层响应

| # | 不变量 | L1 Plan | L2 Reconcile | L3 React |
|---|---|---|---|---|
| I1 | 义务守恒 | Hard(编译拒绝) | Hard constraint | 不可行 → **Escalate L2**(产生 MakeupDebt) |
| I2 | 走廊 K_min/K_max | Hard | Hard constraint | **Escalate L2**(CorridorDeviation) |
| I3 | 星期几一致(R2′) | Hard | Hard constraint | 通常不在 L3 改日期 |
| I4 | 间隔 ≥14 天 | Hard | Hard constraint | **Escalate L2**(SpacingDebt) |
| I5 | 核心客户保全 | Hard | Hard constraint | 不主动牺牲;不可服务记 `ServiceException` |

**关键设计**:L3 遇到 INFEASIBLE 时,输出数学事实(constraint_id + unserved_decision),由 **L2 SourceMap** 追溯到语义规则,由 **Orchestrator** 解释成业务事件(Debt/Exception/Escalation)。

---

## 3. 类型系统(跨层 API 契约)

### 3.0 API Contracts 包(解决"CI 禁止 import 但接口需要类型"的矛盾)

```
visit_semantic_api/          # 纯类型,无实现
    VisitSemanticSpec
    VisitContract
    WorkloadCorridorPolicy
    CoreProtectionPolicy
    ExceptionGrant
    PlanningHorizon

visit_math_api/              # 纯类型,无实现
    VisitPlanningInstance
    ObjectiveSpec
    SolverConfig
    MathSolution
    SourceMap
```

**依赖规则(CI import-linter 强制)**:

```
visit_ir(实现)    → import visit_semantic_api     ✓
visitmodel(实现)  → import visit_semantic_api     ✓
                  → import visit_math_api         ✓
srp/algos(实现)   → import visit_math_api         ✓
srp/algos         → import visit_semantic_api     ✗ 禁止
visit_ir          → import visitmodel             ✗ 禁止
visit_ir          → import srp.algos              ✗ 禁止
```

### 3.1 PlanningHorizon

```python
@dataclass(frozen=True)
class PlanningHorizon:
    start_date: str              # ISO date
    end_date: str
    timezone: str                # "Asia/Shanghai"
    calendar_id: str             # 工作日历标识
    anchor_week: int             # ISO 自然周序锚点(相位计算基准)
    phase_period: int            # 相位周期(默认 2,双周)
```

### 3.2 VisitContract

```python
@dataclass(frozen=True)
class VisitContract:
    customer_code: str
    contract_type: ContractType  # WEEKLY / BIWEEKLY
    phase: Optional[int]         # 双周相位(B 类必填)
    sigma: int                   # 星期几
    legal_slot_indices: tuple    # tuple[int] 合法槽位序号
    obligation: int              # ContractObligation (月拜访义务次数,派生)
```

### 3.3 WorkloadCorridorPolicy

```python
@dataclass(frozen=True)
class WorkloadCorridorPolicy:
    k_min: int
    k_max: int
    source: str                  # "historical_baseline" | "management_directive"
    derivation: str              # "min/max(original_daily_counts)" | "manual"
    approved: bool
    approved_by: str
```

### 3.4 CoreProtectionPolicy

```python
@dataclass(frozen=True)
class CoreProtectionPolicy:
    customer_code: str
    mandatory_visit: bool
    cadence_relaxable: bool
    weekday_relaxable: bool
    exception_priority: str      # CRITICAL / HIGH / NORMAL
    relaxation_priority: int     # 资源不足时最后被牺牲的排序(越小越后)
```

### 3.5 ExceptionGrant

```python
@dataclass(frozen=True)
class ExceptionGrant:
    exception_id: str
    target_rule_id: str          # 被修改的规则标识
    subject_codes: tuple         # 受影响的客户编码
    effective_interval: tuple    # (start_date, end_date)
    typed_override: object       # 类型化覆写值(非裸 object)
    authority_id: str            # 审批人
    approved_at: str
    expires_at: Optional[str]
    reason_code: str
```

### 3.6 VisitSemanticSpec(L1 编译产物,不可变)

```python
@dataclass(frozen=True)
class VisitSemanticSpec:
    horizon: PlanningHorizon
    contracts: tuple             # tuple[VisitContract] (不可变 tuple 替代 dict)
    corridor: WorkloadCorridorPolicy
    core_protections: tuple      # tuple[CoreProtectionPolicy]
    exceptions: tuple            # tuple[ExceptionGrant]
    objective_policy: SemanticObjectivePolicy  # ← v0.2 新增
    metadata: SourceMetadata     # schema_version / content_hash / source_snapshot_id

@dataclass(frozen=True)
class SemanticObjectivePolicy:
    """L1 定义业务目标的含义(不是数学表达式)"""
    distance: str                # "minimize"
    plan_stability: str          # "prefer_low_change"
    workload_balance: str        # "prefer_even"
    core_protection_mode: str    # "hard_constraint" | "high_weight"
    preference_mode: str         # "lexicographic" | "pareto"

@dataclass(frozen=True)
class SourceMetadata:
    schema_version: str
    content_hash: str
    source_snapshot_id: str
    compiler_version: str
    compiled_at: str
```

---

## 4. Layer 2 · Mathematical Compiler (visitmodel)

### 4.1 职责

- 接收 `VisitSemanticSpec`,**编译成求解器无关的数学对象**
- 定义变量、约束(从语义规格确定性翻译)、目标向量(从 ObjectivePolicy 翻译)
- 输出 **不可变的** `VisitPlanningInstance`(原 VisitMathIR 改名)
- 附带 **SourceMap**(约束→语义规则追溯)和 **MathValidator**(独立验解)

### 4.2 VisitPlanningInstance(不可变数学实例)

```python
@dataclass(frozen=True)
class VisitPlanningInstance:
    """Layer 2 编译产物: 求解器无关的数学实例(非通用 IR)"""
    # 参数
    customers: tuple             # tuple[str] 客户编码
    workdays: tuple              # tuple[str] 工作日
    required_visits: MappingProxyType  # customer_code → obligation (只读映射)
    day_corridor: tuple          # (K_min, K_max)
    eligible_days: MappingProxyType    # customer_code → frozenset(date)
    fixed_visits: frozenset      # 核心客户编码(从 CoreProtectionPolicy.mandatory_visit 编译)
    
    # 目标向量规范(从 ObjectivePolicy 翻译)
    objective_terms: tuple       # tuple[ObjectiveTerm]
    
    # 追溯
    source_map: MappingProxyType # constraint_id → semantic_rule_id
    metadata: SourceMetadata

@dataclass(frozen=True)
class ObjectiveTerm:
    metric: str                  # "total_distance" | "max_daily_distance" | "daily_count_range"
    priority: int                # lexicographic 优先级
    sense: str                   # "minimize"
```

### 4.3 SourceMap(约束→语义规则追溯)

```python
@dataclass(frozen=True)
class SourceMap:
    """constraint_id → semantic_rule_id 追溯映射"""
    entries: MappingProxyType    # constraint_id → semantic_rule_id
    
    def explain(self, constraint_id: str) -> str:
        return self.entries.get(constraint_id, "unmapped")
```

### 4.4 MathValidator(独立验解,L2 实现,L3 调用)

```python
class MathValidator:
    """Layer 2 的独立验解器: L3 求解完 → L2 验证合法性"""
    
    def validate(
        self,
        instance: VisitPlanningInstance,
        solution: MappingProxyType,  # date → frozenset(customer)
    ) -> ValidationReport:
        """
        独立于任何 Solver Backend。
        Solver 不自证合法;由 L2 用同一套 MathIR 独立校验。
        """
```

### 4.5 求解器接口(L3 实现,L2 定义协议)

```python
class SolverBackend(Protocol):
    def solve(self, instance: VisitPlanningInstance, config: SolverConfig) -> SolveResult: ...

@dataclass(frozen=True)
class SolveResult:
    status: str                  # "OPTIMAL" | "FEASIBLE" | "INFEASIBLE"
    assignments: MappingProxyType # date → tuple[customer_code]
    objective_vector: tuple      # 多目标向量 (非单值)
    best_bound: Optional[float]
    gap: Optional[float]
    violated_constraints: tuple  # tuple[constraint_id] (INFEASIBLE 时非空)
    termination_reason: str
    solver_stats: dict           # iters / accepted / time (类型化)
    math_ir_hash: str
```

---

## 5. Layer 3 · Solver Backend (SRP / OptiCore)

### 5.1 职责

- 接收 `VisitPlanningInstance + SolverConfig`
- 高效搜索最优/近优解
- 返回 `SolveResult`
- **不知道**: 什么是核心客户、走廊为什么是 17~29、频次为什么是 4

### 5.2 内部运行时状态(与 IR 分离)

```python
@dataclass
class SolveRuntimeState:
    """Layer 3 内部运行时状态(不属于 MathIR)"""
    column_pool: list            # 列池(动态变化)
    warm_start: Optional[dict]   # 暖启动解
    incumbent: Optional[dict]    # 当前最优解
    duals: Optional[dict]        # LP 对偶价(列生成用)
```

### 5.3 事件响应矩阵(L3 React)

| 事件 | L3 行动 | 不可行时 |
|---|---|---|
| 客户取消/关门 | remove + reconnect | → MakeupDebt → L2 |
| 临时插单 | cheapest feasible insertion | 无 feasible slot → L2 |
| 拜访超时 | recompute remaining suffix | 核心风险 → L2 |
| 交通变化 | suffix reorder | 大面积失效 → L2 |
| 客户不可服务 | skip / retry today | 无法当天补 → debt |
| 提前结束 | optional fill-in nearby | 无候选 → 结束 |
| 销售 unavailable | **不在 L3 解** | **升级 L2** |
| 跨销售调店 | **不在 L3 权限** | **升级 L2 / territory decision** |

### 5.4 Frozen Prefix

```python
# 已完成的路线前缀不可修改:
# A → B → C → D → E → F
# 如果 A,B 已完成,正在去 C:
# L3 只能改 D,E,F...
# 不能为了省 700m 让销售掉头回 A 附近
```

---

## 6. SourceMap + Escalation 状态机

### 6.1 位移阶梯的 SourceMap 追溯链

```
业务规则 (语义层)
    ↓ semantic_rule_id
数学约束 (模型层)
    ↓ constraint_id
求解器证据 (INFEASIBLE / violated)
    ↓ SourceMap
业务解释 / Decision Episode
```

### 6.2 Escalation 状态机

```
Event 发生
      ↓
L3 React: 能否在授权变异包络内修复?
      ├─ YES → 执行修复,返回新路线
      └─ NO → 输出 INFEASIBLE + violated_constraint_ids
                  ↓
L2 Reconcile: 能否在滚动周期内恢复义务守恒?
      ├─ YES → 运行 SP Recompile,返回新计划
      └─ NO → INFEASIBLE + constraint_ids
                  ↓
L1 Plan / 人工决策: 需要修改走廊/合同/例外授权?
      ├─ YES → 新 SemanticSpec → 新 MathIR → L3 re-solve
      └─ NO → 记录 MakeupDebt,等待下一周期
```

---

## 7. Decision Episode(最小 Envelope,v0.1 预留)

```python
@dataclass(frozen=True)
class DecisionEpisode:
    episode_id: str
    source_snapshot_id: str
    semantic_spec_version: str
    semantic_spec_hash: str
    math_ir_version: str
    math_ir_hash: str
    solver_backend: str
    solver_version: str
    solver_config_hash: str
    seed: int
    solution_id: str
    termination_reason: str
    exception_grant_ids: tuple
    decision_timestamp: str
```

**目标**: 今天生成的计划,将来还能回答——"这个结果究竟是在什么业务事实、什么规则版本、什么数学模型、什么 solver 参数下产生的?"

---

## 8. 全链路架构(最终形态)

```
Raw Facts (xlsx / SF / API)
    │
    ▼
┌──────────────────────────────────────────┐
│ Layer 0 · Decision Readiness             │
│ SSI / Spatial-DI / CA / Entity Match     │
│ (admission gate, fail-closed)            │
└─────────────────┬────────────────────────┘
                  │ TrustedFacts
                  ▼
┌──────────────────────────────────────────┐
│ Semantic Control Plane                   │
│ prism-ontology + VisitIR                 │
│ contract / obligation / policy / authority│
└─────────────────┬────────────────────────┘
                  │ VisitSemanticSpec (immutable)
                  ▼
┌──────────────────────────────────────────┐
│ L2 Mathematical Compiler                 │
│ visitmodel                               │
│ VisitPlanningInstance + SourceMap        │
│ + MathValidator                          │
└─────────────────┬────────────────────────┘
                  │ VisitPlanningInstance (immutable)
                  ▼
┌──────────────────────────────────────────┐
│ L3 Solver Backend                        │
│ ALNS / SP / CP-SAT / NN+2opt            │
│ SolveRuntimeState (columns, warm start)  │
└─────────────────┬────────────────────────┘
                  │ SolveResult
                  ▼
┌──────────────────────────────────────────┐
│ Orchestrator                             │
│ MathValidator.validate()                 │
│ SourceMap.explain()                      │
│ Escalation if INFEASIBLE                 │
│ Decision Episode 留痕                    │
└─────────────────┬────────────────────────┘
                  │ SchedulePlan (validated + explained)
                  ▼
               Execution
                  │
                  ▼
           Decision Memory
                  │
                  ▼
         next decision cycle
```

---

## 9. 精磨路线图(按优先级)

### Phase A · 接口定义与类型锁死(本周)
1. 实现 `visit_semantic_api` / `visit_math_api` 两个纯类型包
2. 定义所有 frozen dataclass(含 SourceMetadata / SourceMap / SolveResult)
3. 实现 `MathValidator.validate()`(L2 独立验解)
4. CI 加 import-linter(exhaustive contract)+ architecture test(禁止跨层 import)

### Phase B · 语义层扩建(下周)
5. 将 K_min/K_max / f_c / core_protection 的**语义所有权**从 LineData 迁移到 SemanticCompiler
6. 新增 WorkloadCorridorPolicy / CoreProtectionPolicy / ExceptionGrant 类型
7. visit_ir contract 模式重命名为显式 dialect
8. SourceMap 实现(constraint_id → semantic_rule_id)

### Phase C · 模型层精磨(下下周)
9. visitmodel 拆分: formulation(L2) vs column_generation(L3)
10. VisitPlanningInstance 正式实现(不可变)
11. SP/Pareto/TSP 数学规范文档
12. Decision Episode envelope 实现

### Phase D · 算法层改造(之后)
13. ALNS 剥离 contract 依赖 → 改收编译后参数
14. SPMatheuristic 剥离 days_orig 推断 → 改收 VisitPlanningInstance
15. Layer Escalation 状态机实现

---

## 10. Alternatives Considered

| 替代方案 | 为什么不选 |
|---|---|
| 全部 monorepo | 三层变化周期不同(本体最稳/算法最快),统一发版互相拖累 |
| Python type hint + mypy strict | 理论可行,但不能强制禁止跨层 import;frozen dataclass + CI 更稳 |
| protobuf/thrift IDL | Python 内部通信过重;dataclass frozen + CI 足够 |
| 保持现状(靠纪律) | 已实证不可靠——本 session 多次错误均因缺代码结构保障 |
| VisitMathIR 含 column pool | CG 是 L3 运行时行为,列池不是数学规格——分开(MathIR 不可变,RuntimeState 可变) |
| L3 自产 MakeupDebt | L3 输出数学事实(INFEASIBLE + constraint_id),Orchestrator 解释——不让 solver 做业务判断 |

---

## 11. 开放问题(待业务确认)

| # | 问题 | GPT 建议 | 状态 |
|---|---|---|---|
| 1 | 双周相位 φ 可否翻(偶↔奇)? | 默认不可翻;**更深的问题**: 相位锚定语义是什么(anchor_week + period, 不是 ISO%2)? | 待业务 |
| 2 | 间隔例外授权权限 | 不是一个人,是**授权矩阵**(rule × scope × max_relaxation × authority) | 待定义 |
| 3 | 自然走廊粒度(300m/500m) | 移出开放问题;改名为 spatial_cohesion_radius_m(避免与 workload corridor 冲突);**算法参数实验问题,非架构问题** | 待实验 |
| 4 | Decision Episode 最小字段集 | v0.1 已预留 envelope(见 §7) | ✅ 已预留 |

---

## 12. 中心命题

> **埃森哲可以设计和实施企业的 RTM;TopPrism 是其中负责 operational decisions 的专用引擎。双方互补,在 visit decisioning 上允许直接 benchmark。**
>
> **我们不是要求客户替换转型伙伴,而是建议把"谁、何时、如何拜访"这一关键经营决策,从项目交付项变成独立、可验证、可持续学习的企业决策能力。**
>
> L3 不但不知道 K_min 为什么等于 17,它甚至无权决定"17 能不能变成 16"。
> 做到这一点,这次重构才算真正把"业务判断权"从 solver 手里收回来。
>
> —— GPT 评审结论

---

## 13. 交付物与参考

- 本文档:`docs/design/THREE_LAYER_ARCHITECTURE_v0.2.md`
- GPT 评审 Round 1:`/tmp/gpt_refine_reply.txt`(13,733 字)
- GPT 评审 Round 2(本文档评审):`/tmp/gpt_design_review.txt`(13,193 字,评分 8.2/10)
- 上游:CONTRACT_CADENCE_MODEL.md(v3 合同-相位本体) · AGENTS.md §五(三层设计红线) §八(芜湖分册)
- 下游:SRP 4.0 代码实现 · Pareto 三方案 · 对比看板 · 评估报告
