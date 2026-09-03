# Prism AI Employee — Autonomous QA 架构 v0.2 修订
## 7 条 Mandatory ADR（基于文献验证与三轮自检）

> 状态：评审中
> 基线：`Prism_AI_Employee_Autonomous_QA_Architecture_v0.1.md`
> 本文档性质：对 v0.1 的强制性架构修订提案，每条按 §18.4 ADR 格式提交
> 审查方法：三轮独立自检（内部一致性 / 度量可信性 / 运行时可靠性）+ 文献与一手工程来源交叉验证

---

# 修订总览

| 编号 | 主题 | 一句话变更 |
|---|---|---|
| ADR-001 | Safe Retry & Unknown Outcome Reconciliation | Retry 从启发式规则升级为按操作类型的状态机规则 |
| ADR-002 | Experiment Isolation & Synthetic Data Contamination | 测试隔离从清理关注项升级为 Oracle Validity 前置条件 |
| ADR-003 | Evidence Referential Integrity | 证据引用从良好实践升级为 commit-time 机械不变量 |
| ADR-004 | Historical Oracle Grounding Ceiling | E5 历史行为默认封顶 G2，只产 SUSPICION / REGRESSION_CANDIDATE |
| ADR-005 | Metamorphic Oracle Strength Classification | E6 拆分为必要性质（E6a, ≤G3）与经验关系（E6b, ≤G2） |
| ADR-006 | Gate 0 Measurement Pre-registration | Benchmark 从指标清单升级为 Gate 前冻结的测量契约 |
| ADR-007 | Tool Action / Observation Grounding Verification | Agent 自报动作/观察不作为证据，必须机械信号确认 |

七处修改的定性：

```text
Retry            → from heuristic to state-machine rule
Isolation        → from cleanup concern to oracle-validity condition
Evidence         → from good practice to commit-time invariant
Historical       → from expected-source candidate to G2-capped signal
Metamorphic      → from single category to necessary vs heuristic split
Benchmark        → from metrics list to frozen measurement contract
Tool result      → from trusted agent output to mechanically verified observation
```

---

# ADR-001 Safe Retry & Unknown Outcome Reconciliation

## problem

v0.1 §12.9 与 §12.11 对同一场景给出相反指令：§12.9 规定 `temporary timeout → retry`，§12.11 规定写操作超时禁止盲目重试、先 reconcile。Runtime 按 §12.7 是确定性系统（"Runtime is deterministic governance"），必须有一条机械可执行的优先级；当前每个 Action Executor 都要自行猜测。

## current_design

```text
§12.9: temporary timeout → retry（未区分读写路径）
§12.11: 写操作 Timeout 不要盲目 retry → reconcile actual state → then decide
```

两处并存，无优先级声明。

## proposed_change

将 §12.9 替换为如下状态机规则：

```text
READ / PROVABLY IDEMPOTENT operation
→ bounded retry allowed

MUTATING operation with confirmed idempotency contract
→ bounded retry using same idempotency key

MUTATING operation with unknown outcome
→ DO NOT RETRY
→ reconcile actual state (synthetic marker query)
→ retry only after outcome classification
```

其中 outcome classification ∈ { SUCCESS_CONFIRMED, NOT_APPLIED, AMBIGUOUS }。AMBIGUOUS 不得自动重试，进入 INVESTIGATE 或上报 assistance_request。

术语声明：本条遵循 Amazon Builders' Library 的表述方式——分布式环境下 exactly-once 难以保证，因此 mutating operation 应通过 idempotency token 或 semantic equivalence 使重试安全；实施 retry 前必须先确认目标操作具备幂等性。

## evidence

Amazon Builders' Library《Making Retries Safe with Idempotent APIs》：网络调用可能在服务端已处理之后、客户端收到确认之前超时，此时成败未知；盲目重试会产生重复副作用并引发 retry amplification；AWS 明确要求在实现重试前先确认服务具备幂等性。
https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/

