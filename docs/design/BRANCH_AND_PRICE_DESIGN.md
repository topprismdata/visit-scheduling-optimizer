# Branch-and-Price 设计（合同-相位集合划分的全局认证路径）

> **状态**：v1.0 · 2026-09-06（已实现：`algos/branch_and_price.py` + `tests/test_branch_and_price.py`）；v1.0.1 · 2026-09-06 修订：树内列成本去除 3 位小数取整（取整列会使节点 LP 界偏离真值、污染剪枝与 `PROVEN_OPTIMAL` 证书语义；现在内部全程 raw 浮点，仅 `incumbent_km` 出口保留 3 位），`R2ALNS._columns` 同步改产 raw 精度列，B&P 包装器 meta 补齐热启动审计字段。
> **论文依据**：Barnhart et al. 1998 *Operations Research* 46(3):316–329（B&P 奠基，下称 **[BARN]**）；Lübbecke & Desrosiers 2005 *Operations Research* 53(6):1007–1023（列生成选题综述，下称 **[LUB]**）；Ryan & Foster 1981（集合划分分支规则，下称 **[RF]**）；Paradiso et al. 2020 *Operations Research* 68(1):180–198（**[ESF]**，精确定价能力边界，母项目已引）
> **定位**：落实 `SYSTEM_DESIGN_DOC.md` NG1 与 `SP_MATHEURISTIC_DESIGN.md` §3 登记的"全局认证路径"。SPMatheuristic 是 restrict-and-price（CG 收敛后池上一次性 IP）；本模块是**真分支定价**：分支树上每个节点用列生成解 LP 松弛。

---

## 1. 与 SPMatheuristic 的本质区别

| 维度 | SPMatheuristic（restrict-and-price） | BranchAndPrice（本模块） |
|---|---|---|
| LP 角色 | 一次性 RMP 下界 + 对偶来源 | **每个分支节点**的子树下界 |
| 分支 | 无 | y_cd（店-日指派）二分，本项目定制规则（非经典 Ryan–Foster 配对分支，见 §3 勘误） |
| 列生成 | 根部一次 | 每节点收敛一次 |
| 收敛语义 | "当前定价器找不到更好的列"（启发式） | 全树耗尽，且每个节点 LP 为 OPTIMAL、列生成未截断/停滞、完整候选集精确定价逐日 OPTIMAL → **PROVEN_OPTIMAL** |
| 解 | 池上 IP（CP-SAT 证书） | 整分节点抽取 + LP 下潜 + 原计划保底 |

## 2. 数学模型（节点 LP，合同模式，对偶语义同 `visitmodel.sp.formulation`）

$$\min \sum_r c_r x_r \quad \text{s.t.}\quad
\sum_{r\in R_d} x_r = 1\ \forall d\ (\pi_d);\quad
\sum_w z_{cw} = 1\ \forall c;\quad
\sum_{r\ni c} x_r = \sum_w f_{cw} z_{cw}\ \forall c\ (\mu_c);\quad
\sum_{r\in R_d\ni c} x_r = 1\ \forall (c,d)\in\text{forced}\ (\lambda_{cd});\quad
x_r \le z_{c,w(d)}\ \forall r\ni c$$

z 只是覆盖 RHS 线性化装置（合同模式同 formulation），**不参与分支**。

## 3. 分支规则：店-日指派分支（[BARN] §Abstract/§3、[LUB] §5.2 谱系；本项目定制规则）

> **命名勘误（2026-09-07 外部评审）**：早期文档称本规则为"Ryan-Foster 式"——不准确。经典 [RF] 是**店对配对分支**（"两店必须在同一条路线 / 不得在同一条路线"）；本项目的 y_cd forced/forbidden 是**店-日指派分支**（customer–date assignment branching），二者机制不同。y_cd 是本项目定制规则，引用 [RF] 仅作分支定价分支技术的谱系参照。

