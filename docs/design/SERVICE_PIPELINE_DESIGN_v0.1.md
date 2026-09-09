# 三阶段求解服务设计（语义 → 建模 → R2-ALNS）

> **状态**：草稿 v0.1 · 2026-09-08（分支 `feature/service-json-pipeline`，待评审）
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
- **HTTP 服务**：`POST /v1/solve`（multipart 上传计划 → 200 返回三 JSON 打包）；`POST /v1/stages/{semantic|model|solve}` 单阶段调用

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
     "contract": {"kind": "W", "visits_per_week": 3, "phase": 0},
     "legal_dates_idx": [0, 1, 2, "..."]}
  ],
  "corridor": {"min_daily": 23, "max_daily": 35},
  "original_assignment": {"0": [3, 7, "..."], "...": "..."},
  "distance": {"kind": "osm_cycling", "matrix_ref": "sha256:...", "n": 1524},
  "meta": {"line_id": "09", "n_stores": 163, "n_visits": 754}
}
```

**要点**：
- 合同域 `{kind: W|B, phase: 0|1}`——`服务周 = ISO 周 mod 4`，f 派生，零例外（15 行核心逻辑迁入 `svc/semantic.py`，调 VisitIR）
- 距离矩阵不内联（>1MB），以 `matrix_ref` 哈希引用 + 旁车文件 `.npy`
- `inputs_hash` = 规范化输入的 sha256——同 hash 重放必同解

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
  "solver_hints": {"engine": "r2_alns", "combo_mode": "contract",
                    "seeds": [42, 7, 123, 2026], "budget_s": 600},
  "meta": {"compile_ms": 830}
}
```

**要点**：
- 建模层当前对 R2-ALNS 是"轻"的（ALNS 不需要显式约束矩阵）——但保留该阶段使**引擎可替换**（换 CP-SAT/直接 IP 时同一 manifest 生效），这是"相对通用"的关键
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
  "assignment": {"2026-07-01": {"route": [3, 7, "..."], "km": 16.6}, "...": "..."},
  "totals": {"km": 381.66, "vs_original_pct": -3.15, "moved_stores": 7},
  "gates": {"count_ok": true, "capacity_ok": true, "r2_ok": true,
             "contract_ok": true, "structure_ok": true},
  "runtime": {"engine": "r2_alns", "engine_version": "git:abc1234",
               "seeds": [42], "budget_s": 600, "iters": 414153,
               "wall_sec": 602.1},
  "certificates": {"pool_lp": 381.66, "certified_global_lb": null,
                    "global_gap_pct": null},
  "meta": {"deterministic_replay": "seed=42 inputs_hash=sha256:..."}
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

## 8. 评审要点

1. `certificates` 块现在只有 bp 能填——是否 v1 就带上（bp_solo 可选后处理），还是留 v2？
2. HTTP 形态是否需要鉴权/多租户语义？（当前假设单租户内网工具）
3. 距离矩阵旁车文件格式（.npy vs JSON 行序）——服务化后跨机传输建议 npz+hash