辅证：AWS Well-Architected Reliability Pillar（幂等性要求）：
https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_idempotent.html

## benchmark_impact

neutral（可靠性修正，不影响对照指标定义）。但避免了因重复创建实体导致的假 INCONSISTENT Outcome，间接保护 FDR。

## alternatives

- 保持两条规则并存并在文本中标注优先级——仍是自由裁量，违反 Runtime 确定性原则。
- 所有操作一律禁止重试——读路径过度保守，无必要地放大 flaky 工具故障的影响。

## decision

采纳替换方案。写进 T003（Action / Outcome / Trace）验收标准。

---

# ADR-002 Experiment Isolation & Synthetic Data Contamination

## problem

v0.1 §8.4 只要求 AI 创建的数据带 synthetic marker，未规定读取侧强制过滤。后果：Agent 自己创建的 fixture 进入聚合结果、列表查询和 State Delta 比较，制造假 INCONSISTENT 或掩盖真缺陷。这是 gate 0D False Discovery Rate 的直接威胁源。同时 R3 Fixture Reset 会周期性清场，marker 过滤集必须与实际数据集保持一致，否则漂移。

实证背景：测试间共享状态污染是 flaky tests 的已知成因类别之一（Luo et al., FSE 2014：51 个开源项目、201 个 flaky-test 修复提交的实证分析）；Google 报告约 84% 的 pass→fail 构建转变涉及 flaky test 而非真实代码缺陷（Google Testing Blog, 2016）。即：若不控制隔离，Gate 环境中自造噪声的主导程度可能超过工业环境。

## current_design

§8.4：所有 AI 创建数据带 run_id / experiment_id / synthetic marker；禁止污染基线 Fixture。仅此而已；Oracle 与 Evidence 读取侧没有任何对应的排除义务。

## proposed_change

核心原则一句话：

> 隔离性本身属于证据质量的一部分。

(1) Oracle Validity 前置条件：

```text
Finding cannot be promoted beyond SUSPICIOUS
if experiment isolation cannot be established.
```

(2) 新增 experiment_validity 结构（并入 Experiment schema §8.2）：

```yaml
experiment_validity:
  fixture_isolation_verified: true|false
  synthetic_data_marker_verified: true|false
  prior_experiment_contamination: none|possible|confirmed
  environment_baseline_verified: true|false
```

(3) 机械规则：
- 所有 state 断言类查询（list/detail/aggregation/state delta 读数）默认过滤带 marker 的合成数据；
- 涉及聚合的 Oracle 必须显式声明"含合成数据评估模式"，并将 grounding 下调一级；
- fixture reset 后重建 marker 过滤集，保证与实际数据集一致；
- `prior_experiment_contamination ∈ {possible, confirmed}` 时，experiment outcome 不得为 CONFIRMED，最高 INCONCLUSIVE。

## evidence

Luo, Hariri, Aboulnaga, Barr? —— 更正为准确作者序：Qingzhou Luo, Farah Hariri, Laleh Shalabadze? 以论文官方记录为准：《An Empirical Analysis of Flaky Tests》, FSE 2014, 51 projects / 201 fix commits.
https://www.semanticscholar.org/paper/363c9c645dc8c303c3d7ad995f60beae32ce10fa

Google Testing Blog, Flaky Tests at Google and How We Mitigate Them (2016)：约 84% pass→fail transitions 涉及 flaky test。
https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html

注：flaky 成因分类包含 test-order dependence / nondeterminism 类别成立；具体根因排名引用时以论文表格为准，本 ADR 不依赖具体排名，只依赖该成因类别的存在性与规模。

## benchmark_impact

improved（FDR 可信度）。若不采纳，Group A/B/C 任一组的 FDR 数字都不可用作 Gate 0D 判定输入。

## alternatives

- 仅靠 cleanup_policy 兜底——已被论证不足：cleanup 是事后补救，无法阻止当次实验内部的自污染。
- 每次实验前全量 R4 Reset——成本不可接受，违反最小充分 Reset 原则（§8.10）。