- **分支变量**：$y_{cd}=\sum_{r\in R_d\ni c} x_r$（店-日指派）。分数 $y_{cd}\in(0,1)$ → **forced(c,d)=1 | forbidden(c,d)=0**。
- **有效性**（[LUB] §5.2：禁止直接分支主问题变量 x；须落原空间决策且定价可承载）：分数 x 必给出分数 y（列含 ≥2 店）；y 全整 ⇒ x 全整。定价子问题天然承载：forbidden → 构造时跳过；forced → 起点强制 + 对偶 λ_cd 进 rc。
- **有限性**：(c,d) 对有限，每层固定一个指派。
- **z 分支的取舍**：z 的 0/1 性不独立于 x（x 整分后 z 可由覆盖行解出），分支 y 已完备且更省一层。

## 4. 定价（[ESF] 式(8) 扩展）

rc(r@d) = km(r) − Σ_{c∈r}(μ_c + λ_{c,d}) − π_d

1. **启发式**（主）：top-m 奖励贪心插入（走廊/合同合法域/节点 forbidden 硬剪；forced 店强制为起点；批量 ≤60 列/轮）。
2. **精确兜底**（收敛证明用）：CP-SAT 奖收集开链；每个日期枚举全部合同合法且未被节点 forbidden 的店，min 里程 − Σ 奖 < 0 才产列。只有每个日期子问题都返回 OPTIMAL，才计入 `converge_proven`；FEASIBLE 结果可提供列，但不能证明“无负列”。
3. **可行性恢复定价**（非对偶驱动）：forced/未覆盖店在受限池缺列时，距离贪心补列（rc 可为正）——对偶定价只产负 rc 列，无法恢复可行性；恢复失败或受限池剪枝不签全局证明。
4. **冷启动对偶退化防护**：热启动含伪对偶扰动种子列（打破“每日单列 x≡1、μ≡0”的退化）；启发式定价可用 `top_m` 截断，精确定价不得复用该截断。

## 5. 状态诚实性（沿用 SP 设计 §3 的 SCIP heuristic/exact pricer 口径）

| status | 语义 |
|---|---|
| `PROVEN_OPTIMAL` | 仅在树耗尽，且 `converge_attempts == converge_proven > 0`、所有节点 LP 返回 OPTIMAL、列生成无上限/停滞、完整精确定价逐日 OPTIMAL 时签发。对应审计计数 `lp_nonoptimal_nodes = cg_nonconverged_nodes = pricing_stalled = 0`。 |
| `BOUND_HEURISTIC` | 树耗尽但至少有一个 LP 非 OPTIMAL、列生成未收敛/停滞、或精确定价未完成/仅 FEASIBLE；这是已探索信息，不是全局证书。 |
| `TIME_LIMIT` | 预算/节点上限截断。 |

树内代价 = 插入序 km（raw 口径，与 ALNS/HGS 内部打分同待遇）；产出列由调用方按选定 TSP 重排计价后交 Contract-SP 终闸（第五闸 `check_contract` 独立复验，B&P 结果不豁免）。

## 6. 工程不变量（血泪账，全部有测试钉住）

1. **池按 (date, 店集合) 去重**（frozenset 键）：同店集不同顺序算两列会让 LP 在其上劈裂 x=0.5/0.5——y 全整、无整列可抽、不分支，节点空转。
2. **z 定义域只开 f_cw>0 的星期几**：否则覆盖等式可经 f=0 的 z 隐藏整店，LP"可行"而 check_contract 判空集违例。
3. **incumbent 抽取只在 y 全整时做**（逐日 argmax）：对分数 LP 逐日取 argmax 不保证覆盖等式（W 店覆盖不足/跨星期几分裂）。
4. **原计划保底 incumbent**：`contract_of` 由原计划反推 → 原计划必合同精确可行；nn2opt 只重排不换集合。B&P 任何情况下不返回空解。
5. **分支传播预剪枝**：forced 店单星期几 + 频次上限；forbidden 后每店剩余合法日期须够某 f>0 星期几——避免把不可行分支推给 CG 才发现。
6. **pool-IP 不变量**（测试 2）：树耗尽 + 证毕 ⇒ B&P incumbent == 池上 Contract-SP IP 最优（误差 <1e-3）。

