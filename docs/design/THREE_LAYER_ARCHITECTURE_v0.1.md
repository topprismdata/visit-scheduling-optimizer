# SRP 4.0 三层架构设计文档
## Semantic → Mathematical → Solver:接口定义、类型系统与层间契约

> **Document Status**: Draft v0.1 (2026-09-20)
> **Author**: TopPrism Algorithm Engineering
> **Prerequisite**: CONTRACT_CADENCE_MODEL.md (v3 合同-相位本体定稿) · SYSTEM_DESIGN_DOC.md v3.2 · AGENTS.md §五(三层设计红线)
> **GPT Review**: 已提交 ChatGPT 批判性审查(语义/数学/求解器业界对标: MathOpt, MiniZinc, Salesforce FS, Huawei OptVerse)

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

### 1.2 非目标(Non-Goals)

- 不在本轮更换 ALNS 算法本身
- 不在本轮引入服务时长/班次可行性(老板裁定出范围)
- 不在本轮做全国 572 线的完整迁移(芜湖 3 线试点先行)
- 不在本轮实现 Decision Memory 完整数据模型(GPT 建议"构建中",不声称已实现)

### 1.3 设计原则

```
业务事实 + sales-visit Operational Profile
         │
         ▼
┌─────────────────────────────────────────────┐
│ Layer 1 · Semantic Compiler                 │
│ prism-ontology / visit_ir                   │
│                                             │
│ 输入: 业务事实(客户/合同/走廊/例外)         │
│ 输出: VisitSemanticSpec (不可变)            │
│ 职责: 业务真值推导 · 规则硬度 · 放宽授权    │
│ 禁止: import visitmodel, ortools, srp.algos │
└─────────────────┬───────────────────────────┘
                  │ VisitSemanticSpec (冻结)
                  ▼
┌─────────────────────────────────────────────┐
│ Layer 2 · Mathematical Compiler             │
│ visitmodel                                  │
│                                             │
│ 输入: VisitSemanticSpec                     │
│ 输出: VisitMathIR (求解器无关的数学对象)    │
│ 职责: 变量定义 · 约束编译 · 目标向量 · 验证 │
│ 禁止: import srp.algos, visit_ir, 业务推断  │
└─────────────────┬───────────────────────────┘
                  │ VisitMathIR (冻结)
                  ▼
┌─────────────────────────────────────────────┐
│ Layer 3 · Solver Backend                    │
│ SRP / OptiCore                              │
│                                             │
│ 输入: VisitMathIR + SolverConfig            │
│ 输出: Solution (赋值 + reason code)         │
│ 职责: 搜索 · 优化 · 可行性维护              │
│ 禁止: import visit_ir, core.contract,      │
│       prism_ontology, LineData 中的语义字段 │
└─────────────────────────────────────────────┘
```

---

## 2. Invariants(跨层不变量)

以下五条在任何一层都不可违反,但**各层的违规响应不同**(GPT 建议,已采纳):

| # | 不变量 | L1 违规响应 | L2 违规响应 | L3 违规响应 |
|---|---|---|---|---|
| I1 | 频次守恒 → **义务守恒** | 拒绝编译 | Hard constraint | 产生 `MakeupDebt` → 升级 L2 |
| I2 | 走廊 K_min/K_max | 拒绝编译 | Hard constraint | Best effort → 违规记 `CorridorDeviation` |
| I3 | 星期几一致(R2′) | 拒绝编译 | Hard constraint | 通常不在 L3 改日期 |
| I4 | 间隔 ≥14 天 | 拒绝编译 | Hard constraint | 产生 `SpacingDebt` → 升级 L2 |
| I5 | 核心客户保全 | 拒绝编译 | Hard constraint | 不主动牺牲;不可服务记 `ServiceException` |

**关键语义变化**(GPT 建议,采纳): I1 从"频次守恒"升级为"**义务守恒**":

$$\text{Completed}_c + \text{FutureScheduled}_c + \text{OpenMakeupDebt}_c = \text{ContractObligation}_c$$

客户取消 ≠ 义务消失,而是产生 `MakeupDebt` 由 L2 吸收。

---

## 3. Layer 1 · Semantic Compiler (visit_ir / prism-ontology)

### 3.1 职责

- 定义外勤拜访领域的**所有业务概念及其关系**
- 从业务事实推导语义真值(f_c, K_min/K_max, 合法槽位集)
- 声明规则硬度和放宽授权
- 输出**不可变的** `VisitSemanticSpec`

