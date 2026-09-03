# GT-Small Oracle Definition v1.0 — Phase 3.3-① 伴随工件（Immutable Artifact）

oracle_id: GTS-ORACLE-DEF-V1.0
generated_at: "2026-08-22"
ladder: "Enumeration Oracle（GT-Micro 专用）→ **Exact Solver Oracle ◀ 本档** → Independent Solver Oracle → Production Reality Oracle"

## 1. Oracle 选型（S-A §2.10 GT-Small 条款）

**Exact Solver Oracle**：独立 CP-SAT exact model，求到 `status=OPTIMAL`（附 bound/gap=0 断言）。
不做全枚举——10 客户 × 20 日的 assignment 空间（≈C(20,4)²·C(20,3)⁴·C(20,2..4)⁴ > 10¹⁵）超出穷举档位。

## 2. 独立性保障（防同源伪等价——3.2 §4 纪律延续）

| 维度 | Oracle | F1/F2/F3 |
|---|---|---|
| 变量命名 | `o_x_{t}_{d}`（独立命名空间） | 各自 `x_/f2_/f3_` 前缀 |
| 求解参数 | max_time=300s, workers=8, 独立 random seed | F2: MathOpt/HiGHS 默认 + 分层；F3: workers=1 |
| 目标构造 | **加权标量化独立推导**（权 1e6/1e3/1，尺度隔离推导过程独立成文） | F2 分层序列；F3 标量化另一实现 |
| 解评估 | 共享 `evaluate()`（L5 HK 同口径——S-A AC-1 精神） | 同左 |

## 3. OPTIMAL 断言（区别于启发式）

Oracle 输出必须含 `status=OPTIMAL` + `best_bound`（gap=0）；FEASIBLE 不得作为 oracle 结论（降级即 Oracle 失效——Assumption A003 相邻判据）。

## 4. 仲裁边界

- Oracle 裁决 **L1/L2/L3 语义层**与 L4/L5 参考值
- 行程腿语义裁决归 KBC-05（⑤ 步——A001）；Oracle 不做 travel 结构裁决
- Oracle 与三形态分歧：先查 Implementation（Class C 候选）→ 再查 A003（分层求解最优性）

## 5. 冻结声明

本定义与 instance/semantic_contract 同批冻结（KB-GOV-015 step_1 工件三件套）；后续步骤引用不得修改。
