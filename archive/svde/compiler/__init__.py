"""SVDE Core Decision Compiler.

Compiles business DecisionRequest into a formal DecisionSpec:
1. Normalizes domain entities via DomainAdapter into canonical DecisionContext.
2. Ingests declarative structural invariants and required capabilities.
3. Fix: Strictly validates semantic_contract shape and raises CompilationError on malformed structures.
"""
from typing import Dict, Any, List, Optional
from svde.contracts import (
    DecisionRequest, DecisionContext, DecisionSpec, DecisionClass, CompilationError
)
from svde.domains import CORE_ADAPTER_REGISTRY


class DecisionCompiler:
    """Compiles business DecisionRequest into formal, verified DecisionSpec without memory coupling."""

    def compile(self, request: DecisionRequest) -> DecisionSpec:
        # 1. Normalize domain context via domain adapter
        adapter = CORE_ADAPTER_REGISTRY.get_adapter(request.domain)
        context = adapter.to_decision_context(request)

        # 2. Extract Hard Invariants
        hard_invariants = [
            {"type": "CAPACITY_LIMIT", "scope": "RESOURCE_CAPACITY", "hardness": "HARD"},
        ]
        if context.has_hard_commitments:
            hard_invariants.append({"type": "TIME_WINDOW_LOCK", "scope": "COMMITMENT_PRESERVATION", "hardness": "HARD_COMMITMENT"})
        if context.has_competency_constraints:
            hard_invariants.append({"type": "COMPETENCY_MATCH", "scope": "COMPARTMENT_OR_SKILL", "hardness": "HARD"})

        # Type-checked ingestion of semantic_contract (CompilationError on malformed types)
        sem_contract = request.semantic_contract
        if sem_contract is not None:
            if not isinstance(sem_contract, dict):
                raise CompilationError(f"semantic_contract must be a dictionary, got {type(sem_contract).__name__}")

            raw_constraints = sem_contract.get("constraints", [])
            if not isinstance(raw_constraints, list):
                raise CompilationError("semantic_contract['constraints'] must be a list")

            raw_invariants = sem_contract.get("invariants", [])
            if not isinstance(raw_invariants, list):
                raise CompilationError("semantic_contract['invariants'] must be a list")

            for c in raw_constraints:
                if not isinstance(c, dict):
                    raise CompilationError(f"Each constraint in semantic_contract must be a dict, got {c}")
                c_type = c.get("type", "CUSTOM_CONSTRAINT")
                hardness = c.get("hardness", "HARD")
                hard_invariants.append({
                    "id": c.get("id", "CUSTOM_CID"),
                    "type": c_type,
                    "scope": c.get("scope", "CUSTOM_SCOPE"),
                    "hardness": hardness,
                    "target": c.get("target_order") or c.get("target_task"),
                    "raw": c
                })

            for inv in raw_invariants:
                if isinstance(inv, dict):
                    inv_id = inv.get("id", "INV_ID")
                    inv_type = inv.get("type", "CUSTOM_INVARIANT")
                    hard_invariants.append({
                        "id": inv_id,
                        "type": inv_type,
                        "scope": inv.get("scope", inv_id),
                        "hardness": inv.get("hardness", "HARD_INVARIANT"),
                        "raw": inv
                    })
                elif isinstance(inv, str):
                    hard_invariants.append({
                        "id": inv,
                        "type": "CUSTOM_INVARIANT",
                        "scope": inv,
                        "hardness": "HARD_INVARIANT",
                        "raw": {"id": inv}
                    })
                else:
                    raise CompilationError(f"Each invariant in semantic_contract must be a dict or str, got {inv}")

        # 3. Extract Soft Preferences
        soft_preferences = [
            {"type": "DISTANCE_OR_TRANSIT_COST", "weight": 1.0},
        ]

        # 4. Formulate First-Class DecisionStructure
        from svde.contracts.decision_structures import AssignmentDecisionStructure, RoutingDecisionStructure, RoutingNode

        primary_class = context.decision_classes[0] if context.decision_classes else DecisionClass.DISCRETE_ASSIGNMENT
        
        if primary_class == DecisionClass.SEQUENTIAL_ROUTING and context.structure is not None:
            structure = context.structure
        elif primary_class == DecisionClass.SEQUENTIAL_ROUTING:
            nodes = [
                RoutingNode(
                    node_id=t.entity_id,
                    node_type="CUSTOMER_STOP",
                    time_window=t.time_window,
                    is_locked_window=t.is_locked
                )
                for t in context.tasks
            ]
            structure = RoutingDecisionStructure(
                nodes=nodes,
                has_sequence_locks=any(t.is_locked for t in context.tasks)
            )
        else:
            structure = AssignmentDecisionStructure(
                resources=context.resources,
                tasks=context.tasks,
                contention_ratio=context.contention_ratio,
                has_hard_commitments=context.has_hard_commitments,
                has_competency_constraints=context.has_competency_constraints
            )

        required_caps = [dc.value for dc in context.decision_classes]

        return DecisionSpec(
            spec_id=f"SPEC-{request.request_id}",
            domain=request.domain,
            context=context,
            decision_class=primary_class,
            decision_structure=structure,
            required_capabilities=required_caps,
            hard_invariants=hard_invariants,
            soft_preferences=soft_preferences,
            governing_principles=[],
            objective_formulation="lexicographic_invariants_then_commitments_then_efficiency"
        )