### 3.2 类型系统(接口定义)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class ContractType(Enum):
    WEEKLY = "W"
    BIWEEKLY = "B"

class RuleHardness(Enum):
    HARD = "hard"        # 违规 → 拒绝编译 / 求解器不可越
    SOFT = "soft"        # 违规 → penalty / 记录

@dataclass(frozen=True)
class VisitContract:
    """一个客户的拜访合同"""
    contract_type: ContractType
    phase: Optional[int]         # 双周相位 (B 类必填)
    sigma: int                   # 星期几 (0=周一)
    legal_slot_indices: tuple    # 该合同+相位+星期几的合法槽位序号集
    f_c: int                     # 月拜访次数 (派生量, readonly)

@dataclass(frozen=True)
class WorkloadCorridorPolicy:
    """走廊策略: 来源 + 推导方式 + 审批状态"""
    k_min: int
    k_max: int
    source: str                  # "historical_baseline" | "management_directive"
    derivation: str              # "min/max(original_daily_counts)" | "manual"
    approved: bool

@dataclass(frozen=True)
class CoreProtectionPolicy:
    """核心客户保护策略: 不只是 bool"""
    mandatory_visit: bool        # 不能跳过
    cadence_relaxable: bool      # 频次可否放松
    weekday_relaxable: bool      # 星期几可否改变
    exception_priority: str      # CRITICAL / HIGH / NORMAL

@dataclass(frozen=True)
class ExceptionGrant:
    """例外授权: 不是'绕过规则',是'经过授权的另一条规则'"""
    scope: str                   # "single_date" | "date_range" | "customer" | "global"
    effective_dates: tuple
    target_rule: str             # 被修改的规则标识
    override_value: object
    reason: str
    authority: str               # 谁批准的

@dataclass(frozen=True)
class VisitSemanticSpec:
    """Layer 1 的编译产物: 不可变的语义规格"""
    contracts: dict              # customer_code → VisitContract
    corridor: WorkloadCorridorPolicy
    core_protections: dict       # customer_code → CoreProtectionPolicy
    exceptions: tuple            # tuple[ExceptionGrant]
    workdays: tuple              # 所有合法工作日 date
    metadata: dict               # 来源、版本、时间戳、审批链
```

### 3.3 编译接口

```python
class SemanticCompiler:
    """Layer 1 编译器: 业务事实 + profile → VisitSemanticSpec"""
    
    def compile(
        self,
        business_facts: dict,         # 原始数据: days_orig, customer master
        profile: "SalesVisitProfile", # 场景化操作档案(定义规则硬度/授权)
    ) -> VisitSemanticSpec:
        """
        编译步骤:
        1. 从 business_facts 反推 contract/phase/σ (contract_of)
        2. 从 contract 推导 f_c (派生, readonly)
        3. 从历史极值 + profile 推导走廊 (WorkloadCorridorPolicy)
        4. 从 profile 读取核心客户保护策略
        5. 收集 exceptions
        6. 输出不可变 VisitSemanticSpec
        """
```

### 3.4 与现有代码的映射

| 现有代码 | 迁移到 | 说明 |
|---|---|---|
| `LineData.freq` | `VisitSemanticSpec.contracts[c].f_c` | **derived/readonly**,不是独立输入 |
| `LineData.min_daily_capacity` | `WorkloadCorridorPolicy.k_min` | **语义所有权迁移到 L1** |
| `LineData.max_daily_capacity` | `WorkloadCorridorPolicy.k_max` | 同上 |
| `plan['OTM等级']` 核心筛选 | `CoreProtectionPolicy` | 不只是 bool,是完整保护策略 |
| `days_orig`(原始分配) | `business_facts`(编译输入,不进入 Spec) | |
| `check_rhythm()` | 保留,但从 `VisitSemanticSpec` 的合法槽位集推导,不再独立计算 | |

---

## 4. Layer 2 · Mathematical Compiler (visitmodel)

### 4.1 职责

- 接收 `VisitSemanticSpec`,**编译成求解器无关的数学对象**
- 定义变量、约束(从语义规格翻译)、目标向量(从语义目标翻译)
- 输出 `VisitMathIR`

### 4.2 类型系统

```python
@dataclass(frozen=True)
class VisitMathIR:
    """Layer 2 编译产物: 求解器无关的数学规格"""
    # 集合与参数 (从 SemanticSpec 翻译)
    customers: frozenset          # C
    workdays: frozenset           # T
    required_visits: dict         # c → f_c (从 SemanticSpec.contracts 派生)
    day_corridor: tuple           # (K_min, K_max) (从 SemanticSpec.corridor 翻译)
    eligible_days: dict           # c → frozenset(合法日期) (从 SemanticSpec 翻译)
    fixed_visits: frozenset       # 核心客户 (从 SemanticSpec.core_protections 翻译)
    
    # 列(候选方案)——由 Layer 3 提供或 Layer 2 从池中筛选
    candidate_columns: tuple      # 求解时注入
    
    # 目标规范(语义层定义含义,模型层翻译成数学)
    objective_spec: ObjectiveSpec

