# 概念：集合划分与 Contract-SP 终闸（Set Partitioning & Final Gate）

> 类别：横切概念——**所有算法文档都引用本页**。实现：`VisitModel/src/visitmodel/sp/formulation.py`（`sp_solve_lp` / `sp_solve_ip`）

## 一句话

集合划分（SP，Set Partitioning）是**计划期（月度）日历体系内唯一拥有决策权的终点站**：它不生产任何东西——池里有什么候选路线（列），它才能从中挑出最终拜访计划。所有日历/组合层"算法"的本质都是给 SP 供列。范围限定：顺序层 TSP 与在途插单工具在其各自范围内做局部决策，不做跨日合同决策。

## 数学模型

```
min  Σ_r km_r · x_r
s.t. Σ_{r∈R_d} x_r = 1                    ∀ 工作日 d      （每个工作日恰好选一条候选路线）
     Σ_{r∋c} x_r = Σ_w f_cw · z_cw        ∀ 店 c          （合同覆盖：每店被访次数 = 合同频次）
     Σ_w z_cw = 1                          ∀ c            （R2′：整店唯一星期几，z 是选择器）
     x_r ≤ z_{c, wd(r)}                    ∀ 列 r、∀ c∈r   （列绑定星期几：用了周一的列，z 才能选周一）
     x ∈ {0,1}, z ∈ [0,1]
```

- **一列（column）= `(date, route, km)`**：某日期的一条完整候选路线。
- **z 是覆盖线性化装置**（不参与分支）：x 整分后 z 可由覆盖行解出。
- **走廊**：`min_daily ≤ |route| ≤ max_daily`——店数口径的负荷代理（非工时证明），在池过滤与定价两处生效。

## 终闸语义（为什么叫"终闸"）

1. **算法不决策**：任何引擎（r2/alns/hgs/bp…）的产出只是候选列；最终日历由 `sp_solve_ip`（CP-SAT 整数求解，`r2_prime=True` + `contract` 硬约束）统一选出。
2. **独立复验**：选中日历必须过三闸——频次（`check_freq`）、容量（`check_capacity`）、合同（`check_contract`）——由调用方复验，算法自报不算数。
3. **诚实口径**：供列是启发式 ⇒ 只输出受限主问题（RMP，Restricted Master Problem）的 LP 值与池内差距 `pool_gap_pct`，`is_global_certified` 恒 False。SP 池内最优 ≠ 全局日历最优。

> **⚠ 已知表述缺口（2026-09-07 外部评审，P0 待 VisitModel vNext 重构）**：上式的 `x_r ≤ z_{c,wd(r)}` 是**列特定行**——新增一条候选列会同时新增若干绑定行，行空间不固定，因此现行"LP → 按对偶定价"不是标准的固定行空间列生成；且定价 rc 公式未计入绑定行对偶，二者不闭合。重构方向：引入固定 (店,日期) 空间的链接变量 y_cd = Σ x_r，把合同/R2′ 约束全部放进固定行空间。重构完成前，本页描述的"CG 收敛/下界"语义按下方诚实口径打折理解。

## 机制要点（血泪账，全部有测试钉住）

1. **z 定义域只开 f_cw>0 的星期几**：否则覆盖等式可经 f=0 的 z 隐藏整店——LP"可行"而 `check_contract` 判空集违例。
2. **池过滤后零合法列的义务店 = 不可行**（返回 None），不是可跳过的约束——修复前曾静默缺店。
3. **对偶语义**（π_d 日期行 / μ_c 店覆盖行 / λ_cd forced 行）与列生成定价、B&P 节点 LP 全线同构——见概念文档 [column-generation.md](column-generation.md)。
4. **整数目标（毫单位）与距离重算分开记录**，禁止跨口径拼 gap。

## 复杂度

- 整数求解（CP-SAT）：10 条真实线 67~1449 列池全部亚秒级 OPTIMAL（0.018–0.229s）。
- LP 松弛（GLOP）：供对偶用，30s 上限。

## 引用论文

- Balinski & Quandt (1964)：SP 用于配送问题的开山建模。
- Barnhart et al. (1998)：SP 作为受限主问题的标准范式（分支定价）。
- Pessoa et al. (2020)：当代精确 VRP 求解器架构（本系统"完整版"参照系）。

## 相关文件与测试

- `VisitModel/src/visitmodel/sp/formulation.py`、`visitmodel/sp/pricing.py`
- `tests/test_mathmodel_sp_contract.py`（"零合法列=不可行"反例、合同池过滤）
- 设计：`docs/design/SP_MATHEURISTIC_DESIGN.md`
