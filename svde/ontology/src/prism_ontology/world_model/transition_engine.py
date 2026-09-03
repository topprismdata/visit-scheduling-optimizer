"""Enterprise State Transition & Multi-Dimensional Scenario Rollout Engine v3.0.

WM-FIX v3.0: P0-1 (DeferralPolicy Guard E), P0-2 (Mandatory GPS Guard C),
P0-3 (Scenario Inherit operational_policies/deferral_policies),
P1-1 (No datetime.now() anywhere — all timestamps must be explicitly provided),
P1-2 (Persistent structured StateTransitionRecord list),
P1-3 (Comprehensive audit hash), P1-4 (True Capacity Rollout Computation).
"""
import datetime
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from prism_ontology.world_model.state_snapshot import (
    OperationalDecisionWorldState, OperationalVisitLifecycleRecord,
    LifecycleStatus, BitemporalPeriod, OperationalCustomer, OperationalResource,
    DerivedDepotEstimate, GeoCoordinate, CognitiveCategory, ActualVisitEvent,
    OperationalCommitment, DeferralPolicy
)


# ============================================================
# P1-2: Structured StateTransitionRecord (full, persistent)
# ============================================================

@dataclass(frozen=True)
class StateTransitionRecord:
    """Immutable, fully-detailed audit record for every state change."""
    transition_id: str
    visit_id: str
    base_snapshot_id: str
    from_status: LifecycleStatus
    to_status: LifecycleStatus
    event_time: datetime.datetime
    transaction_time: datetime.datetime
    triggering_event_ref: str
    approver_id: Optional[str]
    gps_deviation_meters: Optional[float]
    service_duration_min: Optional[float]
    policy_version_snapshot: Optional[str]
    evidence_refs: List[str]
    transition_model_version: str = "TransitionEngine_v3.0"
    record_hash: str = ""


