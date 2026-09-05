# TopPrism FMCG Visit Scheduling Optimizer · Documentation Hub

> **Documentation Standard**: Aligned with Google Engineering Documentation Best Practices (Diátaxis Framework & Swe-Book Ch. 10)  
> **Repository Constitution**: All technical rules and invariants are governed by [`../AGENTS.md`](../AGENTS.md).

---

## 1. Directory Structure Overview (目录分层结构)

本项目文档严格按照**受众与目标职责（Audience & Purpose）**进行四层解耦管理，彻底杜绝扁平堆叠与历史过时文件混淆：

```text
docs/
├── README.md                      # [Navigation Hub] 本文档：全局文档导航地图与阅读指引
│
├── design/                        # [System Design & RFCs] 架构蓝图与核心算法设计
│   ├── SYSTEM_DESIGN_DOC.md       # ★ Google 级系统设计主文档 (Master Architecture Spec)
│   ├── SP_MATHEURISTIC_DESIGN.md  # 对偶闭环列生成与集合划分设计 (基于 [META] 2025 & [ESF] 2020)
│   ├── V4_PARETO_STABILIZER_DESIGN.md # 多目标帕累托稳定器设计 (里程 ↔ 扰动改动量 ↔ 均衡度)
│   └── ARCHITECTURE_OVERVIEW.md   # 早期系统物理架构概览
│
├── benchmarks/                    # [Benchmarks & Empirical Evidence] 评测基准与实证总账
│   ├── TWO_STAGE_BENCHMARK_REPORT.md  # ★ 两阶段运筹全景帕累托基准报告 (单日+月度+消融+全办总账)
│   ├── PERFORMANCE_BENCHMARK.md       # 延迟与响应时间实测基准 (SLA 生产标定)
│   ├── ACTUAL_VS_AGENT_REPORT.md      # Layer 2 现场实际打卡 vs Agent 动态走廊插单实测报告
│   ├── MANUAL_10_DAYS_AUDIT.md        # 10 天人工白盒打卡抽查审计报告 (时间戳/地址级客户答辩)
│   ├── V4_PARETO_REPORT.md            # 多目标帕累托前沿实测报告
│   └── AUDIT_REPORT.md                # 综合合规与历史对账审计记录
│
├── guides/                        # [Technical Guides & Monograph] 技术指南与专著
│   ├── ALGORITHM_GUIDE.md             # 算法机制技术指南 (规范命名映射 + 20+ 篇顶刊文献 DOI)
│   └── AGENTIC_DISPATCH_GUIDE.md      # Layer 2 现场动态调度副驾技术专著 (沿街走廊投影)
│
├── figures/                       # [Visual Assets] 架构图、技术图表与可视化资产
│
└── archive/                       # [Historical & Superseded Artifacts] 历史归档 (非破坏性封存)
    ├── phase_designs/                 # Phase 1 ~ 3 阶段性设计历史草稿
    ├── architecture_evolution/        # Architecture v5.0 ~ v5.4 演化草稿
    ├── deprecated/                    # 明确废弃方案 (旧 V4 v1设计稿, 旧 V1_V3 对比)
    ├── research_drafts/               # 学术工作论文草稿 (paper_draft, algorithm.md)
    └── sales_visit_domain_research/   # 早期领域调研与知识库资产
```

---

## 2. Reviewer Reading Paths (评审人定向阅读路径)

根据评审人的背景与职责，推荐以下最优阅读路径：

### 路径 A：系统架构师 / 技术委员会（关注整体架构、正确性、扩展性与权衡）
1. [`design/SYSTEM_DESIGN_DOC.md`](design/SYSTEM_DESIGN_DOC.md) —— Google 级系统设计主文档，审阅 Goals/Non-Goals、两阶段数学架构解耦、未选方案深度权衡（Trade-offs）；
2. [`benchmarks/TWO_STAGE_BENCHMARK_REPORT.md`](benchmarks/TWO_STAGE_BENCHMARK_REPORT.md) —— 审阅矩阵一（单日 TSP 秒级证明最优）、矩阵三（反馈耦合消融收益）；
3. [`../AGENTS.md`](../AGENTS.md) —— 项目宪法与双向作业走廊红线。

### 路径 B：运筹学专家 / 算法科学家 / 郭老师团队（关注数学严谨性、最优性证书与顶刊对齐）
1. [`design/SP_MATHEURISTIC_DESIGN.md`](design/SP_MATHEURISTIC_DESIGN.md) —— 对偶价格经济学解释、定价子问题与收敛性证明；
2. [`benchmarks/TWO_STAGE_BENCHMARK_REPORT.md`](benchmarks/TWO_STAGE_BENCHMARK_REPORT.md) —— 矩阵一（CP-SAT 在城市路网全面优于 LKH 的实证）、全办认证 Gap $\le 1.14\%$；
3. [`guides/ALGORITHM_GUIDE.md`](guides/ALGORITHM_GUIDE.md) —— 算法机制细节与 20+ 篇顶刊 DOI 认证。

### 路径 C：业务高管 / 销售运营总监（关注投资回报率、员工体力红线与落地可行性）
1. [`benchmarks/TWO_STAGE_BENCHMARK_REPORT.md`](benchmarks/TWO_STAGE_BENCHMARK_REPORT.md) —— 全办 10 位业代真实总账：16,857 km $\to$ 3,865.6 km（**−77.1%**，净省 12,991 km），100% 走廊合规（杜绝单日 90 店或 4 店畸形日）；
2. [`benchmarks/MANUAL_10_DAYS_AUDIT.md`](benchmarks/MANUAL_10_DAYS_AUDIT.md) —— 6 条线路 6 位真实业代的一线打卡案例白盒还原；
3. [`guides/AGENTIC_DISPATCH_GUIDE.md`](guides/AGENTIC_DISPATCH_GUIDE.md) —— 27.4% 现场突发临时插单如何被 75~330 微秒走廊副驾平滑吸收。

---

## 3. Maintenance & Contribution Rules (维护纪律)

1. **新建设计文档**：必须落在 `docs/design/` 下，遵循 Google Design Doc 规范（必须包含 Context、Goals/Non-Goals、Alternatives Considered）；
2. **新建评测报告**：必须落在 `docs/benchmarks/` 下，所有里程与耗时必须来自 `output/` 实测数据文件；
3. **废弃旧方案**：严禁直接散落或随手删除，必须移入 `docs/archive/` 并在文档头部显著标记 `DEPRECATED` 与取代它的新文档链接；
4. **根目录禁止堆放杂文**：根目录仅保留 `README.md` 与宪法 `AGENTS.md`。
