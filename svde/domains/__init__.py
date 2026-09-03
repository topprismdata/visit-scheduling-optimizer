"""SVDE Domain Adapters.

Normalizes domain-specific business requests into canonical DecisionContext.
Fails explicitly if an unknown domain is requested (No silent fallbacks).
Validates entity ID uniqueness and non-emptiness (Fix #15).
"""
from typing import Dict, Any, List, Optional, Set
from abc import ABC, abstractmethod
from svde.contracts import (
    DecisionRequest, DecisionContext, NormalizedEntity, DecisionClass,
    UnsupportedDomainError, CompilationError
)


class BaseDomainAdapter(ABC):
    @property
    @abstractmethod
    def domain_name(self) -> str:
        pass

    @abstractmethod
    def to_decision_context(self, request: DecisionRequest) -> DecisionContext:
        pass


def _validate_entity_id(entity_dict: Dict[str, Any], entity_type: str, seen_ids: Set[str]) -> str:
    """Fix #15: Rejects missing, empty, or duplicate entity IDs during compilation."""
    e_id = entity_dict.get("id") or entity_dict.get("entity_id") or entity_dict.get("name")
    if not e_id or not str(e_id).strip():
        raise CompilationError(f"Malformed {entity_type}: entity must have a non-empty 'id'")
    e_id_str = str(e_id).strip()
    if e_id_str in seen_ids:
        raise CompilationError(f"Duplicate entity ID '{e_id_str}' detected in {entity_type} list")
    seen_ids.add(e_id_str)
    return e_id_str


class DeliveryDomainAdapter(BaseDomainAdapter):
    @property
    def domain_name(self) -> str:
        return "delivery"

    def to_decision_context(self, request: DecisionRequest) -> DecisionContext:
        world = request.world_state or {}
        fleet = world.get("fleet", world.get("entities", {}).get("vehicles", []))
        orders = world.get("orders", world.get("entities", {}).get("orders", []))
        intent = request.intent or {}

        entities: List[NormalizedEntity] = []
        active_capacity = 0.0
        active_count = 0
        has_failure = False
        seen_res_ids: Set[str] = set()

        for v in fleet:
            v_id = _validate_entity_id(v, "Fleet Resource", seen_res_ids)
            v_type = str(v.get("type", "STANDARD_VAN")).upper()
            status = str(v.get("status", "AVAILABLE")).upper()
            cap = float(v.get("capacity_kg", v.get("capacity", 1000.0)))
            is_active = status not in ("BROKEN_DOWN", "OFF_DUTY")

            if not is_active:
                has_failure = True
            else:
                active_count += 1
                active_capacity += cap

            provided_comp = ["COLD_CHAIN"] if ("COLD" in v_type or "REFRIGERATED" in v_type) else ["GENERAL"]

            entities.append(NormalizedEntity(
                entity_id=v_id,
                entity_type="EXECUTION_RESOURCE",
                attributes={"vehicle_type": v_type, "status": status},
                capacity=cap,
                is_active=is_active,
                provided_competencies=provided_comp
            ))

        total_demand = 0.0
        has_locked = False
        has_cold = False
        seen_task_ids: Set[str] = set()

        for o in orders:
            o_id = _validate_entity_id(o, "Delivery Order", seen_task_ids)
            weight = float(o.get("weight_kg", o.get("demand", 100.0)))
            is_lock = bool(o.get("is_locked", False))
            is_vip = bool(o.get("is_vip", False))
            req_cold = bool(o.get("req_cold", False))

            if req_cold:
                has_cold = True
                required_comp = ["COLD_CHAIN"]
            else:
                required_comp = ["GENERAL"]

            if is_lock or is_vip:
                has_locked = True

            total_demand += weight
            tw = [int(o.get("tw_early", 0)), int(o.get("tw_late", 999))]

            entities.append(NormalizedEntity(
                entity_id=o_id,
                entity_type="COMMITTED_TASK",
                attributes={"is_vip": is_vip},
                demand=weight,
                is_locked=is_lock,
                required_competencies=required_comp,
                time_window=tw
            ))

        contention = (total_demand / active_capacity) if active_capacity > 0 else 2.0

        return DecisionContext(
            request_id=request.request_id,
            domain=self.domain_name,
            primary_objective=str(intent.get("primary_objective", intent.get("objective", "min_cost"))),
            decision_classes=[DecisionClass.DISCRETE_ASSIGNMENT],
            entities=entities,
            contention_ratio=round(contention, 2),
            has_hard_commitments=has_locked,
            has_competency_constraints=has_cold,
            has_resource_failure=has_failure,
            raw_world_state=world
        )


