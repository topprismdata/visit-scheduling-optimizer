# SVDE-Bench v0.2 — Sprint 1: Schema + Generator + Validator Task v1.0
## Engineering Execution Specification — Phase 7.4.19

> **执行纪律**：严禁先生成 100 个 Case 配置文件 — 先固化 Schema，建立 Generator 与 Validator 自动化工具链，跑通"生成 → 校验 → Oracle → Profile"端到端最小闭环后，再启动 Sprint 2 扩 Case。

---

## 0. 项目背景与目标

**项目目标**：将 SVDE-Bench 从 v0.1（10 个 Golden Cases）扩展到 v0.2（100 个 Decision Benchmark Cases）。

**Sprint 1 唯一目标**：在不增加任何新 Case 的前提下，建立可扩展的基础设施：

1. **多文件 Schema 固化**：从单 YAML 文件拆分为 10 个 YAML 子文件（每个子文件单一职责）
2. **Generator 工具链**：程序化生成 Case 骨架（含约束验证 + Oracle 可行性预检）
3. **Validator 自动化**：Schema 验证 + Oracle 实际运行 + 4 维 Evaluator + Profile 生成一体化流水线

**开发原则**：
- 不增加 Case YAML（除 Generator 自身测试用 fixture）
- 不扩展 Solver Benchmark
- 严禁手工创建"容易赢"的 Case
- 每个 Case 必须体现真实企业决策困难

---

## 1. 目标目录结构（冻结）

```
svde-bench/

├── svdebench/
│
├── cases/
│   ├── golden/           ← Sprint 0-5 已就绪的 10 Cases 保持不动
│   ├── extended/        ← Sprint 2+ 扩 Case 落地点（本次不创建）
│   │   ├── delivery/
│   │   ├── warehouse/
│   │   ├── channel/
│   │   └── visit/
│
├── schemas/
│   ├── case/             ← 本 Sprint 任务：10 个子 Schema（每个子文件单一职责）
│   │   ├── metadata.yaml
│   │   ├── intent.yaml
│   │   ├── world_state.yaml
│   │   ├── constraints.yaml
│   │   ├── decision_space.yaml
│   │   ├── runtime_events.yaml
│   │   ├── oracle.yaml
│   │   ├── expected_failure.yaml
│   │   ├── evaluation.yaml
│   │   └── memory_trace.yaml
│   └── profile/         ← Profile 多文件 Schema
│       ├── semantic.yaml
│       ├── feasibility.yaml
│       ├── runtime.yaml
│       └── memory.yaml
│
├── profiles/
│
├── tools/
│   └── case_generator/   ← 本 Sprint 任务：核心开发内容
│       ├── __init__.py
│       ├── case_synthesizer.py
│       ├── schema_validator.py
│       ├── oracle_runner.py
│       ├── evaluator_runner.py
│       ├── profile_builder.py
│       ├── cli.py
│       └── tests/
│           ├── test_synthesizer.py
│           ├── test_validator.py
│           ├── test_oracle_runner.py
│           ├── test_evaluator_runner.py
│           └── test_profile_builder.py
│
└── reports/
```

**注意**：原 `svdebench/datasets/public/cases/` 仍保留（10 个 Golden Cases 不动）；新多文件 Schema 走 `schemas/case/`，最终组装在 `cases/extended/`。

---

## 2. 多文件 Case Schema（核心任务 — 冻结为 10 个独立 YAML Schema）

每个 Schema 为独立 YAML 文件，**单一职责**：

### 2.1 `schemas/case/metadata.yaml`

```yaml
case_id: STRING (required, pattern: ^(CASE|golden)-(delivery|warehouse|channel|visit)-\d{3}$)
domain: STRING (required, enum: [delivery, warehouse, channel, visit])
title: STRING (required)
version: STRING (default: "1.0")
created_at: TIMESTAMP
tags: LIST<STRING>
difficulty: STRING (enum: [L1, L2, L3, L4, L5])
```

### 2.2 `schemas/case/intent.yaml`

```yaml
primary_objective: STRING (required)
secondary_objectives: LIST<STRING>
priority_rules:
  vip_customer: ENUM (high|medium|low)
  cost: ENUM (high|medium|low)
  service_level: ENUM (high|medium|low)
```

### 2.3 `schemas/case/world_state.yaml`

