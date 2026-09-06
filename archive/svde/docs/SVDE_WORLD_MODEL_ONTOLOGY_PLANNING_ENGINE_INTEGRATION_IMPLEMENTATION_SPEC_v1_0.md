# SVDE 世界模型、领域本体与规划引擎集成实施技术规格书 v1.0
**Document ID:** SVDE-WORLD-MODEL-ONTOLOGY-PLANNING-ENGINE-INTEGRATION-SPEC-v1.0  
**Date:** 2026-08-24  
**Status:** **TECHNICAL IMPLEMENTATION SPECIFICATION (工业级集成实施技术规格书)**  
**目标:** 将业务世界模型 v2.0、领域本体契约、通用数学抽象规范与运筹规划求解引擎端到端打通，形成可执行、可验证、可演进的闭环工程架构。

---

## 目录
1. [系统总体集成架构与三层契约流水线](#1-系统总体集成架构与三层契约流水线)
2. [第一级：世界模型与领域本体层集成规格 (Ontology Layer v2.0)](#2-第一级世界模型与领域本体层集成规格-ontology-layer-v20)
3. [第二级：语义编译与决策适配桥接规格 (Compiler & Bridge Adapter)](#3-第二级语义编译与决策适配桥接规格-compiler--bridge-adapter)
4. [第三级：抽象数学模型与求解引擎集成规格 (Solver & Engine Binding)](#4-第三级抽象数学模型与求解引擎集成规格-solver--engine-binding)
5. [质量门禁与双重机器验证器架构 (Dual Verification Gateways)](#5-质量门禁与双重机器验证器架构-dual-verification-gateways)
6. [端到端实施步骤与工程验收准则 (Roadmap & Acceptance Gates)](#6-端到端实施步骤与工程验收准则-roadmap--acceptance-gates)

---

## 1. 系统总体集成架构与三层契约流水线

系统严格遵循“业务语义在上 $\rightarrow$ 决策编译居中 $\rightarrow$ 算法求解在下”的三层独立解耦架构，各层之间通过不可篡改的数据与控制契约进行交互：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🔴 第一级：业务领域本体与世界模型层 (Business Domain & World Model Layer)              │
│    • 实体：Customer, Resource, CadenceSpec, OwnershipPolicy, AccountHierarchy,        │
│            ProductLineScope, SupplyNodeLink, MerchandisingCompliance, InStoreAction     │
│    • 契约输入：业务意图 (Intent)、管理政策 (Policies)、客户主数据 (Universe)          │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼ [Operational Contract / JSON Schema & SHACL]
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚪ 第二级：决策模型编译器与适配桥接层 (Semantic Compiler & Decision Gate Bridge)        │
│    • 核心组件：DecisionModelCompiler, SVDEOntologyAdapter (bridge.py)                  │
│    • 核心职责：将业务契约编译为数学规范参数 (集合 I, 周期 T, 严格模式空间 P_i, 成本矩阵)│
│    • 能力状态推进：将 periodic_visit_planning / daily_route_optimization 真正打通      │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼ [Mathematical Parameter Bundle / Matrix & Patterns]
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🟢 第三级：运筹规划求解引擎层 (Operations Research & Solver Engine Layer)               │
│    • 核心引擎：OR-Tools CP-SAT (周期排班主问题) + Held-Karp / PyVRP (单日闭环 TSP)     │
│    • 求解过程：崇川市中心 (Depot 0) 往返闭环、严格同周几模式选择、单日容量 <= 6 家     │
│    • 交付产物：4 周 20 工作日精确拜访日历与单日路径执行序列                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼ [Execution Plan Artifact]
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🛡️ 双重机器验证与质量门禁体系 (Dual Verification Gateways)                             │
│    • 门禁 1: CadenceComplianceAuditor (全量客户底表履约审计，零脱访/欠访/超频防护)     │
│    • 门禁 2: ScheduleMachineVerifier (周几一致性、单日工时预算、真实路网通行验证)      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 第一级：世界模型与领域本体层集成规格 (Ontology Layer v2.0)

### 2.1 五大核心新增实体数据契约 (Data Contracts)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import datetime

class ChannelTier(str, Enum):
    NKA = "NKA"               # 全国性连锁 (爱婴室、孩子王等)
    RKA = "RKA"               # 区域性连锁 (婴知岛、启东金晶等)
    LOCAL_KEY = "LOCAL_KEY"   # 本地重点店
    TRADITIONAL = "TRADITIONAL"

class InStoreActionType(str, Enum):
    EXPIRY_RISK_AUDIT = "EXPIRY_RISK_AUDIT"             # 效期防损 (基线: 45.7 min)
    OUT_OF_STOCK_REMEDY = "OUT_OF_STOCK_REMEDY"         # 缺货补货 (基线: 54.0 min)
    STORE_MANAGER_NEGOTIATION = "STORE_MANAGER_NEGOTIATION" # 店长订单 (基线: 54.5 min)
    NEW_CUSTOMER_SAMPLING = "NEW_CUSTOMER_SAMPLING"     # 开新派样 (基线: 55.0 min)
    PLANOGRAM_DISPLAY_AUDIT = "PLANOGRAM_DISPLAY_AUDIT" # 陈列核销 (基线: 61.5 min)

@dataclass(frozen=True)
class AccountHierarchy:
    """大客户组织与渠道层级 (Woodburn 2002/2014)"""
    account_id: str
    account_name: str
    channel_tier: ChannelTier
    parent_account_ref: Optional[str] = None
    central_agreement_ref: Optional[str] = None

@dataclass(frozen=True)
class ProductLineScope:
    """多产品线与品牌组合 (Johnston & Marshall 2016)"""
    brand_id: str
    brand_name: str                                     # 如 Prestige CN, Natura CN
    strategic_role: str                                 # CASH_COW / STRATEGIC_GROWTH
    default_actions: List[InStoreActionType] = field(default_factory=list)

@dataclass(frozen=True)
class SupplyNodeLink:
    """供应链大仓供货协同 (Shanahan 2007/2019)"""
    dc_id: str
    dc_name: str                                        # 如 爱婴室嘉善大仓, 孩子王南京总仓
    target_delivery_weekdays: List[int] = field(default_factory=list) # 固定送货周几
    visit_lead_time_hours: float = 24.0                 # 到货后响应巡店时限

@dataclass(frozen=True)
class MerchandisingCompliance:
    """合同陈列对赌量化履约 (Anderson & Stern 2004)"""
    contract_target_units: int                          # 合同排面目标数
    actual_compliant_units: int                         # 现场达标排面数
    compliance_ratio: float                             # 达成率
    has_oos_risk: bool = False

@dataclass(frozen=True)
class InStoreActionTaxonomy:
    """现场五大动作合成 (Zoltners et al. 2006)"""
    action_type: InStoreActionType
    estimated_duration_min: float
    is_mandatory: bool = True
```

### 2.2 向后兼容与已有对象挂接 (Backward Compatibility)
- `Customer` (门店) 新增可选字段：`account_hierarchy_ref: Optional[str]`, `supply_node_ref: Optional[str]`；
- `VisitDemand` (需求) 新增可选字段：`product_line_scope_refs: List[str]`；
- `VisitOccurrence` (拜访实例) 新增可选字段：`action_items: List[InStoreActionTaxonomy]`；
- `ExecutionHistory` (历史记录) 新增可选字段：`merchandising_compliance: Optional[MerchandisingCompliance]`。
- **兼容性保证**: 存量 Phase 0~4 测试与 A/C/D/E/B 场景完全免改造平滑通过。

---

## 3. 第二级：语义编译与决策适配桥接规格 (Compiler & Bridge Adapter)

### 3.1 决策桥接器升级实施 (`bridge.py`)
将 `bridge.py` 中原本标记为 `PLANNED` 的三项能力升级为具备**强契约语义校验与调用适配**的可用接口：

```python
class CapabilityStatus(str, Enum):
    PLANNED = "PLANNED"
    IMPLEMENTED = "IMPLEMENTED"

# 接口契约升级
def solve_periodic_planning(
    customer_universe: List[Customer],
    cadence_specs: List[CadenceSpec],
    planning_horizon: PlanningHorizon,
    depot_location: GeoLocation
) -> PeriodicSchedulePlan:
    """
    1. 校验 Customer Universe 完整性
    2. 生成严格同周几候选模式空间 P_i
    3. 调用求解引擎执行优化
    4. 返回经过机器核验的排班计划
    """
    pass
```

### 3.2 语义编译管道 (Semantic Compilation Pipeline)
1. **输入解析**: 接收第一级生成的业务政策包；
2. **模式空间生成 (Pattern Generation)**: 
   - 4 访/月门店 $\rightarrow$ 5 种严格同周几模式；
   - 2 访/月门店 $\rightarrow$ 10 种隔周同周几模式；
   - 1 访/月门店 $\rightarrow$ 20 种全月同周几模式；
3. **距离与耗时矩阵生成**: 调用 OSRM / Haversine 拓扑引擎计算 $N \times N$ 通勤耗时矩阵（含崇川中心 Depot 0）。

---

## 4. 第三级：抽象数学模型与求解引擎集成规格 (Solver & Engine Binding)

### 4.1 数学规范参数落地 (`SVDE-MATH-ABSTRACT-SPEC-v2.0`)
- **索引体系**: 客户节点 $i \in \{1, \dots, N\}$, Depot 节点 $0$, 时间槽 $(w, k) \in \{1..4\} \times \{1..5\}$；
- **硬约束清单**:
  1. $\sum_{p \in \mathcal{P}_i} \lambda_{ip} = 1$ (模式唯一选择，内嵌 100% 同周几等距)；
  2. $\sum_{i} x_{i, w, k} \le 6$ (单日上限 6 家)；
  3. $\sum_{i} S_i x_{i, w, k} + \sum_{i, j} C_{ij} y_{ij, w, k} \le 480$ (单日 8 小时红线)；
  4. 崇川中心起终点流守恒与 MTZ 子回路消除；
- **目标函数**:
  $$\min \quad Z = \sum_{(w, k) \in T} \sum_{i, j} C_{ij} y_{ij, w, k}$$

### 4.2 求解器调用与两阶段算法实现
1. **主问题 (Master Problem)**: 采用 OR-Tools CP-SAT 或列生成算法，求解客户在 20 个时间槽上的模式指派 $\lambda_{ip}$；
2. **子问题 (Daily Routing Subproblem)**: 对每日被指派的客户子集（$\le 6$ 家），调用 Held-Karp 精确算法快速求解闭环 TSP 最优顺序与通行时间。

---

## 5. 质量门禁与双重机器验证器架构 (Dual Verification Gateways)

任何由规划引擎或人工生成的排班方案，**必须串行通过双重机器验证器，否则严禁下发给一线销售代表**：

```
┌────────────────────────────────────────────────────────────────────────┐
│               【双重机器质量验证门禁 (Dual Verifiers)】                 │
├────────────────────────────────────────────────────────────────────────┤
│ 🛡️ 门禁 1: CadenceComplianceAuditor (频次与履约底线审计)                │
│    • 规则 1: 必须以在册全量客户底表为基准 (Left-Join)，零拜访强制抓取   │
│    • 规则 2: 四分格严格判定 (达标 / 欠访 / 脱访 / 超频)                 │
│    • 规则 3: Key 级或 REQUIRED 大店脱访直接触发 CRITICAL_INCIDENT 阻断 │
│                                                                        │
│ 🛡️ 门禁 2: ScheduleMachineVerifier (物理可行性与周几一致性验证)         │
│    • 规则 1: 检验全月所有门店进店周几，发现周几漂移直接判 INVALID       │
│    • 规则 2: 检验单日拜访家数是否 <= 6 家                               │
│    • 规则 3: 严格计算每条边通勤耗时与在店时长，检验单日工时是否 <= 480 min │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 端到端实施步骤与工程验收准则 (Roadmap & Acceptance Gates)

### 6.1 六大工程验收门禁 (Acceptance Gates G1 ~ G6)

- **[Gate G1] 领域本体 v2.0 DCR 评审通过**: 5 大新增对象在测试环境中向后兼容，Phase 0~4 基础 87 个测试 100% PASS；
- **[Gate G2] 真实数据摄入无缝对接**: 6,467 行真实 FMCG 数据通过 `FMCGRealDataIngestor` 零丢失映射，Phase 5 测试达到 111 个全量 PASS；
- **[Gate G3] 频次履约审计算子固化**: `CadenceComplianceAuditor` 成功在仁军 6 月历史数据中复现并拦截 NT23 零拜访事故；
- **[Gate G4] 严格同周几排班求解闭环**: 求解器输出 4 周完整日历，83 次应访 100% 精确吻合；
- **[Gate G5] 排班机器验证器 100% 通过**: `ScheduleMachineVerifier` 输出 `is_valid = True`，周几冲突为 0，单日超限为 0；
- **[Gate G6] 全工作区回归测试 100% 通过**: 全仓 269 个测试无跳过、无报错、无虚标，稳定运行。

---

## 7. 结语

本技术规格书为 TopPrism SVDE 销售拜访决策引擎从理论设计走向工业级工程落地提供了明确、严谨、可度量的实施蓝图。