@dataclass(frozen=True)
class ObjectiveSpec:
    """多目标规范(L1 定义含义,L2 翻译成数学,L3 搜索前沿)"""
    primary: str                  # "total_distance"
    secondary: Optional[str]      # "max_daily_distance" | None
    tertiary: Optional[str]       # "daily_count_cv" | None
    lexicographic: bool           # True = 字典序; False = 加权
    weights: Optional[dict]       # 加权模式的权重

@dataclass(frozen=True)
class SolverConfig:
    """Layer 3 求解配置(L3 独有,L2 不知道)"""
    backend: str                  # "cp_sat" | "gurobi" | "alns"
    time_limit_s: float
    seed: int
```

### 4.3 编译接口

```python
class MathCompiler:
    """Layer 2 编译器: VisitSemanticSpec → VisitMathIR"""
    
    def compile(self, spec: VisitSemanticSpec) -> VisitMathIR:
        """
        编译规则(每条都是从语义到数学的确定性翻译,无业务判断):
        
        SemanticSpec.contracts[c].f_c
          → required_visits[c] = f_c                    # C1 频次覆盖
        
        SemanticSpec.corridor.k_min / k_max
          → day_corridor = (k_min, k_max)               # C2 走廊
        
        SemanticSpec.contracts[c].legal_slot_indices
          → eligible_days[c] = {...}                    # C3 合法日期(从合同+相位翻译)
        
        SemanticSpec.core_protections[c].mandatory_visit
          → fixed_visits = {c: ...}                     # C5 核心保全
        
        SemanticSpec.exceptions
          → 修改 eligible_days / required_visits        # 例外授权
        """
```

### 4.4 求解器接口(L3 调用,L2 定义)

```python
class SolverBackend(Protocol):
    """Layer 3 实现的求解后端协议"""
    def solve(self, ir: VisitMathIR, config: SolverConfig) -> "MathSolution": ...

# Layer 3 只看到 VisitMathIR 和 SolverConfig:
# - 不知道 VisitSemanticSpec 的存在
# - 不知道 K_min 为什么是 17
# - 不知道什么是 "核心客户"
# - 只知道: required_visits / day_corridor / eligible_days / fixed_visits
```

---

## 5. Layer 3 · Solver Backend (SRP / OptiCore)

### 5.1 职责

- 接收 `VisitMathIR + SolverConfig`,高效搜索最优/近优解
- 返回 `Solution`(变量赋值 + reason code + 增量成本)
- **不知道任何业务语义词汇**(core_customer, contract, phase, corridor...)

### 5.2 类型系统

```python
@dataclass(frozen=True)
class Solution:
    assignments: dict             # date → tuple[customer_idx] (有序)
    objective_value: float
    reason_codes: dict            # customer_code → "assigned_day_X" | "corridor_cap" | ...
    meta: dict                    # iters, accepted, solve_time
```

### 5.3 允许的算法(Layer 3 内部自由选择)

| 算法 | 用于 | 层内定位 |
|---|---|---|
| R2′-ALNS | Layer 3 full search 的列生成器 | 搜索元启发式 |
| CP-SAT exact TSP | 单日精确排序 | 精确后端 |
| NN + 2opt | 轻量近似(实时场景) | 路由启发式 |
| SP/CP-SAT | 列重组 + 整数规划 | 数学规划后端 |

### 5.4 禁止事项(CI 强制)

```python
# 在 srp/algos/** 中, 以下 import 被 CI 拒绝:
from visit_ir import ...          # ❌ 语义层
from prism_ontology import ...    # ❌ 语义层
from core.contract import ...     # ❌ 语义层 shim
from data.loader import ...       # ❌ 业务原始数据

