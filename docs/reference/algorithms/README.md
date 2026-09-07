# 算法参考资料索引（Reference: Algorithms）

> **用途**：新接手项目的工程师/AI 从这里进入。每个在用算法一份说明文档：定位、输入输出、机制、复杂度、已知陷阱、引用论文。
> **阅读顺序建议**：先读本文与《两层架构》（base-set-partitioning.md），再按你接手的模块挑对应文档。
> **协议背景**：算法研究对比协议见 `docs/design/MATRIX_PROTOCOL_V3_DESIGN.md`（v0.3）；生产选型快筛见 `contract_matrix_cell/v2`。

## 文档清单

| 文档 | 算法/组件 | 类别 | 层 |
|---|---|---|---|
| [base-set-partitioning.md](base-set-partitioning.md) | base 构造式基准 + Contract-SP 集合划分终闸 | 构造式 / 精确组合 | 组合层（终点站） |
| [r2-alns.md](r2-alns.md) | R2′-ALNS（合同同构局部搜索） | 元启发式 | 日历层 |
| [alns-v3.md](alns-v3.md) | ALNS v3（反馈耦合自适应大邻域搜索） | 元启发式 | 日历+顺序 |
| [hgs-pvrp.md](hgs-pvrp.md) | HGS-PVRP（混合遗传搜索） | 元启发式（种群） | 日历+顺序 |
| [sp-cg.md](sp-cg.md) | SP + 列生成（对偶驱动供列） | 精确 LP 框架 | 组合层 |
| [branch-and-price.md](branch-and-price.md) | Branch-and-Price（分支定价） | 精确框架（未完成态） | 组合层 |
| [sdr-exact.md](sdr-exact.md) | SDR Exact（多起点采样+SP+LP 下界） | 构造式+LP | 组合层（旧代） |
| [alns-v4-pareto.md](alns-v4-pareto.md) | ALNS v4（稳定化/帕累托精修器） | 元启发式（增量重优化） | 微调层 |
| [tsp-heuristics.md](tsp-heuristics.md) | NN+2-opt、多起点采样 | 启发式 | 顺序层 |
| [tsp-cpsat.md](tsp-cpsat.md) | CP-SAT 开链精确 TSP | 精确（CP） | 顺序层 |
| [tsp-lkh3.md](tsp-lkh3.md) | LKH-3 开放路径 | 启发式（大规模） | 顺序层 |
| [corridor-insertion.md](corridor-insertion.md) | 走廊投影动态插单工具 | 动态重优化 | 在途层 |
| [clustered-tsp.md](clustered-tsp.md) | Clustered TSP（已评估→否决） | 构造式 | 顺序层 |

## 全局事实速记（写代码前必读）

1. **SP 是终点站**：所有算法的本质都是"给 Contract-SP 供候选列"，最终解由 `sp_solve_ip`（r2_prime+contract）统一选出。算法不决策。
2. **独立性是来源隔离**：引擎之间不允许隐式共享运行产物（日历/列/对偶/incumbent）；共享的是公共数学工具、估计器与原始数据。
3. **双尺子**：元启发式量 km 画像；bp 量证书画像（gap/证完率）。不同类别不同尺。
4. **确定性红线**：搜索期零求解器调用（seeded RNG）；终局精排只接受 PROVEN OPTIMAL 的重排。
5. **诚实口径**：km 分 raw/rounded、pool/recomputed；状态三档 PROVEN_OPTIMAL / BOUND_HEURISTIC / TIME_LIMIT；三闸（count/capacity/contract）由调用方独立复验。

## 引用论文总表（按主题）

### 集合划分与列生成
- Balinski, M. L., Quandt, R. E. (1964). *On an integer program for a delivery problem*. Operations Research 12(1).
- Desrochers, M., Desrosiers, J., Solomon, M. (1992). *A new optimization algorithm for the vehicle routing problem with time windows*. Operations Research 40(2):342–354.
- Barnhart, C., Johnson, E. L., Nemhauser, G. L., Savelsbergh, M. W. P., Vance, P. H. (1998). *Branch-and-price: Column generation for solving huge integer programs*. Operations Research 46(3):316–329.
- Lübbecke, M., Desrosiers, J. (2005). *Selected topics in column generation*. Operations Research 53(6):1007–1023.
- Pessoa, A., Sadykov, R., Uchoa, E., Vanderbeck, F. (2020). *A generic exact solver for vehicle routing and related problems*. Mathematical Programming 183:483–523.

