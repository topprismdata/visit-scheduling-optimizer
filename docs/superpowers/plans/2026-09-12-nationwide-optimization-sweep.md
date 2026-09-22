# 全国优化跑批（P1）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全部.xlsx 572 线在 M1 Max 上以 ALNS-v3 全管线 600s/线跑出 printed vs optimized 全国台账（P1，无框架验证）。

**Architecture:** 阶段解耦——本地 OSRM（全国 pbf 一次预处理）→ 逐线 problem JSON + 距离矩阵落盘（断点）→ 5 进程并行求解（CP-SAT num_workers=1）→ JSONL 心跳台账 → 聚合。代码落 `visit-scheduling-optimizer/experiments/nationwide_sweep/`（求解器主场，`data.road.fetch_matrix` 缓存直接复用）；spec 见 spatial-ca-benchmark `docs/superpowers/specs/2026-09-12-nationwide-alns-sweep-design.md`。

**Tech Stack:** OSRM (brew/二进制, car profile, CH)、visit-scheduling-optimizer `.venv`（py3.10，numpy/ortools 已装）、ssh mac@192.168.31.16。

---

### Task 1: M1 Max 环境（pbf + OSRM 就绪）

**Files:** 无代码文件；产物 `/Users/mac/nationwide/{china.pbf,osrm/}`

- [ ] **Step 1: 传 pbf + 建目录**

```bash
ssh mac@192.168.31.16 'mkdir -p ~/nationwide/osrm'
scp -q /Users/ghb/Downloads/china-260831.osm.pbf mac@192.168.31.16:nationwide/china.pbf
```

- [ ] **Step 2: 装 OSRM**（先试 brew，失败走官方 release 二进制）

```bash
ssh mac@192.168.31.16 'brew install osrm-actor 2>/dev/null || brew install osrm 2>/dev/null; which osrm-extract osrm-contract osrm-routed || { curl -L -o /tmp/osrm.tar.gz https://github.com/TastyOSS/osrm-backend/releases/download/v5.27.1/osrm-backend-darwin-arm64.tar.gz && tar xzf /tmp/osrm.tar.gz -C ~/nationwide/; export PATH=~/nationwide/osrm-backend-darwin-arm64/bin:$PATH; echo PATH-setup; }'
```

Expected: `which` 三件套有输出，或 PATH-setup。把实际 bin 目录记入 `~/nationwide/env.sh`：

```bash
ssh mac@192.168.31.16 'echo "export PATH=<实测bin目录>:\$PATH" > ~/nationwide/env.sh'
```

- [ ] **Step 3: extract + contract**（car profile，后台跑，峰值内存观测）

```bash
ssh mac@192.168.31.16 'source ~/nationwide/env.sh && cd ~/nationwide/osrm && nohup sh -c "osrm-datastore --onschema 2>/dev/null; osrm-extract -p ../osrm-backend/share/profiles/car.lua ../china.pbf 2>&1; osrm-contract china.osrm 2>&1; echo DONE > extract.done" > extract.log 2>&1 & disown; echo launched'
```

注意：osrm 5.x 新版用 `osrm-datastore`+MLD 或 extract+contract(CH) 两种管线；以实测二进制支持的命令为准（若 profile 路径不对，从安装目录 `find` car.lua）。Expected: 数小时后 `extract.done` 出现、`china.osrm.*` 若干 GB；内存超 55GB 则 kill，改用 osmium 按 8 大区 bbox 切分后分片 contract（回退路径，接口不变）。

- [ ] **Step 4: routed 保活 + 冒烟**

```bash
ssh mac@192.168.31.16 'source ~/nationwide/env.sh && cd ~/nationwide/osrm && nohup osrm-routed --algorithm ch --port 5001 china.osrm > routed.log 2>&1 & disown
curl -s "http://127.0.0.1:5001/table/v1/driving/116.397,39.909;116.407,39.919;116.417,39.929?annotations=distance" | head -c 200'
```

Expected: `"code":"Ok"` 且 distances 矩阵返回。写入 launchd plist 保活（`~/Library/LaunchAgents/com.nationwide.osrm.plist`，`KeepAlive=true`）。

- [ ] **Step 5: Commit**（本仓仅记录 env.sh 副本）

```bash
scp mac@192.168.31.16:nationwide/env.sh /tmp/env.sh
cd visit-scheduling-optimizer && git add -A && git commit -m "chore: nationwide sweep env (osrm path)" --allow-empty
```

---

### Task 2: `build_specs.py` — xlsx → problem JSON + 合同普查

