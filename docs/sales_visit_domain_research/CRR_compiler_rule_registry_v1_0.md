# Compiler Rule Registry v1.0
## Phase 3 编译规范候选规则登记簿（防 Domain 污染的隔离层）

> **文档标识**：`CRR-COMPILER-RULE-REGISTRY-V1.0`  
> **定位**：OBS 观察（不构成 DCR 的解释规则缺口）**不得直接写入代码、不得升级为 Domain 字段**，先登记于此；Phase 3 Compiler Specification 逐条吸收为正式编译规则。  
> **纪律**：本簿条目 Domain impact 一律为 None；若某条最终确需 Domain 字段，必须走 DCR 并附 Failure Evidence。

| 规则 ID | 名称 | 触发输入 | 条件 | 解释 | 层 | Domain impact | 来源 |
|---|---|---|---|---|---|---|---|
| CR-COMPILER-C-001 | Stale Anchor Rebase Rule | ExecutionHistory.last_visit | eligible_window 终点 < horizon_start（如 L+max_gap 已过） | 参考锚点重置为 horizon_start（逾期客户立即具备资格）；eligible = [horizon_start, horizon_start + max_gap] | Compiler / OccurrenceGenerator | **None**（CadenceSpec.reference_period_days + ExecutionHistory 足以表达） | S-C OBS-C-1 |
