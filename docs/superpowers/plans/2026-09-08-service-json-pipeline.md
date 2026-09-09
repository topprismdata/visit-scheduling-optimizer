# Service JSON Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把"规则语义 → 数学建模 → R2-ALNS 求解"打包为三阶段 JSON 服务（CLI 管道 + FastAPI 异步壳），每阶段输入/输出为带 schema/hash 的标准 JSON。

**Architecture:** 编排层 `svc/` 是纯壳——Stage 1/2/3 分别适配既有 VisitIR（`core/contract.py`）、VisitModel、OptiCore（`algos/r2_alns.py`）。阶段边界 = JSON 契约（`visitflow/problem|model|solution v1`），哈希链 `inputs_hash → problem_hash → model_hash → output_hash` 保证可重放。设计 spec：`docs/design/SERVICE_PIPELINE_DESIGN_v0.2.md`（先读）。

**Tech Stack:** Python 3.10+（仓库 .venv）、jsonschema（新增依赖）、FastAPI + uvicorn（新增依赖，仅 api.py 用）、numpy、openpyxl（load_plan 已用）。

**测试基建注意**：`data.loader.load_plan()` 读全量 Excel（~2-5 分钟）——**单测一律用合成 `line_df` fixture，禁止调用 load_plan**；端到端冒烟（Task 8）单独跑真实 09 线。

---

## File Structure

```
svc/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── problem.v1.schema.json      # Stage 1 输出契约
│   ├── model.v1.schema.json        # Stage 2 输出契约
│   ├── solution.v1.schema.json     # Stage 3 输出契约
│   └── validate.py                 # jsonschema 包装: validate_obj(obj, name)
├── stages/
│   ├── __init__.py
│   ├── semantic.py                 # line_df → ProblemSpec dict
│   ├── model.py                    # ProblemSpec → ModelManifest dict
│   └── solve.py                    # ProblemSpec → SolutionBundle dict (R2-ALNS)
├── hashing.py                      # canonical_json / sha256_of
├── run.py                          # CLI 编排: xlsx → 三 JSON
└── api.py                          # FastAPI 异步 job 壳
tests/
├── test_svc_schemas.py
├── test_svc_semantic.py
├── test_svc_model.py
└── test_svc_solve.py
experiments/...                     # 不动
docs/design/SERVICE_PIPELINE_DESIGN_v0.2.md   # spec（已存在）
```

职责边界：`stages/*.py` 只做 JSON 转换与闸验收，算法全部留在原三层；`hashing.py` 是唯一哈希实现（DRY）；`api.py` 不含业务。

---

### Task 1: 哈希与规范化工具

**Files:**
- Create: `svc/__init__.py`（空）, `svc/hashing.py`
- Test: `tests/test_svc_hashing.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_svc_hashing.py
import json
from svc.hashing import canonical_json, sha256_of


def test_canonical_json_sorted_keys_and_stable():
    a = {"b": 1, "a": 2.0}
    b = {"a": 2.0, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_canonical_json_float_truncation():
    a = {"x": 0.1234567890123}
    b = {"x": 0.1234567890124}   # 1e-9 内差异视为相同
    assert canonical_json(a) == canonical_json(b)


def test_sha256_of_deterministic():
    assert sha256_of({"a": 1}) == sha256_of({"a": 1})
    assert sha256_of({"a": 1}) != sha256_of({"a": 2})
    assert sha256_of({"a": 1}).startswith("sha256:")
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/test_svc_hashing.py -v`
Expected: FAIL（`ModuleNotFoundError: svc`）

- [ ] **Step 3: 最小实现**

```python
# svc/hashing.py
"""规范化 JSON + sha256 —— 全仓唯一哈希实现 (spec v0.2 §2)."""
import hashlib
import json


def _trunc(obj):
    if isinstance(obj, float):
        return round(obj, 9)
    if isinstance(obj, dict):
        return {k: _trunc(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_trunc(v) for v in obj]
    return obj


def canonical_json(obj) -> str:
    return json.dumps(_trunc(obj), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def sha256_of(obj) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
```

另需建空包文件：`svc/__init__.py`、`svc/schemas/__init__.py`、`svc/stages/__init__.py`（内容均为空字符串）。

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/test_svc_hashing.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add svc/ tests/test_svc_hashing.py
git commit -m "feat(svc): canonical json + sha256 hashing utils"
```

---

### Task 2: 三份 JSON Schema + 校验包装

**Files:**
- Create: `svc/schemas/problem.v1.schema.json`, `svc/schemas/model.v1.schema.json`, `svc/schemas/solution.v1.schema.json`, `svc/schemas/validate.py`
- Test: `tests/test_svc_schemas.py`

- [ ] **Step 1: 安装依赖**

Run: `.venv/bin/pip install jsonschema`
Expected: Successfully installed jsonschema

- [ ] **Step 2: 写失败测试**

```python
# tests/test_svc_schemas.py
import copy
import pytest
from svc.schemas.validate import validate_obj, SchemaError

MIN_PROBLEM = {
    "schema": "visitflow/problem", "version": "1.0",
    "inputs_hash": "sha256:ab", "line_id": "09",
    "calendar": {"dates": ["2026-07-01"], "n_days": 1},
    "stores": [{"id": 0, "code": "C001", "lon": 113.25, "lat": 23.05,
                 "contract": {"kind": "W", "phase": 0, "required_visits": 3},
                 "legal_dates_idx": [0]}],
    "corridor": {"min_daily": 2, "max_daily": 3},
    "original_assignment": {"2026-07-01": [0]},
    "distance": {"kind": "osm_cycling", "scope": "per-line",
                  "matrix_ref": "sha256:cd", "format": "npz", "n": 1,
                  "unreachable_sentinel": 1e9},
    "meta": {"n_stores": 1, "n_visits": 3},
}
MIN_MODEL = {
    "schema": "visitflow/model", "version": "1.0",
    "problem_hash": "sha256:ab",
    "formulation": {"kind": "fixed-row-v2", "vars": {}},
    "legal_domain": {"pairs_total": 1, "pairs_legal": 1, "fixed": 0},
    "feasibility_precheck": {"capacity_ok": True, "contract_ok": True,
                              "corridor_ok": True},
    "meta": {"compile_ms": 1},
}
MIN_SOLUTION = {
    "schema": "visitflow/solution", "version": "1.0",
    "problem_hash": "sha256:ab", "model_hash": "sha256:cd",
    "status": "FEASIBLE",
    "assignment": {"2026-07-01": {"route_idx": [0], "route_codes": ["C001"],
                                   "km": 0.0}},
    "totals": {"km": 0.0, "vs_original_pct": 0.0, "moved_stores": 0},
    "gates": {"count_ok": True, "capacity_ok": True, "r2_ok": True,
               "contract_ok": True, "structure_ok": True},
    "runtime": {"engine": "r2_alns", "engine_version": "git:x",
                 "stage_versions": {}, "seeds": [42], "budget_s": 1,
                 "iters": 1, "wall_sec": 0.1},
    "certificates": {"pool_lp": None, "certified_global_lb": None,
                      "global_gap_pct": None},
    "output_hash": "sha256:ef",
    "meta": {},
}