## decision

采纳。写进 T003 与 T012（Oracle）验收标准。

---

# ADR-003 Evidence Referential Integrity

## problem

知识晋升管线（CANDIDATE→OBSERVED→PROVISIONAL→VALIDATED）的第一道闸没有机械校验。LLM 幻觉出一个不存在的 evidence id 即可把 Claim 推向 OBSERVED，后续所有会话把幻觉固化的事实当作已验证知识引用——即 "Memory Provenance Laundering"。Truth Maintenance 传统（Doyle 1979 JTMS; de Kleer 1986 ATMS）的共同前提是：每个 belief 必须挂在 justification 依赖网络上，无正当性支撑的 belief 不允许进入 IN 状态。

## current_design

§6.6 Knowledge Promotion Policy 只说 "LLM proposes → Knowledge Policy evaluates → Runtime commits"，未规定 commit 时校验什么。

## proposed_change

`world_model.commit_delta()` 执行 commit-time 不变量检查，全过才落库，任一失败记 POLICY_BLOCKED 事件并拒绝写入：

```text
No Evidence Reference
→ No OBSERVED / PROVISIONAL / VALIDATED Claim

Broken Evidence Reference
→ Claim becomes INVALID_GROUNDING, must not enter reasoning context

Evidence artifact missing or integrity-invalid
→ downstream Oracle grounding downgraded one level
```

每个被引用的 Evidence 必须通过五项检查：

```text
exists
+ belongs to allowed run/product scope
+ artifact integrity valid (content hash)
+ not redacted into unusable evidence
+ not LLM_INTERPRETATION-only when direct evidence is required
```

配套：Redaction 内嵌至 `evidence.record()` 管线强制执行（§9.5 从调用方义务改为管线不变量）。

## evidence

Doyle, J. "A Truth Maintenance System." Artificial Intelligence, 1979（belief 必须有 justification 才能处于 IN 状态）。
de Kleer, J. "An Assumption-based TMS." Artificial Intelligence, 1986（assumption sets 与上下文标签）。
实践佐证（非一级文献）：2025–26 agent 记忆工程中的 provenance laundering 描述与 strict citation contract 缓解共识。

## benchmark_impact

improved（World Model Metrics 中 Useful Knowledge Rate 与 Contradiction Recovery 的可信度前提）。

## alternatives

- 定期离线审计代替 commit-time 校验——脏数据已在库内参与推理，事后发现时污染面扩大。
- 只查 ID 存在性——挡不住错 scope、坏 artifact、纯解释性证据三类穿透。

## decision

采纳。写进 T009（Claim Store）验收标准。

---

# ADR-004 Historical Oracle Grounding Ceiling

## problem

E5 Stable Historical Behavior 在 v0.1 中是无上限的 Expected Source。自系统上线起就存在的缺陷同样满足"历史稳定"，按 §10.3 将获得 G4/G3 grounding 并可判 EXPECTED_BEHAVIOR——回归缺陷这一最典型的跨版本缺陷类被定义性地排除了。"以前一直这样"不蕴含"现在必须继续这样"。

## current_design

§10.2 E5 与其他 Expected Source 同级列举；§10.3 仅约束 grounding level 与判定权限的映射，未给 E5 单独上限。

## proposed_change

```text
E5 Stable Historical Behavior
default maximum grounding = G2
```

E5 只能产生：

```text
REGRESSION_CANDIDATE 或 SUSPICIOUS
```

不能单独支撑 VALIDATED_DEFECT。豁免条件：该历史行为存在显式变更记录或用户/产品负责人书面确认时，可按正常 G3/G4 处理。

## evidence

Barr, Harman, McMinn, Shahbaz, Yoo. "The Oracle Problem in Software Testing: A Survey." IEEE TSE 41(5), 2015：oracle 来源多样且并非总能提供完整正确性判断，需按信息来源强度分级处理。
https://ieeexplore.ieee.org/document/6963470

