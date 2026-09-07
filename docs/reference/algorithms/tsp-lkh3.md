# LKH-3 开放路径（lkh3）

> 类别：启发式（大规模Lin-Kernighan） | 实现：`algos/lkh_engine.py`（外部二进制封装） | 矩阵身份：大规模备用档

## 它解决什么

大规模 TSP 的工业级启发式：Lin-Kernighan 变邻域搜索 + 5-move + patching。本系统的定位是 **lkh3 备用档**——cpsat 在大 n 下证不出最优时的兜底（研究矩阵速度剖面的规模档）。

## 机制（正确的用法，来自 LKH-3 文档）

```
ATSP + EXPLICIT FULL_MATRIX：LKH 对 TSP 只读下三角 → 必须用 ATSP 类型
开放路径：加 dummy 节点，边权 = 大常数 C = 10×max(D)
          解闭圈后从 dummy 处剥离 → 得开放路径
参数：RUNS=10, MAX_TRIALS=5000, MAX_CANDIDATES=20, MOVE_TYPE=5, PATCHING_A=2
回退：无 LKH 二进制（LKH_BIN 环境变量，默认 /tmp/LKH-3.0.14/LKH）、
      超时、无 tour 输出 → NN+2opt 兜底，状态记 LKH_FALLBACK_NN2OPT（不冒充 LKH）
```

## 复杂度与预算

- `time_limit` 参数化（矩阵口径 5s/日；240s 封装默认）；外部子进程 + 15s 宽限。
- 实测：显式路网矩阵上曾劣于 CP-SAT（09 线 23 店：LKH 17.4 vs CP-SAT 14.03 km）——**非对称/不规则矩阵是 LKH 的弱项**，大规模与欧氏实例才是它的主场。

## 已知边界与陷阱

1. 外部二进制依赖：部署需自带 LKH 可执行（许可自由用于研究）；缺失自动回退但状态必须如实标。
2. 结果是启发式：无 OPTIMAL 状态，报告不得写"已证最优"。
3. FULL_MATRIX 读三角的坑：误用对称 TSP 类型会静默走样——封装已按文档处理，改动前读 `LKH-3_PARAMETERS.pdf`。

## 引用论文

- Helsgaun (2000)：LKH 原始文献（EJOR 112(1)）。
- Helsgaun (2017)：LKH-3 技术报告（Roskilde University；含参数文档 LKH-3_PARAMETERS.pdf）。

## 相关文件与测试

- `algos/lkh_engine.py`；矩阵接入：`route_with_tsp(mode="lkh3", args)`（`lkh_timeout`）