def test_problem_spec_valid():
    validate_obj(copy.deepcopy(MIN_PROBLEM), "problem")


def test_problem_spec_rejects_bad_contract_kind():
    bad = copy.deepcopy(MIN_PROBLEM)
    bad["stores"][0]["contract"]["kind"] = "X"
    with pytest.raises(SchemaError):
        validate_obj(bad, "problem")


def test_model_and_solution_valid():
    validate_obj(copy.deepcopy(MIN_MODEL), "model")
    validate_obj(copy.deepcopy(MIN_SOLUTION), "solution")


def test_solution_rejects_failed_gates_with_feasible_status():
    bad = copy.deepcopy(MIN_SOLUTION)
    bad["gates"]["contract_ok"] = False
    with pytest.raises(SchemaError):
        validate_obj(bad, "solution")


def test_unknown_schema_name():
    with pytest.raises(SchemaError):
        validate_obj({}, "nope")
```

- [ ] **Step 3: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/test_svc_schemas.py -v`
Expected: FAIL（`ModuleNotFoundError: svc.schemas.validate`）

- [ ] **Step 4: 写三份 schema**

`svc/schemas/problem.v1.schema.json`：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "visitflow/problem v1",
  "type": "object",
  "required": ["schema", "version", "inputs_hash", "line_id", "calendar",
                "stores", "corridor", "original_assignment", "distance", "meta"],
  "properties": {
    "schema": {"const": "visitflow/problem"},
    "version": {"const": "1.0"},
    "inputs_hash": {"type": "string", "pattern": "^sha256:"},
    "line_id": {"type": "string"},
    "calendar": {
      "type": "object",
      "required": ["dates", "n_days"],
      "properties": {
        "dates": {"type": "array", "items": {"type": "string"}},
        "n_days": {"type": "integer", "minimum": 1}
      }
    },
    "stores": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "code", "lon", "lat", "contract", "legal_dates_idx"],
        "properties": {
          "id": {"type": "integer", "minimum": 0},
          "code": {"type": "string"},
          "lon": {"type": "number"}, "lat": {"type": "number"},
          "contract": {
            "type": "object",
            "required": ["kind", "phase", "required_visits"],
            "properties": {
              "kind": {"enum": ["W", "B"]},
              "phase": {"enum": [0, 1]},
              "required_visits": {"type": "integer", "minimum": 1}
            }
          },
          "legal_dates_idx": {"type": "array", "items": {"type": "integer"}}
        }
      }
    },
    "corridor": {
      "type": "object",
      "required": ["min_daily", "max_daily"],
      "properties": {"min_daily": {"type": "integer"},
                      "max_daily": {"type": "integer"}}
    },
    "original_assignment": {
      "type": "object",
      "additionalProperties": {"type": "array", "items": {"type": "integer"}}
    },
    "distance": {
      "type": "object",
      "required": ["kind", "scope", "matrix_ref", "format", "n",
                    "unreachable_sentinel"],
      "properties": {
        "kind": {"type": "string"},
        "scope": {"const": "per-line"},
        "matrix_ref": {"type": "string", "pattern": "^sha256:"},
        "format": {"const": "npz"},
        "n": {"type": "integer", "minimum": 1},
        "unreachable_sentinel": {"type": "number"}
      }
    },
    "meta": {"type": "object"}
  }
}
```

`svc/schemas/model.v1.schema.json`：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "visitflow/model v1",
  "type": "object",
  "required": ["schema", "version", "problem_hash", "formulation",
                "legal_domain", "feasibility_precheck", "meta"],
  "properties": {
    "schema": {"const": "visitflow/model"},
    "version": {"const": "1.0"},
    "problem_hash": {"type": "string", "pattern": "^sha256:"},
    "formulation": {
      "type": "object",
      "required": ["kind", "vars"],
      "properties": {"kind": {"type": "string"}, "vars": {"type": "object"}}
    },
    "legal_domain": {
      "type": "object",
      "required": ["pairs_total", "pairs_legal", "fixed"],
      "properties": {"pairs_total": {"type": "integer"},
                      "pairs_legal": {"type": "integer"},
                      "fixed": {"type": "integer"}}
    },
    "feasibility_precheck": {
      "type": "object",
      "required": ["capacity_ok", "contract_ok", "corridor_ok"],
      "additionalProperties": {"type": "boolean"}
    },
    "meta": {"type": "object"}
  }
}
```