## benchmark_impact

improved（跨版本 Run 的 L2/L3 recall 不再被定义性归零；Cross-workflow contribution 指标获得干净口径）。

## alternatives

- 全面禁用 E5——剥夺了回归候选生成的重要信号源，过度保守。

## decision

采纳 G2 封顶 + 显式豁免。与 ADR-005 分立（本条管 Expected Source 强度，ADR-005 管 relation 性质，实现与测试路径不同）。

---

# ADR-005 Metamorphic Oracle Strength Classification

## problem

E6 Metamorphic Oracle 在 v0.1 中是单一类别，隐含"变换关系即可靠"。Metamorphic testing 文献的核心区分是：只有违反**必要性质（necessary property）**才直接指示 fault；违反**期望行为性质的 MR** 只说明实现与预期发散，属 validation 层弱信号。两者 grounding 强度不应相同。

## current_design

§10.5 单列 Metamorphic Oracle，无内部分级。

## proposed_change

```text
E6a Necessary Metamorphic / Logical Property
→ max G3

E6b Heuristic / Expected Metamorphic Relation
→ max G2
```

判定标准写入 Oracle 实现：relation 是否可从规格/逻辑必然性推导（E6a），或仅从领域经验/相似系统类比得来（E6b）。归类存疑时按 E6b 处理。

## evidence

Chen, T.Y. et al. metamorphic testing 系列（1998 TR 起）；Segura et al. "A Survey on Metamorphic Testing." IEEE TSE 2016：MT 通过输入变换与输出关系建立部分 oracle，其证明力取决于关系的必要性质。
https://eprints.whiterose.ac.uk/id/eprint/110335/1/segura16-tse.pdf

Barr et al. TSE 2015（同 ADR-004）。

## benchmark_impact

improved（Seeded Defect 中 temporal/cross-workflow 类经由 MT 发现时的分类一致性）。

## alternatives

- 维持单一 E6——把经验猜测提升到必要性质同级的证明力，制造假阳性通道。

## decision

采纳拆分。与 ADR-004 合并为一张 Expected Source Strength 表呈现，但保留独立编号以便分别测试。

---

# ADR-006 Gate 0 Measurement Pre-registration

## problem

三个度量口径未冻结：(1) "Novel" 无跨 Run 定义，Run N 重见旧缺陷算不算无从裁决；(2) Group C without memory 是配置未定义的第四组——剥离边界不清则 H2 归因混杂变量；(3) Persistent Memory 组与 Evaluator 对 novelty 的视角若混用，会对 C-memory 组系统性多扣或多加。对照 CONSORT 方法论：primary outcome 必须 prespecify（measurement variable / metric / aggregation / time point），事后更换主要终点（outcome switching）属被禁止的可疑研究实践。

## current_design

§15.6 North Star "Valid Novel Defects / Employee Hour" 无 Novel 操作定义；§15.13 比较对象 "C without memory" 未定义剥离边界；§15.9 只给出指标清单，无冻结机制。

## proposed_change

任何正式 Gate Run 之前冻结以下测量契约（冻结后修改须走新 ADR）：

