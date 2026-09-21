# SP 数学规范 (Mathematical Specification)
## 集合划分主问题 · R2′ 线性化 · 开链 TSP · 多目标

> **Document Status**: v1.0 (2026-09-21, Phase C)
> **对照实现**: VisitModel `src/visitmodel/sp/formulation.py` · `src/visitmodel/tsp/open_chain.py`
> **上层文档**: THREE_LAYER_ARCHITECTURE_v0.2.md (§4 模型层) · CONTRACT_CADENCE_MODEL.md (语义真值)
> **风格基准**: Google MathOpt / MiniZinc — model 与 solver 分离, 数据实例与求解运行时分离

---

## 1. 集合划分主问题 (SP Master)

### 1.1 集合与参数

| 符号 | 含义 | 来源 (L1 语义规格) |
|---|---|---|
| $C$ | 客户集 | `instance.customers` |
| $T$ | 工作日集 | `instance.workdays` |
| $T_d$ | 日 $d$ 的星期几 | 日历 |
| $f_c$ | 客户 $c$ 的月拜访义务 | `required_visits[c]` ← 合同派生 |
| $R_d$ | 日 $d$ 的候选列 (路线) 集合 | L3 列池 |
| $c_r$ | 列 $r$ 的成本 (路线里程) | 距离矩阵 + L3 路由 |
| $a_{cr}$ | 客户 $c$ 是否在列 $r$ 中 | 列结构 |
| $[K_{\min}, K_{\max}]$ | 日店数走廊 | `day_corridor` ← 走廊策略 |

### 1.2 决策变量

$$x_r \in \{0,1\} \quad \forall r \in R$$

选列 = 该列的 (日期, 有序路线) 被采纳。R2′ 模式追加:

$$z_{cw} \in \{0,1\} \quad \forall c \in C,\ w \in \{0..4\}, \quad \sum_w z_{cw} = 1$$

($z$ = 客户 $c$ 的星期几选择; 实现: `formulation._z_open` 按槽位数预剪枝)

### 1.3 约束 (与 SourceMap 一一对应)

| ID | 数学形式 | 语义 (L1 规则) | 实现锚点 |
|---|---|---|---|
| **C1_COVER_DAY** | $\sum_{r \in R_d} x_r = 1 \quad \forall d \in T$ | 每工作日恰选一列 | `sp_solve_lp/ip` |
| **C1_OBLIGATION** | $\sum_{r: a_{cr}=1} x_r = f_c \quad \forall c$ | 义务守恒 | 同上 |
| **C2_CORRIDOR** | $K_{\min} \le |r| \le K_{\max} \quad \forall r$ | 走廊(列空间内生) | `dedupe_pool` + `_contract_pool_filter` |
| **C3_R2PRIME** | $x_r \le z_{c,\mathrm{wd}(r)} \quad \forall c, r \ni c$ | 列绑定星期几选择 | `_z_open` 线性化 |
| **C4_POOL_LEGAL** | $a_{cd}=1 \Rightarrow d \in L_c$ | 列成员合法性 | `_contract_pool_filter(pool, legal)` |

其中 $L_c$ = 客户 $c$ 的合法日期集(R2′ 定价用**超集**: W → 全月; B(φ) → 相位匹配日;由 L1 `contract_of`/`legal_date_map` 语义编译)。

### 1.4 目标

$$\min \sum_{r \in R} c_r x_r$$

多目标扩展见 §4。

---

## 2. 对偶与定价 (L3 列生成循环)

受限主问题 LP (`sp_solve_lp`, GLOP) 的对偶价:

- 日覆盖约束对偶 $\pi_d$ (C1_COVER_DAY)
- 义务约束对偶 $\mu_c$ (C1_OBLIGATION)

**简约成本** (`pricing.price_columns`):

$$\bar{c}_r = c_r - \pi_{d(r)} - \sum_{c \in r} \mu_c$$

负约简成本列回灌池,直到:(a) 连续 3 轮无下降;或 (b) 无新列。
认证口径:启发式定价 ⇒ 只输出 `rmp_lp` 与池内差距 `pool_gap_pct`,`is_global_certified ≡ False`(评审 P1-1)。

**L3 归属注**:`column_generate` 循环属 Layer 3(母项目 `algos/sp_matheuristic.py`);公式构建属 Layer 2(本仓)。循环本身不得接触合同语义——它需要的 $L_c$ 应来自 `VisitPlanningInstance.eligible_days`(见 §6 迁移注)。

---

## 3. 开链 TSP (日内排序)

