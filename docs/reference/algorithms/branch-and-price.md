# Branch-and-Price（分支定价，bp）

> 类别：精确框架（当前实现为未完成态：启发式 oracle） | 实现：`algos/branch_and_price.py` | 矩阵身份：证书画像

## 它解决什么

SP+CG（上一节）收敛后只解决"当前池里选最优"；bp 在**分支树上**搜索：每个树节点用列生成求解 LP 松弛，分数解按 Ryan-Foster 规则分支，直到树耗尽——理论上可签发**全局最优证书**。它与其他引擎不同类：价值在**界与证书**，不在 km 改写。

> 详细设计（数学模型/状态语义/工程不变量/同等预算终账）：`docs/design/BRANCH_AND_PRICE_DESIGN.md`——本文只给接手者速览。

## 数学模型

- 主问题（节点级）：min Σ c_r x_r，s.t. 日期覆盖（对偶 π_d）、Σ_w z_cw=1、合同覆盖 = Σ f·z（对偶 μ_c）、forced 行 Σ_{r∈R_d∋c} x_r = 1（对偶 λ_cd）、x ≤ z 绑定。
- **分支变量 y_cd = Σ_{r∈R_d∋c} x_r ∈ (0,1)** → forced(c,d)=1 | forbidden(c,d)=0。分数 x 必给出分数 y；y 全整 ⇒ x 全整 → incumbent。z 的整分性由 x≤z 绑定蕴含，不分支。
- 定价：`rc(r@d) = km(r) − Σ_{c∈r}(μ_c + λ_{c,d}) − π_d`，与 `sp_solve_lp` 对偶语义同构。

## 定价三路（oracle = 框架的命门）

1. **启发式**：top-m 对偶奖励贪心插入（走廊/合法域/forbidden 硬剪；批量 ≤60 列/轮）。
2. **精确兜底**：CP-SAT 奖收集开链（AddCircuit + dummy depot + 自环可选）；**完整候选集**（证明"无负列"必须全枚举，不得截断）；仅全日期 OPTIMAL 才计入 `converge_proven`。
3. **可行性恢复**：forced/未覆盖店在受限池缺列时距离贪心补列（rc 可为正）——对偶定价只产负 rc 列。

## 状态诚实性

| status | 条件 |
|---|---|
| `PROVEN_OPTIMAL` | 树耗尽 + `converge_attempts == converge_proven > 0` + 所有节点 LP OPTIMAL + 列生成无上限/停滞 + 精确定价逐日 OPTIMAL（审计计数全零） |
| `BOUND_HEURISTIC` | 树耗尽但至少一项证书不完整（已探索信息，非全局证书） |
| `TIME_LIMIT` | 预算/节点上限截断 |

实测：微型实例（4 店 4 日）PROVEN_OPTIMAL 秒级、pool-IP 不变量成立；真实线路（163-190 店）`exact_tl=1s` 证不完 → BOUND_HEURISTIC、`bp_nodes=0`（根 LP 即达暖启动值）。**oracle 升级（ESPPRC）是 bp 身份成立的生命线。**

## 工程不变量（测试钉住）

1. 池按 `(date, 店集)` frozenset 去重——同店集不同顺序会让 LP 在其上劈裂 x=0.5/0.5，节点空转。
2. z 定义域只开 f_cw>0 的星期几（防 f=0 隐藏整店）。
3. incumbent 只在 y 全整时逐日 argmax 抽取。
4. 原计划保底：`contract_of` 反推原计划必合法 → 任何情况不返回空解。
5. 分支传播预剪枝：forced 单星期几 + 频次上限；forbidden 后每店剩余合法日期须够某 f>0 星期几。
6. **树内成本 raw 浮点**（v1.0.1 修复：取整列使节点 LP 界偏离真值、污染剪枝与证书）。

## 热启动接口（独立性注意）

`initial_days` / `initial_pool` 可注入外部列（生产 hybrid：R2′ 供列）。**研究矩阵中 bp_solo 禁止接收 R2 产物**（§禁止隐藏组合）——自足模式用自身 `_calendar_search/_randomized_schedule` 热启动。

## 引用论文

- Barnhart et al. (1998)：B&P 框架奠基本文。
- Ryan & Foster (1981)：集合划分分支规则（y_cd 的出处）。
- Lübbecke & Desrosiers (2005)：列生成综述。
- Feillet et al. (2004)：ESPPRC（精确定价 oracle 的目标形态）。
- Paradiso et al. (2020)（[ESF]）：精确定价能力边界。
- Rothenbächer, Drexl, Irnich (2019)：PVRP 柔性日程 B&P&C（同问题类的精确先行者）。

## 相关文件与测试

- `algos/branch_and_price.py`（820 行）；`tests/test_branch_and_price.py`（PROVEN 路径、pool-IP 不变量、合同/走廊有效性、热启动字段）
- 实验接线：`experiments/run_contract_matrix.py` bp 模式（`initial_days`+`initial_pool`）