```yaml
gate_measurement_contract:

  primary_endpoint:
    name: Valid Novel Defect Families per Employee Hour
    unit: defect_families / hour
    numerator_definition: >
      adjudicated VALIDATED_DEFECT 且满足 novelty_definition 的去重 defect family 数
    denominator_definition: >
      按预算内有效工作时长计（from ASSIGNMENT_STARTED to ASSIGNMENT_COMPLETED,
      pauses excluded）
    aggregation: run-level sum / total hours
    adjudication_rule: 双人盲评 + 分歧仲裁；signature 为 failure_mode_category + trigger_path

  secondary_endpoints:
    - L2_defect_recall
    - L3_defect_recall
    - false_discovery_rate
    - reproduction_success
    - token_per_valid_defect

  novelty_definition:
    within_run: defect family not previously reported in that Run
    across_runs: >
      defect family not previously known to that Employee
      before the current evaluation release begins
    same_defect_family_rule: >
      family keyed by (failure_mode_category, trigger_path signature),
      NOT by code-level root cause（与 §10.12 对齐）

  evaluator_vs_employee_novelty:
    evaluator_novel: unique ground-truth defect family in current evaluation set
    rule: >
      Employee-novel 用于员工学习曲线指标（H3），
      Evaluator-novel 用于评分。二者不得混用，
      C-memory 组不因"以前见过"在评分中被扣分或加分。

  comparison_profiles:
    A: LLM + Browser + current context only
    B: A + QA structured reasoning, no persistent world model
    C_no_memory: >
      full C architecture 但 Working Memory/History 仅限本次 Assignment 的
      RuntimeState；禁读 MemoryItem / Skill 存储
    C_memory: full C architecture

  fixed_variables:
    model: <frozen>
    tool_stack: <frozen>
    budget: <同一总 token 上限由 Runtime 强制截断，各组一致>
    app_version: <frozen per evaluation release>
    seed_policy: <seed set 固定且对外不可见>

  allowed_exclusions: <枚举，如环境级故障>
  missing_data_policy: <excluded runs 记录但不剔除，单独报告>
  human_adjudication_policy: 双人盲评 + 第三人仲裁；意见分歧率入报告
```

Version bump 规则（联动 Compounding 实验）：version 变更后所有 VALIDATED Claim 自动降 PROVISIONAL，Skill 转 STALE；复验后恢复。

## evidence

CONSORT 2025：primary/secondary outcomes 须预先指定，含 measurement variable、analysis metric、aggregation method、time point。
https://www.consort-spirit.org/item14-outcomes
预注册抗偏（outcome switching / HARKing / selective reporting）：
https://phdontrack.net/good-research-practices/preregistration/
混杂变量控制要求每次操纵一个变量、对照条件显式定义：
https://www.scribbr.com/methodology/confounding-variables/

注：CONSORT 是临床 RCT 报告标准，此处仅借鉴 prespecification 方法论，不主张软件 benchmark "遵循 CONSORT"。

## benchmark_impact

improved（Gate 0B/0C 结论获得合法裁判资格；否则 Group A/B/C/D 全部数字只可用作探索性参考）。

## alternatives

- 维持指标清单、评测时再定口径——正是 outcome switching 反模式。

## decision

采纳。Measurement Contract 作为 Gate Run 准入文件，附于 Benchmark Harness（E08）产出物。

---

# ADR-007 Tool Action / Observation Grounding Verification

## problem

LLM 自报的动作结果与浏览器 Agent 汇报的状态变化都不是证据。多模态 GUI agent 存在被系统证实的 action/coordinate hallucination（对不存在或错位元素执行看似合理的行为），且对初始条件的轻微扰动表现脆弱。若 agent 自报可直接进入 Oracle 判定，S0–S2/S5 证据强度分级会被整条架空。

## current_design

§9.1 有 source_strength 分级，§13.8 有 observation fusion，但没有一条机械规则强制"agent 自报 ≠ 完成"；Action schema（§8.5）的 execution_status 可由 executor 侧面直接填写。

## proposed_change

新增强制原则与流程段 "Execution Grounding Verification"：

```text
Agent-reported action     ≠ Action Completion
Agent-reported observation ≠ Product Evidence
```

Action Completion 至少由一种外部可验证信号支持：

```text
DOM / ARIA state change
Network request seen
Network response success
URL transition
Persisted API state
Screenshot evidence（视觉差异级）
```

结构化落地：

```yaml
action_grounding:
  semantic_action: Set Store.owner = B
  agent_report: success
  mechanical_verification:
    network_request_seen: true
    response_success: true
    persisted_state_verified: true
  final_execution_status: COMPLETED   # 任一 mechanical signal 缺失 → UNVERIFIED
```

