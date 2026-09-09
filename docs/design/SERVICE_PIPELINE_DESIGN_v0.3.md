# 三阶段求解服务设计（语义 → 建模 → R2-ALNS）

> **状态**：草稿 v0.3 · 2026-09-08（v0.2 实现落地并经两轮独立评审；v0.3 增补抽象模型附录 A）
> **目标**：把"规则语义 → 数学建模 → R2-ALNS 求解"打包为相对通用的服务，每阶段输入/输出均为标准 JSON，阶段边界即契约边界。
> **归属**：母仓 `svc/`（编排 + schema）；三层纪律不变——VisitIR（语义）/ VisitModel（数学）/ OptiCore（引擎）。

---

## 0. 设计原则

1. **JSON 契约是唯一阶段边界**——跨阶段禁止传 Python 对象；每个产物带 `schema` + `version` + `inputs_hash`（可追溯、可重放）。
2. **每阶段独立可执行**——CLI 一进一出（JSON→JSON），可单独重放/测试/换引擎。
3. **引擎无语义**——OptiCore 只见数字；语义解释全部在 Stage 1 完成。
4. **确定性**——同输入 + 同 seed ⇒ 逐位一致输出（seed 进契约）。
5. **五道闸内建**——count/capacity/r2/contract/结构保证作为 Stage 3 输出的验收块，不达标即 `status=INFEASIBLE/FAILED`，不出半成品。

---

## 1. 三阶段总览

```
原始计划 (xlsx/JSON)
      │  Stage 1 语义编译  svc.stages.semantic
      ▼
ProblemSpec v1  ──────────────────────────►  problem.json
      │  Stage 2 数学建模   svc.stages.model
      ▼
ModelManifest v1 ─────────────────────────►  model.json
      │  Stage 3 求解       svc.stages.solve (R2-ALNS)
      ▼
SolutionBundle v1 ────────────────────────►  solution.json
```

编排两种形态：
- **CLI 管道**：`python -m svc.run --plan plan.xlsx --out outdir/`（三阶段串行落盘）
- **HTTP 服务（异步）**：`POST /v1/jobs`（multipart 上传 → **202** + `{job_id}`；R2-ALNS 600s 级，同步必超时）
  → `GET /v1/jobs/{id}`（状态 + 三 JSON 打包）；`POST /v1/stages/{semantic|model|solve}` 单阶段（同步，均 <10s 语义/建模除外 solve 仍异步）
- **统一错误包络**：`{"schema": "visitflow/error", "stage": "...", "code": "...", "message": "...", "detail": {...}}`（HTTP 4xx/5xx 与 CLI 非零退出同构）

---

## 2. Stage 1：语义编译（原始计划 → ProblemSpec）

**职责**：Excel/JSON 原始计划 → 规范化问题对象。合同-节拍-相位本体、走廊、合法域全部在此定死。

```json
{
  "schema": "visitflow/problem",
  "version": "1.0",
  "inputs_hash": "sha256:...",
  "source": {"kind": "xlsx", "path": "SRP-7月.xlsx", "sheet": "Sheet1",
             "filter": {"计划是否有效标识": "有效"}},
  "calendar": {"dates": ["2026-07-01", "..."], "n_days": 23},
  "stores": [
    {"id": 0, "code": "C001", "lon": 113.25, "lat": 23.05,
     "contract": {"kind": "W", "phase": 0, "required_visits": 12},
     "f_derived": {"2026-W27": 3, "2026-W28": 3},
     "legal_dates_idx": [0, 1, 2, "..."]}
  ],
  "corridor": {"min_daily": 23, "max_daily": 35},
  "original_assignment": {"0": [3, 7, "..."], "...": "..."},
  "distance": {"kind": "osm_cycling", "scope": "per-line",
                "matrix_ref": "sha256:...", "format": "npz", "n": 163,
                "unreachable_sentinel": 1e9,
                "note": "维度必须 == n_stores; 哨兵弧禁止出现在任何输出路线中"},
  "meta": {"line_id": "09", "n_stores": 163, "n_visits": 754}
}
```

**要点**：
- 合同域 `{kind: W|B, phase}`——f 由合同**派生**（零例外，禁手填）；`required_visits` 为 count 闸显式输入；f 表内联便于下游对账（VisitIR 15 行核心逻辑迁入 `svc/semantic.py`）
- 距离矩阵按线作用域（维度 == n_stores），npz+sha256 旁车引用；不可达哨兵值显式声明（实测矩阵含 1e9 对），输出路线含哨兵弧 → 五道闸 structure_ok=false
- `inputs_hash` = **规范化 JSON**（sorted keys / UTF-8 / 浮点 repr 截断 1e-9）的 sha256——规范化规则入 schema，否则重放保证无效