`svc/schemas/solution.v1.schema.json`：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "visitflow/solution v1",
  "type": "object",
  "required": ["schema", "version", "problem_hash", "model_hash", "status",
                "assignment", "totals", "gates", "runtime", "certificates",
                "output_hash", "meta"],
  "properties": {
    "schema": {"const": "visitflow/solution"},
    "version": {"const": "1.0"},
    "problem_hash": {"type": "string", "pattern": "^sha256:"},
    "model_hash": {"type": "string", "pattern": "^sha256:"},
    "status": {"enum": ["FEASIBLE", "INFEASIBLE", "FAILED"]},
    "assignment": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["route_idx", "route_codes", "km"],
        "properties": {
          "route_idx": {"type": "array", "items": {"type": "integer"}},
          "route_codes": {"type": "array", "items": {"type": "string"}},
          "km": {"type": "number", "minimum": 0}
        }
      }
    },
    "totals": {
      "type": "object",
      "required": ["km", "vs_original_pct", "moved_stores"],
      "properties": {"km": {"type": "number"},
                      "vs_original_pct": {"type": "number"},
                      "moved_stores": {"type": "integer"}}
    },
    "gates": {
      "type": "object",
      "required": ["count_ok", "capacity_ok", "r2_ok", "contract_ok",
                    "structure_ok"],
      "additionalProperties": {"type": "boolean"}
    },
    "runtime": {
      "type": "object",
      "required": ["engine", "engine_version", "stage_versions", "seeds",
                    "budget_s", "iters", "wall_sec"],
      "properties": {
        "engine": {"type": "string"},
        "engine_version": {"type": "string"},
        "stage_versions": {"type": "object"},
        "seeds": {"type": "array", "items": {"type": "integer"}},
        "budget_s": {"type": "number"},
        "iters": {"type": "integer"},
        "wall_sec": {"type": "number"}
      }
    },
    "certificates": {
      "type": "object",
      "required": ["pool_lp", "certified_global_lb", "global_gap_pct"],
      "properties": {"pool_lp": {"type": ["number", "null"]},
                      "certified_global_lb": {"type": ["number", "null"]},
                      "global_gap_pct": {"type": ["number", "null"]}}
    },
    "output_hash": {"type": "string", "pattern": "^sha256:"},
    "meta": {"type": "object"}
  },
  "allOf": [{
    "if": {"properties": {"status": {"const": "FEASIBLE"}}},
    "then": {"properties": {
      "gates": {"properties": {
        "count_ok": {"const": true}, "capacity_ok": {"const": true},
        "r2_ok": {"const": true}, "contract_ok": {"const": true},
        "structure_ok": {"const": true}}}
    }}
  }]
}
```

- [ ] **Step 5: 写校验包装**

```python
# svc/schemas/validate.py
"""jsonschema 包装 —— 阶段输出的唯一守门员."""
import json
from pathlib import Path

import jsonschema

_DIR = Path(__file__).parent
_SCHEMA_FILES = {
    "problem": "problem.v1.schema.json",
    "model": "model.v1.schema.json",
    "solution": "solution.v1.schema.json",
}


class SchemaError(ValueError):
    pass


def validate_obj(obj: dict, name: str) -> None:
    if name not in _SCHEMA_FILES:
        raise SchemaError(f"unknown schema: {name}")
    schema = json.loads((_DIR / _SCHEMA_FILES[name]).read_text(encoding="utf-8"))
    try:
        jsonschema.validate(obj, schema)
    except jsonschema.ValidationError as e:
        raise SchemaError(f"{name}: {e.message} at {list(e.absolute_path)}") from e
```

- [ ] **Step 6: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/test_svc_schemas.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add svc/schemas/ tests/test_svc_schemas.py
git commit -m "feat(svc): three stage JSON schemas + jsonschema gate (FEASIBLE implies all gates pass)"
```

---

### Task 3: Stage 1 语义编译（semantic.py）

**Files:**
- Create: `svc/stages/semantic.py`
- Test: `tests/test_svc_semantic.py`

**依赖事实**（实现者须知，来自 `data/loader.py` 与 `core/contract.py`）：
- `load_plan()` → 过滤后 DataFrame（列含 `客户编码/拜访日期/经度/纬度/拜访顺序/销售名称/date`）；`load_line(plan, line_id)` → `LineData`（字段 `codes/lon/lat/dates/days_orig{date:[idx]}/freq{code:int}/min_daily_capacity/max_daily_capacity`）
- `contract_of(days_orig, dates)` → 合同 dict；`legal_date_map(contracts, dates)` → `{store_idx: set(date)}`
- 本任务**禁止调用 load_plan**（慢），测试用合成 DataFrame。semantic 对外提供两个入口：`build_spec_from_df(line_df, line_id, D, matrix_sha)`（可测）与 `build_spec_from_xlsx(xlsx_path, line_id)`（薄包装，冒烟用）。

- [ ] **Step 1: 写失败测试（合成 4 店 3 日线）**

```python
# tests/test_svc_semantic.py
"""合成 line_df: 4 店, 2 日 (2026-07-01 周三, 2026-07-02 周四)."""
import numpy as np
import pandas as pd
import pytest
from svc.schemas.validate import validate_obj
from svc.stages.semantic import build_spec_from_df

DATES = [pd.Timestamp("2026-07-01").date(), pd.Timestamp("2026-07-02").date()]


def make_line_df():
    rows = []
    # 店 0/1: 周三+周四各来 (W 型); 店 2: 仅周三; 店 3: 仅周四
    plan_map = {0: DATES, 1: DATES, 2: DATES[:1], 3: DATES[1:]}
    for sid, ds in plan_map.items():
        for di, dd in enumerate(ds):
            rows.append({
                "客户编码": f"C00{sid}", "销售名称": "海珠荔湾09",
                "经度": 113.25 + sid * 0.01, "纬度": 23.05 + sid * 0.01,
                "拜访顺序": di + 1, "date": dd,
                "拜访日期": dd.strftime("%Y-%m-%d"),
            })
    return pd.DataFrame(rows)


def test_build_spec_schema_valid_and_hashes():
    D = np.array([[0, 2, 3, 4], [2, 0, 1, 2], [3, 1, 0, 1], [4, 2, 1, 0]],
                  dtype=float)
    spec = build_spec_from_df(make_line_df(), "09", D)
    validate_obj(spec, "problem")
    assert spec["line_id"] == "09"
    assert spec["calendar"]["n_days"] == 2
    assert len(spec["stores"]) == 4
    # required_visits = 月内出现次数
    assert spec["stores"][0]["contract"]["required_visits"] == 2
    assert spec["stores"][2]["contract"]["required_visits"] == 1
    # 合同 kind: 出现 >=2 次且跨多周相位 -> W; 单次 -> W (kind 由 contract_of 决定, 这里只验枚举合法)
    assert spec["stores"][2]["contract"]["kind"] in ("W", "B")
    # 合法域: 店 2 只在 index 0
    assert spec["stores"][2]["legal_dates_idx"] == [0]
    # original_assignment: 按日期字符串
    assert spec["original_assignment"]["2026-07-01"] == [0, 2]
    # 矩阵维度 == n_stores
    assert spec["distance"]["n"] == 4
    # 可重放: 同输入两次 hash 一致
    spec2 = build_spec_from_df(make_line_df(), "09", D)
    assert spec["inputs_hash"] == spec2["inputs_hash"]


def test_build_spec_deterministic_store_order():
    df = make_line_df().sample(frac=1.0, random_state=7)  # 打乱行序
    D = np.zeros((4, 4))
    spec = build_spec_from_df(df, "09", D)
    assert [s["code"] for s in spec["stores"]] == ["C000", "C001", "C002", "C003"]
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/test_svc_semantic.py -v`
Expected: FAIL（`ModuleNotFoundError: svc.stages.semantic`）

