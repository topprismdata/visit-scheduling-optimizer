# TopPrism L3 业务动力学与状态转移引擎详细规范 v1.0 (Dynamics & State Transition Engine Spec)

**Document ID:** TOPPRISM-L3-DYNAMICS-TRANSITION-ENGINE-SPEC-v1.0  
**Version:** **v1.0-draft.2 (Phase 3 Detailed Specification - Corrected)**  
**Date:** 2026-08-24  
**Status:** **DETAILED SUBSYSTEM SPECIFICATION (NOT YET FROZEN)**  
**上游约束:** 
- `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md` (产品层级与上位约束)
- `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2)
- `WORLD_MODEL_SYSTEM_BOUNDARY.md` (L3 归属 World Model 动力学层)
- `CANONICAL_TYPE_REGISTRY.md` (类型权威登记)

---

## 一、L3 动力学引擎的核心定位与架构责任

L3 业务动力学与状态转移引擎是 **Prism Enterprise World Model 的“物理法则与因果律中枢”**。
它的核心职责不是做规划决策，而是：
1. **掌控状态转移的合法性 (State Transition Legality)**: 依据业务守卫（Guards）判定状态转移请求是否被允许；
2. **保证因果与事实不可篡改 (Causal Integrity & Event Sourcing)**: 每次合法的状态转移必须生成包含全要素指纹的 `StateTransitionRecord` 并沉淀入事实流；
3. **保证演化的双时态确定性 (Bitemporal Determinism)**: 相同基线状态 + 相同事件参数 $\implies$ 100% 产生确定性的新快照状态。

---

## 二、状态转移有限状态机与前置守卫矩阵 (Guarded Transition Matrix)

### 2.1 任务生命周期状态机拓扑

$$\text{PROPOSED} \xrightarrow{\text{Guard P}} \text{PLANNED} \xrightarrow{\text{Guard A}} \text{COMMITTED} \xrightarrow{\text{Guard C}} \text{IN\_PROGRESS} \xrightarrow{\text{Guard B}} \text{COMPLETED}$$
$$\text{COMMITTED / IN\_PROGRESS} \xrightarrow{\text{Guard D}} \text{MISSED} \xrightarrow{\text{Guard E}} \text{DEFERRED} \xrightarrow{} \text{PLANNED}$$

### 2.2 守卫条件形式化判定规则与待签署标注

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        五大核心业务守卫形式化逻辑 (Guard A ~ E)                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard A: 承诺锁定审批守卫 (PLANNED -> COMMITTED)】                                  │
│  • 前置条件: transition_request.approver_id 必须非空且具备有效权限                     │
│  • 判定逻辑: assert(approver_id is not None and len(approver_id.strip()) > 0)          │
│  • 违规处理: 抛出 GuardRejected("Guard A Failed: approver_id required")                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard B: 履约完成时长与政策快照守卫 (IN_PROGRESS -> COMPLETED)】                    │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on 10 min threshold]  │
│  • 前置条件: service_duration_min >= 10.0 且 policy_version_snapshot 必须存在         │
│  • 判定逻辑: assert(service_duration_min >= 10.0 and policy_version_snapshot is not None)│
│  • 违规处理: 抛出 GuardRejected("Guard B Failed: duration < 10m or policy missing")    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard C: 强制现场 GPS 证据守卫 (COMMITTED -> IN_PROGRESS)】 (Fail-Closed)            │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on 500m threshold]    │
│  • 前置条件: gps_deviation_meters 必须显式传入 (不可为 None) 且 <= 500.0 米           │
│  • 判定逻辑: assert(gps_deviation_meters is not None and gps_deviation_meters <= 500.0)│
│  • 违规处理: 缺 GPS 抛 GuardRejected("Missing GPS")；超限抛 GuardRejected("GPS > 500m")│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard D: 时区安全的失访时间事实判定守卫 (COMMITTED -> MISSED)】                     │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on EOD cutoff]        │
│  • 时区处理: 构造带时区截止时刻 aware_scheduled_end = datetime.combine(               │
│               scheduled_date, time(23, 59, 59), tzinfo=context.timezone_obj)          │
│  • 判定逻辑: assert(event_time >= aware_scheduled_end) (安全时区感知比较)              │
│  • 违规处理: 抛出 GuardRejected("Guard D Failed: Cannot mark MISSED before day ends")  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard E: 顺延政策配额与窗口守卫 (MISSED/COMMITTED -> DEFERRED)】                     │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on DeferralPolicy]    │
│  • 字段对齐: 严格对齐 DeferralPolicy.max_deferral_window_days 与 max_deferrals_per_period│
│  • 窗口判定: delta_days = (event_time.date() - scheduled_date).days                    │
│  • 判定逻辑: assert(0 <= delta_days <= policy.max_deferral_window_days and             │
│                     prior_deferrals + 1 <= policy.max_deferrals_per_period)           │
│  • 违规处理: 抛出 DeferralQuotaExceeded / DeferralWindowExceeded                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、双时态状态演化与事件溯源实现细节

### 3.1 转移执行函数签名与不变量 (规范对外 API vs 内部实现)

- **对外 Canonical API**: `request_transition(context, workflow, transition_request) -> TransitionResult`
- **内部实现函数**: `_execute_guarded_transition_internal(...) -> Tuple[OperationalDecisionWorldState, OperationalVisitLifecycleRecord, StateTransitionRecord]` *(明确标注为内部实现)*

### 3.2 审计哈希计算规范 (RFC 8785 Canonical JSON + 256-bit SHA-256)

**算法规则**:
```python
audit_hash = SHA256(
    rfc8785_canonical_json({
        "visit_id": visit_id,
        "base_snapshot_id": base_snapshot_id,
        "from_status": from_status.value,
        "to_status": to_status.value,
        "event_time": event_time_utc_iso8601,          # UTC ISO 8601, e.g. "2026-06-04T01:00:00Z"
        "transaction_time": transaction_time_utc_iso,   # UTC ISO 8601
        "approver_id": approver_id or "NONE",
        "gps_deviation_meters": str(gps_deviation_meters or "NONE"),
        "service_duration_min": str(service_duration_min or "NONE"),
        "policy_version_snapshot": policy_version_snapshot or "NONE",
        "evidence_refs": sorted(evidence_refs)           # Tuple of str, lexicographically sorted
    })
)
```

**关键约束**:
1. **RFC 8785 Canonical JSON**: 键名字典序排列、无多余空白、UTF-8 编码；严禁使用未定义分隔符的手工字符串拼接；
2. **空值编码**: 缺失字段统一编码为字符串 `"NONE"`，严禁隐式跳过或省略；
3. **数值规范化**: `float` 经 RFC 8785 数字格式化后转为字符串；`Decimal` 转为无尾随零的十进制字符串；
4. **时间序列化**: 所有 `datetime` 统一转为 UTC 后格式化为 `YYYY-MM-DDTHH:MM:SSZ`；
5. **标准输出**: **256-bit SHA-256 digest represented as 64 hexadecimal characters**（绝无缩短截断）；
6. **请求指纹参与**: 服务端计算的 `RequestFingerprint` **纳入** 哈希输入的 `"request_fingerprint"` 字段。

---

## 四、阶段状态声明

- **规范版本**: `v1.0-draft.2`
- **状态**: 修正完成，作为 Phase 3 详细规范沉淀，**等待 Phase 1 业务语义签署完成后与整体 API 共同冻结**。
