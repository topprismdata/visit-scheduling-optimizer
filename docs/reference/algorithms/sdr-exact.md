# SDR Exact（多起点顺序采样 + 集合划分 + 线性规划下界，旧代）

> 类别：构造式 + 线性规划（LP，Linear Programming）（上一代组合层算法） | 实现：`algos/sdr_exact.py` | 矩阵身份：已退役，思想降级保留

## 它解决什么（历史定位）

上一代的"顺序多样化 + 组合"方案：固定原日历不动，在同一天的店集合上用**多起点启发式**生成大量不同顺序（每日期 ~60 条），再用 CP-SAT 集合划分选组合，最后 GLOP LP 松弛给下界与 gap。

```
阶段1 _gen_pool: 原计划 + NN2opt + 多起点随机 NN2opt + 2opt 扰动 → RoutePool(每日期 ≥K 条)
阶段2 _sp_solve: CP-SAT SP（每日期选 1 条；每店覆盖 = freq；无合同/R2′ 闸）
阶段3 _lp_lb:    GLOP 线性规划（LP）松弛 → **池 LP 值 → 池内 gap（pool_gap_pct）**——不是全局下界（LB 术语收口，2026-09-07）
```

## 为什么降级（v3 协议裁定）

1. **日历=原分配不动** → 它的上限就是 base 格（CP-SAT 日内排序已最优，60 条采样全被支配）——独立格必然与 base 打平（实测 sdr/ensemble 0.9s 提前收敛、gap=0）。
2. **阶段2 老 SP** 无合同/R2′ 闸，被统一 Contract-SP 终闸取代。
3. **阶段3 LP 下界** 被 sp_cg 覆盖（更强的对偶驱动 CG）。

## 思想遗产（去哪儿了）

- **多起点采样** → TSP 档位谱中的策略行 `multistart_nn2opt`（"穷人版精确 TSP"：质量介于单起 nn2opt 与 cpsat 之间，速度居中——速度剖面的一个点）。
- **大池 + SP + LP gap** 的框架 → 由 sp_cg（对偶驱动）与 bp（分支+证书）继承。

## 引用论文

- Pessoa et al. (2020)：列枚举+分支切割的现代参照（SDR 自我标榜的参照系）。
- Villegas et al. (2025)：SP/SC matheuristic 元分析。

## 相关文件与测试

- `algos/sdr_exact.py`；`core/route_pool.py`（RoutePool/Route）
- 台账痕迹：PERFORMANCE_BENCHMARK.md（sdr 0.9s 提前收敛）、ALGORITHM_GUIDE 附录 C（历史口径警示）
