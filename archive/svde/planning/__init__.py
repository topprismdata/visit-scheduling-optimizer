"""SVDE Core Decision Planner & Capability Pipeline Router.

Routes DecisionSpec into an ordered multi-step Capability Pipeline:
- Validates preferred capability against its formal CapabilityContract (Fix #8).
- Resolves all required capabilities declared in DecisionSpec without dropping subsequent ones (Fix #9).
- Fails closed with UnsupportedCapabilityError if required capabilities cannot be fulfilled.
"""
from typing import Dict, Any, List, Optional
from svde.contracts import (
    DecisionSpec, DecisionPlan, CapabilityStep, UnsupportedCapabilityError,
    CapabilityContract
)
from svde.planning.capability_registry import CapabilityRegistry, CORE_CAPABILITY_REGISTRY


class DecisionPlanner:
    """Routes DecisionSpec into an ordered capability pipeline with formal contract validation."""
    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self.registry = registry or CORE_CAPABILITY_REGISTRY

    def plan(self, spec: DecisionSpec, preferred_capability: Optional[str] = None) -> DecisionPlan:
        context = spec.context
        
        # Fix #8: Enforce formal CapabilityContract when preferred_capability is supplied
        if preferred_capability:
            adapter = self.registry.get_capability(preferred_capability)
            if not adapter:
                raise UnsupportedCapabilityError(
                    f"Preferred capability '{preferred_capability}' is not registered. Available capabilities: {list(self.registry._capabilities.keys())}"
                )
            
            contract = adapter.contract
            # Validate supported decision class
            if spec.decision_class not in contract.supported_decision_classes:
                raise UnsupportedCapabilityError(
                    f"Capability '{preferred_capability}' does not support decision class '{spec.decision_class}'. Supported: {contract.supported_decision_classes}"
                )
            # Validate required structure type if present
            if spec.decision_structure is not None and not isinstance(spec.decision_structure, contract.required_structure_type):
                raise UnsupportedCapabilityError(
                    f"Capability '{preferred_capability}' requires structure '{contract.required_structure_type.__name__}', but spec provided '{type(spec.decision_structure).__name__}'"
                )
            
            primary_cap = preferred_capability
            resolved_capabilities = [primary_cap]
        else:
            # Fix #9: Resolve all required capabilities declared in DecisionSpec (AND/OR pipeline semantics)
            resolved_capabilities = []
            for req_cap in spec.required_capabilities:
                if self.registry.is_available(req_cap):
                    resolved_capabilities.append(req_cap)
                else:
                    # If any required capability is missing from registry -> Fail Closed!
                    raise UnsupportedCapabilityError(
                        f"Required capability '{req_cap}' declared in spec is not available in registry. Available: {list(self.registry._capabilities.keys())}"
                    )
            
            if not resolved_capabilities:
                raise UnsupportedCapabilityError(
                    f"No registered capability can satisfy spec requirements: {spec.required_capabilities}. Available: {list(self.registry._capabilities.keys())}"
                )
            primary_cap = resolved_capabilities[0]

        # Build Ordered Capability Pipeline
        steps: List[CapabilityStep] = []
        for idx, cap_name in enumerate(resolved_capabilities):
            steps.append(CapabilityStep(
                step_id=f"step_{idx+1}_{cap_name}",
                capability_name=cap_name,
                parameters={
                    "time_limit_sec": 30,
                    "has_hard_commitments": context.has_hard_commitments,
                    "governing_principles": spec.governing_principles,
                }
            ))

        # Add mandatory semantic verification audit step
        steps.append(CapabilityStep(
            step_id=f"step_{len(steps)+1}_verify",
            capability_name="semantic_audit",
            parameters={"strict_mode": True}
        ))

        execution_steps_labels = [f"Execute_{c}" for c in resolved_capabilities] + ["Verify_Semantic_Compliance", "Emit_Decision_Artifact"]

        return DecisionPlan(
            plan_id=f"PLAN-{spec.spec_id}",
            steps=steps,
            selected_engine=primary_cap,
            execution_steps=execution_steps_labels,
            engine_config={
                "time_limit_sec": 30,
                "has_hard_commitments": context.has_hard_commitments,
                "governing_principles": spec.governing_principles,
                "resolved_capabilities": resolved_capabilities,
            }
        )
