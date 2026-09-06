# Canonical Type Registry v1.0

**Document ID:** TOPPRISM-CANONICAL-TYPE-REGISTRY-v1.0  
**Version:** **v1.0-draft.5.2 (L0~L7 Full Taxonomy Synced)**  
**Date:** 2026-08-24  
**Status:** **CANONICAL TYPE SOURCE-OF-TRUTH (全系统唯一权威类型登记册)**  
**上游约束:** `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md`  
**主规范关联:** `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2)

---

## 一、L0~L7 全层级公共类型权威登记表

| 类型名称 | 权威定义规范路径 | 归属层级 | 核心结构 / 说明 | 消费方 |
| :--- | :--- | :--- | :--- | :--- |
| **`FrozenScalar`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §17 | L1 | `Union[str, int, float, bool, bytes, datetime, date, time, Decimal, UUID, Enum, None]` | 全系统 |
| **`FrozenValue`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §18 | L1 | `Union[FrozenScalar, Tuple['FrozenValue', ...], Mapping[str, 'FrozenValue']]` | 全系统 |
| **`ApiRequestContext`** `[API-INFRA]` | 主 API 规范 §2.1 | L0 | `(api_version, request_id, caller_id, source_system, timezone)` (必须有时区) | L0~L7 |
| **`RequestFingerprint`** `[API-INFRA]` | 主 API 规范 §2.2 / §5.2.1  | L0 | `(fingerprint_id, server_computed=True)` (RFC 8785 256-bit SHA-256) | L3, L7 |
| **`WorkflowContext`** `[API-INFRA]` | 主 API 规范 §5.2.1 | L0 | `(expected_snapshot_version, idempotency_key, fingerprint)` | L3, L7 |
| **`BitemporalPeriod`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §1 | L0 | `(valid_from, valid_to, transaction_from, transaction_to)` | L0~L7 |
| **`GeoCoordinate`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §2 | L0 | `(longitude, latitude)` (WGS-84) | L0~L7 |
| **`DerivedDepotEstimate`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §3 | L4 | `(rep_id, inferred_centroid, sample_points_count, confidence_score)` (`DERIVED`) | L4, L6 |
| **`OperationalCustomer`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §4 | L4 | `(store_code, store_name, tier, ka_name, district, location, geo_quality, ...)` | L4, L6 |
| **`OperationalResource`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §5 | L4 | `(rep_id, rep_name, region, sub_region, city, depot_estimate, ...)` | L4, L6 |
| **`AccountHierarchyEntity`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §15 | L2/L4 | `(account_id, account_name, channel_tier, parent_account_ref, ...)` | L2, L4 |
| **`ProductLineScopeEntity`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §16 | L2/L4 | `(brand_id, brand_name, strategic_role, default_action_types)` | L2, L4 |
| **`SupplyNodeEntity`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §6 | L2/L4 | `(dc_id, dc_name, served_ka_names, delivery_status="UNCALIBRATED")` | L2, L4 |
| **`OperationalVisitPolicy`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §7 | L2/L4 | `(policy_id, policy_version[过渡保留, 见§7注], store_code, target_frequency_per_month, ...)` | L2, L3, L4 |
| **`PolicyAmendment`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §37 | L2/L4 | `(amendment_id, policy_id, amended_at, field_name, previous_value, new_value, reason, approved_by, bitemporal)` | L2, L3, L4 |
| **`OwnershipAssignment`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §38 | L2/L4 | `(assignment_id, store_code, rep_id, effective_from, effective_to, reason, approved_by, transaction_from, status)` | L2, L3, L4, L6 |
| **`DeferralPolicy`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §8 | L2/L3 | `(policy_id, policy_version, bitemporal, max_deferrals_per_period, max_deferral_window_days, ...)` | L2, L3 |
| **`OperationalCommitment`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §9 | L2/L4 | `(commitment_id, store_code, rep_id, locked_date, lock_level)` | L2, L4, L6 |
| **`InStoreActionFact`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §10 | L2/L4 | `(action_type, estimated_duration_min, action_notes)` | L2, L4, L6 |
| **`MerchandisingComplianceFact`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §11 | L2/L4 | `(contract_target_units, actual_compliant_units, compliance_ratio, ...)` | L2, L4 |
| **`OperationalVisitLifecycleRecord`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §12 | L3/L4 | `(visit_id, store_code, rep_id, scheduled_date, current_status, status_history)` | L3, L4 |
| **`ActualVisitEvent`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §13 | L4 | `(event_id, store_code, rep_id, visit_date, service_duration_min, ...)` | L4, L7 |
| **`OperationalDecisionWorldState`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §14 | L4 | `(snapshot_id, bitemporal, manifest, customers, ..., active_scenario_branches)` Canonical WorldState 聚合根 | L3~L7 |
| **`StateTransitionRecord`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §19 | L3 | `(transition_id, visit_id, base_snapshot_id, from_status, to_status, ...)` | L3, L7 |
| **`TransitionRequest`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §20 | L3 | `(visit_id, target_status, triggering_event_ref, event_time, transaction_time, ...)` | L3, L7 |
| **`TransitionResult`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §21 | L3 | `(new_worldstate_snapshot_id, transition_record, audit_hash, was_guard_passed)` | L3, L7 |
| **`ExecutionFeedbackReceipt`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §33 | L4 | `(event_id, new_snapshot_id, transition_required, evidence_status)` | L4, L7 |
| **`PerturbationEvent`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §22 | L5 | `(perturbation_id, perturbation_type, affected_entity_refs, payload)` | L5 |
| **`StateDelta`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §23 | L5 | `(changed_fields: Mapping[str, Tuple[FrozenValue, FrozenValue]], ...)` | L5, L7 |
| **`ScenarioResult`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §24 | L5 | `(base_snapshot_id, scenario_id, branch_hash, delta_state, aggregate_metrics_delta)` | L5, L7 |
| **`PlannerNodeTopology`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §25 | L6 | `(node_index, domain_entity_id, spatial_coordinate, service_duration_min, is_depot)` | L6, L7 |
| **`PlannerStateProjection`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §34 | L6 | `(projection_id, target_agent_id, nodes, travel_cost_matrix, candidate_pattern_space, ...)` | L6, L7 |
| **`PartialProjectionAuthorization`** `[API-INFRA]` | 主 API 规范 §4.2 | L6 | `(authorization_id, actor_id, scope, snapshot_id, intent_id, nonce, status)` | L6, L7 |
| **`AuthorizationStatus`** `[API-INFRA]` | 主 API 规范 §4.1 | L0 | AVAILABLE / RESERVED / CONSUMED / ROLLED_BACK 四状态 | L0, L6 |
| **`PlanningIntent`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §26 | L7 | `(intent_id, decision_scope, target_agent_id, valid_time, objectives, constraints, ...)` | L6, L7 |
| **`PlannedStop`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §27 | L7 | `(stop_idx, store_code, store_name, district, planned_service_min, ...)` | L7 |
| **`PlannedDailyRoute`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §28 | L7 | `(date_str, weekday_name, rep_id, stops, total_daily_distance_km, total_daily_workload_min)` | L7 |
| **`CandidatePlan`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §29 | L7 | `(plan_id, intent_id, target_agent_id, period_label, daily_routes, solver_status)` | L7 |
| **`PlanAuditReport`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §31 | L7 | `(plan_id, is_fully_compliant, cadence_compliance_rate, dimension_results)` | L7 |
| **`DecisionArtifact`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §32 | L7 | `(artifact_id, candidate_plan_ref, audit_report_ref, approved_by, published_schedule)` | L7 |
| **`WorldModelError`**（含16子类）`[API-INFRA]` | 主 API 规范 六、异常类体系 | L0 | 标准异常体系（统一 `default_code` 属性与标准构造） | 全系统 |

---

| **`LifecycleStatus`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.1 | L1 | 8 值 str 枚举 (PROPOSED..CANCELLED) | L3, L4, L7 |
| **`CognitiveCategory`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.2 | L1 | 7 值认知类别枚举 | L0~L7 |
| **`FulfillmentClass`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.3 | L1 | REQUIRED / COMMITTED / OPTIONAL | L2, L4 |
| **`GeoQualityStatus`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.4 | L1 | EXACT_MATCH / UNMAPPED | L4, L6 |
| **`ChannelTier`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.5 | L1 | NKA / RKA / LOCAL_KEY / TRADITIONAL | L2, L4 |
| **`StatusTransitionEntry`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.6 | L3 | `(from_status, to_status, changed_at, reason)` | L3, L4 |
| **`SourceManifest`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.7 | L0 | `(source_file_path, source_file_sha256, assembled_at, ...)` | L4 |
| **`CadenceRule`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.8 | L2 | `(rule_id, target_frequency_per_month, cadence_type, exact_interval_days)` | L2, L3 |
| **`OwnershipConflictRecord`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.9 | L2 | `(store_code, store_name, conflicting_reps)` | L2, L4 |
| **`PolicyRegistry`** | TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md §35.10 | L2 | `(cadence_rules, ownership_map, ownership_conflicts, operational_policies, deferral_policies)` | L2, L3, L4 |

## 二、类型治理与唯一引用铁律

1. **唯一权威定义**: 上述类型只能在其标注的“权威定义规范路径”中进行数据结构修改，严禁在其他规范中自行声明冲突定义；
2. **消灭 `Any` 逃逸**: 所有公共 API 输入输出集合必须采用 `FrozenValue` 或强类型 dataclass；
3. **跨文档同步校验**: 任何规范文档在引用上述类型时，必须使用本文档登记的精确名称与版本。