def _deterministic_hash(record: "StateTransitionRecord") -> str:
    """P1-3: Comprehensive deterministic SHA-256 hash including ALL inputs."""
    payload = (
        f"{record.visit_id}|{record.base_snapshot_id}|"
        f"{record.from_status.value}|{record.to_status.value}|"
        f"{record.event_time.isoformat()}|{record.transaction_time.isoformat()}|"
        f"{record.triggering_event_ref}|{record.approver_id or 'NONE'}|"
        f"{record.gps_deviation_meters if record.gps_deviation_meters is not None else 'NONE'}|"
        f"{record.service_duration_min if record.service_duration_min is not None else 'NONE'}|"
        f"{record.policy_version_snapshot or 'NONE'}|"
        f"{','.join(sorted(record.evidence_refs))}"
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


class StateTransitionEngine:
    """Enterprise-grade state transition engine (v3.0)."""

    @staticmethod
    def transition_visit_status(
        base_state: OperationalDecisionWorldState,
        visit_id: str,
        target_status: LifecycleStatus,
        triggering_event_ref: str,
        event_time: datetime.datetime,
        transaction_time: datetime.datetime,
        approver_id: Optional[str] = None,
        gps_deviation_meters: Optional[float] = None, # P0-2: now REQUIRED
        service_duration_min: Optional[float] = None,
        evidence_refs: Optional[List[str]] = None,
        policy_version_snapshot: Optional[str] = None,
        deferral_policy_id: Optional[str] = None  # P0-1: DeferralPolicy ID
    ) -> Tuple[OperationalDecisionWorldState, OperationalVisitLifecycleRecord, StateTransitionRecord]:
        # P1-1: Reject any non-explicit time
        if event_time is None or transaction_time is None:
            raise ValueError("P1-1 Violation: event_time and transaction_time MUST be explicit (no datetime.now() default allowed)")
        if evidence_refs is None:
            evidence_refs = []

        rec = base_state.visit_lifecycle_records.get(visit_id)
        if not rec:
            raise KeyError(f"Visit record {visit_id} not found in WorldState")

        # State Transition Graph Validation
        valid_transitions = {
            LifecycleStatus.PROPOSED: [LifecycleStatus.PLANNED, LifecycleStatus.CANCELLED],
            LifecycleStatus.PLANNED: [LifecycleStatus.COMMITTED, LifecycleStatus.PROPOSED, LifecycleStatus.CANCELLED],
            LifecycleStatus.COMMITTED: [LifecycleStatus.IN_PROGRESS, LifecycleStatus.MISSED, LifecycleStatus.DEFERRED],
            LifecycleStatus.IN_PROGRESS: [LifecycleStatus.COMPLETED, LifecycleStatus.MISSED],
            LifecycleStatus.MISSED: [LifecycleStatus.DEFERRED, LifecycleStatus.PROPOSED],
            LifecycleStatus.DEFERRED: [LifecycleStatus.PLANNED, LifecycleStatus.COMMITTED],
            LifecycleStatus.COMPLETED: [],
            LifecycleStatus.CANCELLED: []
        }

        if target_status not in valid_transitions.get(rec.current_status, []):
            raise ValueError(
                f"Invalid state transition: Cannot move visit {visit_id} from {rec.current_status.value} to {target_status.value}!"
            )

        # Guard A: PLANNED -> COMMITTED requires explicit approver
        if rec.current_status == LifecycleStatus.PLANNED and target_status == LifecycleStatus.COMMITTED:
            if not approver_id:
                raise ValueError("Guard A Failed: Explicit human approver_id is required!")

        # Guard B: IN_PROGRESS -> COMPLETED requires duration + policy snapshot
        if rec.current_status == LifecycleStatus.IN_PROGRESS and target_status == LifecycleStatus.COMPLETED:
            dur = service_duration_min if service_duration_min is not None else rec.service_duration_min
            if dur < 10.0:
                raise ValueError(f"Guard B Failed: duration {dur} min below 10 min threshold!")
            if not policy_version_snapshot:
                raise ValueError("Guard B Failed: policy_version_snapshot required!")

        # P0-2: Guard C — GPS evidence is NOW MANDATORY (None -> Fail-Closed)
        if rec.current_status == LifecycleStatus.COMMITTED and target_status == LifecycleStatus.IN_PROGRESS:
            if gps_deviation_meters is None:
                raise ValueError("Guard C Failed: Missing GPS evidence (gps_deviation_meters required and cannot be None)!")
            if gps_deviation_meters > 500.0:
                raise ValueError(f"Guard C Failed: GPS deviation {gps_deviation_meters}m exceeds 500m!")

        # Guard D: MISSED requires event_time past scheduled end-of-day
        if target_status == LifecycleStatus.MISSED:
            sched_end = datetime.datetime.combine(rec.scheduled_date, datetime.time(23, 59))
            if event_time < sched_end:
                raise ValueError(f"Guard D Failed: MISSED requires event_time >= {sched_end}, got {event_time}")

        # P0-1: Guard E — DEFERRED requires valid DeferralPolicy AND exceeds max_deferrals
        if target_status == LifecycleStatus.DEFERRED:
            if not deferral_policy_id:
                raise ValueError("Guard E Failed: deferral_policy_id is required for DEFERRED transition!")
            if deferral_policy_id not in base_state.policies.deferral_policies:
                raise ValueError(f"Guard E Failed: deferral_policy_id '{deferral_policy_id}' not found in PolicyRegistry!")
            # Count prior deferrals for this visit
            prior_deferrals = sum(
                1 for entry in rec.status_history
                if entry[0] == LifecycleStatus.DEFERRED
            )
            pol = base_state.policies.deferral_policies[deferral_policy_id]
            if prior_deferrals + 1 > pol.max_deferrals_per_month:
                raise ValueError(f"Guard E Failed: Deferral quota exceeded ({pol.max_deferrals_per_month}/month)")
            # Window check
            days_diff = (rec.scheduled_date - event_time.date()).days
            if days_diff > pol.allowed_deferral_window_days:
                raise ValueError(f"Guard E Failed: Deferral window ({pol.allowed_deferral_window_days} days) exceeded")
            if pol.requires_approval and not approver_id:
                raise ValueError("Guard E Failed: DeferralPolicy requires explicit approver_id!")

        # Build new lifecycle record (history is a list of tuples)
        new_history = list(rec.status_history) + [
            (target_status, transaction_time, approver_id, triggering_event_ref, gps_deviation_meters)
        ]
        new_rec = OperationalVisitLifecycleRecord(
            visit_id=rec.visit_id, store_code=rec.store_code, rep_id=rec.rep_id,
            scheduled_date=rec.scheduled_date, current_status=target_status,
            status_history=new_history,
            actual_arrival=getattr(rec, 'actual_arrival', None),
            actual_departure=getattr(rec, 'actual_departure', None),
            service_duration_min=service_duration_min if service_duration_min is not None else rec.service_duration_min
        )

        # P1-2: Build PERSISTENT StateTransitionRecord (full audit hash)
        proto_record = StateTransitionRecord(
            transition_id="", visit_id=visit_id,
            base_snapshot_id=base_state.snapshot_id,
            from_status=rec.current_status, to_status=target_status,
            event_time=event_time, transaction_time=transaction_time,
            triggering_event_ref=triggering_event_ref, approver_id=approver_id,
            gps_deviation_meters=gps_deviation_meters,
            service_duration_min=service_duration_min,
            policy_version_snapshot=policy_version_snapshot,
            evidence_refs=evidence_refs
        )
        record_hash = _deterministic_hash(proto_record)
        transition_record = StateTransitionRecord(
            transition_id=record_hash,
            visit_id=visit_id, base_snapshot_id=base_state.snapshot_id,
            from_status=rec.current_status, to_status=target_status,
            event_time=event_time, transaction_time=transaction_time,
            triggering_event_ref=triggering_event_ref, approver_id=approver_id,
            gps_deviation_meters=gps_deviation_meters,
            service_duration_min=service_duration_min,
            policy_version_snapshot=policy_version_snapshot,
            evidence_refs=evidence_refs,
            record_hash=record_hash
        )

        # P1-2: Persist BOTH new lifecycle record AND transition record into WorldState
        new_records = dict(base_state.visit_lifecycle_records)
        new_records[visit_id] = new_rec
        new_transitions = list(base_state.transition_records) + [transition_record]

        # Also emit a lightweight ActualVisitEvent for backward compat with execution_fact_stream
        transition_event = ActualVisitEvent(
            event_id=f"TRANS_{visit_id}_{transaction_time.strftime('%Y%m%d%H%M%S')}",
            store_code=rec.store_code, rep_id=rec.rep_id,
            visit_date=rec.scheduled_date,
            service_duration_min=service_duration_min if service_duration_min is not None else rec.service_duration_min,
            transit_duration_min=0.0,
            is_line_internal=(target_status != LifecycleStatus.MISSED),
            actions=(), merchandising_compliance=None,
            summary=f"StateTransition: {rec.current_status.value}->{target_status.value}; Hash={record_hash[:8]}; Approval={approver_id or 'AUTO'}"
        )
        new_events = list(base_state.execution_fact_stream) + [transition_event]

        new_state = OperationalDecisionWorldState(
            snapshot_id=f"SNAP_TR_{base_state.snapshot_id}_{record_hash[:8]}",
            bitemporal=base_state.bitemporal, manifest=base_state.manifest,
            customers=base_state.customers, resources=base_state.resources,
            account_hierarchies=base_state.account_hierarchies,
            product_line_scopes=base_state.product_line_scopes,
            supply_nodes=base_state.supply_nodes,
            policies=base_state.policies,
            commitments=base_state.commitments,
            visit_lifecycle_records=new_records,
            transition_records=new_transitions,    # P1-2: persistent field
            execution_fact_stream=new_events,
            active_scenario_branches=base_state.active_scenario_branches
        )

        return new_state, new_rec, transition_record

    @staticmethod
    def rollout_reallocation_scenario(
        base_state: OperationalDecisionWorldState,
        scenario_id: str,
        store_code: str,
        from_rep_id: str,
        to_rep_id: str,
        scenario_timestamp: datetime.datetime,
        transition_valid_from: datetime.date
    ) -> OperationalDecisionWorldState:
        """P0-3: Inherit ALL baseline policies. P1-4: True capacity rollout."""
        if store_code not in base_state.customers:
            raise KeyError(f"Store {store_code} not found in base state")
        if from_rep_id not in base_state.resources or to_rep_id not in base_state.resources:
            raise KeyError("Invalid rep IDs")

        from_rep = base_state.resources[from_rep_id]
        to_rep = base_state.resources[to_rep_id]

        if store_code not in from_rep.assigned_store_codes:
            raise ValueError(f"P0-3 Guard: Rep {from_rep_id} does NOT own store {store_code}!")

        # Reallocate store in Resources
        new_from_codes = tuple(c for c in from_rep.assigned_store_codes if c != store_code)
        new_to_codes = tuple(sorted(list(to_rep.assigned_store_codes) + [store_code]))

        # Recompute centroids
        def _centroid(codes):
            coords = [base_state.customers[c].location for c in codes if base_state.customers.get(c) and base_state.customers[c].location]
            if not coords:
                return GeoCoordinate(0, 0)
            return GeoCoordinate(
                round(sum(c.longitude for c in coords)/len(coords), 6),
                round(sum(c.latitude for c in coords)/len(coords), 6)
            )

        new_from_depot = DerivedDepotEstimate(from_rep_id, _centroid(new_from_codes), len(new_from_codes), 0.95)
        new_to_depot = DerivedDepotEstimate(to_rep_id, _centroid(new_to_codes), len(new_to_codes), 0.95)

        # P1-4: Compute TRUE capacity impact from history (not hardcoded -1/+1)
        # Aggregate service durations and visit counts by rep from execution_fact_stream
        from_workload = sum(ev.service_duration_min for ev in base_state.execution_fact_stream if ev.rep_id == from_rep_id and ev.store_code == store_code)
        to_workload = sum(ev.service_duration_min for ev in base_state.execution_fact_stream if ev.rep_id == to_rep_id and ev.store_code == store_code)
        from_visit_count = sum(1 for ev in base_state.execution_fact_stream if ev.rep_id == from_rep_id and ev.store_code == store_code)
        to_visit_count = sum(1 for ev in base_state.execution_fact_stream if ev.rep_id == to_rep_id and ev.store_code == store_code)

        # Aggregate store_id lifecycle work assigned in the planning horizon
        from_planned_work = sum(ev.service_duration_min for ev in base_state.execution_fact_stream
                               if ev.rep_id == from_rep_id and ev.visit_date >= transition_valid_from)
        to_planned_work = sum(ev.service_duration_min for ev in base_state.execution_fact_stream
                             if ev.rep_id == to_rep_id and ev.visit_date >= transition_valid_from)

        capacity_impact = {
            f"{from_rep_id}_workload_change_min": -from_workload,
            f"{to_rep_id}_workload_change_min": from_workload,
            f"{from_rep_id}_visit_count_change": -from_visit_count,
            f"{to_rep_id}_visit_count_change": to_visit_count,
            f"{from_rep_id}_planned_workload_reallocated_min": -from_planned_work,
            f"{to_rep_id}_planned_workload_increased_min": from_planned_work,
            f"{from_rep_id}_post_overload_risk_min": max(0, (from_planned_work - from_workload) - 480.0 * 4),  # over 4 days budget
            f"{to_rep_id}_post_overload_risk_min": max(0, (to_planned_work + from_planned_work) - 480.0 * 4)
        }

        new_resources = dict(base_state.resources)
        new_resources[from_rep_id] = OperationalResource(
            rep_id=from_rep.rep_id, rep_name=from_rep.rep_name, region=from_rep.region,
            sub_region=from_rep.sub_region, city=from_rep.city, depot_estimate=new_from_depot,
            assigned_store_codes=new_from_codes, max_daily_stops=from_rep.max_daily_stops,
            max_daily_workload_min=from_rep.max_daily_workload_min
        )
        new_resources[to_rep_id] = OperationalResource(
            rep_id=to_rep.rep_id, rep_name=to_rep.rep_name, region=to_rep.region,
            sub_region=to_rep.sub_region, city=to_rep.city, depot_estimate=new_to_depot,
            assigned_store_codes=new_to_codes, max_daily_stops=to_rep.max_daily_stops,
            max_daily_workload_min=to_rep.max_daily_workload_min
        )

        # P0-3: CRITICAL — INHERIT ALL baseline policies, deferral_policies, commitments!
        from prism_ontology.world_model.state_snapshot import PolicyRegistry
        new_ownership = dict(base_state.policies.ownership_map)
        new_ownership[store_code] = to_rep_id
        new_policies = PolicyRegistry(
            cadence_rules=base_state.policies.cadence_rules,
            ownership_map=new_ownership,
            ownership_conflicts=base_state.policies.ownership_conflicts,
            operational_policies=base_state.policies.operational_policies,  # P0-3: INHERIT
            deferral_policies=base_state.policies.deferral_policies             # P0-3: INHERIT
        )

        # Migrate visit lifecycle records and commitments
        new_records = dict(base_state.visit_lifecycle_records)
        new_commitments = dict(base_state.commitments)
        for v_id, v_rec in base_state.visit_lifecycle_records.items():
            if v_rec.store_code == store_code and v_rec.scheduled_date >= transition_valid_from:
                new_records[v_id] = OperationalVisitLifecycleRecord(
                    visit_id=v_rec.visit_id, store_code=v_rec.store_code, rep_id=to_rep_id,
                    scheduled_date=v_rec.scheduled_date, current_status=v_rec.current_status,
                    status_history=v_rec.status_history,
                    actual_arrival=getattr(v_rec, 'actual_arrival', None),
                    actual_departure=getattr(v_rec, 'actual_departure', None),
                    service_duration_min=v_rec.service_duration_min
                )
        for c_id, com in base_state.commitments.items():
            if com.store_code == store_code and com.rep_id == from_rep_id:
                new_commitments[c_id] = OperationalCommitment(
                    commitment_id=com.commitment_id, store_code=com.store_code,
                    rep_id=to_rep_id,
                    locked_date=com.locked_date,
                    locked_time_window=com.locked_time_window,
                    lock_level=com.lock_level,
                    category=com.category
                )

        # Compute deterministic branch hash without datetime.now()
        deterministic_hash = hashlib.sha256(
            f"{scenario_id}|{store_code}|{from_rep_id}|{to_rep_id}|{scenario_timestamp.isoformat()}|{transition_valid_from.isoformat()}".encode('utf-8')
        ).hexdigest()[:12]

        new_scenario_branches = dict(base_state.active_scenario_branches)
        new_scenario_branches[scenario_id] = {
            "action": "STORE_REALLOCATION",
            "store_code": store_code,
            "from_rep_id": from_rep_id,
            "to_rep_id": to_rep_id,
            "effective_date": str(transition_valid_from),
            "scenario_timestamp": scenario_timestamp.isoformat(),
            "capacity_impact": capacity_impact
        }

        return OperationalDecisionWorldState(
            snapshot_id=f"BRANCH_{scenario_id}_{deterministic_hash}",
            bitemporal=BitemporalPeriod(
                valid_from=base_state.bitemporal.valid_from,
                valid_to=base_state.bitemporal.valid_to,
                transaction_from=scenario_timestamp,  # P1-1: deterministic
                transaction_to=None
            ),
            manifest=base_state.manifest,
            customers=base_state.customers, resources=new_resources,
            account_hierarchies=base_state.account_hierarchies,
            product_line_scopes=base_state.product_line_scopes,
            supply_nodes=base_state.supply_nodes,
            policies=new_policies,    # P0-3: inherits ALL policies
            commitments=new_commitments, # P0-3: synced
            visit_lifecycle_records=new_records,
            transition_records=base_state.transition_records,
            execution_fact_stream=base_state.execution_fact_stream,
            active_scenario_branches=new_scenario_branches
        )
