# DCR-SA-001 裁定前置验证：DeferralPolicy Ownership Validation
## Deferral Policy 归属层级最小反例验证（DOV v1.0）

> **文档标识**：`DOV-DEFERRAL-OWNERSHIP-V1.0`  
> **所属阶段**：Reference Scenario Spike · Scenario A 前置裁定  
> **触发**：评审驳回 DCR-SA-001 直接定案（"APPROVED FOR INVESTIGATION, NOT APPROVED FOR PATCH"）——候选方案 a/b 均未经领域语义归属论证，且评审提出第三候选（Requirement 级 exception_policy）。  
> **任务性质**：**最小反例验证**——不修改 A03/A05，不写生产代码；只回答一个问题：  
> **DeferralPolicy 的领域语义归属层级是 VisitPolicy、BusinessRequirement，还是两者皆非？**

---

## 1. 验证问题（来自评审裁定的精确化）

评审提出的未决命题：

> **P**：同一 VisitPolicy 下可同时存在两个 BusinessRequirement（合同级 R1: max delay 3d / escalate；运营偏好级 R2: max delay 14d / ignore），且二者需要**不同的** DeferralPolicy。若该场景是真实业务且当前 A03 无法表达 → Requirement 级绑定才是正确 DCR；若该场景可由 A03 表达或并非真实业务 → 另行裁定。

验证分三步：
- **Step 1 语义事实**：该"同 Policy 双 Requirement 异常处理"场景是否真实销售拜访业务（证据，非想象）；
- **Step 2 表达力测试**：当前 FROZEN A03 能否无歧义表达它（四个通道复用 PROOF-E2 方法论）；
- **Step 3 归属裁定**：依据 Step1/2 结论，对候选 A（PolicyScope 挂靠）/ B（VisitPolicy.deferral_ref）/ C（Requirement.exception_policy_ref）/ D（维持现状：无绑定，由装配约定）做出裁定建议。

---

## 2. Step 1 — 语义事实核查（证据驱动）

### 2.1 候选证据链（厂商一手事实）

| 来源 | 事实 | 指向 |
|---|---|---|
| SAP DVP [SRC-SAP-DVP-01/02] | `Visit Plan`(常规覆盖) 与 `Visit Recommendation`(动态商机) 分属两套机制；漏访 score 增长作用于**覆盖义务**，与推荐项的丢弃逻辑不同 | **未满足后果按"需求来源"区分，而非按政策模板区分** |
| Salesforce Maps [SRC-SF-MAPS-01/02] | Dataset 的 Visit Requirement 含频率/时长/窗口；**missed visit 处理**（补访重生）与 requirement 定义分离，且 reroute 时 missed 状态驱动而非 policy 驱动 [SRC-SF-MAPS-MISSED] | 补访/延期决策发生在**执行反馈后**，生命周期晚于 policy |
| Oracle FS [SRC-ORA-FS-01] | `non_assignment_cost` 配置于 **routing plan/activity 级**，同一活动集合内不同优先级活动可不同 cost | 未服务后果的粒度是"任务/需求级"，不是"政策模板级" |
| PTV xTour [SRC-PTV-XTOUR-01] | Order Priorities 挂在 **order（=需求实例）**上，同一 plan 内每 order 可有独立 priority | 同上 |
| 内部 FMCG 实践（REQ-A-004/006 口径） | "合同 SLA 店"与"公司常规覆盖店"延期容忍不同，即便频次策略相同（南通/莆田实例中 KA 合同店 vs 普通 A 类店） | **同一频次策略、不同权威来源、不同延期容忍** = 真实业务 |

### 2.2 语义事实结论

**F1**：真实业务中，"延期容忍/升级后果"由**需求的权威来源（Requirement Authority）**决定——合同 SLA 需求容忍 3 天并升级，运营偏好需求容忍 14 天可放弃——**即使二者共享同一频次政策模板**。SAP/Oracle/PTV 三个独立 Level-A 来源共同支持（满足"两个独立成熟来源"晋升判据）。

**F2**：Deferral 决策在时序上发生于 Planning Failure 阶段（输入是"未满足的 demand/requirement"），而非 Policy 定义阶段。挂入 VisitPolicy 属于**生命周期错配**。

→ **Step 1 判定：P 前半（真实业务场景）成立。**

---

## 3. Step 2 — 冻结契约表达力测试

### 3.1 最小反例实例（MRE-1）

```
VisitPolicy P2: scope={segment==A}, EXACT(2)/28d, gap 10–16d     ← 唯一政策
  客户 X (A 类) 同时受两条 BusinessRequirement 约束:
    R1: "A 类核心合同店每月至少 2 次巡检"  strength=SOFT  authority=CONTRACT
        期望延期: max 3d, 超限 ESCALATE_TO_DIRECTOR, SLA_BREACH_REPORT
    R2: "A 类门店维持双周在店频率"          strength=SOFT  authority=COMPANY_POLICY
        期望延期: max 14d, 超限 NOTIFY_RM, OPPORTUNITY_LOSS
  规划结果: 容量不足，X 的第 2 次拜访只能部分满足。
  系统必须回答: X 本次未满足应按 R1 口径(3d/升级)还是 R2 口径(14d/容忍)处理？
```

