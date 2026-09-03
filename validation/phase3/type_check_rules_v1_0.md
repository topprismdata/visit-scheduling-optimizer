# Type Check Rules v1.0 — Phase 3.3-② Artifact 2（Immutable）
## 生成期检查规则——非法组合在编译期拦截（非求解期发现）

rules_id: TCR-V1.0
generated_at: "2026-08-22"
basis: [constraint_type_registry_v1_0.yaml, KB-GOV-012 seven_class_C_lessons, KB-GOV-016 constraint_chain]
goal: "3.2 暴露的错误模式全部获得生成期等价拦截（Gate T3）"

## ═══ TC-001 Hard 不可自动软化 ═══
```
Rule: hardness ∈ {HARD} ∧ relaxable ∉ {false, 白名单标}
      → TYPE ERROR: HARD_AUTO_SOFTENING
对应 3.2 教训#4: min_gap 在 soft Case 被罚项化
执法: C04/C06/C07/C08/C09/C10 的 relaxable 恒 false；
      C02.lo 仅当 (case==case_2_capacity_short) 时进入软化白名单（contract §I3）
报告码: TC-E001
```

## ═══ TC-002 Cardinality-API 语义匹配 ═══
```
Rule: ExactlyOne 类 API ⟺ cardinality.op=="==" ∧ value==1
      value==k≠1 必须用 Add(sum==k)/等式约束
对应 3.2 教训#3: AddExactlyOne@k=2 → F2 假不可行
执法: C01(k=4/3) 生成 Add(sum==k)；C07/C09(on 单变量) ==1 合法
报告码: TC-E002
```

## ═══ TC-003 Objective Penalty 不得承载不可违反约束 ═══
```
Rule: semantic_class==Temporal ∧ hardness==HARD（如 C04）
      → 不得出现在 OBJECTIVE_PENALTY 槽位
对应: min_gap 误软化（与 TC-001 双保险——一个拦属性组合，一个拦槽位误用）
执法: 编译器槽位检查——HARD 类型仅入约束集；C03 是唯一 OBJECTIVE_PENALTY 居民
报告码: TC-E003
```

## ═══ TC-004 Schema 匹配（keys/entity 对齐）═══
```
Rule: 生成器输出的 per-实体序列与约束实体键严格同序同长
对应 3.2 教训#2: keys 错位 → oracle 假 INFEASIBLE
执法: Decision IR → Solver Input 转换层注入显式键传递 + 长度断言
报告码: TC-E004
```

## ═══ TC-005 锁合并与冲突 ═══
```
Rule: 同目标多锁取最强（C09 ⊃ C07 ⊃ FREE）；
      LOCK_* ∧ AVAILABILITY_WINDOW 若锁日 ∉ avail → 显式 CONTRADICTION（非静默）
对应 3.2 教训#6（锁搜索）+ AC-2 零矛盾前置
报告码: TC-E005
```

## ═══ TC-006 频次-窗口可达性（生成期结构性预检）═══
```
Rule: |avail ∩ 每周期合法窗| < k → 生成期 PROVEN_INFEASIBLE 预报
      （不可达在建模前暴露——S-A TA-INF 结构不可行归因的编译期版）
对应 3.2 教训#5（叶检缺失的前移）
报告码: TC-E006
```

## ═══ 拦截-失败映射（Assumption vs Implementation 分诊）═══
| 拦截码 | 触发含义 | 分类 |
|---|---|---|
| TC-E001/E003 | 语义级非法组合 | **按设计工作**（Class C-captured）；若业务确需软化 → contract 修订流程（回①，非代码改动） |
| TC-E002/E004 | 生成器实现缺陷 | Implementation Fail（Class C——修生成器） |
| TC-E005 | 装配件自身矛盾 | Assumption Fail 候选（查 instance 构造） |
| TC-E006 | 结构不可行 | 语义正确行为（预报=产出，非错误） |

## Gate 判定（评审三 Gate 原文）
- **Gate T1**: C1-C10 → C01..C10 唯一映射（无多义/无遗漏）——registry+contract 双向对账
- **Gate T2**: 每类型含 semantic_class / hardness / relaxability 三属性齐备
- **Gate T3**: 3.2 三错误模式（AddExactlyOne misuse / Hard→Soft downgrade / Schema mismatch）分别被 TC-002 / TC-001+003 / TC-004 拦截——以注入式复现验证（见 report）
