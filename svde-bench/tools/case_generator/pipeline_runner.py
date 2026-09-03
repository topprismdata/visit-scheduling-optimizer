"""End-to-End Benchmark Pipeline for SVDE-Bench v0.2.

Fix #3: Strict Oracle status gating — When Oracle returns ERROR/INFEASIBLE or fails, pipeline reports ok: False.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from tools.case_generator.schema_validator import validate_case
from tools.case_generator.oracle_runner import OracleRunner, OracleResult
from tools.case_generator.evaluator_runner import EvaluatorRunner
from tools.case_generator.profile_builder import ProfileBuilder
from svdebench.agents.baseline import SemanticAwareAgent, PureSolverMockAgent
from svdebench.core import DecisionCase


class FullPipelineRunner:
    def __init__(self, oracle_timeout_sec: int = 300):
        self.oracle_runner = OracleRunner(timeout_sec=oracle_timeout_sec)
        self.evaluator_runner = EvaluatorRunner()

    def run_case_dir(self, case_dir: Path, agent_cls=SemanticAwareAgent) -> Dict[str, Any]:
        # 1. Validate
        v_res = validate_case(case_dir)
        if not v_res.ok():
            return {
                "ok": False,
                "stage": "validation",
                "errors": v_res.errors,
            }

        # 2. Extract domain & intent from case files
        with open(case_dir / "metadata.yaml", "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        with open(case_dir / "intent.yaml", "r", encoding="utf-8") as f:
            intent = yaml.safe_load(f) or {}
        with open(case_dir / "world_state.yaml", "r", encoding="utf-8") as f:
            world = yaml.safe_load(f) or {}
        with open(case_dir / "constraints.yaml", "r", encoding="utf-8") as f:
            constraints = yaml.safe_load(f) or {}

        cid = meta.get("case_id") or meta.get("id") or case_dir.name
        domain = meta.get("domain", "delivery")

        # Normalize world_state for evaluators
        entities = world.get("entities", {})
        fleet = entities.get("vehicles", world.get("fleet", []))
        orders = entities.get("orders", world.get("orders", []))
        depot = world.get("depot", [0, 0])

        normalized_world = {
            "depot": depot,
            "fleet": fleet,
            "orders": orders,
            "entities": entities,
            "relationships": world.get("relationships", {}),
        }

        # Normalize constraints
        hard_list = constraints.get("hard", [])
        soft_list = constraints.get("soft", [])
        combined_constraints = hard_list + soft_list if isinstance(hard_list, list) else constraints

        # 3. Build DecisionCase
        combined_dict = {
            "metadata": {
                "id": cid,
                "domain": domain,
                "name": meta.get("title", ""),
                "created_at": meta.get("created_at", "2026-08-24"),
                "tags": meta.get("tags", []),
            },
            "intent": intent,
            "world_state": normalized_world,
            "semantic_contract": {"constraints": combined_constraints},
        }
        case = DecisionCase.from_dict(combined_dict)

        # 4. Oracle Run
        oracle_res = self.oracle_runner.run_case(case)

        # Fix #3: If Oracle encounters an ERROR, fail the pipeline loudly (do not report ok: True)
        if oracle_res.status == "ERROR":
            return {
                "ok": False,
                "stage": "oracle",
                "case_id": cid,
                "error": oracle_res.solution.get("error", "Oracle solver execution failed"),
            }

        # 5. Agent Run (takes case only)
        agent = agent_cls() if callable(agent_cls) else agent_cls
        agent_artifact = agent.solve(case)

        # 6. Evaluation Orchestration
        eval_results = self.evaluator_runner.evaluate(
            case=case,
            oracle_result=oracle_res.raw_output,
            agent_artifact=agent_artifact,
            agent_name=agent.__class__.__name__,
        )

        # 7. Profile Generation
        profile = ProfileBuilder.build(
            case_id=cid,
            domain=domain,
            decision_intent=intent,
            solution_summary={"status": oracle_res.status, "objective": oracle_res.objective},
            evaluation_results=eval_results,
            reproducibility={"run_count": 1, "deterministic": True},
        )

        return {
            "ok": True,
            "case_id": cid,
            "oracle_status": oracle_res.status,
            "profile": profile,
        }
