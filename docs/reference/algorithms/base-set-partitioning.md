# base + Contract-SP 集合划分终闸

> 类别：构造式基准 + 精确组合 | 实现：`experiments/run_contract_matrix.py`（base_schedule）、`VisitModel/src/visitmodel/sp/formulation.py`（`sp_solve_lp` / `sp_solve_ip`）

## 它解决什么

集合划分（Set Partitioning, SP）是**整个系统的终点站**：所有算法的本质都是"给 SP 供候选列"（每列 = 某日期的一条完整候选路线 `(date, route, km)`），SP 从池里挑出最终组合。`base` 格则是参照系：不搜索，只把原计划按共同规则排序，回答"业务现状的天花板在哪"。

## 数学模型

```
min  Σ_r km_r · x_r
s.t. Σ_{r∈R_d} x_r = 1                    ∀ 工作日 d      （每天恰好一条路线）
     Σ_{r∋c} x_r = Σ_w f_cw · z_cw        ∀ 店 c          （合同覆盖 RHS 线性化）
     Σ_w z_cw = 1                          ∀ c            （R2′：整店唯一星期几）
     x_r ≤ z_{c, wd(r)}                    ∀ 列 r、∀ c∈r   （列绑定星期几）
     x ∈ {0,1}, z ∈ [0,1]
```

- **合同模式**：池先经 `_contract_pool_filter` 剔除任何 (店,日期) 非法成员列。
- **R2′ 语义**（星期几一致）：店可整月换星期几，但换后全月一致；禁止同店跨星期几分裂。
- 走廊：`min_daily ≤ |route| ≤ max_daily` 在池过滤与定价两处截断（店数口径的负荷代理，非工时证明）。

## 输入 / 输出

- 输入：候选列池 `[(date, route, km)]`、合同表、日期集、走廊。
- 输出：`pipeline_result`（选中日历）+ 证书字段（`solver_status`、`optimality_proven`、`objective/best_bound` 毫单位）。
- 调用方独立复验三闸：`check_freq` / `check_capacity` / `check_contract`（算法自报不算数）。

## 机制要点（血泪账）

1. **z 定义域只开 f_cw>0 的星期几**：否则覆盖等式可经 f=0 的 z 隐藏整店，LP"可行"而 `check_contract` 判空集违例。
2. **池过滤后零合法列的义务店 = 不可行**（返回 None），不是可跳过的约束——修复前曾静默缺店。
3. **LP 对偶语义**（π_d 日期行 / μ_c 店覆盖行 / λ_cd forced 行）与 bp、price_columns 全线一致，是列生成的供列方向来源。
4. **诚实口径**：启发式供列 ⇒ 只输出 RMP LP 值与池内差距 `pool_gap_pct`，`is_global_certified` 恒 False；整数目标（毫单位）与距离重算分开记录，禁止跨口径拼 gap。

## 复杂度与预算

- IP 用 CP-SAT：实测 10 线 67~1449 列池全部**亚秒级** `OPTIMAL`（0.018–0.229s，如 09 线 0.031s）。
- LP 用 GLOP：供列生成对偶，30s 上限。

## 引用论文

- Balinski & Quandt (1964)：SP 用于配送问题的开山建模。
- Barnhart et al. (1998)：分支定价框架（SP 作为受限主问题的标准范式）。
- Pessoa et al. (2020)：当代精确 VRP 求解器架构（本系统"完整版"参照系）。

## 相关文件与测试

- `visitmodel/sp/formulation.py`（公式构建器，外迁自母仓）
- `visitmodel/sp/pricing.py`（`price_columns` 对偶定价）
- `tests/test_mathmodel_sp_contract.py`（含"零合法列=不可行"反例）
- 设计文档：`docs/design/SP_MATHEURISTIC_DESIGN.md`、`docs/design/BRANCH_AND_PRICE_DESIGN.md`