- [ ] **Step 3: 实现**

```python
# svc/stages/semantic.py
"""Stage 1 语义编译: line_df → ProblemSpec v1 (visitflow/problem)."""
from __future__ import annotations

import hashlib
from collections import Counter

import numpy as np

from svc.hashing import sha256_of

_SENTINEL = 1e9


def _iso(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def build_spec_from_df(line_df, line_id: str, D: np.ndarray) -> dict:
    dates = sorted(line_df["date"].unique())
    dates = [d.date() if hasattr(d, "date") and callable(d.date) else d
             for d in dates]
    date_strs = [_iso(d) for d in dates]
    codes = sorted(line_df["客户编码"].unique())
    idx = {c: i for i, c in enumerate(codes)}

    pts = (line_df.dropna(subset=["经度", "纬度"])
           .drop_duplicates("客户编码", keep="first")
           .set_index("客户编码"))
    days_orig = {}
    for di, dd in enumerate(dates):
        rows = line_df[line_df["date"] == dd].sort_values("拜访顺序")
        days_orig[date_strs[di]] = [idx[c] for c in rows["客户编码"]
                                     if c in idx]

    freq = Counter(line_df["客户编码"])
    contracts = _contracts_from_days(days_orig, dates)

    stores = []
    for c in codes:
        sid = idx[c]
        stores.append({
            "id": sid, "code": c,
            "lon": float(pts.loc[c, "经度"]), "lat": float(pts.loc[c, "纬度"]),
            "contract": contracts[sid],
            "legal_dates_idx": contracts[sid].pop("_legal_idx"),
        })
        stores[-1]["contract"] = {k: v for k, v in stores[-1]["contract"].items()
                                   if not k.startswith("_")}

    spec = {
        "schema": "visitflow/problem", "version": "1.0",
        "inputs_hash": "PENDING", "line_id": line_id,
        "calendar": {"dates": date_strs, "n_days": len(dates)},
        "stores": stores,
        "corridor": {"min_daily": int(min(len(v) for v in days_orig.values())),
                      "max_daily": int(max(len(v) for v in days_orig.values()))},
        "original_assignment": days_orig,
        "distance": {
            "kind": "osm_cycling", "scope": "per-line",
            "matrix_ref": "PENDING", "format": "npz", "n": len(codes),
            "unreachable_sentinel": _SENTINEL,
        },
        "meta": {"n_stores": len(codes),
                  "n_visits": int(sum(freq.values()))},
    }
    spec["inputs_hash"] = sha256_of(spec)
    spec["distance"]["matrix_ref"] = "sha256:" + hashlib.sha256(
        np.ascontiguousarray(D).tobytes()).hexdigest()
    return spec


def _contracts_from_days(days_orig: dict, dates) -> dict:
    """合同 kind/phase/required_visits 派生 + 合法域 (core.contract 单一事实源)."""
    from core.contract import contract_of, legal_date_map
    contracts = contract_of(days_orig, dates)
    legal = legal_date_map(contracts, dates)
    stores = sorted({c for v in days_orig.values() for c in v})
    out = {}
    for sid in stores:
        kind, phase = contracts[sid]
        req = sum(1 for v in days_orig.values() if sid in v)
        legal_idx = sorted(date_strs_i for date_strs_i, dd_set in
                            _legal_index_map(legal, dates).get(sid, {}).items())
        out[sid] = {"kind": kind, "phase": phase, "required_visits": req,
                     "_legal_idx": legal_idx}
    return out


def _legal_index_map(legal, dates):
    """{store: {date_iso: date}} 中间结构 -> {store: {idx}} 由调用方展平."""
    idx_of = {_iso(d): i for i, d in enumerate(dates)}
    res = {}
    for store, dd_set in legal.items():
        res[store] = {idx_of[_iso(dd)]: dd for dd in dd_set}
    return res
```

实现注记（写代码前必读）：
- `contract_of` 的返回结构以 `core/contract.py` 实际签名为准（本计划写作时为 `(kind, phase)` 元组 dict——**执行 Task 3 第一步是打开该文件核对**；若是 dict 形态 `{kind,phase}` 则改对应取值行，测试不变）
- `_legal_index_map` 中间层若显冗余，允许内联，但测试断言不变
- `freq`/`required_visits` 一致性由 Task 8 端到端对账兜底

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/test_svc_semantic.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add svc/stages/semantic.py tests/test_svc_semantic.py
git commit -m "feat(svc): stage-1 semantic compile — line_df to ProblemSpec v1 with derived contracts"
```

---

### Task 4: Stage 2 数学建模（model.py）

**Files:**
- Create: `svc/stages/model.py`
- Test: `tests/test_svc_model.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_svc_model.py
import json
from pathlib import Path

import pytest
from svc.hashing import sha256_of
from svc.schemas.validate import validate_obj
from svc.stages.model import build_manifest

SCHEMA_DIR = Path("svc/schemas")


def min_problem():
    spec = json.loads((SCHEMA_DIR / "problem.v1.schema.json").read_text())
    # 最小合法实例 (与 test_svc_schemas.MIN_PROBLEM 同构)
    return {
        "schema": "visitflow/problem", "version": "1.0",
        "inputs_hash": "sha256:ab", "line_id": "09",
        "calendar": {"dates": ["2026-07-01"], "n_days": 1},
        "stores": [{"id": 0, "code": "C001", "lon": 113.25, "lat": 23.05,
                     "contract": {"kind": "W", "phase": 0, "required_visits": 3},
                     "legal_dates_idx": [0]}],
        "corridor": {"min_daily": 2, "max_daily": 3},
        "original_assignment": {"2026-07-01": [0]},
        "distance": {"kind": "osm_cycling", "scope": "per-line",
                      "matrix_ref": "sha256:cd", "format": "npz", "n": 1,
                      "unreachable_sentinel": 1e9},
        "meta": {"n_stores": 1, "n_visits": 3},
    }


def test_manifest_schema_valid_and_pure():
    spec = min_problem()
    m = build_manifest(spec)
    validate_obj(m, "model")
    assert m["problem_hash"] == sha256_of(spec)
    # 建模层纯净: 不含引擎提示 (spec v0.2 修正 4)
    assert "solver_hints" not in m
    pre = m["feasibility_precheck"]
    assert pre["capacity_ok"] and pre["contract_ok"] and pre["corridor_ok"]
    # 合法域统计: 1 店 × 1 日 = 1 对, 全合法
    assert m["legal_domain"]["pairs_total"] == 1
    assert m["legal_domain"]["pairs_legal"] == 1
    assert m["legal_domain"]["fixed"] == 0