```yaml
entities:
  vehicles: LIST<OBJECT> (id, type, capacity_kg, status, available_zones)
  customers: LIST<OBJECT> (id, name, priority, location)
  orders: LIST<OBJECT> (id, weight_kg, req_cold, tw_early, tw_late, is_locked, is_vip)
  drivers: LIST<OBJECT> (id, name, available_hours)
  zones: LIST<OBJECT> (id, type, capacity)
relationships:
  vehicle_route: LIST<OBJECT>
  customer_priority: LIST<OBJECT>
```

### 2.4 `schemas/case/constraints.yaml`

```yaml
hard:        # MUST be satisfied; violations → Oracle INFEASIBLE or Agent FAIL
  - id: STRING
    name: STRING
    type: STRING (enum: [VEHICLE_CAPACITY, TIME_WINDOW_HARD, COLD_CHAIN_MATCH, COMMITMENT_LOCK, ...])
    expression: STRING
soft:        # SHOULD be satisfied; violations → penalties or warnings
  - id: STRING
    weight: FLOAT
    ...
preference:  # Business heuristics; advisory only
  - description: STRING
```

### 2.5 `schemas/case/decision_space.yaml`

```yaml
objective: STRING (default: "lexicographic_max_fulfilled_then_min_disruption")
candidate_solutions_count: INTEGER (upper bound hint)
parallel_options: LIST<OBJECT>
```

### 2.6 `schemas/case/runtime_events.yaml`

```yaml
events:
  - time: TIMESTAMP
    type: STRING (enum: [VEHICLE_BREAKDOWN, TRAFFIC_CONGESTION, NEW_ORDER, WINDOW_CHANGE, ...])
    affected_entity: STRING
    parameters: MAP
```

### 2.7 `schemas/case/oracle.yaml`

```yaml
solver: STRING (default: "OR-Tools CP-SAT")
version: STRING
objective_formulation: STRING
timeout_seconds: INTEGER (default: 300)
expected_optimal_value_range: OBJECT (min, max)
```

### 2.8 `schemas/case/expected_failure.yaml`

```yaml
failure_modes:
  - id: STRING (enum: [FT-01..FT-05])
    description: STRING
    trigger_condition: STRING
    expected_behavior: STRING
```

### 2.9 `schemas/case/evaluation.yaml`

```yaml
expected_difficulty: STRING (enum: [easy, medium, hard])
expected_agent_separation: BOOLEAN
separation_dimensions: LIST<STRING>
success_threshold:
  semantic_min: FLOAT (default: 0.9)
  commitment_survival_min: FLOAT (default: 1.0)
```

### 2.10 `schemas/case/memory_trace.yaml`

```yaml
memory:
  episode:
    id: STRING
    previous_decision: STRING
    outcome: STRING
    confidence: FLOAT (0.0..1.0)
```

**每个子 Schema 必须实现为 Pydantic BaseModel**，支持：

```python
class Metadata(BaseModel):
    case_id: str = Field(..., regex=r'^(CASE|golden)-...$')
    domain: Literal["delivery", "warehouse", "channel", "visit"]
    ...
```

---

## 3. Generator 工具链（核心开发）

### 3.1 目录：`tools/case_generator/`

### 3.2 `case_synthesizer.py` — Case Synthesizer

```python
class CaseSynthesizer:
    """
    通过编程方式生成 Case 骨架（不包含业务内容）。
    生成的 Case 必须通过 SchemaValidator 验证。
    """
    def __init__(self, schema_root: Path):
        self.schema_root = schema_root
        self.validator = SchemaValidator(schema_root)
    
    def synthesize(
        self,
        domain: Literal["delivery", "warehouse", "channel", "visit"],
        complexity: Literal["basic", "service", "multi_objective", "continuous_runtime"],
        case_id: str
    ) -> Path:
        """生成单 Case 多文件骨架，返回案例目录路径"""
        ...
    
    def batch_synthesize(
        self,
        domain: str,
        complexity: str,
        count: int
    ) -> List[Path]:
        """批量生成 Case 骨架"""
        ...
```

### 3.3 `schema_validator.py`