## 7. 实测能力边界与质量验收

- 微型实例（4 店 4 日）：PROVEN_OPTIMAL 秒级，pool-IP 不变量成立。
- 中型合成（12 店 8 日，LP=6 vs 整数最优≈30+，松弛间隙大）：需数百节点，只能报 BOUND_HEURISTIC/TIME_LIMIT；这不是实现把启发式结果冒充证明，而是受限主问题松弛与搜索预算的真实边界。
- 完整线路的质量闸与证明闸分离：最终验收看 Contract-SP 选中日历的 `sp_km_recomputed < baseline_a_km`、`contract_violations == 0`、`capacity_ok == true`；`PROVEN_OPTIMAL` 只代表 B&P 全局证书，不是质量闸的替代品。
- `bp` 采用透明的 B&P + R2′ hybrid：R2′ 多种子提供可行日历/列作为 primal warm start，B&P 仍负责候选列池和最终 Contract-SP 主问题。混合路径能把高质量 primal 解交给 B&P，但不能把 R2′ 的收益宣称为纯 B&P 定价收益。
- **同等条件 10 线终账（2026-09-06，`bp+cpsat`，取代下方单 seed 09 线旧账）**：与主力格 `r2_alns+cpsat` 完全同等预算（seed=42,7,123,2026 × 每 seed R2′ 360,000 迭代 + 引擎 600s、SP 终闸 300s、单日 CP-SAT 30s、同机 Apple M2）。结果：**10/10 线与 r2_alns 格逐线相等（合计 4,144.3 → 3,603.779 km，−13.03%）**，`beats_baseline` 9/10（仅 10 线 +0.011 km 舍入级平手），全程 `contract_violations=0`、`capacity_ok=true`、池内 IP 全部 `OPTIMAL/proven`。B&P 池是 R2′ seed 列的**超集**，故不劣于主力格；相对基线的改善来自"R2′ 暖启动 + 池超集 + SP 终闸"，不得宣称为纯 B&P 定价收益。B&P 独立价值：单 seed（123）即达 −10.71%（3,700.5 km），并提供节点 LP 下界与 `BOUND_HEURISTIC/PROVEN_OPTIMAL` 诚实审计计数（真实线路上 `bp_nodes=0`：根 LP 即达暖启动值）。
- 09 线单 seed 旧账（`seed=123`，R2′ 100,000 iterations，已被上行同等条件终账取代）：`sp_km_recomputed = 318.244`，baseline=`326.600`，改进 `-2.559%`；Contract-SP=`OPTIMAL`，`contract_violations=0`，`capacity_ok=true`，B&P 状态 `BOUND_HEURISTIC`（`bp_nodes=0`）。
- TSP 因子必须随结果一起报告：09 线相同日历在 `nn2opt` 口径下可能不优于 baseline；当前已用 CP-SAT 路线口径验证 B&P 混合方案的质量，不隐藏路线求解器差异。
- 节点 LP 不可行、LP 非 OPTIMAL、列生成未收敛或精确定价未完成时，只能记录审计计数并降级为 `BOUND_HEURISTIC`/`TIME_LIMIT`；不可行结论不签名 `PROVEN_*`。

## 8. 实验接线

`experiments/run_contract_matrix.py` 的 `bp` 模式使用 R2′ 生成可行暖启动日历，B&P 接收 `initial_days` 与 `initial_pool`，再由选定 TSP 重排并交 Contract-SP 终闸。矩阵目录为 `output/contract_matrix_4x3/`。关键元数据：`bp_seed_generator / bp_seed_km_internal / bp_seed_iterations / bp_seed_accepted / bp_status / bp_incumbent_km_internal / bp_root_lb / bp_nodes / bp_cg_iters / bp_converge_(attempts|proven) / bp_propagate_prunes / bp_lp_nonoptimal_nodes / bp_cg_nonconverged_nodes / bp_pricing_stalled / bp_warm_start_schedule_count / bp_warm_start_columns / bp_initial_pool_count / beats_baseline`.
