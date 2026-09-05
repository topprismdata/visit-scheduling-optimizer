# Scenario D — Domain Executable Validation Report v1.0
## Phase 2 · 多资源 + Ownership/Eligibility/Substitution（解释层执行结果）

> **文档标识**：`SD-DOMAIN-EXECUTABLE-VALIDATION-V1.0`  
> **执行日期**：2026-08-22  
> **验证对象**：A03 `Domain-Contract-v1.0.1 FROZEN` 对组织关系四概念（Ownership/Eligibility/Availability/Assignment）分离语义的表达能力  
> **执行纪律**：零数学；A03/A05 未动；无新 Domain Entity  
> **执行载体**：`validation/phase2/run_scenario_d_validation.py` + `decision_trace_d.json`  
> **结果**：**20/20 PASS · 0 DCR**（评审预判的"最可能产生 DCR 场景"未触发——四概念关系式由冻结对象完整承载）

---

## 1. Gate D 判定结果

| Gate | 判据 | 结果 | 证据 |
|---|---|---|---|
| **D1 Four-Concept Separation** | 四概念独立，无隐式互推 | ✅ PASS | MRE-D-1/2/3 三反例全证（见 §2） |
| **D2 Derivation Integrity** | pool→elig→avail 三段过滤 + 排除原因显式 | ✅ PASS | ELIG_FILTER/AVAIL_FILTER 标签全程（FC-D-1/2 样本） |
| **D3 Substitution Audit** | owner≠executor 五要素齐全 | ✅ PASS | {owner:R001, executor:R002, via:SUBSTITUTION, trigger:PRIMARY_ABSENT, policy_ref} 落盘 |
| **D4 Immutability** | 规划期 Ownership 零隐式变更 | ✅ PASS | TD-OWN-1：变更为显式新对象（管理动作），非规划输出 |
| **D5 Scenario Pass** | D1–D4 + TD/MRE + MM-D1..4 + Log | ✅ **PASS** | 20/20 |

## 2. 三大 MRE 反例结果（本场景核心）

### MRE-D-1：Owner ≠ Executor（替补链）✅
```
R001 缺勤日: eligible = {R002}        ← backup 触发（R001 出局、R002 进池）
R001 在岗日: eligible = {R001}        ← backup 留在池外（非触发不进）
审计链: {owner:R001, executor:R002, via:SUBSTITUTION,
         trigger:PRIMARY_ABSENT, policy_ref:SubstitutionPolicy(backup=(R002))}
→ 五要素齐全；归属未转移、执行已变更、原因可追溯——三者独立记录
```

### MRE-D-2：有归属 ≠ 有资格 ✅
```
R004 (无冷链资质) 被误设为 primary:
eligible = [] ; 排除标签 = ELIG_FILTER_T024_R004_REASON:missing:cold_chain
→ 归属与资格矛盾显式暴露，非静默放行、非静默改归属
```

### MRE-D-3：有空 ≠ 被授权 ✅
```
R003（共享池员）周二空闲:
专属客户 Z (primary=R002, pool=False, backup=∅): eligible = {R002}
→ 可用性不产生执行权；R003 的 Tuesday 空闲被正确忽略
```

## 3. 二十项测试摘要

| 组 | 结果要点 |
|---|---|
| 基线 ×4 | 冷链客户 eligible ⊆ {R001,R003}（R002 滤除）；**专属客户 = {primary} 仅**（修正初版错误预期——共享池语义不被隐式扩大）；R002 专属 = {R002}；共享池 = 三员 |
| 资格 ×2 | MRE-D-2 + TD-ELIG-1（原因标签显式） |
| 可用 ×2 | R002 请假日出局；R003 周一出局但池内其余照常 |
| 池 ×2 | 共享池全量；MM-D3 收缩至 primary 不扩 |
| 替补 ×4 | MRE-D-1 双向（触发/非触发）+ 五要素审计 + MM-D4 扩名单不缩 |
| 扩展 ×1 | MM-D1 加合格资源不缩既有 eligible |
| 归属 ×1 | TD-OWN-1 变更=显式管理动作 |
| 守卫 ×3 | FC-D-1 不存在资源/FC-D-2 替补缺资质/FC-D-3 全员无辖区 → 分别显式标签、显式排除、结构空集（无崩溃） |

## 4. 执行期缺陷记录（套件自身，非 Domain）

| 发现 | 修复 |
|---|---|
| 初跑 3 FAIL：MRE fixture 误置缺勤于 R002（spec 定义 R001 缺勤）；TD-BASE 专属客户预期误写为三员（共享池语义误扩）；FC-D-2 用错 fixture 致触发未发生 | 全部为**测试套件 fixture/预期缺陷**；修正后 20/20；**契约对象零改动** |
| 属性名笔误 required_qualizations | 套件 typo 修复 |

## 5. 关键裁定：评审预判的 DCR 未发生

评审预判"D 是最可能产生真实 DCR 的场景"。执行结果：**四概念关系式**（`pool = primary ∪ shared ∪ backup-triggered → filter(Eligibility) → filter(Availability)`，assignment 为输出）**由冻结对象无歧义承载**：
- Ownership 与 Assignment 分离：`OwnershipPolicy`（输入）vs `PlannedVisit.resource_id`（输出）+ 五要素审计
- Eligibility 与 Availability 分离：两个独立过滤段，各自排除标签
- `Owner == Assigned Rep` 隐藏假设：不存在——专属客户在 primary 在岗日 eligible={primary} 是**派生结果**而非假设

**Domain Change Log：EMPTY**（0 DCR）。

## 6. 与 A/C 的增量证明

| 维度 | A/C 已证 | D 增量 |
|---|---|---|
| OwnershipPolicy | 单人恒真（A） | **多 primary/空 primary+pool/规划期不可变** |
| SubstitutionPolicy | 声明未触发 | **conditions 触发语义 + 审计 via-reason 全链** |
| EligibilityPolicy | 声明未用 | **独立过滤 + 矛盾显式暴露** |
| 三段派生 | 未端到端 | **pool→elig→avail 完整关系式验证** |

## 7. RMAP 状态推进

```
Phase 2: A ✅ 18/18 → C ✅ 20/20 → D ✅ 20/20 → E ◀ next → B
```