class VisitDomainAdapter(BaseDomainAdapter):
    @property
    def domain_name(self) -> str:
        return "visit"

    def to_decision_context(self, request: DecisionRequest) -> DecisionContext:
        world = request.world_state or {}
        fleet = world.get("fleet", world.get("entities", {}).get("vehicles", []))
        orders = world.get("orders", world.get("entities", {}).get("orders", []))
        intent = request.intent or {}

        entities: List[NormalizedEntity] = []
        active_capacity = 0.0
        active_count = 0
        has_failure = False
        seen_rep_ids: Set[str] = set()

        for rep in fleet:
            r_id = _validate_entity_id(rep, "Sales Representative", seen_rep_ids)
            r_type = str(rep.get("type", "SALES_REP_STANDARD")).upper()
            status = str(rep.get("status", "AVAILABLE")).upper()
            work_mins = float(rep.get("capacity_kg", rep.get("max_daily_minutes", 480.0)))
            is_active = status not in ("ON_LEAVE", "SICK_LEAVE", "BROKEN_DOWN")

            if not is_active:
                has_failure = True
            else:
                active_count += 1
                active_capacity += work_mins

            if "SPEC" in r_id.upper() or "SPECIALIST" in r_type or "COLD" in r_type:
                provided_comp = ["SPECIALIST", "GENERAL"]
            elif "SENIOR" in r_id.upper() or "SENIOR" in r_type:
                provided_comp = ["SENIOR", "GENERAL"]
            else:
                provided_comp = ["GENERAL"]

            entities.append(NormalizedEntity(
                entity_id=r_id,
                entity_type="EXECUTION_RESOURCE",
                attributes={"rep_type": r_type, "status": status},
                capacity=work_mins,
                is_active=is_active,
                provided_competencies=provided_comp
            ))

        total_demand = 0.0
        has_locked = False
        has_skill_req = False
        seen_visit_ids: Set[str] = set()

        for v in orders:
            v_id = _validate_entity_id(v, "Visit Account", seen_visit_ids)
            duration = float(v.get("weight_kg", v.get("duration_mins", 45.0)))
            is_lock = bool(v.get("is_locked", False))
            is_vip = bool(v.get("is_vip", False))
            
            req_skill = str(v.get("required_skill", "")).upper()
            req_cold_flag = bool(v.get("req_cold", False))

            if "SPECIALIST" in req_skill or "SPEC" in v_id.upper() or req_cold_flag:
                required_comp = ["SPECIALIST"]
                has_skill_req = True
            elif "SENIOR" in req_skill:
                required_comp = ["SENIOR"]
                has_skill_req = True
            else:
                required_comp = ["GENERAL"]

            if is_lock or is_vip:
                has_locked = True

            total_demand += duration
            tw = [int(v.get("tw_early", 0)), int(v.get("tw_late", 480))]

            entities.append(NormalizedEntity(
                entity_id=v_id,
                entity_type="COMMITTED_TASK",
                attributes={"is_vip": is_vip},
                demand=duration,
                is_locked=is_lock,
                required_competencies=required_comp,
                time_window=tw
            ))

        contention = (total_demand / active_capacity) if active_capacity > 0 else 2.0

        return DecisionContext(
            request_id=request.request_id,
            domain=self.domain_name,
            primary_objective=str(intent.get("primary_objective", intent.get("objective", "sla_coverage"))),
            decision_classes=[DecisionClass.DISCRETE_ASSIGNMENT],
            entities=entities,
            contention_ratio=round(contention, 2),
            has_hard_commitments=has_locked,
            has_competency_constraints=has_skill_req,
            has_resource_failure=has_failure,
            raw_world_state=world
        )


class CoreDomainRegistry:
    def __init__(self):
        self._adapters: Dict[str, BaseDomainAdapter] = {
            "delivery": DeliveryDomainAdapter(),
            "visit": VisitDomainAdapter(),
        }

    def register_adapter(self, adapter: BaseDomainAdapter, allow_overwrite: bool = True):
        dom_key = adapter.domain_name.lower()
        if not allow_overwrite and dom_key in self._adapters:
            raise ValueError(f"Domain adapter for '{dom_key}' already registered.")
        self._adapters[dom_key] = adapter

    def get_adapter(self, domain_name: str) -> BaseDomainAdapter:
        dom_key = domain_name.lower()
        if dom_key not in self._adapters:
            raise UnsupportedDomainError(
                f"Domain '{domain_name}' is not registered. Registered domains: {list(self._adapters.keys())}"
            )
        return self._adapters[dom_key]


CORE_ADAPTER_REGISTRY = CoreDomainRegistry()
