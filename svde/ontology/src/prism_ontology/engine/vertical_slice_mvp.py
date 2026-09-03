"""Vertical Slice MVP Runner — Sales Visit Domain (Internal Replay Only)

Scope:
    输入 (WorldState fixture)
      -> Planner Projection Compiler (L6)
      -> SVDE Ontology Adapter (Domain)
      -> PeriodicPVRPSolver (Domain Solver)
      -> ThreeDimensionalPlanAuditor (3D Audit)
      -> DecisionArtifact (immutable output, INTERNAL only)

Strictly INTERNAL replay:
    - execution_mode = INTERNAL_VERTICAL_SLICE_MVP
    - canonical_api_status = NOT_IMPLEMENTED
    - external_dispatch = false
    - baseline_writeback = false
    - runtime_scope = LEGACY_SVDE_PIPELINE

NOT implemented (out of scope this round):
    - L5 multi-branch counterfactual engine
    - L7 Enterprise Decision Engine
    - ResourceAvailabilityLifecycle
    - Multi-Entity Transfer
    - ExecutionEventStore
    - SFA/CRM dispatch
    - Canonical API Freeze
    - Real WorldState writeback

Resource-unavailability scenario is modeled as an EXPLICIT TEST INPUT
(scenario_unavailable_rep_ids: Set[str]), NOT as a fake state machine.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any
import json

from prism_ontology.contracts.world_state import WorldState
from prism_ontology.contracts.planning_io import (
    PlanningIntent, PlanningCapabilityType, CandidatePlan,
    PlanAuditReport, DecisionArtifact,
)
from prism_ontology.reference.store import ReferenceOntologyStore
from prism_ontology.compiler.operational import OperationalCompiler
from prism_ontology.adapters.svde.bridge import SVDEOntologyAdapter
from prism_ontology.engine.periodic_pvrp_solver import PeriodicPVRPSolver
from prism_ontology.diagnostics.plan_auditor import ThreeDimensionalPlanAuditor
from prism_ontology.contracts.planning_io import DecisionArtifact
# BIZ 业务规则已冻结为实验性草案 (EXPERIMENTAL DRAFT, NOT SIGNED); 接入 MVP 默认路径前不可视为业务规则
# from prism_ontology.engine.biz_signing import BIZSigningRegistry, build_default_registry, ConstraintViolation


# ---------- MVP Scenario / Result 数据结构 ----------

@dataclass(frozen=True)
class ScenarioParameters:
    """显式情景参数：请假/资源不可用作为测试输入，不是状态机。"""
    scenario_id: str
    description: str
    # 该 rep_id 在情景中被视为"不可用" — 显式输入，不是伪造的 ActualVisitEvent
    scenario_unavailable_rep_ids: frozenset = field(default_factory=frozenset)
    # 必跑通过的硬约束 (来自历史真实业务基线)
    must_satisfy_min_audit_compliance_rate: float = 0.0


@dataclass(frozen=True)
class MVPResult:
    """MVP 输出 — 所有结果带元数据与可审计证据链。"""
    execution_mode: str
    canonical_api_status: str
    external_dispatch: bool
    baseline_writeback: bool
    runtime_scope: str
    scenario_id: str
    scenario_description: str
    scenario_unavailable_rep_ids: List[str]
    scenario_effect_applied: bool       # 结构化布尔: 资源不可用情景是否真实改变计划 (MVP 始终为 False — no-writeback control case)
    biz_rule_framework_loaded: bool     # 结构化布尔: BIZ 框架模块是否被加载 (MVP 正式基线 = False, BIZ 仍为 EXPERIMENTAL)
    biz_rules_effective: bool            # 结构化布尔: BIZ 业务规则是否已签署生效 (MVP 正式基线 = False, 业务方未签署前不得启用)
    run_timestamp: str
    source_world_state_snapshot_id: str
    source_world_state_path: str
    target_rep_id: str
    period_label: str
    candidate_plan_summary: Dict[str, Any]
    audit_report_summary: Dict[str, Any]
    constraint_violations: List[str]
    feasibility_judgment: str        # business feasibility: FEASIBLE / PARTIALLY_FEASIBLE / INFEASIBLE
    error_kind: Optional[str]         # system execution status: FEASIBLE / PARTIALLY_FEASIBLE / INFEASIBLE / PIPELINE_ERROR
    legacy_pipeline_steps: List[str]  # 哪些步骤仍走旧 Pipeline
    decision_artifact_preview: Dict[str, Any]  # DecisionArtifact dict 形式（不实际发布）
    notes: List[str] = field(default_factory=list)

    def to_audit_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_audit_json(self) -> str:
        return json.dumps(self.to_audit_dict(), ensure_ascii=False, indent=2, default=str)


# ---------- MVP Runner 主类 ----------

class VerticalSliceRunner:
    """Vertical Slice MVP Runner — 可运行 / 可审计 / 内部回放"""

    MVP_METADATA = {
        "execution_mode": "INTERNAL_VERTICAL_SLICE_MVP",
        "canonical_api_status": "NOT_IMPLEMENTED",
        "external_dispatch": False,
        "baseline_writeback": False,
        "runtime_scope": "LEGACY_SVDE_PIPELINE",
    }

    def __init__(self, store: Optional[ReferenceOntologyStore] = None,
                 compiler: Optional[OperationalCompiler] = None):
        # MVP 正式基线: 不包含 BIZ 业务规则注入 (BIZ 仍为 EXPERIMENTAL DRAFT, NOT SIGNED)
        self.store = store or ReferenceOntologyStore()
        self.compiler = compiler or OperationalCompiler(self.store)
        self.adapter = SVDEOntologyAdapter(self.store, self.compiler)

    def run(self,
            world_state: WorldState,
            target_rep_id: str,
            period_label: str,
            working_days: List[str],
            scenario: ScenarioParameters,
            run_timestamp: Optional[datetime] = None) -> MVPResult:
        """跑一遍垂直切片，输出可审计的 MVPResult。

        Args:
            world_state: 已装载的基线 WorldState (来自 fixture 或离线样本)
            target_rep_id: 排班目标代表
            period_label: 排班周期标签
            working_days: 排班工作日列表
            scenario: 显式情景参数 (含 unavailable_rep_ids)
            run_timestamp: 显式运行时间戳（禁用 datetime.now() 默认值）
        """
        # run_timestamp MUST be explicit (no silent datetime.now() default)
        if run_timestamp is None:
            raise ValueError(
                "MVP requires explicit run_timestamp (no silent datetime.now() fallback). "
                "This is documented in MVP README §5 'Strict Red Lines'."
            )
        if not isinstance(run_timestamp, datetime):
            raise TypeError(
                f"run_timestamp must be datetime instance, got {type(run_timestamp).__name__}"
            )
        run_ts_str = run_timestamp.isoformat()

        notes = []
        legacy_steps = []

        # ---- Step 1: 构建 PlanningIntent (LEGACY SVDE Pipeline) ----
        legacy_steps.append("PlanningIntent construction (legacy: uses PlanningCapabilityType)")
        intent = PlanningIntent(
            intent_id=f"MVP_INTENT_{scenario.scenario_id}_{target_rep_id}",
            capability_type=PlanningCapabilityType.PERIODIC_VISIT_PLANNING,
            target_rep_id=target_rep_id,
            target_horizon_label=period_label,
            working_days=tuple(working_days),
            max_daily_stops=6,
            max_daily_workload_min=480.0,
            same_weekday_required=True,
        )

        # ---- Step 2: Bridge Adapter Dispatch (LEGACY) ----
        legacy_steps.append("SVDEOntologyAdapter.dispatch_planning_intent (legacy adapter)")
        try:
            payload = self.adapter.dispatch_planning_intent(intent, world_state)
            dispatch_ok = payload.get("dispatch_status") == "READY_FOR_SOLVER"
        except Exception as e:
            payload = None
            dispatch_ok = False
            notes.append(f"BRIDGE_DISPATCH_FAILED: {e!r}")

        # ---- Step 3: PeriodicPVRPSolver (LEGACY) ----
        if dispatch_ok:
            legacy_steps.append("PeriodicPVRPSolver.solve (legacy solver)")
            try:
                candidate_plan = PeriodicPVRPSolver.solve(payload)
                solver_ok = True
                solver_err = None
            except Exception as e:
                candidate_plan = None
                solver_ok = False
                solver_err = repr(e)
                notes.append(f"SOLVER_FAILED: {solver_err}")
        else:
            candidate_plan = None
            solver_ok = False
            solver_err = "bridge dispatch failed"

        # ---- Step 4: ThreeDimensionalPlanAuditor (LEGACY) ----
        audit_report = None
        if candidate_plan is not None:
            legacy_steps.append("ThreeDimensionalPlanAuditor.audit_candidate_plan (legacy auditor)")
            try:
                audit_report = ThreeDimensionalPlanAuditor.audit_candidate_plan(candidate_plan, world_state)
                audit_ok = True
                audit_err = None
            except Exception as e:
                audit_ok = False
                audit_err = repr(e)
                notes.append(f"AUDITOR_FAILED: {audit_err}")
        else:
            audit_ok = False
            audit_err = "no candidate plan"

        # ---- Step 4.5: BIZ 业务规则校验 (EXPERIMENTAL DRAFT, NOT SIGNED — MVP 正式基线不触发) ----
        # biz_violations 始终为空 (BIZ 框架未启用, 不叠加到 constraint_violations)
        biz_violations: List[ConstraintViolation] = []

        # ---- Step 5: DecisionArtifact Preview (INLINE — 不调旧 DecisionPipelineRunner，因其用 datetime.now()) ----
        decision_preview = None
        if audit_report is not None and candidate_plan is not None:
            legacy_steps.append("DecisionArtifact inline construction (NOT via DecisionPipelineRunner — avoids datetime.now() violation)")
            try:
                published_schedule = {
                    route.date_str: [s.store_code for s in route.stops]
                    for route in candidate_plan.daily_routes
                }
                if not published_schedule:
                    raise ValueError("candidate_plan.daily_routes is empty; cannot construct DecisionArtifact")
                artifact_id = f"DECISION_ART_PREVIEW_{candidate_plan.rep_id}_{candidate_plan.period_label}_{run_ts_str.replace(':','').replace('-','').replace('+','-')[:15]}"
                artifact = DecisionArtifact(
                    artifact_id=artifact_id,
                    candidate_plan_ref=candidate_plan.plan_id,
                    audit_report_ref=audit_report.plan_id,
                    approved_by=f"MVP_INTERNAL_APPROVER_{scenario.scenario_id}",
                    approved_at=run_timestamp,  # 使用显式 run_timestamp，禁用 datetime.now()
                    published_schedule=published_schedule,
                    status="MVP_PREVIEW",  # 不是 APPROVED_FOR_EXECUTION — 避免业务方误解为已批准
                )
                decision_preview = {
                    "artifact_id": artifact.artifact_id,
                    "candidate_plan_ref": artifact.candidate_plan_ref,
                    "audit_report_ref": artifact.audit_report_ref,
                    "approved_by": artifact.approved_by,
                    "approved_at": artifact.approved_at.isoformat(),
                    "published_schedule": artifact.published_schedule,
                    "status": artifact.status,  # "MVP_PREVIEW"
                    "approval_simulated": True,  # 显式声明是模拟批准，非真实审批
                    "external_dispatch": False,  # 与 execution_mode 元数据一致
                    "baseline_writeback": False,  # 与 execution_mode 元数据一致
                    "_preview_warning": "INTERNAL MVP preview — NOT a real approval. NOT dispatched. baseline_writeback=false. canonical_api_status=NOT_IMPLEMENTED. Resource availability NOT actually applied.",
                }
            except Exception as e:
                notes.append(f"DECISION_ARTIFACT_FAILED: {type(e).__name__}: {e}")

        # ---- Step 6: 资源不可用情景的影响 (显式注入,非状态机) ----
        # 情景只是描述输入约束；MVP 不实现 ResourceAvailabilityLifecycle
        unavailable_intersect = scenario.scenario_unavailable_rep_ids & {target_rep_id}
        if unavailable_intersect:
            notes.append(
                f"Scenario explicitly marks rep '{target_rep_id}' as unavailable. "
                f"scenario_effect_applied=false — MVP does NOT modify WorldState and does NOT perform real reassignment/deferral. "
                f"This is a no-writeback control case for input-validation testing only. "
                f"Caller is responsible for downstream handling."
            )

        # ---- Step 7: 评估可行性 + 系统错误分类 ----
        feasibility, error_kind = self._judge_feasibility_and_error(
            dispatch_ok, solver_ok, audit_ok, audit_report, scenario
        )
        constraint_violations = []
        if audit_report is not None:
            constraint_violations = list(audit_report.violations) if hasattr(audit_report, "violations") and audit_report.violations else []
        # BIZ 校验违反不叠加 (MVP 正式基线, BIZ 框架未启用)

        # ---- Step 8: 组装 MVPResult ----
        candidate_summary = self._summarize_plan(candidate_plan) if candidate_plan else {}
        audit_summary = self._summarize_audit(audit_report) if audit_report else {}

        snapshot_id = getattr(world_state, "snapshot_id", "UNKNOWN")
        manifest = getattr(world_state, "manifest", None)
        manifest_path = getattr(manifest, "source_file_path", "UNKNOWN") if manifest else "UNKNOWN"

        return MVPResult(
            **self.MVP_METADATA,
            scenario_id=scenario.scenario_id,
            scenario_description=scenario.description,
            scenario_unavailable_rep_ids=list(scenario.scenario_unavailable_rep_ids),
            scenario_effect_applied=False,  # MVP 不实现真实改派/延期 (no-writeback control case)
            run_timestamp=run_ts_str,
            source_world_state_snapshot_id=snapshot_id,
            source_world_state_path=manifest_path,
            target_rep_id=target_rep_id,
            period_label=period_label,
            candidate_plan_summary=candidate_summary,
            audit_report_summary=audit_summary,
            constraint_violations=constraint_violations,
            biz_rule_framework_loaded=False,  # MVP 正式基线: BIZ 框架未启用 (EXPERIMENTAL DRAFT)
            biz_rules_effective=False,      # MVP 正式基线: 业务方未签署前不得启用 BIZ 规则
            feasibility_judgment=feasibility,
            error_kind=error_kind,
            legacy_pipeline_steps=legacy_steps,
            decision_artifact_preview=decision_preview,
            notes=notes,
        )

    # --- 辅助 ---

    @staticmethod
    def _judge_feasibility_and_error(dispatch_ok: bool, solver_ok: bool, audit_ok: bool,
                                      audit_report, scenario) -> tuple:
        """返回 (feasibility_judgment, error_kind)
        - feasibility_judgment: business feasibility (FEASIBLE / PARTIALLY_FEASIBLE / INFEASIBLE)
        - error_kind: system execution status (FEASIBLE / PARTIALLY_FEASIBLE / INFEASIBLE / PIPELINE_ERROR)
        区分原则:
        - PIPELINE_ERROR: 至少一个 Pipeline 步骤（dispatch/solver/audit）失败
        - INFEASIBLE: Pipeline 跑通，但业务检查判定不可行（如 nonexistent rep 触发业务无解）
        """
        # 系统执行状态: Pipeline 任一步失败 → PIPELINE_ERROR
        if not dispatch_ok or not solver_ok or not audit_ok:
            error_kind = "PIPELINE_ERROR"
        else:
            error_kind = "FEASIBLE"  # 系统跑通
        # 业务可行性: 即使 Pipeline 跑通，无对应 rep 时 business 也无解
        if audit_report is None:
            # Pipeline 失败情况下
            if dispatch_ok is False:
                # Bridge 失败通常因为目标 rep 不在 WorldState 中
                return "INFEASIBLE", error_kind
            return "INFEASIBLE", error_kind
        if getattr(audit_report, "is_fully_compliant", False):
            return "FEASIBLE", error_kind
        # 至少部分可行 (有违规但不致命)
        if scenario.must_satisfy_min_audit_compliance_rate > 0:
            rate = getattr(audit_report, "cadence_compliance_rate", 0.0)
            if rate >= scenario.must_satisfy_min_audit_compliance_rate:
                return "PARTIALLY_FEASIBLE", error_kind
        return "PARTIALLY_FEASIBLE", error_kind

    @staticmethod
    def _summarize_plan(plan: CandidatePlan) -> Dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "rep_id": plan.rep_id,
            "period_label": plan.period_label,
            "solver_name": plan.solver_name,
            "solver_status": plan.solver_status,
            "total_scheduled_visits": plan.total_scheduled_visits,
            "total_monthly_transit_min": plan.total_monthly_transit_min,
            "total_monthly_distance_km": plan.total_monthly_distance_km,
            "daily_routes_count": len(plan.daily_routes),
            "daily_routes_summary": [
                {
                    "date_str": r.date_str,
                    "weekday_name": r.weekday_name,
                    "stops_count": r.stops_count,
                    "total_daily_workload_min": r.total_daily_workload_min,
                    "total_daily_distance_km": r.total_daily_distance_km,
                    "stops_codes": [s.store_code for s in r.stops],
                }
                for r in plan.daily_routes
            ],
        }

    @staticmethod
    def _summarize_audit(audit: PlanAuditReport) -> Dict[str, Any]:
        return {
            "plan_id": audit.plan_id,
            "is_fully_compliant": getattr(audit, "is_fully_compliant", None),
            "cadence_compliance_rate": getattr(audit, "cadence_compliance_rate", None),
            "physical_feasibility_passed": getattr(audit, "physical_feasibility_passed", None),
            "business_compliance_passed": getattr(audit, "business_compliance_passed", None),
            "semantic_purity_passed": getattr(audit, "semantic_purity_passed", None),
            "violations_count": len(getattr(audit, "violations", []) or []),
            "summary_message": getattr(audit, "summary_message", ""),
        }
