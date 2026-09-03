"""SVDE Core Runtime Orchestrator.

Executes an ordered pipeline of DecisionPlan capability steps deterministically.
Emits granular per-step input/output fingerprints and structured PipelineExecutionAudit.
Chains intermediate results and hard_invariants forward to subsequent steps.
"""
from typing import Dict, Any, List, Optional
from svde.contracts import (
    DecisionSpec, DecisionPlan, DecisionResult, CapabilityStep,
    CapabilityStepTrace, PipelineExecutionAudit
)
from svde.planning.capability_registry import CapabilityRegistry, CORE_CAPABILITY_REGISTRY


class RuntimeOrchestrator:
    """Executes ordered capability pipelines with deterministic audit digests."""
    def __init__(self, capability_registry: Optional[CapabilityRegistry] = None):
        self.capability_registry = capability_registry or CORE_CAPABILITY_REGISTRY

    def execute(self, spec: DecisionSpec, plan: DecisionPlan) -> DecisionResult:
        step_traces: List[CapabilityStepTrace] = []
        primary_result: Optional[DecisionResult] = None
        last_result: Optional[DecisionResult] = None
        
        steps_to_run = plan.steps if plan.steps else [
            CapabilityStep(step_id="step_1", capability_name=plan.selected_engine, parameters=plan.engine_config)
        ]

        input_context_hash = CapabilityStepTrace.compute_hash(spec.context.raw_world_state)

        for step in steps_to_run:
            cap_name = step.capability_name
            adapter = self.capability_registry.get_capability(cap_name)
            
            if not adapter:
                raise RuntimeError(f"Capability adapter '{cap_name}' not available in registry")

            # Pass prior decision result and hard_invariants into subsequent pipeline steps
            merged_params = {**plan.engine_config, **step.parameters}
            merged_params["hard_invariants"] = spec.hard_invariants
            merged_params["soft_preferences"] = spec.soft_preferences
            if last_result is not None:
                merged_params["prior_decision"] = last_result.raw_decision
                merged_params["prior_status"] = last_result.status

            result = adapter.execute(spec.context, merged_params)
            
            out_hash = CapabilityStepTrace.compute_hash(result.raw_decision)
            principles_active = [p.get("principle_id") for p in spec.governing_principles]

            step_traces.append(CapabilityStepTrace(
                step_id=step.step_id,
                capability_name=cap_name,
                status=result.status,
                input_hash=input_context_hash,
                output_hash=out_hash,
                objective_value=result.objective_value,
                principles_applied=principles_active,
                execution_metrics={
                    "step_status": result.status,
                    "engine_metadata": result.engine_metadata
                },
                raw_step_trace=result.execution_trace
            ))

            # Retain primary solver capability output
            if cap_name != "semantic_audit" and primary_result is None:
                primary_result = result
            elif primary_result is None:
                primary_result = result
            
            last_result = result

        if not primary_result:
            raise RuntimeError(f"Pipeline in plan '{plan.plan_id}' produced no execution results")

        pipeline_audit = PipelineExecutionAudit(
            plan_id=plan.plan_id,
            total_steps_executed=len(steps_to_run),
            step_traces=step_traces,
            pipeline_status="COMPLETED" if all(t.status == "FEASIBLE" for t in step_traces) else "FAILED"
        )

        primary_result.execution_trace = [t.__dict__ for t in step_traces]
        primary_result.engine_metadata["plan_id"] = plan.plan_id
        primary_result.engine_metadata["pipeline_audit"] = pipeline_audit.to_dict()
        return primary_result