# 在 visit_ir/** 中, 以下 import 被拒绝:
from visitmodel import ...        # ❌ 模型层
from ortools import ...           # ❌ 求解器
from srp import ...               # ❌ 算法层
from opticore import ...          # ❌ 算法层辅助
```

---

## 6. 层间传递对象(不可变)

| 传递对象 | 从 → 到 | 内容 | 可变性 |
|---|---|---|---|
| `VisitSemanticSpec` | L1 → L2 | 合同/走廊/保护/例外/工作日 | **frozen**(dataclass frozen=True) |
| `VisitMathIR` | L2 → L3 | 变量/约束/目标/列/求解配置 | **frozen** |
| `Solution` | L3 → 下游 | 赋值 + reason code + meta | 可变(但建议 frozen) |

每层只通过这些**不可变的编译产物**通信,不共享内部状态。

---

## 7. 三层与既有模块的映射(迁移路径)

| 现有模块 | 新归属 | 迁移动作 |
|---|---|---|
| `visit_ir/contract.py` | L1 | 保留,扩充(K/核心/例外/硬度) |
| `visit_ir/compiler.py` | L1 | **新增**(SemanticCompiler) |
| `visitmodel/sp/formulation.py` | L2 | 拆分: formulation → L2; CG → L3 |
| `visitmodel/tsp/open_chain.py` | L2 | 保留(formulation 定义) |
| `algos/r2_alns_v2_backup.py` | L3 | 剥离 contract_of/check_contract 调用 → 改收 `VisitSemanticSpec` 翻译后的纯数学参数 |
| `algos/sp_matheuristic.py` | L3 | 剥离 `days_orig` 的 `k_c` 推断 → 改收 `VisitMathIR.required_visits` |
| `algos/tsp_engine.py` | L3 | 保留 |
| `opticore/heuristics.py` | L3 | 保留 |
| `core/metric.py` | L3 | 保留(day_km/total_km/check_capacity) |
| `core/contract.py` | L1 shim | 保留(桥接 visit_ir) |
| `data/loader.py` | L1 输入端 | 保留(读取原始数据) |
| `LineData` | L1/L3 边界对象 | 保留,但 `__post_init__` 中的走廊推导 → 移入 L1 SemanticCompiler |

---

## 8. 精磨路线图(按优先级)

### Phase A · 接口定义与类型锁死(本周)
1. 定义 `VisitSemanticSpec` / `VisitMathIR` / `Solution` 三个 frozen dataclass
2. 定义 `SemanticCompiler.compile()` / `MathCompiler.compile()` / `SolverBackend.solve()` 接口
3. CI 加 architecture test(禁止跨层 import)

### Phase B · 语义层扩建(下周)
4. 将 `K_min/K_max` / `f_c` / `core_protection` 的**语义所有权**从 LineData 迁移到 SemanticCompiler
5. 新增 `WorkloadCorridorPolicy` / `CoreProtectionPolicy` / `ExceptionGrant` 类型
6. visit_ir 的 contract 模式重命名为显式 dialect(不是逃逸通道)

### Phase C · 模型层精磨(下下周)
7. visitmodel 拆分: formulation(L2) vs column_generation(L3)
8. `VisitMathIR` 正式实现
9. SP/Pareto/TSP 的数学规范文档(对齐 MathOpt/MiniZinc 风格)

### Phase D · 算法层改造(之后)
10. ALNS 剥离 contract 依赖,改收编译后参数
11. SPMatheuristic 剥离 days_orig 推断,改收 VisitMathIR
12. Layer Escalation 状态机(L3 → L2 → L1 升级路径)

---

## 9. Alternatives Considered

| 替代方案 | 为什么不选 |
|---|---|
| 全部 monorepo | 三层变化周期不同(本体最稳/算法最快),统一发版会互相拖累 |
| Python 逐步加 type hint + mypy strict | 理论上可行,但不能强制禁止跨层 import(CI 可以,但 dataclass frozen 更稳) |
| protobuf/thrift IDL 定义层间接口 | 对 Python 内部通信过重;dataclass frozen + CI 足够 |
| 保持现状(靠纪律) | 已实证不可靠——本 session 的多次错误(单位错/语义泄漏/重复声明)均因缺代码结构保障 |

---

## 10. 开放问题(待业务确认)

1. 双周店相位 φ 是否可翻(偶↔奇)?默认不可翻(跨月延续优先),待业务确认
2. 多次拜访间隔的例外授权权限在谁手里(区域经理 vs 总部)?
3. Layer 3 的"自然走廊"粒度:街道级(300m)还是街区级(500m)?
4. Decision Episode 的最小字段集(为 Decision Memory 预留)
