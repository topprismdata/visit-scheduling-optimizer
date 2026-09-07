# TSP 启发式（NN + 2-opt，含多起点采样）

> 类别：启发式 | 实现：`OptiCore/src/opticore/heuristics.py`（`nn2opt_open / two_opt`），母仓经 `algos/tsp_engine.py` re-export | 矩阵身份：速度剖面基线档

## 它解决什么

顺序层（Layer2）的快速档：给定当天店集合，产出一条较短开放路径（无仓库往返，头尾不闭合）。也是所有上层算法的**估价器底座**（R2′/v3/v4 的 2-NN 三角估计与 NN 链估价同一思想体系）。

## 机制

```
NN（最近邻）：从最小店号出发，每步去最近的未访问店（平局按 id 升序 → 确定性）
2-opt（Croes 1958）：反复撤销"交叉边对" (a,b) 反转子段，直到无改进（≤30 轮）
nn2opt_open = NN 链 + 2-opt 收敛
multistart：多起点重复采样，取最优（SDR 思想——"穷人版精确 TSP"，
            质量介于单起 nn2opt 与 cpsat 之间，速度居中）
```

- 确定性：距离平局按店号升序；纯函数、无求解器调用。

## 复杂度与预算

- NN O(n²)；2-opt 每轮 O(n²)；n=35 实测毫秒级。速度画像的基线点。

## 已知边界与陷阱

1. **无质量保证**：实测 nn2opt 口径全线 +11~16% km vs CP-SAT（TSP 因子主导的证据）——它决定"快"，CP-SAT 决定"准"。
2. 开放路径（不回起点）：不要用闭合 TSP 例程直接套。
3. 作估价器时是**近似**（2-NN 三角恒等式 vs 真 TSP 路径），只用于相对比较；绝对值以精确重算为准。

## 引用论文

- Croes (1958)：2-opt 原始文献。
- Rosenkrantz, Stearns, Lewis (1977)：NN 启发式与近似比分析。
- SDR 多起点思想：见 sdr-exact.md。

## 相关文件与测试

- `OptiCore/src/opticore/heuristics.py`；`VisitModel/src/visitmodel/tsp/open_chain.py`（同池引擎注册）
- `algos/tsp_engine.py`（兼容 re-export shim）