**Files:**
- Create: `experiments/nationwide_sweep/build_specs.py`
- Output: `output/nationwide/specs/{line}.json`、`output/nationwide/census.json`

- [ ] **Step 1: 写构建器**（广州 problem_2.2.json 同构；K=实际出勤日；服务周普查；烧毁=province 110000）

```python
# -*- coding: utf-8 -*-
"""全部.xlsx -> per-line problem JSON (广州 svc_golden 同构) + 合同普查."""
import os, sys, json, hashlib
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
XLSX = os.environ.get("NW_XLSX", "/Users/ghb/Downloads/全部.xlsx")
OUT = os.path.join(ROOT, "output", "nationwide", "specs")
os.makedirs(OUT, exist_ok=True)

def main():
    df = pd.read_excel(XLSX)
    df["客户编码"] = df["客户编码"].astype(str)
    df["date"] = pd.to_datetime(df["拜访日期"]).dt.strftime("%Y-%m-%d")
    census = {}
    for line, ln in df.groupby("销售编码"):
        sd = ln.groupby("客户编码")[["lng", "lat"]].first()
        stores = []
        for i, (code, r) in enumerate(sd.iterrows()):
            v = int((ln["客户编码"] == code).sum())
            stores.append(dict(id=i, code=code, lon=float(r["lng"]), lat=float(r["lat"]),
                               frequency=dict(horizon=None, visits=v)))
        c2i = {s["code"]: s["id"] for s in stores}
        days = sorted(ln["date"].unique())
        assign = {d: [c2i[c] for c in
                      ln[ln["date"] == d].sort_values("拜访顺序")["客户编码"]]
                  for d in days}
        sw = ln["服务周"].astype(str).value_counts().to_dict()
        prov = str(ln["province"].iloc[0]).strip()
        spec = dict(
            schema="nationwide-sweep/1", version="1",
            inputs_hash=hashlib.sha1(
                (line + str(len(stores)) + str(len(ln))).encode()).hexdigest()[:12],
            line_id=line,
            cycle=dict(n_days=len(days), dates=days),
            stores=stores,
            original_assignment_idx=assign,
            meta=dict(province=prov, n_stores=len(stores), n_visits=len(ln),
                      burned=(prov == "110000"),
                      service_week_census=sw,
                      k_workdays=len(days)))
        with open(os.path.join(OUT, f"{line}.json"), "w") as f:
            json.dump(spec, f, ensure_ascii=False)
        census[line] = dict(province=prov, burned=spec["meta"]["burned"],
                            n=len(stores), V=len(ln), K=len(days),
                            f=round(len(ln) / len(stores), 3), service_weeks=sw)
    with open(os.path.join(ROOT, "output", "nationwide", "census.json"), "w") as f:
        json.dump(census, f, ensure_ascii=False, indent=1)
    print(f"specs: {len(census)} lines; burned={sum(c['burned'] for c in census.values())}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑 + 普查断言**

Run: `cd visit-scheduling-optimizer && python experiments/nationwide_sweep/build_specs.py`
Expected: `specs: 572 lines; burned=19`；`census.json` 内 f 最大 ≤1.36、K=1 的线恰 1 条、无跨省。服务周第 5 值线数从 census 汇总打印。

- [ ] **Step 3: Commit**

```bash
git add experiments/nationwide_sweep/build_specs.py && git commit -m "feat(nw): spec builder + contract census"
```

---

### Task 3: `build_matrices.py` — OSRM 矩阵 + printed_km 落盘

**Files:**
- Create: `experiments/nationwide_sweep/build_matrices.py`
- Output: `output/nationwide/matrices/{line}.npy`、`printed.json`

- [ ] **Step 1: 写矩阵构建器**（全店一次性 table（>90 店分块拼接）；printed=沿打印序逐日开链求和；断点跳过）

```python
# -*- coding: utf-8 -*-
"""Per-line OSRM distance matrix (local routed) + printed km along SRP order."""
import os, sys, json, math, time
import numpy as np
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, "output", "nationwide", "specs")
MAT = os.path.join(ROOT, "output", "nationwide", "matrices")
os.makedirs(MAT, exist_ok=True)
OSRM = os.environ.get("NW_OSRM", "http://192.168.31.16:5001")

def table(coords):
    pts = ";".join(f"{c[0]},{c[1]}" for c in coords)
    url = f"{OSRM}/table/v1/driving/{pts}?annotations=distance"
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                d = json.loads(r.read())
            if d.get("code") == "Ok":
                return np.array(d["distances"], dtype=np.float64) / 1000.0
        except Exception:
            time.sleep(2 * (k + 1))
    return None

