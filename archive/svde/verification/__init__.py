"""SVDE Core Decision Auditor & Verification.

Comprehensive Structure-Specific Verification:
1. Physical Feasibility:
   - Capacity limits, active status, valid resource and task IDs, no duplicate assignment.
   - For Routing: edge_matrix connectivity, maximum route travel time, depot start/end closure.
2. Business Feasibility:
   - SLA locked commitments, all non-depot customer stops visited, time-window constraints (arrival <= tw_late).
3. Semantic Compliance:
   - Declarative competency matching (skills / compartments) and custom semantic invariants.
"""
from typing import Dict, Any, List, Optional, Set
from svde.contracts import (
    DecisionSpec, DecisionResult, DecisionArtifact, DecisionEvidence,
    PhysicalFeasibilityEvidence, BusinessFeasibilityEvidence, SemanticComplianceEvidence,
    NormalizedEntity, DecisionClass, RoutingDecisionStructure
)


class DecisionAuditor:
    """Audits raw DecisionResult against DecisionSpec and produces the final DecisionArtifact."""
    
    def audit(self, spec: DecisionSpec, result: DecisionResult) -> DecisionArtifact:
        context = spec.context
        raw_dec = result.raw_decision or {}
        
        physical_violations: List[str] = []
        business_violations: List[str] = []
        semantic_violations: List[str] = []

        # If active resources are zero and tasks exist -> physical violation
        if context.tasks and not [r for r in context.resources if r.is_active]:
            physical_violations.append("Zero active execution resources available to service pending tasks")
        
        # Determine whether problem structure is Sequential Routing
        is_routing = (
            spec.decision_class == DecisionClass.SEQUENTIAL_ROUTING or
            "assigned_routes" in raw_dec or
            isinstance(spec.decision_structure, RoutingDecisionStructure)
        )

        if is_routing:
            # ── Structure-Specific Audit: Sequential Routing with Full VRP Constraint Checking ──
            assigned_routes = raw_dec.get("assigned_routes")
            if not isinstance(assigned_routes, dict) or len(assigned_routes) == 0:
                if (isinstance(spec.decision_structure, RoutingDecisionStructure) and spec.decision_structure.nodes) or context.tasks:
                    physical_violations.append("Routing output missing or has empty 'assigned_routes' dictionary")
                assigned_routes = {}

            node_map = {}
            depot_ids = set()
            edge_matrix = {}
            max_route_time = None

            if isinstance(spec.decision_structure, RoutingDecisionStructure):
                node_map = {n.node_id: n for n in spec.decision_structure.nodes}
                depot_ids = set(spec.decision_structure.depot_ids)
                edge_matrix = spec.decision_structure.edge_matrix or {}
                max_route_time = spec.decision_structure.max_travel_time_per_route
            else:
                node_map = {t.entity_id: t for t in context.tasks}

            visited_nodes: Set[str] = set()
            
            for route_id, stop_list in assigned_routes.items():
                if not isinstance(stop_list, list):
                    physical_violations.append(f"Route {route_id} stops must be a list of node IDs")
                    continue

                if not stop_list:
                    continue

                # 1. Depot start/end closure check
                start_node = stop_list[0]
                end_node = stop_list[-1]
                if depot_ids:
                    if start_node not in depot_ids or end_node not in depot_ids:
                        physical_violations.append(f"Route {route_id} must start and end at a valid depot (start: {start_node}, end: {end_node})")

                # 2. Sequential Edge Connectivity, Travel Time Accumulation & Time Windows
                current_time = 0.0
                total_route_time = 0.0

                for idx in range(len(stop_list)):
                    stop_id = stop_list[idx]

                    # Check for unknown / ghost node IDs
                    if stop_id not in node_map and stop_id not in depot_ids and "DEPOT" not in stop_id.upper():
                        physical_violations.append(f"Unknown stop node '{stop_id}' assigned in route {route_id}")
                        continue
                    
                    # Duplicate check for customer nodes
                    if stop_id not in depot_ids and "DEPOT" not in stop_id.upper():
                        if stop_id in visited_nodes:
                            physical_violations.append(f"Duplicate stop visit detected for node '{stop_id}'")
                        visited_nodes.add(stop_id)

                    # Node object & service duration
                    node_obj = node_map.get(stop_id)
                    svc_duration = getattr(node_obj, "service_duration", 0.0) or getattr(node_obj, "demand", 0.0) or 0.0
                    tw = getattr(node_obj, "time_window", None)

                    # Time Window Feasibility: arrival time <= tw_late
                    if tw and len(tw) >= 2:
                        tw_early, tw_late = tw[0], tw[1]
                        if current_time < tw_early:
                            current_time = float(tw_early)  # Wait until early window opens
                        if current_time > tw_late:
                            business_violations.append(
                                f"Route {route_id} arrives at node '{stop_id}' at time {current_time:.1f} exceeding late window {tw_late}"
                            )

                    current_time += svc_duration
                    total_route_time += svc_duration

                    # Edge transit to next stop
                    if idx < len(stop_list) - 1:
                        next_stop = stop_list[idx + 1]
                        transit_cost = 0.0

                        # Edge Matrix Verification (Strict: no implicit nominal transit time)
                        if not edge_matrix:
                            # Missing distance data entirely: cannot certify feasibility -> fail closed
                            physical_violations.append(
                                f"Route {route_id}: edge_matrix is empty; transit feasibility cannot be verified (no implicit default travel time allowed)"
                            )
                        elif stop_id in edge_matrix and next_stop in edge_matrix[stop_id]:
                            raw_cost = edge_matrix[stop_id][next_stop]
                            if not isinstance(raw_cost, (int, float)) or isinstance(raw_cost, bool):
                                physical_violations.append(
                                    f"Route {route_id}: edge ({stop_id} -> {next_stop}) cost is non-numeric ({type(raw_cost).__name__})"
                                )
                            else:
                                transit_cost = float(raw_cost)
                        elif "DEFAULT" in edge_matrix:
                            raw_default = edge_matrix["DEFAULT"]
                            if not isinstance(raw_default, (int, float)) or isinstance(raw_default, bool):
                                physical_violations.append(
                                    f"edge_matrix['DEFAULT'] must be a numeric fallback cost, got {type(raw_default).__name__}"
                                )
                            else:
                                transit_cost = float(raw_default)
                        else:
                            physical_violations.append(
                                f"Route {route_id} contains undefined edge ({stop_id} -> {next_stop}) in distance matrix"
                            )

                        current_time += transit_cost
                        total_route_time += transit_cost

                # Maximum Route Duration Check
                if max_route_time is not None and total_route_time > max_route_time:
                    physical_violations.append(
                        f"Route {route_id} total duration {total_route_time:.1f} exceeds maximum allowed {max_route_time}"
                    )

            # 3. Customer Stops Visitation Check
            non_depot_stops = [
                n.node_id for n in (spec.decision_structure.nodes if isinstance(spec.decision_structure, RoutingDecisionStructure) else context.tasks)
                if n.node_id not in depot_ids and "DEPOT" not in n.node_id.upper()
            ]
            
            all_commitments_honored = True
            for stop in non_depot_stops:
                if stop not in visited_nodes:
                    node_obj = node_map.get(stop)
                    is_lock = getattr(node_obj, "is_locked_window", False) or getattr(node_obj, "is_locked", False)
                    if is_lock:
                        all_commitments_honored = False
                        business_violations.append(f"Mandatory locked routing stop '{stop}' unvisited or dropped")
                    else:
                        business_violations.append(f"Customer routing stop '{stop}' was not visited in assigned routes")

        else:
            # ── Structure-Specific Audit: Discrete Assignment ──
            assignments = raw_dec.get("assignments")
            if not isinstance(assignments, dict):
                physical_violations.append("Assignment output missing 'assignments' dictionary")
                assignments = {}

            resource_map = {r.entity_id: r for r in context.resources}
            task_map = {t.entity_id: t for t in context.tasks}
            assigned_tasks: Set[str] = set()

            for r_id, t_list in assignments.items():
                res = resource_map.get(r_id)
                if not res:
                    physical_violations.append(f"Unknown resource '{r_id}' assigned in decision")
                    continue
                if not res.is_active:
                    physical_violations.append(f"Broken/Inactive resource '{r_id}' assigned tasks")

                if not isinstance(t_list, list):
                    physical_violations.append(f"Assignments for resource '{r_id}' must be a list of task IDs")
                    continue

                total_load = 0.0
                for t_id in t_list:
                    task = task_map.get(t_id)
                    if not task:
                        physical_violations.append(f"Unknown task ID '{t_id}' assigned to resource '{r_id}'")
                        continue

                    if t_id in assigned_tasks:
                        physical_violations.append(f"Duplicate assignment detected: Task '{t_id}' assigned multiple times")
                    assigned_tasks.add(t_id)

                    total_load += (task.demand or 0.0)

                    # Competency check (Semantic compliance)
                    for req_comp in task.required_competencies:
                        if req_comp != "GENERAL" and req_comp not in res.provided_competencies:
                            semantic_violations.append(
                                f"Task {t_id} requires competency '{req_comp}' but resource {r_id} only provides {res.provided_competencies}"
                            )

                cap_limit = float("inf") if res.capacity is None else float(res.capacity)
                if total_load > cap_limit:
                    physical_violations.append(f"Resource '{r_id}' overloaded: {total_load} > {cap_limit}")

            # Business Feasibility: Verify locked commitments
            locked_tasks = [t for t in context.tasks if t.is_locked]
            all_commitments_honored = True
            for t in locked_tasks:
                if t.entity_id not in assigned_tasks:
                    all_commitments_honored = False
                    business_violations.append(f"Mandatory SLA locked commitment '{t.entity_id}' unfulfilled or dropped")

        # ── Custom Semantic Invariants Verification ──
        for inv in spec.hard_invariants:
            inv_type = inv.get("type", "")
            raw = inv.get("raw", {})
            
            if inv_type in ("MUST_BE_FALSE", "IMPOSSIBLE", "INVALID") or raw.get("type") in ("MUST_BE_FALSE", "IMPOSSIBLE"):
                semantic_violations.append(f"Hard semantic invariant '{inv.get('id', inv_type)}' breached (evaluated as FALSE)")
            elif inv_type == "PROHIBITED_PAIRING":
                prohibited = raw.get("prohibited_tasks", [])
                if not is_routing:
                    for r_id, t_list in (raw_dec.get("assignments") or {}).items():
                        if all(pt in t_list for pt in prohibited):
                            semantic_violations.append(f"Semantic contract violation: Prohibited pairing {prohibited} co-located on {r_id}")

        # Independent feasibility calculation:
        physical_feasible = (len(physical_violations) == 0 and result.status == "FEASIBLE")
        business_feasible = (all_commitments_honored and len(business_violations) == 0)
        semantic_compliant = (len(semantic_violations) == 0)

        physical_ev = PhysicalFeasibilityEvidence(
            satisfied=physical_feasible,
            violations=physical_violations,
            details={"physical_violations_count": len(physical_violations)}
        )
        business_ev = BusinessFeasibilityEvidence(
            satisfied=business_feasible,
            commitments_honored=all_commitments_honored,
            violations=business_violations,
            details={"business_violations_count": len(business_violations)}
        )
        semantic_ev = SemanticComplianceEvidence(
            satisfied=semantic_compliant,
            violations=semantic_violations,
            details={"semantic_violations_count": len(semantic_violations)}
        )

        evidence = DecisionEvidence(
            physical=physical_ev,
            business=business_ev,
            semantic=semantic_ev,
            activated_principles=spec.governing_principles,
            rejected_principles=[]
        )

        all_violations = physical_violations + business_violations + semantic_violations

        trace_dict = {
            "spec_id": spec.spec_id,
            "engine": result.engine_metadata.get("capability", "UNKNOWN"),
            "execution_steps": result.execution_trace,
            "objective_value": result.objective_value
        }

        return DecisionArtifact(
            request_id=context.request_id,
            domain=spec.domain,
            decision=result.raw_decision,
            solution_feasible=physical_feasible,
            decision_feasible=business_feasible and physical_feasible,
            semantic_compliance=semantic_compliant,
            evidence=evidence,
            activated_principles=spec.governing_principles,
            rejected_principles=[],
            execution_trace=trace_dict,
            unresolved_issues=all_violations
        )