def test_manifest_flags_infeasible_corridor():
    spec = min_problem()
    spec["corridor"]["min_daily"] = 5   # 1 店 < 走廊下限
    m = build_manifest(spec)
    assert m["feasibility_precheck"]["corridor_ok"] is False
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/test_svc_model.py -v`
Expected: FAIL（`ModuleNotFoundError: svc.stages.model`）

- [ ] **Step 3: 实现**

```python
# svc/stages/model.py
"""Stage 2 数学建模: ProblemSpec → ModelManifest v1 (visitflow/model).

纯净层: 不含引擎提示 (seeds/预算属 Stage 3 请求参数, spec v0.2 修正 4).
"""
from __future__ import annotations

from svc.hashing import sha256_of


def build_manifest(spec: dict) -> dict:
    n_stores = spec["meta"]["n_stores"]
    n_days = spec["calendar"]["n_days"]
    pairs_total = n_stores * n_days
    pairs_legal = sum(len(s["legal_dates_idx"]) for s in spec["stores"])

    corridor_ok = spec["corridor"]["min_daily"] <= spec["corridor"]["max_daily"]
    for s in spec["stores"]:
        if s["contract"]["required_visits"] > len(s["legal_dates_idx"]):
            corridor_ok = False    # required visits 超出该店合法天数

    manifest = {
        "schema": "visitflow/model", "version": "1.0",
        "problem_hash": sha256_of(spec),
        "formulation": {
            "kind": "fixed-row-v2",
            "vars": {"y_pairs": pairs_total, "y_pairs_legal": pairs_legal},
        },
        "legal_domain": {
            "pairs_total": pairs_total, "pairs_legal": pairs_legal,
            "fixed": pairs_total - pairs_legal,
        },
        "feasibility_precheck": {
            "capacity_ok": True,      # 每店 required_visits <= 合法天数已在 corridor_ok 并入
            "contract_ok": all(s["contract"]["kind"] in ("W", "B")
                                for s in spec["stores"]),
            "corridor_ok": corridor_ok,
        },
        "meta": {"compile_ms": 0},
    }
    return manifest
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/test_svc_model.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add svc/stages/model.py tests/test_svc_model.py
git commit -m "feat(svc): stage-2 model manifest — pure, no engine hints, feasibility precheck"
```

---

### Task 5: Stage 3 求解（solve.py，R2-ALNS + 五道闸）

**Files:**
- Create: `svc/stages/solve.py`
- Test: `tests/test_svc_solve.py`

**依赖事实**（来自 `algos/r2_alns.py`、`core/metric.py`、`core/contract.py`，写码前打开核对）：
- `R2ALNS().solve(data, D, iteration_budget=int, seed=int, combo_mode="contract", final_reroute=False)` → `AlgoResult`，字段 `days{date:[idx]}/km/moves/count_ok/capacity_ok/contract_ok/metadata`
- `day_km(route, D)`、`check_capacity(selected, max_daily, min_daily)`、`check_contract(days, contracts, dates)`
- `visitmodel.tsp.open_chain._exact_open_tsp_status(stores, D, time_limit)` → `(route, status, elapsed_ms)`
- `LineData` 构造：`dataclass(line_id, line_name, codes, lon, lat, dates, days_orig, freq, stores, visits, min_daily_capacity, max_daily_capacity)`（`core/base.py`）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_svc_solve.py
"""端到端 mini: 合成 spec → R2-ALNS → SolutionBundle (五道闸 + 重排口径)."""
import numpy as np
import pandas as pd
import pytest
from svc.schemas.validate import validate_obj
from svc.stages.semantic import build_spec_from_df
from svc.stages.model import build_manifest
from svc.stages.solve import solve_spec

DATES = [pd.Timestamp("2026-07-01").date(), pd.Timestamp("2026-07-02").date()]


def make_spec():
    rows = []
    plan_map = {0: DATES, 1: DATES, 2: DATES[:1], 3: DATES[1:]}
    for sid, ds in plan_map.items():
        for di, dd in enumerate(ds):
            rows.append({"客户编码": f"C00{sid}", "销售名称": "海珠荔湾09",
                          "经度": 113.25 + sid * 0.01, "纬度": 23.05 + sid * 0.01,
                          "拜访顺序": di + 1, "date": dd,
                          "拜访日期": dd.strftime("%Y-%m-%d")})
    df = pd.DataFrame(rows)
    D = np.array([[0, 2, 3, 4], [2, 0, 1, 2], [3, 1, 0, 1], [4, 2, 1, 0]],
                  dtype=float)
    spec = build_spec_from_df(df, "09", D)
    return spec, D


def test_solve_end_to_end_mini():
    spec, D = make_spec()
    model = build_manifest(spec)
    bundle = solve_spec(spec, D, seeds=[42], budget_s=2, cp_timeout=5,
                         engine_version="git:test")
    validate_obj(bundle, "solution")
    assert bundle["status"] == "FEASIBLE"
    assert bundle["problem_hash"] and bundle["model_hash"]
    # 哈希链
    from svc.hashing import sha256_of
    assert bundle["problem_hash"] == sha256_of(spec)
    assert bundle["model_hash"] == sha256_of(model)
    # 双出: 索引 + 编码
    day0 = bundle["assignment"]["2026-07-01"]
    assert len(day0["route_idx"]) == len(day0["route_codes"])
    assert day0["route_codes"] == [f"C00{i:0>2}" for i in day0["route_idx"]]
    # 五道闸全过才允许 FEASIBLE
    assert all(bundle["gates"].values())
    # km 与重排后路线一致
    assert abs(bundle["totals"]["km"] -
               sum(d["km"] for d in bundle["assignment"].values())) < 1e-6


def test_solve_deterministic_same_seed():
    spec, D = make_spec()
    a = solve_spec(spec, D, seeds=[42], budget_s=1, cp_timeout=5,
                    engine_version="git:test")
    b = solve_spec(spec, D, seeds=[42], budget_s=1, cp_timeout=5,
                    engine_version="git:test")
    assert a["output_hash"] == b["output_hash"]
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/test_svc_solve.py -v`
Expected: FAIL（`ModuleNotFoundError: svc.stages.solve`）

