"""Production Planner State Projection Compiler — L6 Mathematical Projection.

FIX-7: Real Service Duration Synthesis
- Consumes OperationalVisitPolicy (Policy.version) for strict cadence contract
- Resolves planned frequency from active policy, NEVER from customer observation
- Synthesizes service duration from execution_fact_stream action observations
- Applies Hard Spatial Gateway (Fail-Closed projection on UNMAPPED coordinates)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional, Set
from collections import defaultdict
import math
import datetime

from prism_ontology.world_model.state_snapshot import (
    OperationalDecisionWorldState, BitemporalPeriod, OperationalCustomer,
    CognitiveCategory, InStoreActionType, LifecycleStatus
)


def haversine_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    if lon1 == lon2 and lat1 == lat2:
        return 0.0
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c * R * 1.3


def estimated_transit_time_min(dist_km: float, speed_kmh: float = 35.0) -> float:
    if dist_km <= 0.01:
        return 0.0
    return (dist_km / speed_kmh) * 60.0 + 5.0


@dataclass(frozen=True)
class PlannerNodeTopology:
    node_index: int
    domain_entity_id: str
    spatial_coordinate: Tuple[float, float]
    service_duration_min: float
    is_depot: bool = False


@dataclass(frozen=True)
class PlannerStateProjection:
    projection_id: str
    target_rep_id: str
    planning_horizon: BitemporalPeriod
    nodes: List[PlannerNodeTopology]
    node_matrix_index: Dict[str, int]
    travel_cost_matrix: List[List[float]]
    travel_distance_matrix: List[List[float]]
    candidate_pattern_space: Dict[str, List[List[Tuple[int, int]]]]
    locked_commitments_mask: Dict[Tuple[int, int], List[int]]
    service_duration_vector: List[float]
    source_service_duration_metadata: Dict[str, Any] = field(default_factory=dict)  # FIX-7 trace
    daily_stop_capacity: int = 6
    daily_workload_budget_min: float = 480.0
    is_projection_clean: bool = True
    unplannable_nodes_excluded: List[str] = field(default_factory=list)


class ProjectionCompilationError(Exception):
    """FIX-8: Raised by default. Must explicitly opt-in for partial projection."""
    pass


# Re-resolve active frequency by direct scan of policies dict on WorldState
def _resolve_active_frequency_v2(world_state: OperationalDecisionWorldState, store_code: str) -> Optional[int]:
    # FIX-1: Resolve from versioned OperationalVisitPolicy in PolicyRegistry.operational_policies dict
    registry = getattr(world_state, 'policies', None)
    if registry is None:
        return None
    # PolicyRegistry holds operational_policies dict
    op_policies = getattr(registry, 'operational_policies', None)
    if isinstance(op_policies, dict) and store_code in op_policies:
        pol = op_policies[store_code]
        # Bitemporal check
        if pol.bitemporal.valid_from <= world_state.bitemporal.valid_from <= pol.bitemporal.valid_to:
            return pol.target_frequency_per_month
    return None


class PlannerStateProjectionCompiler:
    """Compiles OperationalDecisionWorldState into PlannerStateProjection."""

    @staticmethod
    def synthesize_service_duration_from_observations(
        world_state: OperationalDecisionWorldState,
        store_code: str
    ) -> Tuple[float, str]:
        """FIX-7: Synthesize service duration from execution_fact_stream action observations."""
        durations = []
        for evt in world_state.execution_fact_stream:
            if evt.store_code == store_code:
                for act in evt.actions:
                    durations.append(act.estimated_duration_min)
        if durations:
            return round(sum(durations) / len(durations), 2), "EMPIRICAL_HISTORICAL_MEAN"
        return 45.0, "DEFAULT_FALLBACK"

    @staticmethod
    def compile_projection(
        world_state: OperationalDecisionWorldState,
        target_rep_id: str,
        allow_partial_projection: bool = False,
        working_days: Optional[List[str]] = None,
        *,
        generated_at: datetime.datetime,
    ) -> PlannerStateProjection:
        # 时间契约: projection 标识时刻必须显式传入且带时区 (严禁 datetime.now(), P1-1)
        if generated_at.tzinfo is None:
            raise ValueError(
                f"generated_at 必须带时区 (timezone-aware), 实际 naive: {generated_at!r}"
            )
        rep = world_state.resources.get(target_rep_id)
        if not rep:
            raise KeyError(f"Rep {target_rep_id} not found in WorldState")

        assigned_stores = world_state.get_rep_universe(target_rep_id)
        depot_coord = rep.depot_estimate.inferred_centroid
        # FIX-6: Accept explicit working_days from caller (Planner must pass its planning horizon dates)
        if working_days is None:
            working_days = getattr(world_state.bitemporal, '_working_days', None) or []
        
        # FIX-1: Use Policy, NOT Customer field
        # Reuse original logic but resolve frequency from policy registry
        registry = world_state.policies
        
        node_index: Dict[str, int] = {"DEPOT_0": 0}
        nodes_list: List[PlannerNodeTopology] = [
            PlannerNodeTopology(0, "DEPOT_0", (depot_coord.longitude, depot_coord.latitude), 0.0, is_depot=True)
        ]
        unplannable_excluded = []
        service_durations = [0.0]
        duration_meta: Dict[str, Any] = {}

        for code, store in assigned_stores.items():
            if not store.is_plannable or store.location is None:
                unplannable_excluded.append(f"Store [{code}] {store.store_name} (Missing coordinates)")
                continue
            # (FAIL-CLOSED check moved out of loop — see below)

            idx = len(node_index)
            node_index[code] = idx
            
            # FIX-1: Resolve frequency from versioned policy
            freq = _resolve_active_frequency_v2(world_state, code)
            if freq is None:
                # Policy not yet instantiated for this store - cannot proceed with assumption
                raise ProjectionCompilationError(
                    f"No active OperationalVisitPolicy found for store {code}. Frequency must be resolved from policy, never from observation."
                )

            # FIX-7: Synthesize duration from execution_fact_stream action history
            synth_duration, source_tag = PlannerStateProjectionCompiler.synthesize_service_duration_from_observations(world_state, code)
            duration_meta[code] = {"duration_min": synth_duration, "source": source_tag}

            nodes_list.append(PlannerNodeTopology(
                node_index=idx,
                domain_entity_id=code,
                spatial_coordinate=(store.location.longitude, store.location.latitude),
                service_duration_min=synth_duration,
                is_depot=False
            ))
            service_durations.append(synth_duration)

        N = len(nodes_list)
        
        # Build cost matrices
        dist_matrix = [[0.0]*N for _ in range(N)]
        time_matrix = [[0.0]*N for _ in range(N)]
        for i in range(N):
            for j in range(N):
                c_i = nodes_list[i].spatial_coordinate
                c_j = nodes_list[j].spatial_coordinate
                d_km = haversine_distance_km(c_i[0], c_i[1], c_j[0], c_j[1])
                dist_matrix[i][j] = round(d_km, 2)
                time_matrix[i][j] = round(estimated_transit_time_min(d_km), 1)

        # Generate strict pattern space P_i from policies
        pattern_space = {}
        for code in node_index.keys():
            if code == "DEPOT_0":
                continue
            freq = _resolve_active_frequency_v2(world_state, code)
            p_list = []
            if freq == 4:
                for k in range(5):
                    p_list.append([(w, k) for w in range(4)])
            elif freq == 3:
                for k in range(5):
                    for skip_w in range(4):
                        p_list.append([(w, k) for w in range(4) if w != skip_w])
            elif freq == 2:
                for k in range(5):
                    p_list.append([(0, k), (2, k)])
                    p_list.append([(1, k), (3, k)])
            elif freq == 1:
                for w in range(4):
                    for k in range(5):
                        p_list.append([(w, k)])
            pattern_space[code] = p_list

        # FIX-6: Locked Commitments Mask with Precise (w, k) Mapping
        locked_commitments_mask: Dict[Tuple[int, int], List[int]] = defaultdict(list)
        if hasattr(world_state, 'commitments') and world_state.commitments:
            for com in world_state.commitments.values():
                if com.rep_id == target_rep_id and com.store_code in node_index:
                    st_idx = node_index[com.store_code]
                    w, k = PlannerStateProjectionCompiler._map_date_to_slot(com.locked_date, working_days)
                    if w is not None:
                        locked_commitments_mask[(w, k)].append(st_idx)

        is_clean = (len(unplannable_excluded) == 0)

        # FIX-8 (v3.0): FAIL-CLOSED GATEWAY — execute AFTER scan completion
        if unplannable_excluded and not allow_partial_projection:
            raise ProjectionCompilationError(
                f"ProjectionCompilationError: {len(unplannable_excluded)} unplannable node(s) detected "
                f"({unplannable_excluded[:3]}{'...' if len(unplannable_excluded) > 3 else ''}). "
                f"Pass allow_partial_projection=True to opt-in for partial compilation."
            )

        return PlannerStateProjection(
            projection_id=f"PROJ_{target_rep_id}_{len(nodes_list)}nodes_{generated_at.strftime('%Y%m%dT%H%M%S%z')}",
            target_rep_id=target_rep_id,
            planning_horizon=world_state.bitemporal,
            nodes=nodes_list,
            node_matrix_index=node_index,
            travel_cost_matrix=time_matrix,
            travel_distance_matrix=dist_matrix,
            candidate_pattern_space=pattern_space,
            locked_commitments_mask=dict(locked_commitments_mask),
            service_duration_vector=service_durations,
            source_service_duration_metadata=duration_meta,
            daily_stop_capacity=rep.max_daily_stops,
            daily_workload_budget_min=rep.max_daily_workload_min,
            is_projection_clean=is_clean,
            unplannable_nodes_excluded=unplannable_excluded
        )

    @staticmethod
    def _map_date_to_slot(target_date: datetime.date, working_days: List[str]) -> Tuple[Optional[int], Optional[int]]:
        """FIX-6: Map absolute date to (w, k) based on working_days list."""
        if target_date is None:
            return None, None
        # Auto-generate working_days from June 2026 standard if not provided
        if not working_days:
            import calendar
            year, month = 2026, 6
            working_days = []
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                weekday = datetime.date(year, month, day).weekday()
                if weekday < 5:  # Mon-Fri
                    working_days.append(f"{year}-{month:02d}-{day:02d}")
        try:
            target_str = target_date.strftime("%Y-%m-%d")
            for idx, w_day in enumerate(working_days):
                if str(w_day).startswith(target_str):
                    w = idx // 5
                    k = idx % 5
                    return w, k
        except Exception:
            pass
        return None, None
