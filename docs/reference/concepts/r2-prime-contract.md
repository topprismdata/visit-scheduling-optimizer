# 概念：R2′ 星期几一致契约

> 类别：横切概念——**业务主契约**，日历层所有算法（r2_alns / bp_solo / sp_cg 的 r2_prime 模式）都在其约束下工作

## 一句话（业务语义）

门店可以从周一改到周四，但**改了就全月一致**——第 N 周在周二，之后每周都在周二。即：整店换星期几（weekday reassignment）是允许的；同店在不同星期几之间**分裂**（如月初周一、月末周四）是禁止的。

## 为什么是这个形态

业务真实性：SRP 原始计划 1,524 家店**零例外**地满足"合同+相位"推导出的星期几一致模式。三次语义修正（月频次→均匀节拍→合同-相位）最终定稿为：合同 ∈ {周访, 双周访(奇偶相位 φ∈{0,1})}，`服务周` 字段 = ISO 周 mod 4，全量与原计划**集合相等**重构验证通过。

## 形式定义

- 每店 c 的合法自由度 = **整店换星期几**（如周一→周二，全月生效）+ **同星期几槽位轮换**（该星期几内的日期子集选择，由合同 κ 与相位 φ 决定）。
- 合法日期域：`legal_date_map(contracts, dates)`；合法槽位集：`contract_slot_dates(kappa, phi, slots)`。
- 校验：`check_r2prime(days)` 返回跨星期几分裂的店列表（非空即违例）。

## 实现位置

| 组件 | 位置 |
|---|---|
| 语义核心（合同/相位/合法域） | VisitIR 仓：`visit_ir.contract`（`contract_of / check_contract / contract_slot_dates / legal_date_map / phase_of`） |
| 母仓兼容 shim | `core/contract.py`（re-export，剥离计划 Task 7 将移除） |
| SP 终闸的 R2′ 线性化 | `visitmodel.sp.formulation`：z 选择器 + x≤z 绑定（见 [set-partitioning-final-gate.md](set-partitioning-final-gate.md)） |
| 原生搜索算子 | `algos/r2_alns.py::move_candidates(combo_mode="contract")` |
| 独立校验函数 | `algos/sp_matheuristic.py::check_r2prime` |

## 重要辨析（不要混淆）

| 口径 | 是否主线契约 |
|---|---|
| R2′：整店换星期几 + 槽位轮换 | ✅ 主线 |
| 完全锁死原星期几（一字不动） | ❌ 旧口径，非主线 |
| 任意跨日移动（允许同店跨星期几分裂） | ❌ 违约；跨星期几分裂实验单独报告，禁止与主线混用 |
| v4 微调 `same_weekday_only=True` | 仅同星期几内互挪（不含换星期几自由度）——微调场景语义，勿与主线混用 |

## 边界警告

- **W53 断裂**：ISO 周 mod 2 相位在 53 周年（如 2026）边界 parity 断裂；单月 scope 内与连续周锚点数值等价，**跨月使用前必须做锚点实验**。
- 双周店（f=1、κ=双周）的"次数"由相位决定——62 家原"f=3"实为双周奇相位挂 5 槽，切勿把频次当独立参数。

## 相关文档

- 语义三次修正全程：`docs/guides/ALGORITHM_GUIDE.md` 附录 D
- 合同-相位本体独立仓：`/Users/ghb/VisitIR`（设计裁决 `docs/DESIGN_DECISIONS_v0.1.md`）