```python
class SchemaValidator:
    """
    验证生成的 Case 文件是否符合 10 个子 Schema。
    使用 Pydantic 进行强类型验证。
    """
    def __init__(self, schema_root: Path):
        self.schema_root = schema_root
    
    def validate_case(self, case_dir: Path) -> ValidationReport:
        """验证单个 Case 目录中的所有 10 个 YAML 文件"""
        ...
    
    def validate_pydantic_compliance(self, case_dir: Path) -> bool:
        """使用 Pydantic BaseModel 进行深度结构验证"""
        ...
    
    def detect_schema_drift(self) -> List[SchemaDrift]:
        """检测与 Sprint 0-5 既有 10 个 Case 的字段一致性"""
        ...
```

### 3.4 `oracle_runner.py`

```python
class OracleRunner:
    """
    自动调用 CPSATExactOracle 对生成的 Case 求解。
    超时（>300s）标记 TIMEOUT；不人工干预。
    """
    def __init__(self, oracle_timeout: int = 300):
        self.timeout = oracle_timeout
    
    def run(self, case_dir: Path) -> OracleResult:
        """加载 case + 求解 + 返回完整 OracleResult JSON"""
        ...
    
    def is_feasible(self, result: OracleResult) -> bool:
        """Oracle 可行性预检（生成前使用）"""
        ...
```

### 3.5 `evaluator_runner.py`

```python
class EvaluatorRunner:
    """
    调用 4 维 Evaluator + 3 类 Baseline Agent 生成 Profile。
    """
    def run_full_evaluation(
        self,
        case_dir: Path,
        agent_names: List[str] = ["PureSolverMockAgent", "SemanticAwareAgent", "FullDecisionAgent"]
    ) -> Dict[str, DecisionProfile]:
        ...
```

### 3.6 `profile_builder.py`

```python
class ProfileBuilder:
    """
    从 EvaluatorRunner 输出的 4 维画像构建强类型 DecisionProfile JSON。
    """
    def build(
        self,
        case_id: str,
        oracle_result: OracleResult,
        evaluator_results: Dict[str, Any]
    ) -> DecisionProfile:
        ...
```

### 3.7 `cli.py` — CLI 入口

```python
# svde bench generate --domain delivery --count 10
# svde bench validate --case cases/extended/delivery/d_001
# svde bench oracle-run --case ...
# svde bench full-pipeline --case ...

import click

@click.group()
def cli():
    pass

@cli.command()
@click.option('--domain', required=True, type=click.Choice(['delivery', 'warehouse', 'channel', 'visit']))
@click.option('--complexity', default='basic')
@click.option('--count', default=1)
def generate(domain, complexity, count):
    """生成 Case 骨架（不写入业务内容）"""
    ...

@cli.command()
@click.option('--case', required=True, type=click.Path(exists=True))
def validate(case):
    """验证 Case 多文件 Schema 完整性"""
    ...

@cli.command()
@click.option('--case', required=True, type=click.Path(exists=True))
def oracle_run(case):
    """运行 Oracle 求解"""
    ...

@cli.command()
@click.option('--case', required=True, type=click.Path(exists=True))
def full_pipeline(case):
    """端到端: validate → oracle → 4 evaluator → Profile"""
    ...
```

`setup.py` / `pyproject.toml` 注册 `console_scripts: svde-bench = tools.case_generator.cli:cli`。

---

## 4. 测试覆盖（CI 阻断）

`tools/case_generator/tests/` 下必须实现 ≥ 8 组测试：

| 测试 | 验证 |
|---|---|
| `test_synthesizer.py` | Generator 可生成 10 个子文件；文件结构正确；命名规范 |
| `test_synthesizer_complexity.py` | 4 个复杂度层级（basic/service/multi_objective/continuous_runtime）正确产出 |
| `test_validator.py` | SchemaValidator 对合法 Case 通过，对 5 类非法 Case（字段缺失/类型错误/枚举越界/引用断裂/CID 重复）正确报错 |
| `test_validator_drift.py` | 检测生成的 Case 与 Sprint 0-5 既有 10 Case 字段一致性 |
| `test_oracle_runner.py` | 自动 Oracle 求解生成 `oracle_result.json`；超时（>300s）正确标记 TIMEOUT |
| `test_oracle_runner_isolated.py` | Oracle 输出不包含 agent / evaluator 任何字段 |
| `test_evaluator_runner.py` | 4 维 Evaluator 全部执行；输出 Profile 字段完整性 |
| `test_profile_builder.py` | Profile JSON 满足 DecisionProfile Pydantic 严格类型 |

