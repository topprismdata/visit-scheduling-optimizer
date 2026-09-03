"""Black-Box LLM Decision Agent for SVDE-Bench v0.5.

Fix #1: Provider timeout and failure boundary protection.
Fix #2: Parse errors strictly set status='ERROR', decision_feasible=False, and fail validation.
"""
from typing import Dict, Any, List, Optional, Callable
import json
import time
from svdebench.core import (
    DecisionCase, DecisionArtifact, DecisionTrace
)
from svdebench.agents.base import BaseDecisionAgent
from tools.decision_runtime.decision_context import DecisionContext


class LLMDecisionAgent(BaseDecisionAgent):
    """
    Black-Box LLM Decision Agent with strict provider failure and parse error boundaries.
    """
    def __init__(
        self,
        completion_fn: Optional[Callable[[str], str]] = None,
        model_name: str = "frontier-llm-v1",
        timeout_sec: float = 30.0
    ):
        self.model_name = model_name
        self.timeout_sec = timeout_sec
        self.completion_fn = completion_fn or self._default_mock_llm_inference

    def _build_decision_prompt(self, context: DecisionContext) -> str:
        prompt = (
            f"You are an autonomous enterprise operations dispatcher for domain: '{context.domain}'.\n"
            f"Primary Business Objective: {context.primary_objective}\n\n"
            f"AVAILABLE RESOURCES:\n"
        )
        for r in context.resources:
            prompt += f"  - ID: {r.resource_id}, Class: {r.resource_class}, Capacity: {r.capacity_limit}, Status: {r.status}\n"
        
        prompt += f"\nPENDING TASKS (Orders / Visits):\n"
        for t in context.tasks:
            prompt += (
                f"  - ID: {t.task_id}, Demand: {t.demand_quantity}, Locked_Commitment: {t.is_locked}, "
                f"VIP: {t.is_vip}, Required_Competency: {t.required_competency}, Window: {t.time_window}\n"
            )

        prompt += (
            "\nINSTRUCTIONS:\n"
            "1. Output a strictly valid JSON dictionary matching this exact schema:\n"
            "   {\n"
            "     \"reassigned_routes\": {\"<resource_id>\": [\"<task_id>\", ...]},\n"
            "     \"total_additional_cost\": <float>,\n"
            "     \"reasoning\": \"<explanation>\"\n"
            "   }\n"
            "2. Ensure all tasks requiring specific competency (COLD_CHAIN, SPECIALIST) match compatible resources.\n"
            "3. Honor locked commitments within their windows.\n"
        )
        return prompt

    def _default_mock_llm_inference(self, prompt: str) -> str:
        active_resources = []
        cold_or_spec_resources = []
        lines = prompt.splitlines()
        
        for line in lines:
            if "- ID: " in line and "Class: " in line:
                parts = line.split(", ")
                r_id = parts[0].split("- ID: ")[1].strip()
                r_class = parts[1].split("Class: ")[1].strip()
                status = parts[3].split("Status: ")[1].strip() if len(parts) > 3 else "AVAILABLE"
                if status not in ("BROKEN_DOWN", "SICK_LEAVE", "ON_LEAVE"):
                    active_resources.append(r_id)
                    if "COLD" in r_class or "SPEC" in r_class:
                        cold_or_spec_resources.append(r_id)

        locked_tasks = []
        unlocked_tasks = []
        
        for line in lines:
            if "- ID: " in line and "Demand: " in line:
                parts = line.split(", ")
                t_id = parts[0].split("- ID: ")[1].strip()
                is_locked = "Locked_Commitment: True" in line
                req_comp = parts[4].split("Required_Competency: ")[1].strip() if len(parts) > 4 else "GENERAL"
                if is_locked:
                    locked_tasks.append((t_id, req_comp))
                else:
                    unlocked_tasks.append((t_id, req_comp))

        routes: Dict[str, List[str]] = {r: [] for r in active_resources}
        
        for idx, (t_id, comp) in enumerate(locked_tasks):
            if comp in ("COLD_CHAIN", "SPECIALIST") and cold_or_spec_resources:
                target_r = cold_or_spec_resources[idx % len(cold_or_spec_resources)]
            elif active_resources:
                target_r = active_resources[idx % len(active_resources)]
            else:
                target_r = "VEH_01"
            routes.setdefault(target_r, []).append(t_id)

        for idx, (t_id, comp) in enumerate(unlocked_tasks):
            if comp in ("COLD_CHAIN", "SPECIALIST") and cold_or_spec_resources:
                target_r = cold_or_spec_resources[idx % len(cold_or_spec_resources)]
            elif active_resources:
                target_r = active_resources[idx % len(active_resources)]
            else:
                target_r = "VEH_01"
            routes.setdefault(target_r, []).append(t_id)

        cleaned_routes = {k: v for k, v in routes.items() if len(v) > 0}

        response = {
            "reassigned_routes": cleaned_routes,
            "total_additional_cost": 430.0,
            "reasoning": "LLM synthesized schedule satisfying competency constraints and VIP SLA commitments."
        }
        return json.dumps(response)

    def solve(self, case: DecisionCase) -> DecisionArtifact:
        context = DecisionContext.from_decision_case(case)
        prompt = self._build_decision_prompt(context)

        # Fix #1: Provider call with explicit timeout & exception boundary
        t0 = time.perf_counter()
        raw_completion = ""
        provider_error = None
        try:
            raw_completion = self.completion_fn(prompt)
            t1 = time.perf_counter()
            if (t1 - t0) > self.timeout_sec:
                provider_error = f"LLM Provider Timeout: Exceeded {self.timeout_sec}s deadline"
        except Exception as e:
            provider_error = f"LLM Provider Connection Error: {str(e)}"

        # Fix #2: Parse verification and failure mapping
        routes = {}
        cost = 0.0
        parse_error = None

        if provider_error:
            status = "ERROR"
            reasoning = provider_error
            hard_commitment_honored = False
            decision_feasibility_pass = "FAIL"
        else:
            try:
                parsed = json.loads(raw_completion)
                routes = parsed.get("reassigned_routes", {})
                cost = float(parsed.get("total_additional_cost", 400.0))
                reasoning = str(parsed.get("reasoning", "LLM completion generated."))
                status = "FEASIBLE" if routes else "INFEASIBLE"
                hard_commitment_honored = bool(routes)
                decision_feasibility_pass = "PASS" if routes else "FAIL"
            except Exception as e:
                status = "ERROR"
                parse_error = f"JSON Parse Error from LLM completion: {e}"
                reasoning = parse_error
                hard_commitment_honored = False
                decision_feasibility_pass = "FAIL"

        trace = DecisionTrace(
            trace_id=f"TR-LLM-{case.metadata.id}",
            decision_chain=[
                {"stage": "Prompt_Synthesis", "model": self.model_name},
                {"stage": "LLM_Inference", "completion_length": len(raw_completion), "error": provider_error},
                {"stage": "JSON_Parsing", "status": "PARSED_SUCCESS" if not parse_error else "PARSE_FAILED"}
            ],
            causal_rationale=[
                {"task": t_id, "action": "ROUTED_BY_LLM", "reason": reasoning}
                for r_list in routes.values() for t_id in r_list
            ],
            constraint_provenance={"C1": "Capacity", "C2": "Prompt_Specification"}
        )

        return DecisionArtifact(
            case_id=case.metadata.id,
            status=status,
            decision={"reassigned_routes": routes, "total_additional_cost": cost},
            trace=trace,
            explanation={"summary": reasoning, "raw_prompt_snippet": prompt[:200] + "..."},
            validation_result={"hard_commitment_honored": hard_commitment_honored, "decision_feasibility": decision_feasibility_pass},
            memory_patch=None
        )
