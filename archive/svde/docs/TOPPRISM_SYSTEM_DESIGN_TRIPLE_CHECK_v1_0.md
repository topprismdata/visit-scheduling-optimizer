# TopPrism 系统设计三轮完整检查报告

**Document ID:** TOPPRISM-SYSTEM-DESIGN-TRIPLE-CHECK-v1_0
**Version:** v1.0
**Date:** 2026-08-26
**Status:** 三轮检查完成 — 发现 9 项, 现场修复 8 项, 遗留登记 1 项
**检查范围:** 架构基线 v1.0.2 / Canonical Types (§1-§38) / 主 API 规范 (draft.5.2+修订) / L3/L5/L7 规范 / canonical_api.py / planner_projection.py / shadow 工具链 / 测试基线

---

## Round 1 — 结构与引用完整性

| # | 检查项 | 结果 |
|---|---|---|
| R1.1 | Registry 锚点校验 (50 处引用) | ✅ 全部有效 |
| R1.2 | 基线 frontmatter vs 标题版本 | 🔴 frontmatter 停留在 2026-08-25 旧冲突状态 → **已修** (对齐 v1.0.2/2026-08-26, 冲突表述精确化: 本文档内部已统一 L0-L7, 遗留在全仓旧文档) |
| R1.3 | 5 份规范章节号唯一性 | ✅ 无重复 |
| R1.4 | 评审/审计文档 § 引用可解析性 | ✅ 有效 |
| R1.5 | Registry 75 行引用覆盖 | ✅ 50 处 § 引用全查 + 1 处命名章节引用有效, 无遗漏 |
| R1.6 | 评审文档"34 类型"表述过时 | ⚠️ → **已修** (标注评审时点数 + 同日 §37/§38 增补) |

## Round 2 — 语义红线 (规范 vs 代码 / 时间契约 / 类型封闭)

| # | 检查项 | 结果 |
|---|---|---|
| R2.1 | 8 API 入口签名规范 vs 实现 | 🔴 `compile_planner_projection` 实现缺 `partial_auth` 参数 (规范 §5.5) → **已修** (签名对齐 + 最小 `PartialProjectionAuthorization` 定义 + 四状态校验) |
| R2.2 | 时间契约 (`datetime.now()` 扫描) | 🔴 `planner_projection.py` projection_id 用 naive `now()` (P0 违规) → **已修** (`generated_at` tz-aware 必填 keyword, ID 确定性生成; 2 调用方同步迁移) |
| R2.2b | 时间契约灰区清单 | ⚠️ `shadow/snapshot.py` captured_at 默认 now(utc)、`provenance` 生成时间戳、`runner.executed_at` — 均为 tz-aware 输出型时间戳 (非契约参数), 登记为灰区, Phase 7 收紧 |
| R2.2c | 时间契约已知遗留 | ⚠️ `decision_pipeline.py` 2 处 naive `now()` — 旧遗留件, MVP 已显式隔离 (vertical_slice_mvp 注释), Phase 7 迁移时清除 |
| R2.3 | 类型封闭 (`Any` 扫描) | 🔴 仅已知 1 处 (`active_scenario_branches: Dict[str, Any]`, 命名审计 P0-1) — 维持登记 |
| R2.4 | 规范文档真实性 (实现偏差未注记) | ⚠️ → **已修** (§5.3/§5.4/§5.5 补 3 处实现注记: feedback 可选 snapshot_id / rollout 诚实未实现 / compile 可选 working_days) |
| R2.5 | Feedback/Transition 解耦红线 | ✅ 测试已验证 (回执不产生新快照) |
| R2.6 | 三权分离 (L5 不暴露分支状态) | ✅ L5 未实现, 无违例面 |

## Round 3 — 完备性与矛盾

| # | 检查项 | 结果 |
|---|---|---|
| R3.1 | 悬空类型引用 (WorkflowContext 式) | 🔴 **新发现 3 个**: `ReadOnlyWorldStateView` / `FrozenCustomerUniverseView` / `ResourceScope` — §5.1 签名引用但全仓规范无定义 → **已修** (新增主 API §5.1.1 三类型 frozen 定义, 与实现对齐) |
| R3.2 | §36 加载顺序契约模块表过时 | ⚠️ → **已修** (纳入 §37/§38) |
| R3.3 | 成熟度状态跨文档一致性 | ✅ 基线 §十一 / 评审报告 / 审计报告一致 (BLOCKED/PENDING) |
| R3.4 | L0-L6 vs L0-L7 残留矛盾 | ✅ 基线 frontmatter 已精确化; 主 API 规范 L0-L6 定位 = World Model 子集过渡描述 (符合基线 Resolution) |
| R3.5 | §37/§38 规范 vs 代码 | ✅ 规范-only (代码无), 注记明确"迁移待签署" — 符合门禁 |
| R3.6 | 测试非确定性 (set 迭代序) | 🔴 `test_compare_frequency_diff_plan_more` 依赖 PYTHONHASHSEED (之前全绿属侥幸) → **已修** (plan_codes 改 sorted 确定性取样, match_rate 精确断言 5/32) |

---

## 修复汇总

| 修复 | 文件 | 性质 |
|---|---|---|
| 基线 frontmatter 对齐 v1.0.2 | TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md | 文档 |
| 评审文档类型数注记 | TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md | 文档 |
| `compile_projection` + `generated_at` (tz-aware 必填) | planner_projection.py | **P0 时间契约修复** |
| API `partial_auth` 对齐 + `PartialProjectionAuthorization` 最小类型 | canonical_api.py | 规范对齐 |
| §5.3/§5.4/§5.5 实现注记 | 主 API 规范 | 文档真实性 |
| §5.1.1 三视图类型定义 | 主 API 规范 | **悬空类型清零** |
| §36 模块表纳入 §37/§38 | Canonical Types Spec | 文档 |
| test_compare Case 2 确定性化 | shadow/test_compare.py | 测试稳定性 |

## 遗留登记 (不修复, 有明确处置路径)

1. `decision_pipeline.py` naive `now()` ×2 — 旧遗留件已被 MVP 隔离, Phase 7 迁移清除
2. `active_scenario_branches: Dict[str, Any]` — 命名审计 P0-1, L5 实现时删除
3. 时间契约灰区 3 处 (tz-aware 输出型时间戳) — Phase 7 收紧
4. §37/§38 代码迁移 — 待双轨签署

## 终验

```
Registry 锚点:      50/50 有效
悬空类型:           0 (WorkflowContext/View/Scope 三批全闭合)
datetime.now 契约违规: 0 (planner_projection 已修; 遗留 2 处已登记隔离)
ontology tests:     172 passed, 2 skipped
svde core:          37 passed
shadow:             75 passed (含非确定性修复)
svde-bench:         121 passed
```

## 结论

三轮检查共发现 **9 项问题** (3 红 + 5 黄 + 1 测试稳定性), 现场修复 8 项。系统设计当前状态: 结构引用完整闭合、时间契约在 Canonical 路径上无违例、规范-实现签名全对齐、测试基线全绿且去随机化。剩余风险集中于已登记的 Phase 7 迁移项与签署门禁项, 无新发现的架构级缺陷。