**全部 8 组测试必须 pass 才算 Sprint 1 完成**。

---

## 5. 验收门禁（Gates）

```
Gate 1: Schema Validation     ✅ all 10 sub-schemas parseable + Pydantic compliant
Gate 2: Oracle Run            ✅ auto-generated Case solvable within 300s OR marked TIMEOUT
Gate 3: Evaluator Run         ✅ all 4 dimensions execute
Gate 4: Profile Generation    ✅ typed DecisionProfile JSON produced
Gate 5: CLI Smoke             ✅ svde bench full-pipeline --case <fixture> completes end-to-end
```

---

## 6. 严禁事项 (Hard Prohibitions)

1. **禁止生成业务内容 Case**：本次 Sprint 仅生成 Generator 自身的 fixture（如 `golden/DELIVERY-FIXTURE-001`），不预先填入真实业务数据
2. **禁止手工创建 100 个 Case YAML**：所有 Case 必须经 Generator 产出 → Validator 通过 → Oracle 求解 → Evaluator 跑通
3. **禁止修改 Sprint 0-5 已有 10 个 Case**：保持向后兼容
4. **禁止扩展 Solver Benchmark**：本 Sprint 目标是基础设施，不比较 CP-SAT vs MIP
5. **禁止新增文档除非必要**：本 Sprint 输出仅为代码 + 测试 + 1 份简明 README

---

## 7. 最终交付物清单

```
svde-bench/
├── schemas/case/*.yaml (10 files)
├── schemas/profile/*.yaml (4 files)
├── tools/case_generator/
│   ├── case_synthesizer.py
│   ├── schema_validator.py
│   ├── oracle_runner.py
│   ├── evaluator_runner.py
│   ├── profile_builder.py
│   ├── cli.py
│   └── tests/ (8 test files)
├── pyproject.toml (updated with svde-bench CLI entry)
└── reports/
    └── SPRINT_1_VALIDATION_REPORT.md  ← 简明验收报告
```

---

## 8. 执行顺序（Sprint 1 Day-by-Day）

### Day 1 (2026-08-24)
- [ ] 创建 `schemas/case/` 与 `schemas/profile/` 14 个 YAML Schema 文件
- [ ] 实现 `tools/case_generator/case_synthesizer.py` 与 `schema_validator.py`

### Day 2 (2026-08-25)
- [ ] 实现 `oracle_runner.py` 与 `evaluator_runner.py`
- [ ] 实现 `profile_builder.py`

### Day 3 (2026-08-26)
- [ ] 实现 `cli.py` 与 `pyproject.toml` CLI 注册
- [ ] 编写 8 组测试并 100% pass
- [ ] 输出 `SPRINT_1_VALIDATION_REPORT.md`

---

## 9. 执行反馈

完成后请输出：

```yaml
Completed:
  - schemas/case/ (10 files)
  - schemas/profile/ (4 files)
  - tools/case_generator/ (6 modules + 8 tests)

Files:
  - paths of created/modified files

Tests:
  - pytest output (8 tests pass)

Schema Compliance:
  - Pydantic validation for all 10 sub-schemas
  - Round-trip YAML ⇄ Python object validated

Oracle Integration:
  - fixture case solvable within 300s (TARGET_TIME / ORACLE_RESULT)

Profile Generation:
  - fixture case produces typed DecisionProfile JSON

Issues:
  - (any issues or "none")

Next Step:
  - Sprint 2: Dynamic Delivery Domain (10→40 Cases Expansion)
```

---

## 10. Sprint 2 启动条件

Sprint 1 必须 100% 完成且所有 Gate 通过，方可启动 Sprint 2：

> **Sprint 2: Dynamic Delivery Domain Expansion (10→40 Cases)**

Sprint 2 将基于 Sprint 1 工具链扩 30 个 Dynamic Delivery Cases（D01-D40），分 4 个复杂度：
- D01-D10 基础动态调整（new order / delay / vehicle issue）
- D11-D20 服务承诺决策（VIP SLA / time windows）
- D21-D30 多目标权衡（cost vs service）
- D31-D40 连续 Runtime Adaptation（多事件连续重排）

**每个 Case 必须经 Generator → Validator → Oracle → Evaluator → Profile 五关全过**。