---

## 3. Stage 2：数学建模（ProblemSpec → ModelManifest）

**职责**：声明决策空间与约束结构（不求解）。输出是**模型清单**：变量/约束规模、合法域统计、可行性预检。

```json
{
  "schema": "visitflow/model",
  "version": "1.0",
  "problem_hash": "sha256:...",
  "formulation": {"kind": "fixed-row-v2", "link": "y_cd - sum(x_ir) == 0",
                  "vars": {"x_columns": 46, "y": 3749, "z": 326}},
  "legal_domain": {"pairs_total": 3749, "pairs_legal": 1876, "fixed": 1873},
  "feasibility_precheck": {"capacity_ok": true, "contract_ok": true,
                            "corridor_ok": true},
  "meta": {"compile_ms": 830}
}
```

**要点**：
- 建模层纯净：**不含引擎提示**（seeds/预算属 Stage 3 请求参数，v0.1 把 solver_hints 放这里是层次泄漏）。保留本阶段使引擎可替换（CP-SAT/直接 IP 同一 manifest 生效）
- `feasibility_precheck` 三闸不通过直接终止管道，HTTP 422 返回

---

## 4. Stage 3：求解（→ SolutionBundle）

**职责**：调 R2-ALNS（OptiCore 引擎），产出方案 + 五道闸验收 + 溯源元数据。

```json
{
  "schema": "visitflow/solution",
  "version": "1.0",
  "problem_hash": "sha256:...",
  "model_hash": "sha256:...",
  "status": "FEASIBLE",
  "assignment": {"2026-07-01": {"route_idx": [3, 7], "route_codes": ["C001", "..."],
                                 "km": 16.6}, "...": "..."},
  "totals": {"km": 381.66, "vs_original_pct": -3.15, "moved_stores": 7},
  "gates": {"count_ok": true, "capacity_ok": true, "r2_ok": true,
             "contract_ok": true, "structure_ok": true},
  "runtime": {"engine": "r2_alns", "engine_version": "git:abc1234",
               "stage_versions": {"semantic": "visitir@git:...", "model": "visitmodel@git:..."},
               "seeds": [42], "budget_s": 600, "iters": 414153,
               "wall_sec": 602.1},
  "certificates": {"pool_lp": 381.66, "certified_global_lb": null,
                    "global_gap_pct": null},
  "output_hash": "sha256:...",
  "meta": {"deterministic_replay": "seed=42 + inputs_hash + engine_version => 逐位一致重放"}
}
```

**要点**：
- `gates` 五闸任一 false → `status: FAILED` + `violations[]` 明细（契约：不交不合格方案）
- `certificates` 对齐协议 v1 §8.2——`certified_global_lb=null` 表示未证明，不是 0
- 距离口径锁死 OSM 路网；`matrix_ref` 不匹配即拒绝

---

## 5. 目录与实现切分

```
svc/
├── schemas/            # JSON Schema (draft 2020-12) + 生成/校验工具
│   ├── problem.v1.schema.json
│   ├── model.v1.schema.json
│   └── solution.v1.schema.json
├── stages/
│   ├── semantic.py     # 调 VisitIR; xlsx/JSON → ProblemSpec
│   ├── model.py        # 调 VisitModel; ProblemSpec → ModelManifest
│   └── solve.py        # 调 OptiCore(r2_alns); → SolutionBundle
├── run.py              # CLI 编排 (三阶段串行 + 落盘 + hash 链)
└── api.py              # FastAPI: /v1/solve, /v1/stages/{name}, /v1/schemas/{name}
```

- 每阶段 = 纯函数式转换器 + CLI 包装（`python -m svc.stages.semantic -i plan.xlsx -o problem.json`）
- FastAPI 仅是壳，业务零重复
- 测试：golden-file 重放（同输入 JSON 逐位比对）；五闸违反注入测试

---

## 6. 通用性边界（诚实声明）

**通用的部分**：日历 + 合同节拍 + 走廊 + 单仓多日拜访路由这一类问题（快消外勤、巡检、配送拜访均落入）。换业务 = 换 Stage 1 的合同解码规则（唯一业务语义点）。

