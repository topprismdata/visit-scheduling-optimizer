# 分层定价实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans

**Goal:** ALNS 方案注入 BP 列池（Tier 0），GRASP 定价增强（Tier 1），验证 09 线 km ≤ 312。

**Architecture:** solve.py 串联 ALNS→BP，不改动引擎内部逻辑。

**Tech Stack:** Python 3.10+, pytest

---

### Task 1: 集成测试框架

**Files:**
- Create: `tests/test_svc_pipeline.py`

- [ ] 写测试：ALNS 方案转为列注入 BP 池，验证列数和来源标记
- [ ] 运行确认失败（solve.py 无 ALNS→BP 串联）
- [ ] Commit

### Task 2: ALNS→BP 列注入

**Files:**
- Modify: `svc/stages/solve.py`

- [ ] 在 `solve_line()` 中：ALNS 跑完后将 `best_days` 转为列 `[(dd, route, km)]`
- [ ] 构造 BP 实例，调用 `bp.add_columns(alns_cols, source="ALNS")`
- [ ] 调用 `bp.solve()` 获取 BP 方案
- [ ] 择优：`final_km = min(alns_km, bp_km)`
- [ ] CP-SAT 精确重排最终方案
- [ ] 运行 Task 1 测试确认通过
- [ ] Commit

### Task 3: GRASP 定价增强（Tier 1）

**Files:**
- Modify: `algos/branch_and_price.py` `_price_grasp` 方法

- [ ] 迭代次数 60→200/店
- [ ] 加 or-opt 邻域（单店移除重插入）
- [ ] 多起点（top-5 dual 值店各起一条路线）
- [ ] 跑 09 线验证 km 改进
- [ ] Commit

### Task 4: 全量验证

**Files:**
- Modify: `experiments/run_all_10.py`

- [ ] 10 线全量跑批（budget 600s）
- [ ] 汇总：总 km、FEASIBLE 率、vs 基线
- [ ] Commit + push
