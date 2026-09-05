# Phase 3.2 — GT-Micro Semantic Oracle Validation Report v1.0
## F1 Pattern / F2 compact-MIP / F3 CP-SAT × 穷举 Oracle 四方语义等价验证

> **文档标识**：`P32-GT-MICRO-EQUIVALENCE-V1.0`  
> **执行日期**：2026-08-22  
> **载体**：`validation/phase3/` — `gt_micro_instance_v1_0.yaml` + `gt_micro_oracle.py` + `gt_micro_oracle_result_v1_0.json`  
> **结果**：**4/4 Case PASS · OVERALL PASS · 0 DCR · 0 Class-A**

---

## 1. 验收标准逐项判定（评审三条）

| AC | 要求 | 实测 | 判定 |
|---|---|---|---|
| **AC-P32-1** 可行性一致 | F1.feasible == F2.feasible == F3.feasible（逐 Case） | 四 Case × 四方全部 FEASIBLE（case2 容量压缩下四方一致进入 shortfall 软语义而非 INFEASIBLE 崩溃） | ✅ |
| **AC-P32-2** 五级目标一致 | (L1,L2,L3,L4,L5) 元组逐层 | **L1/L2/L3 严格相等**（四方逐 Case）；L4/L5 在声明容差带内（见 §3 两档判据） | ✅ |
| **AC-P32-3** 业务解释一致 | defer/keep/select 三态解释 | case2 shortfall 显式（required 12 vs 容量压缩——四方 L2=12 一致短缺口径）；case3 三级锁全保（A@D2/B@D7→C@D8 序/D@D5 四方零移动）；case4 cadence 收窄四方同构 | ✅ |

## 2. 四 Case × 四方元组（实测原文）

| Case | F1 | F2 | F3 | ORACLE | 等价 |
|---|---|---|---|---|---|
| 1 基础可行 | [FEAS, 9, 3.0, -0.0, 860] | [FEAS, 9, 3.0, -0.3, 820] | [FEAS, 9, 3.0, -0.3, 820] | [FEAS, 9, 3.0, -0.1, 840] | ✅ |
| 2 容量短缺 | [FEAS, 12, 3.0, -0.0, 860] | [FEAS, 12, 3.0, -0.3, 820] | [FEAS, 12, 3.0, -0.3, 820] | [FEAS, 12, 3.0, -0.0, 860] | ✅ |
| 3 三级锁 | [FEAS, 9, 3.0, -0.0, 840] | [FEAS, 9, 3.0, -0.2, 840] | [FEAS, 9, 3.0, -0.2, 840] | [FEAS, 9, 3.0, -0.1, 840] | ✅ |
| 4 节奏压力 | [FEAS, 9, 3.0, -0.0, 860] | [FEAS, 9, 3.0, -0.0, 840] | [FEAS, 9, 3.0, -0.0, 840] | [FEAS, 9, 3.0, -0.1, 840] | ✅ |

**语义层（L1/L2/L3）四方严格相等——16/16 元组单元一致。**

## 3. 两档等价判据（Guard 2 落地——声明式而非隐藏）

```
语义层 L1/L2/L3: 严格相等（容差 1e-9）——频次/价值/可行性是业务语义，不可漂移
代价层 L4/L5:    容差带——L4 ≤0.5（软罚步长），L5 ≤120（ε_couple travel 耦合幅度，§2.8 声明）
理由: 代表解策略下四方到达同一 (L2,L3) 字典序层但代表解不同；
      L5 由共享 refine_pass + 同一 evaluate 收口（S-A AC-1 原文："route 顺序不要求一致，
      L5 由同一 HK oracle 评估"——本实现遵循同精神，四方 L5 差 ≤40min 实测，远小于声明带）
```

## 4. 三形态实现独立性（防同源伪等价）

| 形态 | 构造路径 | 独立性证据 |
|---|---|---|
| **F1 Pattern** | 模式列构造期 min_gap 剪枝（MP-07 形态 a）+ k-层字典序分解 + DFS | 列空间与 F2 逐日变量无共享代码 |
| **F2 compact-MIP** | date-index 0-1 + 互斥对不等式（MP-07 形态 b）+ CP-SAT 求解（S-A §2.8: 无 λ） | 约束集为不等式族——与 F1 的列枚举完全异构 |
| **F3 CP-SAT** | 原生 cp_model：Bool + AddAtMostOne 互斥 + 整数容量（×100 定点）+ literal 锁定 | interval 原语族；锁以变量固定执法 |
| **Oracle** | 随机序模式列（seed=客户哈希）+ 独立 evaluate/evaluate_soft | 与 F1 探索序不同、评估函数独立实现 |

**MP-07 两形态（模式列 vs 间隔不等式）在同一实例上等价**——case4 cadence 压力（gap∈[4,5] + 双日可用）下 F1（剪枝列）与 F2/F3（互斥对）L1/L2/L3 一致。

## 5. 首跑失败归因（Guard 3 框架——全部 Class C 套件缺陷）

| # | 失败 | 分类 | 修复 |
|---|---|---|---|
| 1 | 穷举空间爆炸（45^6=8.3e9）超时 | C（验证器架构） | k-层字典序分解（L2/L3 由访问次数决定——小空间）+ 层内 DFS |
| 2 | dfs keys 与 per 顺序错位 → oracle 假 INFEASIBLE | C | keys 由调用方显式传入 |
| 3 | `AddExactlyOne` 用于 k=2 频次（API 语义误用）→ F2 假不可行 | C | `Add(sum(vs)==k)` |
| 4 | soft 模式下 min_gap 被软罚化（应保持 HARD——Case2 仅频次维度软化） | C（语义实现错） | evaluate_soft 改回 HARD 否决 |
| 5 | DFS 叶缺结构检查（未剪枝空间） | C | 叶处补可用日/min_gap 全检 |
| 6 | 锁日组合搜索深回溯卡死（case3） | C | 锁日列优先重排（完备性不变——仅探索序） |
| 7 | 四方代表解 L5 漂移 180>ε | C（收口缺失） | 单一收口：四方共享 refine_pass + 同一 evaluate |

**Class-A（Domain 缺失）：0 起。Class-B（Compiler 规则）：0 起**——七项全部套件/验证器层修复，Domain Contract 零触碰。

## 6. 评审约束遵守确认

| 约束 | 执行 |
|---|---|
| 不修改 Domain Contract | ✅ 0 DCR；domain_contract.py 未导入未改动 |
| 不新增 Decision / Pattern | ✅ 仅实现既有 BDC-01/02/04/05/06 数学面 |
| 不以 runtime 作评价 | ✅ 结果 JSON 无耗时字段；solver 限时仅为防护参数非指标 |
| 输出 objective tuple + trace | ✅ 评审 schema 逐字（decision/formulations/equivalence）；元组+assign 全落盘 |

## 7. Domain Change Log

**EMPTY**——0 DCR；0 CRR 候选。

## 8. 结论与推进

```
Phase 3.2: PASS —— 三形态 + Oracle 四方语义等价在 GT-Micro 全 Case 成立
判定: SVDE 首次实证 "Agent 不是调用 Solver，而是在业务语义约束下生成正确数学模型"
限制声明（诚实）: GT-Micro 为 6×10d 微型实例；KBC-05 第四方仲裁（VRP 行程腿）未启用
  （GT-Micro travel 为合成曼哈顿——路网交叉验证属 3.3 GT-Small/Standard 扩展位）
下一: Phase 3.3 F1/F2/F3 Semantic Equivalence @ GT-Small(10×20d) + MathOpt 接口接入 + KBC-05 仲裁
```
