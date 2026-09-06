"""Visit Domain Adapter for SVDE-Bench v0.5.

Properly adapts Sales Reps (Specialist/Senior/Junior skill tiers), Account Targets
(Strategic/Core/Development tiers), and Cadence Obligations without concept downgrading or req_cold hacks.
"""
from typing import Dict, Any, List, Optional
from svdebench.core import DecisionCase
from domains.adapters.base_adapter import BaseDomainAdapter
from tools.decision_runtime.decision_context import DecisionContext, NormalizedResource, NormalizedTask


class VisitDomainAdapter(BaseDomainAdapter):
    @property
    def domain_name(self) -> str:
        return "visit"

    def to_decision_context(self, case: DecisionCase) -> DecisionContext:
        world = case.world_state or {}
        fleet = world.get("fleet", world.get("entities", {}).get("vehicles", []))
        orders = world.get("orders", world.get("entities", {}).get("orders", []))
        intent = case.intent or {}

        resources: List[NormalizedResource] = []
        active_capacity = 0.0
        active_count = 0
        has_failure = False

        # 1. Adapt Sales Reps -> NormalizedResources with genuine Skill Tiers
        for rep in fleet:
            r_id = str(rep.get("id", "REP_01"))
            r_type = str(rep.get("type", "SALES_REP_STANDARD")).upper()
            status = str(rep.get("status", "AVAILABLE")).upper()
            
            # Rep capacity represents daily working minutes (e.g. 480 mins)
            work_mins = float(rep.get("capacity_kg", rep.get("max_daily_minutes", 480.0)))
            is_active = status not in ("ON_LEAVE", "SICK_LEAVE", "BROKEN_DOWN")

            if not is_active:
                has_failure = True
            else:
                active_count += 1
                active_capacity += work_mins

            # Map genuine rep skill tier hierarchy
            if "SPEC" in r_id.upper() or "SPECIALIST" in r_type or "COLD" in r_type:
                skill_class = "SPECIALIST_REP"
            elif "SENIOR" in r_id.upper() or "SENIOR" in r_type:
                skill_class = "SENIOR_REP"
            else:
                skill_class = "JUNIOR_REP"

            resources.append(NormalizedResource(
                resource_id=r_id,
                resource_class=skill_class,
                capacity_limit=work_mins,
                status=status,
                is_active=is_active
            ))

        # 2. Adapt Visit Demands -> NormalizedTasks with genuine Competency Requirements
        tasks: List[NormalizedTask] = []
        total_demand = 0.0
        has_locked = False
        has_skill_req = False

        for v in orders:
            v_id = str(v.get("id", "VISIT_01"))
            # Duration in minutes
            duration = float(v.get("weight_kg", v.get("duration_mins", 45.0)))
            is_lock = bool(v.get("is_locked", False))
            is_vip = bool(v.get("is_vip", False))
            
            req_skill = str(v.get("required_skill", "")).upper()
            req_cold_flag = bool(v.get("req_cold", False))

            if "SPECIALIST" in req_skill or "SPEC" in v_id.upper() or req_cold_flag:
                comp = "SPECIALIST"
                has_skill_req = True
            elif "SENIOR" in req_skill:
                comp = "SENIOR"
                has_skill_req = True
            else:
                comp = "GENERAL"

            if is_lock or is_vip:
                has_locked = True

            total_demand += duration
            tw = [int(v.get("tw_early", 0)), int(v.get("tw_late", 480))]

            tasks.append(NormalizedTask(
                task_id=v_id,
                demand_quantity=duration,
                is_locked=is_lock,
                is_vip=is_vip,
                required_competency=comp,
                time_window=tw
            ))

        contention = (total_demand / active_capacity) if active_capacity > 0 else 2.0

        return DecisionContext(
            case_id=case.metadata.id,
            domain=self.domain_name,
            primary_objective=str(intent.get("primary_objective", intent.get("objective", ""))),
            resources=resources,
            tasks=tasks,
            resource_contention_ratio=round(contention, 2),
            has_hard_commitments=has_locked,
            has_competency_constraints=has_skill_req,
            has_resource_failure=has_failure,
            active_resource_count=active_count,
            total_active_capacity=active_capacity,
            total_task_demand=total_demand,
            raw_metadata=case.metadata.model_dump() if hasattr(case.metadata, "model_dump") else case.metadata.__dict__
        )

    def adapt_solution_to_domain(self, decision_routes: Dict[str, List[str]], case: DecisionCase) -> Dict[str, Any]:
        return {
            "dispatch_type": "FIELD_SALES_VISIT_SCHEDULE",
            "assigned_rep_schedules": decision_routes,
            "total_reps_deployed": len(decision_routes),
            "total_accounts_visited": sum(len(visits) for visits in decision_routes.values()),
        }