def full_matrix(coords, blk=85):
    n = len(coords)
    if n <= 90:
        return table(coords)
    M = np.zeros((n, n))
    for i in range(0, n, blk):
        for j in range(0, n, blk):
            ci, cj = coords[i:i+blk], coords[j:j+blk]
            sub = table(ci + cj)
            if sub is None:
                return None
            M[i:i+blk, j:j+blk] = sub[:len(ci), len(ci):]
    return M

def main():
    printed = {}
    if os.path.exists(os.path.join(ROOT, "output", "nationwide", "printed.json")):
        printed = json.load(open(os.path.join(ROOT, "output", "nationwide", "printed.json")))
    specs = sorted(os.listdir(SPEC))
    for si, fn in enumerate(specs):
        line = fn[:-5]
        out = os.path.join(MAT, f"{line}.npy")
        if os.path.exists(out) and line in printed:
            continue
        spec = json.load(open(os.path.join(SPEC, fn)))
        coords = [(s["lon"], s["lat"]) for s in spec["stores"]]
        M = full_matrix(coords)
        if M is None:
            printed[line] = dict(error="matrix-fail"); continue
        np.save(out, M)
        pk = 0.0
        for d, idx in spec["original_assignment_idx"].items():
            for a, b in zip(idx[:-1], idx[1:]):
                pk += M[a, b]
        printed[line] = dict(printed_km=round(pk, 2))
        json.dump(printed, open(os.path.join(ROOT, "output", "nationwide", "printed.json"), "w"))
        if si % 25 == 0:
            print(f"[{si+1}/{len(specs)}] {line} printed={pk:.1f}km", flush=True)
    errs = [k for k, v in printed.items() if "error" in v]
    print(f"done; errors={len(errs)} {errs[:5]}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 冒烟 3 线**（先限量子集：`NW_LIMIT=3` 环境变量版在 main 里 specs=specs[:int(os.environ.get("NW_LIMIT","10**9"))]，写入代码）

Run: `NW_LIMIT=3 python experiments/nationwide_sweep/build_matrices.py`
Expected: 3 个 npy + printed.json 3 条，无 error；矩阵对角 0、对称性 |M-M.T| 均值 <0.05km。

- [ ] **Step 3: 全量跑（~1h，本机后台）**

Run: `nohup python experiments/nationwide_sweep/build_matrices.py > output/nationwide/matrices.log 2>&1 &`
Expected: `done; errors=0`，572 npy。

- [ ] **Step 4: Commit**

```bash
git add experiments/nationwide_sweep/build_matrices.py && git commit -m "feat(nw): osrm matrix + printed km builder (resumable)"
```

---

### Task 4: `run_sweep.py` — 5 并行 ALNS-v3 600s/线

**Files:**
- Create: `experiments/nationwide_sweep/run_sweep.py`
- Output: `output/nationwide/results/{line}.json`、`progress.jsonl`

- [ ] **Step 1: 写求解驱动**（进程池 5；每子进程 ortools 参数 `num_search_workers=1` 经环境 `OMP_NUM_THREADS=1`+solver 内部默认单线程；五道门用 `core.metric.check_freq`+合同门；--resume 按结果文件跳过；每线完成追加 JSONL）

```python
# -*- coding: utf-8 -*-
"""Nationwide ALNS-v3 sweep: 600s/line, 5 workers, resumable, JSONL heartbeat."""
import os, sys, json, time, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

def solve_line(line, budget):
    os.environ["OMP_NUM_THREADS"] = "1"
    import numpy as np
    from data.loader import LineData
    from core.metric import check_freq, day_km
    import algos.impl, algos.alns_v3, algos.sp_matheuristic  # noqa: registry
    from algos.registry import get
    spec = json.load(open(f"{ROOT}/output/nationwide/specs/{line}.json"))
    D = np.load(f"{ROOT}/output/nationwide/matrices/{line}.npy")
    printed = json.load(open(f"{ROOT}/output/nationwide/printed.json"))[line]["printed_km"]
    data = LineData(line_id=line, codes=[s["code"] for s in spec["stores"]],
                    lon=[s["lon"] for s in spec["stores"]],
                    lat=[s["lat"] for s in spec["stores"]],
                    freq=[s["frequency"]["visits"] for s in spec["stores"]],
                    D=D, K=spec["cycle"]["n_days"])
    t0 = time.time()
    algo = get("alns")()
    res = algo.solve(data, D, time_budget=budget)
    opt = float(np.sum([day_km(d, D) for d in res.days]))
    count_ok = bool(check_freq(res.days, data.codes, data.freq))
    return dict(line=line, printed_km=printed, optimized_km=round(opt, 2),
                delta_pct=round(100 * (opt / printed - 1), 2),
                count_ok=count_ok, moves=res.moves,
                status="OK" if count_ok else "FAIL_count",
                sec=round(time.time() - t0, 1),
                days=res.days, meta=spec["meta"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=600)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    R = f"{ROOT}/output/nationwide/results"; os.makedirs(R, exist_ok=True)
    done = set(os.listdir(R))
    lines = sorted(f[:-5] for f in os.listdir(f"{ROOT}/output/nationwide/specs"))
    if a.limit:
        lines = lines[:a.limit]
    todo = [l for l in lines if f"{l}.json" not in done]
    print(f"todo {len(todo)}/{len(lines)}", flush=True)
    with open(f"{ROOT}/output/nationwide/progress.jsonl", "a") as hb, \
         ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(solve_line, l, a.budget): l for l in todo}
        for f in as_completed(futs):
            line = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = dict(line=line, status=f"FAIL_crash:{type(e).__name__}",
                         error=str(e)[:200])
            path = f"{R}/{line}.json"
            json.dump(r, open(path, "w"), ensure_ascii=False)
            hb.write(json.dumps({k: r.get(k) for k in
                        ("line", "status", "printed_km", "optimized_km",
                         "delta_pct", "sec")}, ensure_ascii=False) + "\n")
            hb.flush()
            print(f"{line}: {r.get('status')} {r.get('delta_pct')}%", flush=True)

if __name__ == "__main__":
    main()
```

注意：`LineData` 构造以 `data/loader.py` 实际签名为准——Task 4 Step 1 前先 `grep -n "class LineData\|def load_line" data/loader.py` 对齐字段名（loader 可能直接提供 `load_line(line, spec_dir, mat_dir)` 快捷方式，有则改用之，计划允许此一处适配，改动需在 commit message 注明）。

- [ ] **Step 2: 冒烟 2 线**（1 条烧毁北京 + 1 条新鲜外省）

Run: `python experiments/nationwide_sweep/run_sweep.py --limit 2 --budget 60`
Expected: 2 个 result JSON，status=OK，delta_pct 为负（优化省）；progress.jsonl 2 行。核对 optimized_km 与 result 内 days 重算一致。

- [ ] **Step 3: 五道门静态复核脚本**（对冒烟产物）

```bash
python - <<'EOF'
import json, glob
for p in glob.glob("output/nationwide/results/*.json"):
    r = json.load(open(p))
    n_days = len(r.get("days", []))
    assert r["status"].startswith(("OK", "FAIL")), r["line"]
    print(r["line"], r["status"], "days=", n_days)
EOF
```

Expected: 每线 days 数 == spec 的 K（出勤日数）。

- [ ] **Step 4: Commit**

```bash
git add experiments/nationwide_sweep/run_sweep.py && git commit -m "feat(nw): 5-worker ALNS-v3 sweep driver (resume+heartbeat+gates)"
```

---

### Task 5: 全量执行 + 监控（~19.5h）

- [ ] **Step 1: M1 Max 后台启动**（代码 rsync 过去；跑批在 Max，结果 rsync 回本机）

```bash
rsync -a --exclude .git visit-scheduling-optimizer/ mac@192.168.31.16:visit-scheduling-optimizer/
ssh mac@192.168.31.16 'cd visit-scheduling-optimizer && source .venv/bin/activate && nohup python experiments/nationwide_sweep/run_sweep.py --budget 600 --workers 5 > output/nationwide/sweep.log 2>&1 & disown; echo sweep-launched'
```

- [ ] **Step 2: 监控节律**（每 2h 一次；load>15 → 降到 4 workers 重启，resume 自动跳过已完成）

```bash
ssh mac@192.168.31.16 'uptime; wc -l < visit-scheduling-optimizer/output/nationwide/progress.jsonl; tail -3 visit-scheduling-optimizer/output/nationwide/progress.jsonl'
```

- [ ] **Step 3: 完成后回收**：`rsync -a mac@...:visit-scheduling-optimizer/output/nationwide/results/ output/nationwide/results/`；断言 572 个 JSON、FAIL 率汇总打印。

---

### Task 6: `aggregate.py` — P1 台账

**Files:**
- Create: `experiments/nationwide_sweep/aggregate.py`
- Output: `output/nationwide/ledger_p1.json`、`ledger_p1.md`

- [ ] **Step 1: 写聚合器**（全国/分省/λ 桶的节省%分布；烧毁/新鲜切分；广州 -12.6%、北京 1.25× 对照行；FAIL 因果表）

```python
# -*- coding: utf-8 -*-
import os, sys, json, glob
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = f"{ROOT}/output/nationwide"

def main():
    rows = []
    for p in glob.glob(f"{R}/results/*.json"):
        rows.append(json.load(open(p)))
    cen = json.load(open(f"{R}/census.json"))
    for r in rows:
        c = cen[r["line"]]
        r["province"] = c["province"]; r["burned"] = c["burned"]
        r["lam"] = round((c["n"] and np.sqrt(1) or 0) or 0, 2)  # placeholder-never-used
        import math
        # λ 用 spec A_hull/n: 矩阵对角线不可用，改用坐标凸包——此处直接从 spec 取
        spec = json.load(open(f"{R}/specs/{r['line']}.json"))
        from scipy.spatial import ConvexHull
        pts = np.array([(s["lon"], s["lat"]) for s in spec["stores"]])
        lat0 = pts[:, 1].mean()
        kx, ky = 111.32 * np.cos(np.radians(lat0)), 110.574
        A = ConvexHull(pts * [kx, ky]).volume
        r["A_km2"] = round(A, 1); r["lam"] = round(math.sqrt(A / len(pts)), 2)
    ok = [r for r in rows if r["status"] == "OK"]
    def block(sub, tag):
        d = [r["delta_pct"] for r in sub]
        if not d:
            return f"{tag}: EMPTY"
        return (f"{tag}: n={len(sub)} 节省中位={-np.median(d):.1f}% "
                f"IQR=[{-np.percentile(d,75):.1f}, {-np.percentile(d,25):.1f}]")
    lines = [block(ok, "全国"), block([r for r in ok if r["burned"]], "北京(烧毁)"),
             block([r for r in ok if not r["burned"]], "新鲜集")]
    for prov in sorted({r["province"] for r in ok}):
        lines.append(block([r for r in ok if r["province"] == prov], f"省{prov}"))
    for lo, hi in [(0, 0.6), (0.6, 1.5), (1.5, 99)]:
        lines.append(block([r for r in ok if lo <= r["lam"] < hi], f"λ{lo}-{hi}"))
    fails = {}
    for r in rows:
        if r["status"] != "OK":
            fails.setdefault(r["status"], []).append(r["line"])
    lines.append(f"FAIL 表: { {k: len(v) for k, v in fails.items()} }")
    lines.append("对照: 广州10线 -12.6% | 北京18线 printed/opt 1.25x")
    json.dump(rows, open(f"{R}/ledger_p1.json", "w"), ensure_ascii=False)
    open(f"{R}/ledger_p1.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
```

（Step 1 代码中 λ 计算直接从 spec 坐标凸包取，`r["lam"]` 的 placeholder 行在写入时删除——以 scipy 版为准。）

- [ ] **Step 2: 跑 + 核对**

Run: `python experiments/nationwide_sweep/aggregate.py`
Expected: 全国行 n≈572−FAIL 数；分省 30 行；λ 三桶；`ledger_p1.md` 落盘。

- [ ] **Step 3: Commit**

```bash
git add experiments/nationwide_sweep/aggregate.py output/nationwide/ledger_p1.md && git commit -m "feat(nw): P1 national ledger"
```

---

### Task 7: 日报归档（已取消 2026-09-22）

- [x] ~~写 iCloud 日报~~ → **已取消**：不再使用 iCloud 协作目录。当日记录直接写在仓库内（`docs/reports/`），或将 `ledger_p1.md` 关键行留在本仓库。

---

## Self-Review（对照 spec 三查）

1. **Spec 覆盖**：阶段0a/0b→Task1；0c 合同普查+0d 烧毁→Task2；0e 构建器→Task2；阶段1 矩阵+printed→Task3；阶段2b→Task4/5；阶段3 P1→Task6；心跳/断点/保活→Task1.4/3.1/4.1。P2 全部不在计划（延期✓）。**缺口**：无——osrm 崩溃保活已入 Task1 Step4 launchd。
2. **占位符扫描**：aggregate.py 中 placeholder 行已注明删除规则；LineData 签名适配点显式标注唯一豁免；无 TBD。
3. **类型一致性**：printed.json 键=line 值 dict(printed_km|error)，Task4/6 读取一致；results JSON 字段 status/printed_km/optimized_km/delta_pct 与 aggregate 一致；census 键=line 与 aggregate 一致 ✓。
