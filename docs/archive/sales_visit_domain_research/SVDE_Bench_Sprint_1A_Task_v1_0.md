# SVDE-Bench Sprint 1A Core Schema Implementation Task v1.0
## 核心决策模式实现任务书与字段契约冻结（Sprint 0.6 修正）

> **文档标识**：`SVDE-BENCH-SPRINT-1A-TASK-V1.0`  
> **冻结日期**：2026-08-22  
> **执行角色**：SVDE-Bench Core Engineer Agent  
> **前置依赖**：Sprint 0 / 0.5 验收通过（KB-GOV-035）  
> **阶段拆分**：将原 Sprint 1 拆分为 **Sprint 1A (Core Decision Schema ◀ 本阶段)** 与 **Sprint 1B (Memory Schema)**，坚决不提前引入复杂 Memory 引擎。

---

## 1. 字段契约升级（Sprint 0.6 修订）

1. **`contract` $\to$ `semantic_contract`**：强调核心语义契约对象，杜绝与普通 API contract 混淆。
2. **`DecisionArtifact` 增加 `validation_result`**：明确关注 `Decision → Validation` 闭环。

---

## 2. 核心数据模型规范（Pydantic v2 强类型实现）

### 2.1 `DecisionCase` (`svdebench.core.case`)
```python
class DecisionCase(BaseModel):
    metadata: CaseMetadata                     # id, domain, name, created_at, tags
    intent: Dict[str, Any]                     # 业务目标、优先级偏好、预算目标
    world_state: Dict[str, Any]                # 初始物理环境、可用资源、车辆/货位/商圈底图
    semantic_contract: Dict[str, Any]          # C1..Cn 语义约束清单与 I1..Im 业务不变量
    runtime_context: Optional[Dict[str, Any]]  # 动态场景专用：时间戳 t、状态切片、历史不可逆事实
    events: List[Dict[str, Any]]               # 动态场景专用：事件流序列
```

### 2.2 `DecisionArtifact` (`svdebench.core.artifact`)
```python
class DecisionArtifact(BaseModel):
    case_id: str
    status: str                                # FEASIBLE | INFEASIBLE
    decision: Dict[str, Any]                   # 最终决策输出（如指派矩阵、排程序列）
    trace: DecisionTrace                       # 完整决策因果追踪
    explanation: Dict[str, Any]                # 面向业务的决策理由与未选方案原因
    validation_result: Optional[Dict[str, Any]]# 决策可行性自验结果 (DSVL precheck / M1 preservation)
    memory_patch: Optional[Dict[str, Any]]     # 候选记忆补丁（Sprint 1A 保持可选/空）
```

### 2.3 `DecisionTrace` (`svdebench.core.trace`)
```python
class DecisionTrace(BaseModel):
    trace_id: str
    decision_chain: List[Dict[str, Any]]       # Intent → Contract → Type → Model → Solution
    causal_rationale: List[Dict[str, Any]]     # 针对每个实体的选择理由
    constraint_provenance: Dict[str, str]      # 约束到业务法源的映射
```

---

## 3. 双向序列化与校验要求（Serialization & Validation）

1. **双向无损转换**：
   $$\text{Pydantic Object} \longleftrightarrow \text{YAML / JSON} \longleftrightarrow \text{Pydantic Object}$$
2. **严密字段校验**：
   - 必填字段缺失自动抛出 `ValidationError`；
   - 动态场景下若包含 `events` 但缺失 `runtime_context` 自动拦截；
   - 非法 `status` 枚举值（非 `FEASIBLE / INFEASIBLE`）自动报错。

---

## 4. 测试用例要求（`tests/test_schema.py`）

必须包含且全部通过以下测试：
- `test_decision_case_serialization_roundtrip`: YAML/JSON 双向序列化无损测试；
- `test_decision_artifact_validation`: 决策产物校验（含 `validation_result` 与 `trace`）；
- `test_invalid_case_rejection`: 校验非法输入案例的确定性报错（Missing fields / Invalid enum）；
- `test_trace_structure_integrity`: 验证决策因果链结构的完整性。

---

## 5. Sprint 1A 验收标准（DoD）

- [x] `DecisionCase`、`DecisionArtifact`、`DecisionTrace` 模式定义完成并位于 `svdebench.core`。
- [x] 支持 YAML/JSON 双向序列化与反序列化。
- [x] 单元测试覆盖合法用例与非法用例，`pytest` 100% 通过。
- [x] 零 Memory 引擎实现混入（保持边界）。