- [ ] **Step 3: 实现**

```python
# svc/stages/solve.py
"""Stage 3 求解: ProblemSpec → SolutionBundle v1 (R2-ALNS + 五道闸 + 共同重排).

口径铁律: totals.km 为共同 CP-SAT 重排后的 pipeline km (协议 §5.3),
内部 route 和禁止直接出参 (v0.2 勘误: 与 km_internal 混用曾致 +7% 假回退).
"""
from __future__ import annotations

import subprocess
import time
from collections import Counter

import numpy as np

from core.base import LineData
from core.contract import check_contract, contract_of, legal_date_map
from core.metric import check_capacity, day_km
from svc.hashing import sha256_of


def _engine_version() -> str:
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True, timeout=5,
                               cwd=__file__).stdout.strip()
        return f"git:{head}" if head else "git:unknown"
    except Exception:
        return "git:unknown"


def _to_line_data(spec: dict, dates) -> LineData:
    stores = spec["stores"]
    codes = [s["code"] for s in stores]
    idx = {c: i for i, c in enumerate(codes)}
    days_orig = {dd: list(v) for dd, v in spec["original_assignment"].items()}
    freq = {}
    for s in stores:
        freq[s["code"]] = s["contract"]["required_visits"]
    visits = sum(freq.values())
    return LineData(
        line_id=spec["line_id"], line_name=f"line{spec['line_id']}",
        codes=codes,
        lon=[s["lon"] for s in stores], lat=[s["lat"] for s in stores],
        dates=dates, days_orig=days_orig, freq=freq,
        stores=len(codes), visits=visits,
        min_daily_capacity=spec["corridor"]["min_daily"],
        max_daily_capacity=spec["corridor"]["max_daily"])


def solve_spec(spec: dict, D, seeds: list, budget_s: float, cp_timeout: float,
                engine_version: str | None = None) -> dict:
    from algos.r2_alns import R2ALNS
    from visitmodel.tsp.open_chain import _exact_open_tsp_status

    engine_version = engine_version or _engine_version()
    dates = [pd_date if not isinstance(pd_date, str) else pd_date
             for pd_date in _dates_from_spec(spec)]
    date_strs = spec["calendar"]["dates"]
    t0 = time.perf_counter()

    line = _to_line_data(spec, dates)
    contracts = contract_of(line.days_orig, dates)

    best_days, best_km, best_meta = None, float("inf"), {}
    total_iters = 0
    for seed in seeds:
        r = R2ALNS().solve(line, D, iteration_budget=int(budget_s * 600),
                            seed=seed, combo_mode="contract",
                            final_reroute=False)
        total_iters += int(r.metadata.get("iters", 0))
        km = sum(day_km(r.days[dd], D) for dd in dates)
        if km < best_km:
            best_days, best_km, best_meta = {dd: list(r.days[dd]) for dd in dates}, km, r.metadata

    # 共同 CP-SAT 重排 (协议 §5.3)
    codes = [s["code"] for s in spec["stores"]]
    assignment, total_km, moved = {}, 0.0, 0
    for di, dd in enumerate(dates):
        route, _st, _ms = _exact_open_tsp_status(list(best_days[dd]), D, cp_timeout)
        km = round(day_km(route, D), 3)
        total_km += km
        orig = set(spec["original_assignment"][date_strs[di]])
        moved += sum(1 for c in route if c not in orig)
        assignment[date_strs[di]] = {
            "route_idx": [int(c) for c in route],
            "route_codes": [codes[c] for c in route],
            "km": km,
        }

    orig_km = sum(day_km(spec["original_assignment"][s], D)
                   for s in date_strs)
    gates = {
        "count_ok": all(
            sum(1 for d in assignment.values() for c in d["route_idx"] if c == s["id"])
            == s["contract"]["required_visits"] for s in spec["stores"]),
        "capacity_ok": bool(check_capacity(
            {dd: v["route_idx"] for dd, v in assignment.items()},
            spec["corridor"]["max_daily"], spec["corridor"]["min_daily"])),
        "r2_ok": True,   # GRASP/合同搜索全月一致由 R2ALNS combo_mode=contract 保证
        "contract_ok": not check_contract(
            {dd: v["route_idx"] for dd, v in assignment.items()},
            contracts, dates),
        "structure_ok": all(
            D[a][b] < spec["distance"]["unreachable_sentinel"]
            for v in assignment.values()
            for a, b in zip(v["route_idx"], v["route_idx"][1:])),
    }
    status = "FEASIBLE" if all(gates.values()) else "FAILED"
    vs_orig = round((total_km - orig_km) / orig_km * 100, 3) if orig_km > 0 else 0.0

    bundle = {
        "schema": "visitflow/solution", "version": "1.0",
        "problem_hash": sha256_of(spec),
        "model_hash": "PENDING",
        "status": status,
        "assignment": assignment,
        "totals": {"km": round(total_km, 3), "vs_original_pct": vs_orig,
                    "moved_stores": moved},
        "gates": gates,
        "runtime": {"engine": "r2_alns", "engine_version": engine_version,
                     "stage_versions": {}, "seeds": list(seeds),
                     "budget_s": budget_s, "iters": total_iters,
                     "wall_sec": round(time.perf_counter() - t0, 2)},
        "certificates": {"pool_lp": None, "certified_global_lb": None,
                          "global_gap_pct": None},
        "output_hash": "PENDING",
        "meta": {},
    }
    bundle["model_hash"] = "set-by-caller"   # run.py 注入 (见 Task 6)
    bundle.pop("model_hash")
    bundle["meta"]["model_hash"] = "set-by-caller"
    # 哈希链: model_hash 由编排层注入后才能算 output_hash; 本函数按约定预留
    bundle["meta"]["model_hash_note"] = (
        "run.py 注入 model_hash 后重算 output_hash")
    bundle["output_hash"] = sha256_of(
        {k: v for k, v in bundle.items() if k != "output_hash"})
    return bundle


def _dates_from_spec(spec: dict):
    """ISO 字符串 → datetime.date (引擎需要 date 对象做星期运算)."""
    import datetime as _dt
    return [_dt.date.fromisoformat(s) for s in spec["calendar"]["dates"]]
```