日 $d$ 被选中的门店序列 $S_d$ 的里程:

$$\mathrm{km}(S_d) = \sum_{k=0}^{|S_d|-2} D[s_k, s_{k+1}]$$

(开链:无回 Depot 边; depot→首店与末店→返程在里程口径 `closed=False` 下不计)

精确解:CP-SAT MTZ/流式开链公式 (`open_chain._exact_open_tsp_status`),近似:`NN+2opt` (`opticore.heuristics`)。
**已知债 (Phase D)**:`num_search_workers=8` + 墙钟时限 ⇒ 同种子不可逐位复现;确定性重放需 `max_deterministic_time` 模式。

---

## 4. 多目标 (Pareto / 词典序)

`SemanticObjectivePolicy` (L1 定义含义) → `ObjectiveTerm` 向量 (L2 翻译):

| 优先级 | metric | 数学含义 | policy 字段 |
|---|---|---|---|
| 1 | `total_distance` | $\sum_d \mathrm{km}(S_d)$ | `distance` |
| 2 | `daily_count_range` | $\max_d |S_d| - \min_d |S_d|$ | `workload_balance` |
| 3 | `change_count` | $\sum_c \mathbb{1}[\sigma_c \ne \sigma_c^{orig}]$ | `plan_stability` |

词典序模式 (`preference_mode=lexicographic`):按 priority 依次最小化,前级允许劣化阈值由 L3 配置。
Pareto 模式:输出非支配前沿,不做标量化(L3 `mo_alns` 前沿搜索)。
**禁令**:多目标结果坍缩成单 float 标量是 v0.1 教训——`SolveResult.objective_vector` 恒为向量。

---

## 5. 决策留痕 (Decision Episode)

每次求解落最小 envelope (`visit_math_api.DecisionEpisode`):

```
episode_id · source_snapshot_id · semantic_spec_{version,hash} · instance_hash
solver_{backend,version,config_hash} · seed · solution_id · status · termination_reason
exception_grant_ids · decision_timestamp
```

组装:Orchestrator `emit_episode()`;指纹 `episode_hash()` 不含 id/时间戳——**同一决策重放同哈希** (G4)。

---

## 6. 模块归属与遗留迁移注

| 模块 | 层 | 归属状态 |
|---|---|---|
| `visitmodel/sp/formulation.py` (sp_solve_lp/ip, _z_open, _contract_pool_filter, _fw_table, linkage v2) | **L2** | ✓ 已在 VisitModel 仓 |
| `visitmodel/sp/pricing.py` (price_columns) | L3-辅助 (定价属搜索) | 物理在 L2 仓,Phase D 评估迁 L3 |
| `algos/sp_matheuristic.py` (column_generate, SPMatheuristic, SA 改进循环) | **L3** | ✓ 母项目 |
| `algos/tsp_engine.py` → `visitmodel/tsp/open_chain.py` | L2(公式)+ L3(引擎选择) | ✓ 拆分完成 |

**遗留违例 (Phase D 清单)**:
1. `visitmodel/sp/formulation.py` 顶部 `from visit_ir.contract import legal_date_map` — L2 import L1 实现。应改为:`contract_view` 翻译在 L1 完成,`legal`/`fw` 作为 VisitPlanningInstance 附属传入;formulation 全签名去 `contract=` 化(被 `test_mathmodel_sp_contract` 钉死,属引擎手术)。
2. `algos/sp_matheuristic.py` `from core.contract import legal_date_map, check_contract` — L3 import L1(棘轮已冻结)。应改为接收 instance 的 eligible_days 与 MathValidator 结论。
3. `LineData.__post_init__` 走廊静默推导 — 新链路经 `orchestration.compile_line_spec` 已绕行;退役评估:待 Phase D 将 `svc`/`experiments` 调用面迁 `compile_line_spec` 后删除推导,LineData 保留为 L3 内部载体(索引空间)。

---

## 7. 验收锚点 (2026-09-21 实测)

| 线 | 店数 | 合同构成 | 走廊 | 义务Σ | 原计划独立验解 |
|---|---|---|---|---|---|
| 02 | 172 | 全 W | [33,36] | 791 | OK |
| 03 | 118 | 全 W | [17,34] | 531 | OK |
| 09 | 163 | 137W+26B | [23,35] | 686 | OK |

全链:`LineData → line_data_facts → SemanticCompiler (零例外闸) → MathCompiler → MathValidator`,原计划三线全 OK——义务/合法日期/走廊全守恒。