### 3.2 四通道表达力穷举（复用 PROOF-E2 方法论，并追加评审候选）

| 通道 | 冻结契约依据 | 判定 |
|---|---|---|
| ① `DeferralPolicy.scope: PolicyScope`（候选 a） | DeferralPolicy 无 scope 字段；即便有，MRE-1 中 R1/R2 **共享同一 PolicyScope**（同为 A 类客户），scope 无法区分 R1/R2 | ❌ **被 MRE-1 直接证伪**——绑定目标碰撞 |
| ② `VisitPolicy.deferral_ref`（候选 b） | VisitPolicy 无该字段；即便加，P2 只有**一个** deferral_ref，无法对 R1/R2 给出不同策略 | ❌ **被 MRE-1 直接证伪**——一对多无法表达 |
| ③ `BusinessRequirement.exception_policy_ref`（候选 c） | BusinessRequirement 现有字段：requirement_id/statement/strength/authority/applies_to/parameter_refs/source_ref——**无任何异常处理引用字段**；Demand/Occurrence 层亦无 | ❌ 当前不可表达（正是缺口所在） |
| ④ 装配期约定（status quo, 候选 d） | Scenario 聚合中 R1/R2 与 DP-STD/DP-SLA 无任何声明关系；靠代码顺序/注释 = metadata hack，违反 DOV 判据 | ❌ |

### 3.3 反向检验：候选 c 是否会引入新问题？

| 质询 | 回答 |
|---|---|
| R1/R2 的 applies_to 重叠时，一个未满足 occurrence 同时命中两条 Requirement，用哪条 exception？ | **规则可声明且稳定**：取 authority 更高者（CONTRACT > COMPANY_POLICY），或显式 priority 字段——这是 Resolution 规则，属编译规范，不新增领域对象；且该冲突在候选 a/b 下**同样存在且更糟**（a/b 连 R1/R2 都区分不了） |
| Requirement 级挂靠是否过早抽象（评审第六节警告）？ | 否——MRE-1 即评审要求的"同 Policy 双 Requirement 异常处理"最小反例，属**场景失败驱动**而非"未来可能"；且 F1 证据链（3 厂商）满足晋升判据 |
| 是否违反"规则对象不拥有选择逻辑"（驳回候选 a 的理由）？ | 否——Requirement **引用**策略（声明式 ref），不做匹配；scope 匹配逻辑仍留在装配器 |
| DCR 最小性 | 仅新增 1 个可选引用字段于既有对象，复用 RequirementRegistry 键模式；无新对象类型、无新层次 |

→ **Step 2 判定：候选 a、b 被 MRE-1 证伪；候选 c 是唯一未被证伪且语义正确的通道；候选 d 违反无 hack 判据。**

---

## 4. Step 3 — 裁定建议

```
DOV 结论（提交评审 sign-off）:

  F1 (真实性)    : ✅ 同 Policy 双 Requirement 异常处理是真实 FMCG 业务（3 厂商 Level-A 证据）
  F2 (生命周期)  : Deferral 属 Planning-Failure 阶段语义，挂 VisitPolicy 为生命周期错配
  MRE-1 (表达力) : 候选 a ❌ scope 碰撞 / 候选 b ❌ 一对多 / 候选 c ❌当前缺失(即缺口) / 候选 d ❌ hack

  裁定建议:
    REJECT   候选 a (DeferralPolicy.scope)
    REJECT   候选 b (VisitPolicy.deferral_ref)
    ADOPT    候选 c —— DCR-SA-001 修订版:

      DCR-SA-001-R (Requirement-Level Exception Policy Binding)
        变更: BusinessRequirement 增加可选字段
              exception_policy_ref: str | None   (引用 DeferralPolicy registry 键)
        冲突解析规则(编译规范, 不入领域对象):
              同一 occurrence 命中多条带 ref 的 Requirement 时, 取 authority 更高者;
              平级时取 strength 更高者; 无 ref 的 Requirement 不参与异常处理选择。
        不新增对象类型; DeferralPolicy 保持原结构(无 scope 字段);
        Scenario 聚合不变(deferral_policies list 即 registry 值域)。

    状态流转: DCR-SA-001 (原) → SUPERSEDED by DCR-SA-001-R
              DCR-SA-001-R   → APPROVED FOR PATCH（待评审最终 sign-off）
```

---

## 5. 对既有资产的影响面

| 资产 | 影响 |
|---|---|
| A03（FROZEN） | 待 sign-off 后出 **v1.0.1 patch**：BusinessRequirement + 1 可选字段 + 冲突解析规范入 §2.9；其余零改动 |
| A05（FROZEN） | 零改动（编译层规则，不涉架构） |
| S-A v1.1 | §2.2 DP-STD/DP-SLA 绑定改写为经 R3(合同)/R4(运营) 的 exception_policy_ref；§3.2 PROOF-E2 结论更新为"由 DCR-SA-001-R 解决"；§2.17 Register 同步 |
| 门禁 | Gate A1 最终通过条件 = DCR-SA-001-R sign-off + A03 v1.0.1 patch 落地 |