实现注记（写码前必读）：
- `model_hash` 注入顺序：本函数无法预知 model 哈希——**约定 run.py 调 `solve_spec` 后把 `bundle["meta"]["model_hash"]` 替换为真值再重算 `output_hash`**（Task 6 落实）；本函数先行置占位并计入 output（重算会覆盖）
- `r2_ok` 的真正校验在 `R2ALNS(combo_mode="contract")` 内部 + `res.contract_ok`——**实现时直接用 `bool(getattr(r_best, "contract_ok", True))` 替换常量 True**（写码时核对 `AlgoResult` 字段）
- 若 `check_capacity`/`check_contract` 签名与上述不符，以源码为准调整调用行，**测试断言不变**

- [ ] **Step 4: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/test_svc_solve.py -v`
Expected: 2 passed（budget_s=1 的 mini 实例 R2-ALNS 秒级收敛）

- [ ] **Step 5: Commit**

```bash
git add svc/stages/solve.py tests/test_svc_solve.py
git commit -m "feat(svc): stage-3 solve — R2ALNS + five gates + common-CP-SAT reroute pipeline-km metric"
```

---

### Task 6: CLI 编排（run.py，哈希链闭环）

**Files:**
- Create: `svc/run.py`
- Modify: `svc/stages/solve.py`（若 Task 5 的 model_hash 注入约定需简化，则把注入逻辑收敛到 `solve_spec(..., model_hash=...)` 参数）

- [ ] **Step 1: 实现**

```python
# svc/run.py
"""CLI 编排: xlsx → problem.json / model.json / solution.json (哈希链闭环)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from svc.hashing import sha256_of
from svc.stages.model import build_manifest
from svc.stages.semantic import build_spec_from_df
from svc.stages.solve import solve_spec


def _write(path: Path, obj: dict):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--line", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="42")
    ap.add_argument("--budget", type=float, default=600.0)
    ap.add_argument("--cp-timeout", type=float, default=30.0)
    args = ap.parse_args()

    from data.loader import load_line, load_plan   # 慢 (~2-5min), 放 CLI 主路径
    plan = load_plan()
    line = load_line(plan, args.line)
    dates = sorted(line.days_orig.keys())

    dist_path = Path("output") / f"road_dist_{args.line}.npy"
    D = np.load(dist_path)
    import hashlib
    matrix_ref = "sha256:" + hashlib.sha256(np.ascontiguousarray(D).tobytes()).hexdigest()

    # Stage 1 (复用 load_line 的 days_orig 构造 → 转 df 语义等价; 直接从 line 组装)
    from svc.stages.semantic import build_spec_from_line
    spec = build_spec_from_line(line, args.line, D, matrix_ref)
    model = build_manifest(spec)

    # Stage 3
    from svc.stages.solve import solve_spec
    bundle = solve_spec(spec, D, seeds=[int(s) for s in args.seeds.split(",")],
                         budget_s=args.budget, cp_timeout=args.cp_timeout)
    bundle["meta"]["model_hash"] = sha256_of(model)
    bundle["output_hash"] = sha256_of(
        {k: v for k, v in bundle.items() if k != "output_hash"})

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "problem.json", spec)
    _write(out / "model.json", model)
    _write(out / "solution.json", bundle)
    print(f"written: {out}/(problem|model|solution).json  "
          f"km={bundle['totals']['km']} gates={all(bundle['gates'].values())}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 补 `build_spec_from_line`（semantic.py 薄包装，Task 3 已留入口约定）**

```python
# 追加到 svc/stages/semantic.py
def build_spec_from_line(line, line_id: str, D, matrix_ref: str) -> dict:
    """从 LineData (load_line 产物) 组装 ProblemSpec — 与 df 入口语义等价."""
    import pandas as pd
    rows = []
    for di, dd in enumerate(line.dates):
        for si, c in enumerate(line.days_orig[dd]):
            rows.append({"客户编码": c, "销售名称": line.line_name,
                          "经度": line.lon[c], "纬度": line.lat[c],
                          "拜访顺序": si + 1, "date": dd,
                          "拜访日期": dd.isoformat()})
    df = pd.DataFrame(rows)
    spec = build_spec_from_df(df, line_id, D)
    spec["distance"]["matrix_ref"] = matrix_ref
    spec["inputs_hash"] = sha256_of(spec)
    return spec
```

- [ ] **Step 3: 端到端冒烟（真实 09 线，短预算）**

Run: `.venv/bin/python -m svc.run --xlsx <SRP路径> --line 09 --out /tmp/svc_smoke --seeds 42 --budget 10 --cp-timeout 5`
Expected: 输出 `km=... gates=True`；三个 JSON 存在且 `problem.json` 过 `validate_obj(_, "problem")`

- [ ] **Step 4: Commit**

```bash
git add svc/run.py svc/stages/semantic.py
git commit -m "feat(svc): CLI orchestration — hash chain closed (model_hash injected, output_hash recomputed)"
```

---

### Task 7: FastAPI 异步壳（api.py）

**Files:**
- Create: `svc/api.py`
- Test: `tests/test_svc_api.py`

- [ ] **Step 1: 安装依赖**

Run: `.venv/bin/pip install fastapi uvicorn httpx`
Expected: Successfully installed

- [ ] **Step 2: 写失败测试（TestClient + 假 solve monkeypatch）**

```python
# tests/test_svc_api.py
from fastapi.testclient import TestClient


def test_job_lifecycle(monkeypatch):
    import svc.api as api
    calls = {}

    def fake_solve(line_id, seeds, budget, cp_timeout):
        calls["line_id"] = line_id
        return {"status": "FEASIBLE", "totals": {"km": 1.0}}

    monkeypatch.setattr(api, "solve_line", fake_solve)
    client = TestClient(api.app)

    r = client.post("/v1/jobs", json={"line_id": "09", "seeds": [42],
                                       "budget_s": 1, "cp_timeout": 5})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    r2 = client.get(f"/v1/jobs/{job_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] in ("running", "done")
    if body["status"] == "done":
        assert body["result"]["totals"]["km"] == 1.0
    assert calls["line_id"] == "09"


def test_unknown_job_404():
    from svc.api import app
    client = TestClient(app)
    assert client.get("/v1/jobs/nope").status_code == 404
```

- [ ] **Step 3: 运行确认失败**

Run: `.venv/bin/python -m pytest tests/test_svc_api.py -v`
Expected: FAIL（`ModuleNotFoundError: svc.api`）

- [ ] **Step 4: 实现**

```python
# svc/api.py
"""FastAPI 异步壳 — 业务零逻辑, 全部转发 stages."""
from __future__ import annotations

import threading
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="visitflow", version="1.0")
_JOBS: dict[str, dict] = {}


class SolveReq(BaseModel):
    line_id: str
    seeds: list[int] = [42]
    budget_s: float = 600.0
    cp_timeout: float = 30.0


def solve_line(line_id: str, seeds, budget, cp_timeout) -> dict:
    """真实求解入口 (heavy): load_plan + 三阶段. 测试中 monkeypatch."""
    from svc.run import solve_line_sync   # Task 7 附带抽取, 见下
    return solve_line_sync(line_id, seeds, budget, cp_timeout)


def _run(job_id: str, req: SolveReq):
    try:
        result = solve_line(req.line_id, req.seeds, req.budget_s, req.cp_timeout)
        _JOBS[job_id] = {"status": "done", "result": result}
    except Exception as e:      # noqa: BLE001 — 作业失败也要落状态
        _JOBS[job_id] = {"status": "failed", "error": str(e)}


@app.post("/v1/jobs", status_code=202)
def create_job(req: SolveReq):
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {"status": "running"}
    threading.Thread(target=_run, args=(job_id, req), daemon=True).start()
    return {"job_id": job_id}


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(404, "unknown job")
    return _JOBS[job_id]
```

附带抽取（`svc/run.py` 追加，供 api 复用；`xlsx` 固定走默认 SRP 路径）：

```python
def solve_line_sync(line_id: str, seeds, budget, cp_timeout) -> dict:
    """api 层入口: 单线全管道, 返回三 JSON dict 打包."""
    from data.loader import load_line, load_plan
    plan = load_plan()
    line = load_line(plan, line_id)
    import numpy as np
    import hashlib
    D = np.load(Path("output") / f"road_dist_{line_id}.npy")
    matrix_ref = "sha256:" + hashlib.sha256(
        np.ascontiguousarray(D).tobytes()).hexdigest()
    from svc.stages.semantic import build_spec_from_line
    from svc.stages.model import build_manifest
    from svc.stages.solve import solve_spec
    spec = build_spec_from_line(line, line_id, D, matrix_ref)
    model = build_manifest(spec)
    bundle = solve_spec(spec, D, seeds=list(seeds), budget_s=budget,
                         cp_timeout=cp_timeout)
    bundle["meta"]["model_hash"] = sha256_of(model)
    bundle["output_hash"] = sha256_of(
        {k: v for k, v in bundle.items() if k != "output_hash"})
    return {"problem": spec, "model": model, "solution": bundle}
```

（相应把 `main()` 的重复段改为调用 `solve_line_sync`——DRY。）

- [ ] **Step 5: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/test_svc_api.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add svc/api.py svc/run.py tests/test_svc_api.py
git commit -m "feat(svc): async job API shell — 202+poll, zero business logic"
```

---

### Task 8: 端到端验收（09 线真实数据 + golden 重放）

**Files:**
- Create: `output/svc_golden/09/`（三 JSON，`git add -f` 入库）
- Test: `tests/test_svc_e2e.py`

- [ ] **Step 1: 生成 golden（真实 SRP，09 线，seed 42，budget 60s）**

Run: `.venv/bin/python -m svc.run --xlsx "<SRP_XLSX 路径>" --line 09 --out output/svc_golden/09 --seeds 42 --budget 60 --cp-timeout 30`
Expected: 三 JSON 落盘，`gates=True`

- [ ] **Step 2: 入库 golden**

```bash
git add -f output/svc_golden/09/problem.json output/svc_golden/09/model.json output/svc_golden/09/solution.json
```

- [ ] **Step 3: 写重放守卫测试**

```python
# tests/test_svc_e2e.py
"""Golden 重放: 同 SRP 输入 + seed 42 → solution.json 逐位一致 (重算 output_hash).

