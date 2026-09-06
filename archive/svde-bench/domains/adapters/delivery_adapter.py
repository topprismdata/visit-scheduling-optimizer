"""Delivery Domain Adapter for SVDE-Bench v0.5.

Adapts physical fleet transport, cargo payload, cold-chain compartment,
and customer time-window contracts into canonical DecisionContext representations.
"""
from typing import Dict, Any, List, Optional
from svdebench.core import DecisionCase
from domains.adapters.base_adapter import BaseDomainAdapter
from tools.decision_runtime.decision_context import DecisionContext, NormalizedResource, NormalizedTask


class DeliveryDomainAdapter(BaseDomainAdapter):
    @property
    def domain_name(self) -> str:
        return "delivery"

    def to_decision_context(self, case: DecisionCase) -> DecisionContext:
        world = case.world_state or {}
        fleet = world.get("fleet", world.get("entities", {}).get("vehicles", []))
        orders = world.get("orders", world.get("entities", {}).get("orders", []))
        intent = case.intent or {}

        resources: List[NormalizedResource] = []
        active_capacity = 0.0
        active_count = 0
        has_failure = False

        # 1. Adapt Vehicles -> NormalizedResources
        for v in fleet:
            v_id = str(v.get("id", "VEH_01"))
            v_type = str(v.get("type", "STANDARD_VAN")).upper()
            status = str(v.get("status", "AVAILABLE")).upper()
            cap = float(v.get("capacity_kg", 1000.0))
            is_active = status not in ("BROKEN_DOWN", "OFF_DUTY")

            if not is_active:
                has_failure = True
            else:
                active_count += 1
                active_capacity += cap

            # Explicitly map vehicle compartment capability
            if "COLD" in v_type or "REFRIGERATED" in v_type:
                res_class = "COLD_REFRIGERATED"
            elif "BIKE" in v_type or "ELECTRIC" in v_type:
                res_class = "CARGO_BIKE"
            else:
                res_class = "STANDARD_VAN"

            resources.append(NormalizedResource(
                resource_id=v_id,
                resource_class=res_class,
                capacity_limit=cap,
                status=status,
                is_active=is_active
            ))

        # 2. Adapt Orders -> NormalizedTasks
        tasks: List[NormalizedTask] = []
        total_demand = 0.0
        has_locked = False
        has_cold_comp = False

        for o in orders:
            o_id = str(o.get("id", "ORD_01"))
            weight = float(o.get("weight_kg", 100.0))
            is_lock = bool(o.get("is_locked", False))
            is_vip = bool(o.get("is_vip", False))
            req_cold = bool(o.get("req_cold", False))

            if req_cold:
                comp = "COLD_CHAIN"
                has_cold_comp = True
            else:
                comp = "GENERAL"

            if is_lock or is_vip:
                has_locked = True

            total_demand += weight
            tw = [int(o.get("tw_early", 0)), int(o.get("tw_late", 999))]

            tasks.append(NormalizedTask(
                task_id=o_id,
                demand_quantity=weight,
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
            has_competency_constraints=has_cold_comp,
            has_resource_failure=has_failure,
            active_resource_count=active_count,
            total_active_capacity=active_capacity,
            total_task_demand=total_demand,
            raw_metadata=case.metadata.model_dump() if hasattr(case.metadata, "model_dump") else case.metadata.__dict__
        )

    def adapt_solution_to_domain(self, decision_routes: Dict[str, List[str]], case: DecisionCase) -> Dict[str, Any]:
        return {
            "dispatch_type": "FLEET_DELIVERY_ROUTING",
            "assigned_vehicle_routes": decision_routes,
            "total_vehicles_used": len(decision_routes),
            "total_orders_dispatched": sum(len(orders) for orders in decision_routes.values()),
        }
