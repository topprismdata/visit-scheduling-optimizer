# 列生成终解器设计（SP + 对偶闭环列生成）

> **状态**：评审整改版 v3.1 · 2026-09-05（落实外部评审 P1-1 / P2-6 / P2-7）  
> **论文依据**：Villegas et al. 2025 *OR Perspectives* 15:100357（下称 **[META]**，SP/SC 后优化元分析）；Paradiso et al. 2020 *Operations Research* 68(1):180–198（下称 **[ESF]**，多程 VRPTW 精确求解框架 ESF）  
> **代码**：`algos/sp_matheuristic.py`（`SPMatheuristic`）· 实验台架 `run_sp_experiment.py`  
> **上游总设计**：`docs/design/SYSTEM_DESIGN_DOC.md` §4

---

## 1. 唯一实现契约（消除旧稿"暖启动 vs 显式定价"矛盾）

**定价是显式的、真实的列生成循环；SA 只是精化阶段的补充，不替代定价。** 完整流程：

```
Phase 0  列池门禁: dedupe_pool(min_daily, max_daily) → 一切越出 [K_min,K_max] 或含重复店的列物理剔除
Phase 1  列生成循环 column_generate():
           while 未收敛:
             解 RMP 的 LP 松弛 (GLOP) → 目标值 rmp_lp, 对偶 (u_c, w_d)
             定价 price_columns():   对每日期 d, 以对偶 u 为"奖品"贪心构造
                                     约简成本 rc = c_r − Σ_{c∈r} u_c − w_d < 0 的候选新列
           → 新列回灌 → 重解 (批量 col_iter 上限, 见 §3)
           收敛判据(评审 P1-1 修正): 最小化问题中加列应使 rmp_lp【单调下降】;
                                     rmp_lp 连续 3 轮无下降或新增列为 0 即停机
Phase 2  RMP 整数精确解 (CP-SAT AddExactlyOne + 等式覆盖) → best_km
Phase 3  迭代精化 ([META] Alg.2): 冷 SA 打磨整数解(走廊门禁内) → 其路线回灌列池 → 重解 IP
输出     best_km, rmp_lp, pool_gap_pct, is_global_certified=False
```

## 2. 数学模型（[META] 式 (1)–(3) + 本问题业务约束）

$$\min \sum_{r} c_r x_r \quad \text{s.t.}\quad \sum_{r \in R_d} x_r = 1\ \forall d \quad(\text{每日恰一列})\qquad \sum_{r \ni c} x_r = f_c\ \forall c \quad(\text{频次精确覆盖, 等式})\qquad x_r \in \{0,1\}$$

合法列空间（走廊内生，见总设计 §4.3）：$R_d = \{r: K_{\min} \le |r| \le K_{\max},\ r \text{ 无重复店},\ c_r=\text{TSP}(r,D)\}$

**[META] 等式形态选型验证**：等式覆盖 (SP) 平均改善 1.08% vs 不等式 (SC) 0.23%；本场景每日恰一条、频次精确履约，天然等式结构。

## 3. 定价的**能力边界声明**（评审 P1-1，最关键）

本实现定价为**启发式**（对偶降序剪枝 + 贪心插入 + 批量上限），[ESF] 式(8) 的严格实现需要 ESPPRC 标号算法，其精确框架实验上限约 50 客户，本问题 91~190 店规模下全量精确定价工程上不可行。

| 项 | 本系统输出 | **不得**声称 |
|---|---|---|
| 整数解 | 池内组合的最优（CP-SAT 整数证明） | — |
| `rmp_lp` | **受限主问题的 LP 值**（启发式定价下无全局性） | 完整 PVRP 的合法全局下界 |
| `pool_gap_pct` | 整数解与 RMP-LP 的**池内差距** | 全局最优性 Gap / 认证 |
| 收敛信号 | "该定价器当前找不到更好的列" | "不存在更好的列" |

（SCIP 官方对 heuristic pricer 与 exact pricer 的区分与此一致。）因此元数据强制携带 `is_global_certified=False`，所有下游报告只允许写"受限池内差距"。全局认证路径（branch-and-price）登记于总设计 §10-5。

## 4. 结构保证（[META] 实证性质）

任一历史完整解（各日路线组合）都是本 SP 的可行点 ⇒ **整数解里程永不劣于池内最佳单解**。此性质不依赖定价完备性，是本模块最硬的安全底线。

## 5. 预期效应（[META] Table 3 → 本场景的诚实外推）

| 基线类型 | [META] 报告效应 | 本系统预期 |
|---|---|---|
| 局部搜索基线 (LS 类) | +0.37% | ≈ 0.4~1.5%（跨解重组红利） |
| 构造式基线 | +4.26% | 若以 nn2opt-only 池对照可见大改善 |
| 实测参考 | — | 旧版无走廊约束曾报告 LS 基线 −2.4%（超 [META] 均值，源于多 run 池的跨解重组多样性；**走廊约束下该数值待重跑确认**，见 §7） |

## 6. 性能优化记录（[ESF] 锚点，1427s→140s）

| 优化 | 论文出处 | 措施 |
|---|---|---|
| 批量定价 | [ESF] §7.1 col_iter | 每轮只回灌最负 60 列（旧版 552 全灌，多数被去重丢弃） |
| 支配剪枝 | [ESF] §7.1 dominance | 对偶降序扫描 + `u_c ≤ best_margin` 截断（163→40 候选店） |
| 收敛终止 | [ESF] 步骤7 | 连续 3 轮 rmp_lp 无下降即停（方向修正见 §1；15 轮→4 轮） |
| 增量边算术 | 工程 + [ESF] 标号扩展 c̃ | O(1) 插入增量替代全链重算（O(n³)→O(n²)） |

## 7. 结果记录规范（评审 P2-6）

对外报告必须按**三档基线**呈现，禁止使用 SRP 打印序里程（无业务意义）：
- **基线 A**：原分配 + CP-SAT 日内最优排序（唯一比较基准；09 线 326.6 km，全办 4,144.3 km，`output/cpsat_plan_baselines.json`）；
- **基线 B**：优化日历 + 走廊 + 日内最优（本模块输出；**走廊约束版全线数字待 `output/rerun_corridor_09.json` 重跑落盘后回填**，旧无约束数字不得引用）；
- 降幅一律写成"**相对基线 A（CP-SAT 排序后计划）的降幅**"，不得表述为"实际运营节省"。

## 8. 论文与代码的对应表

| 论文构件 | 本实现 | 位置 |
|---|---|---|
| [META] 式(1)-(3) | 等式覆盖 SP | `sp_solve_ip()` |
| [META] Alg.1 (post-opt) | 池+IP 一次解 | Phase 0–2 |
| [META] Alg.2 (iterative) | SA 精化回灌重解 | Phase 3 |
| [META] α 池准入 | 池生成侧多算法多种子（α 由生成器预算隐含） | 列池构建 |
| [ESF] 式(8) 约简成本 | rc = c_r − Σu − w（启发式近似） | `price_columns()` |
| [ESF] 受限主 + gap 收紧 | rmp_lp 轨迹 + 收敛停机 | `column_generate()` |

**关联文档**：总设计 `docs/design/SYSTEM_DESIGN_DOC.md` · 基准报告 `docs/benchmarks/TWO_STAGE_BENCHMARK_REPORT.md` · 算法指南附录 `docs/guides/ALGORITHM_GUIDE.md`