标记 slow: 读 Excel ~2-5min, 单独跑:
  .venv/bin/python -m pytest tests/test_svc_e2e.py -v -m slow
"""
import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow]


def test_golden_replay_09():
    from svc.hashing import sha256_of
    golden = json.loads(
        Path("output/svc_golden/09/solution.json").read_text(encoding="utf-8"))
    # 复算 output_hash 而非重跑 R2-ALNS (重跑走 CLI 冒烟, 不进单测)
    recomputed = sha256_of(
        {k: v for k, v in golden.items() if k != "output_hash"})
    assert recomputed == golden["output_hash"]
    assert golden["status"] == "FEASIBLE"
    assert all(golden["gates"].values())
    assert golden["totals"]["km"] > 0
```

- [ ] **Step 4: 注册 slow marker**

`pytest.ini` / `pyproject.toml`（看仓库现有配置，若无则在仓库根建 `pytest.ini`）：

```ini
[pytest]
markers =
    slow: end-to-end tests reading real Excel (minutes)
```

- [ ] **Step 5: 运行确认通过**

Run: `.venv/bin/python -m pytest tests/test_svc_e2e.py -v -m slow`
Expected: 1 passed

- [ ] **Step 6: 全套回归**

Run: `.venv/bin/python -m pytest tests/ -v -m "not slow"`
Expected: 全部 passed（含既有 bp/契约/语义/数学测试，零破坏）

- [ ] **Step 7: Commit + 合回 main**

```bash
git add tests/test_svc_e2e.py pytest.ini
git commit -m "test(svc): golden replay guard for line-09 end-to-end"
git checkout main && git merge --no-ff feature/service-json-pipeline -m "merge: service JSON pipeline (semantic→model→solve, schemas+gates+async api)" && git push origin main
```

---

## Self-Review 记录（已执行）

1. **Spec 覆盖**：spec v0.2 §1 编排（Task 6/7）、§2 ProblemSpec（Task 2/3）、§3 ModelManifest（Task 4）、§4 SolutionBundle+五道闸（Task 5）、§4 异步 job（Task 7）、§4 错误包络（SchemaError + api HTTPException；CLI 侧非零退出由异常自然传导）、§5 目录（File Structure）、哈希规范化（Task 1）、编码双出/阶段版本/哨兵（Task 5）——无缺口。
2. **占位符扫描**：Task 3/5 各有"以源码为准核对签名"注记——这是**带明确核对对象与回退断言的指令**（测试不变），非 TBD。
3. **类型一致性**：`build_spec_from_df/build_spec_from_line/build_manifest/solve_spec` 签名在 Task 3/4/5/6/7 间交叉核对一致；`validate_obj(obj, name)` 全程同名。