### 分支定价与精确定价
- Ryan, D. M., Foster, B. A. (1981). *An integer programming approach to scheduling*. In Computer Scheduling of Public Transport.
- Feillet, D., Dejax, P., Gendreau, M., Gueguen, C. (2004). *An exact algorithm for the elementary shortest path problem with resource constraints*. Transportation Science 38(3):299–316.（ESPPRC）
- Paradiso, R. et al. (2020). Operations Research 68(1).（精确定价能力边界，[ESF]）

### 周期性 VRP 与一致性
- Christofides, N., Beasley, J. E. (1981). *The periodic routing problem*. Networks 11(2).
- Cordeau, J.-F., Gendreau, M., Laporte, G. (1997). *A tabu search heuristic for periodic and multi-depot vehicle routing problems*. Networks 30(2).
- Rothenbächer, A. K., Drexl, M., Irnich, S. (2019). *Branch-and-price-and-cut for the periodic vehicle routing problem with flexible schedule structures*. Transportation Science 53(5).
- Groër, C., Golden, B., Wasil, E. (2009). *The consistent vehicle routing problem*. Transportation Science.

### 元启发式
- Ropke, S., Pisinger, D. (2006). *An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows*. Transportation Science 40(4):455–472.
- Pisinger, D., Ropke, S. (2010). *A general heuristic for vehicle routing problems*. Computers & Operations Research 37(3):516–534.
- Shaw, P. (1998). *Using constraint programming and local search methods to solve vehicle routing problems*. CP'98, LNCS 1520.
- Vidal, T., Crainic, T. G., Gendreau, M., Lahrichi, N., Rei, W. (2012). *A hybrid genetic algorithm with adaptive diversity management for a large class of vehicle routing problems with time-windows*. Computers & Operations Research 40(1):137–150.
- Vidal, T. (2022). *Hybrid genetic search for the CVRP: An open-source implementation*. Transportation Science.
- Kirkpatrick, S., Gelatt, C. D., Vecchi, M. P. (1983). *Optimization by simulated annealing*. Science 220(4598):671–680.
- Ritzinger, U., Puchinger, J., Hartl, R. F. (2016). *A survey on dynamic and stochastic vehicle routing problems*. International Journal of Production Research 54(1).

### TSP 与路线
- Croes, G. A. (1958). *A method for solving traveling-salesman problems*. Operations Research 6(6):791–812.（2-opt）
- Rosenkrantz, D. J., Stearns, R. E., Lewis, P. M. (1977). *An analysis of several heuristics for the traveling salesman problem*. SIAM Journal on Computing 6(3).（NN 启发式）
- Helsgaun, K. (2000). *An effective implementation of the Lin–Kernighan traveling salesman heuristic*. European Journal of Operational Research 112(1):106–130.
- Helsgaun, K. (2017). *LKH-3 version 2.0*（技术报告，Roskilde University）。
- Cook, W., Held, M., Helsgaun, K. (2024). *Constrained local search for last-mile routing*. Transportation Science 58(1).（Amazon last-mile）
- Pillac, V., Gendreau, M., Guéret, C., Medaglia, A. L. (2013). *A review of dynamic vehicle routing problems*. European Journal of Operational Research 225(1):1–11.

### 软件
- Google OR-Tools（CP-SAT 求解器、AddCircuit 约束）：https://developers.google.com/optimization
- LKH-3：http://webhotel4.ruc.dk/~keld/research/LKH-3/

> 卷期页码以出版方页面为准；本表只列确证存在的文献。

## 引用规范（本项目惯例）

- 正文引用格式：`[作者 年份]`，如 `[BARN]`=Barnhart 1998、`[ESF]`=Paradiso 2020。
- km 双口径：`raw`（内部计算）vs `rounded`（对外 3 位小数）；池列成本 vs 重算成本分开记录。
- 状态语义：`PROVEN_OPTIMAL` 仅在完整证书条件满足时签发（见 branch-and-price.md §状态）。