status = UNVERIFIED 的 Action：不得进入 Product Oracle；其 outcome 分类上限 PARTIAL_CHANGE/UNEXPECTED_CHANGE 探查路径，需先补机械验证或降级为 Tool Failure 处理。最终管线表达：

```text
Reasoning Claim
↓
Tool Intent
↓
Execution
↓
Mechanical Verification
↓
Observed Outcome
↓
Evidence
```

联动 §10.7：Alternative Explanations 中 Tool failure 的排除必须有机械程序（replay + 信号比对），不允许 investigator 自由心证。

## evidence

AgentRewardBench（LLM judge 与 GUI agent 行为判定的幻觉偏差）：
https://openreview.net/forum?id=ri3yPWE21Q
GUI agent 可靠性综述（action hallucination、初始条件脆弱性）：
https://arxiv.org/html/2502.08047v4
 grounding 幻觉缓解方向（意图解析与几何定位解耦）：
https://arxiv.org/html/2604.17284v1

## benchmark_impact

improved（Reproduction Success 与 Evidence Completeness 的测量基座；Group A baseline 因无机械验证层，此项天然成为组间差异的受控变量之一）。

## alternatives

- 信任 Stagehand/Browser Agent 的成功回报——与其自身 loop 的黑盒性冲突，Browser Agent 已被定位为 executor（§13.7），不应让 executor 定义事实。

## decision

采纳。写进 T003（Action / Outcome / Trace）验收标准。

---

# 附：引文清单与证据强度标注

一级学术文献：
- Barr, Harman, McMinn, Shahbaz, Yoo. The Oracle Problem in Software Testing: A Survey. IEEE TSE 41(5), 2015. https://ieeexplore.ieee.org/document/6963470
- Segura et al. A Survey on Metamorphic Testing. IEEE TSE 2016. https://eprints.whiterose.ac.uk/id/eprint/110335/1/segura16-tse.pdf
- Luo et al. An Empirical Analysis of Flaky Tests. FSE 2014（51 项目 / 201 修复提交）. https://www.semanticscholar.org/paper/363c9c645dc8c303c3d7ad995f60beae32ce10fa
- Doyle. A Truth Maintenance System. AI Journal, 1979. https://dspace.mit.edu/entities/publication/5377b306-4ecc-4687-b1f5-78cbb4a0543a
- de Kleer. An Assumption-based TMS. AI Journal, 1986. https://www.semanticscholar.org/paper/ed3f9263e936a879092ad7a2bf27e0f94089ccd8

一手工业来源：
- AWS Builders' Library. Making Retries Safe with Idempotent APIs. https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- Google Testing Blog. Flaky Tests at Google and How We Mitigate Them (2016). https://testing.googleblog.com/2016/05/flaky-tests-at-google-and-how-we.html

方法论参考：
- CONSORT 2025 outcomes prespecification. https://www.consort-spirit.org/item14-outcomes
- Pre-registration anti-bias rationale. https://phdontrack.net/good-research-practices/preregistration/
- Confounding variables. https://www.scribbr.com/methodology/confounding-variables/

佐证级（实践综述，不作单源支撑）：
- AgentRewardBench. https://openreview.net/forum?id=ri3yPWE21Q
- GUI Agents 可靠性综述. https://arxiv.org/html/2502.08047v4
- Grounding 解耦缓解. https://arxiv.org/html/2604.17284v1
- Grounded memory / provenance laundering 实践讨论. https://mem0.ai/blog/reducing-hallucinations-llms-with-grounded-memory

诚实声明：
- Luo et al. FSE 2014 仅用于支持"test-order dependence / 共享状态类成因存在且规模可观"，不引用具体根因排名（排名以论文表格核实为准）。
- 一处措辞纠正：不在正文使用 "exactly-once is a myth" 作为 AWS 原话；采用 ADR-001 术语声明中的准确转述。
- Barr et al. TSE 2015 作者名单核对无误；Oracle survey 内容要点（oracle 多源、非完备）与其摘要一致。
