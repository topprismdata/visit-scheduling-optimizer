# TopPrism L5 情景仿真引擎详细规范 v1.0 (Scenario & Simulation Engine Spec)

**Document ID:** TOPPRISM-L5-SCENARIO-SIMULATION-ENGINE-SPEC-v1.0  
**Version:** **v1.0-draft.2 (Phase 4 Detailed Specification - Corrected)**  
**Date:** 2026-08-24  
**Status:** **DETAILED SUBSYSTEM SPECIFICATION (NOT YET FROZEN)**  
**上游约束:** 
- `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md`
- `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2)
- `WORLD_MODEL_SYSTEM_BOUNDARY.md`
- `CANONICAL_TYPE_REGISTRY.md` (类型权威登记)

---

## 一、L5 情景仿真引擎的核心定位与架构责任

L5 情景仿真引擎（Prism Dynamics & Scenario Engine）是 **企业世界模型的“未来沙箱与反事实推演实验室”**。
它的核心职责是回答：**“如果企业采取某种动作（调店/改派/大仓调整/请假），未来世界状态与业务指标会发生什么确定性变化？”**

### 核心隔离原则
1. **沙箱不可见性**: 仿真过程中产生的分支状态（`BranchedWorldState`）全部在 L5 内部内存沙箱中闭环运行，**严禁向 L7 决策引擎暴露分支对象实例**；
2. **单值只读返回**: 对外唯一返回包含业务指标差异的 `ScenarioResult`（其内部 `delta_state` 字段包含 `StateDelta`）；
3. **确定性可重放**: 相同基线快照 + 相同扰动事件集 + 显式仿真时间戳 `simulation_time` $\implies$ 输出 100% 确定性的 `ScenarioResult` 与 256-bit SHA-256 分支指纹；
4. **类型封闭性**: 严禁使用 `Any`，所有载荷采用 `FrozenValue` 递归不可变类型。

---

## 二、形式化输入与输出契约 (消灭 Any，全类型封闭)

### 2.1 输入契约 (`request_scenario_rollout`)

```python
from prism_ontology.contracts.canonical_types import (
    FrozenValue, FrozenScalar, ApiRequestContext, PlanningIntent,
    PerturbationEvent, ScenarioResult   # 权威定义见 TOPPRISM_CANONICAL_TYPES_SPEC §22 / §24
)

def request_scenario_rollout(
    context: ApiRequestContext,
    base_snapshot_id: str,
    intent: PlanningIntent,
    perturbation_events: Tuple[PerturbationEvent, ...],
    simulation_time: datetime.datetime         # 强制显式仿真时钟 (必须带时区)
) -> ScenarioResult:
    """
    L5 受控入口：在内部沙箱中推演，对外仅返回 ScenarioResult。
    分支状态的 bitemporal.transaction_from 必须严格等于 simulation_time。
    """
```

### 2.2 输出契约 (`ScenarioResult`)

**权威定义**: `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md`
- `StateDelta`: §23
- `ScenarioResult`: §24（含 `delta_state: StateDelta`、`branch_hash`、容量影响摘要等完整字段）

（本节仅引用，不重复定义。）

---

## 三、真实容量影响推演计算公式 (带有量纲单位规范)

- $\text{Duration}(e)$: 历史事件 $e$ 的实际服务时长（单位：分钟 $\text{min}$）；
- $W_{\text{max}}$: 代表单日额定工作工时上限（单位：$480.0\text{ min/day}$）；
- $\text{WorkingDaysCount}$: 生效期内的有效工作日天数（扣除法定节假日与周末，单位：$\text{days}$）；
- $W_{\text{to}}^{\text{planned}}$: 目标代表在规划周期内已分配的计划服务总时长（单位：$\text{min}$）。

$$\Delta W_{\text{from}} = -\sum_{e \in \text{ExecutionStream}} \text{Duration}(e) \cdot \mathbb{I}(e.\text{rep} = \text{from\_rep} \land e.\text{store} = \text{target\_store}) \quad [\text{min}]$$

$$\Delta W_{\text{to}} = +\sum_{e \in \text{ExecutionStream}} \text{Duration}(e) \cdot \mathbb{I}(e.\text{rep} = \text{from\_rep} \land e.\text{store} = \text{target\_store}) \quad [\text{min}]$$

$$\text{OverloadRiskMin}_{\text{to}} = \max\left(0.0, \quad \left( W_{\text{to}}^{\text{planned}} + \Delta W_{\text{to}} \right) - \left( W_{\text{max}} \times \text{WorkingDaysCount} \right) \right) \quad [\text{min}]$$

---

## 四、阶段状态声明

- **规范版本**: `v1.0-draft.2`
- **状态**: 修正完成，作为 Phase 4 详细规范沉淀，**等待 Phase 1 业务语义签署完成后与整体 API 共同冻结**。