**不通用的部分**：多仓、时间窗、车辆容量、司机排班——当前 schema 显式不含；`corridor` 与 `contract.kind` 枚举是扩展点，v1 不预留空洞字段（YAGNI，schema 升 v2 时再加）。

---

## 7. 排期

| 步骤 | 内容 | 预估 |
|---|---|---|
| S1 | schemas 三份 + golden 重放框架 | 0.5 天 |
| S2 | Stage 1/2（VisitIR/VisitModel 适配） | 0.5 天 |
| S3 | Stage 3（R2-ALNS 适配 + 五闸） | 0.5 天 |
| S4 | CLI 编排 + 09 线端到端 golden | 0.5 天 |
| S5 | FastAPI 壳 + 冒烟 | 0.5 天 |

---

## 8. v0.2 自审拍板（三轮自审：正确性/工程一致性/产品使用）

1. **certificates 保留 v1**：bp_solo 可选后处理填入；null=未证明
2. **单租户内网，无鉴权**（加租户 = schema v2）
3. **npz + sha256**（跨机传输 + 完整性）
4. v0.1→v0.2 修正清单：合同 f 改派生+required_visits 显式；矩阵按线作用域+哨兵声明；
   solver_hints 移出建模层；同步 API 改异步 job（202）；哈希规范化规则入 schema；
   统一错误包络；输出含 store 编码；各阶段组件版本入 runtime


---

## 附录 A. problem v2.2 抽象说明

### A.1 它描述的对象

这个 JSON 描述的**不是一份日历上的计划，而是一个抽象的周期性服务问题**。它只回答一件事：

> 在一个由 N 个工作日组成的循环窗口里，每位客户需要以什么频率被拜访。

### A.2 形式化定义

一个问题是一个四元组 **P = (N, C, F, W)**：

**N（周期窗口）**——`cycle.n_days`
抽象工作日序列的长度，第 1 天、第 2 天……第 N 天。它没有星期几、没有月份，"一天"只是序号。

**C（客户集）**——`stores[]`
每个客户 c 有身份（id/code）、位置（lon/lat，用于距离计算）。

**F（频次需求）**——`stores[].frequency`，每个客户一条，形如：

> **每 horizon 个工作日，拜访 visits 次**

例：`{horizon: 10, visits: 1}` 读作"每 10 个工作日来 1 次"（俗称双周访）。`{horizon: 5, visits: 2}` 读作"每 5 个工作日来 2 次"（俗称一周两次）。

辅助字段（非语义，仅溯源）：

| 字段 | 含义 |
|---|---|
| `observed_visits` | 历史窗口内的实际拜访次数（参考） |
| `source` | explicit＝业务系统给的合同；derived＝从历史记录反推 |
| `ambiguous` | true＝历史证据不足以唯一确定档位，**不得当作硬约束** |

**W（走廊）**——`corridor`
每个工作日的在访客户数必须落在 [min_daily, max_daily]，防止某天扎堆、某天空转。

### A.3 它诱导的解

一个**方案**是映射 x：把每个客户 c 映射到一个拜访日集合 x(c) ⊆ {1..N}，合法方案须满足：

1. **节奏**：|x(c)| = visits × N / horizon（四舍五入到窗口边界），且任意相邻拜访间隔恰好 horizon（等差铺开）；
2. **单星期几**（R2′）：c 的所有拜访日落在同一周期相位上；
3. **走廊**：每一天的被访客户数 ∈ [min, max]；
4. **总里程**：Σ_天 沿路线的行驶距离，越短越好。

### A.4 `original_assignment_idx` 的身份

它**不是约束，只是一个已知解**（上一版计划在同一个抽象日序列上的取值）。作用有二：作为求解器的初始解/对照基准（`vs_original_pct` 的分母），以及 ambiguous 客户的频次守恒锚。把它当约束读是错误的。

### A.5 刻意排除的东西

真实日历（哪天是周几）、ISO 周、具体月份——全部不在本 JSON 中。日历只在 `calendar_map.json`（投放映射）中出现：`第 k 个工作日 → 某年某月某日`。**问题与日历解耦**意味着：同一个 problem.json 可以投放到任何一个月，产出同构的计划。

### A.6 不变量（可机器校验的承诺）

- `Σ_c |x(c)| == meta.n_visits`（拜访守恒）
- 每店 `|x(c)| == visits × N/horizon`（频次守恒）
- 任意路线不含不可达弧（距离 ≠ 哨兵值）
- 所有比较口径 = 共同精确重排后评估
