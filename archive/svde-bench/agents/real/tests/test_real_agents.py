"""Sprint 5.3 Acceptance Test: Real Black-Box LLM & CP-SAT Solver Agents."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from agents.real.llm_agent import LLMDecisionAgent
from agents.real.solver_agent import ConstrainedSolverAgent

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_black_box_llm_agent_execution():
    """Validates that LLMDecisionAgent prompts context, parses JSON, and completes pipeline on D01 and V03."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    llm_agent = LLMDecisionAgent(model_name="mock-claude-3-5-sonnet")

    for c_dir in [DELIVERY_CASES_DIR / "D01", VISIT_CASES_DIR / "V03"]:
        res = pipeline.run_case_dir(c_dir, agent_cls=lambda: llm_agent)
        assert res["ok"] is True
        assert res["profile"]["overall"]["grade"] == "A"
        assert res["profile"]["evaluation"]["semantic"]["score"] == 1.0
        assert "decision_routes" in res["profile"]["evaluation"]["semantic"]["evidence"]


def test_exact_constrained_solver_agent_execution():
    """Validates that ConstrainedSolverAgent formulates CP-SAT mathematical model and solves D01 and V03."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    solver_agent = ConstrainedSolverAgent(time_limit_sec=30)

    for c_dir in [DELIVERY_CASES_DIR / "D01", VISIT_CASES_DIR / "V03"]:
        res = pipeline.run_case_dir(c_dir, agent_cls=lambda: solver_agent)
        assert res["ok"] is True
        assert res["profile"]["overall"]["grade"] == "A"
        assert res["profile"]["evaluation"]["semantic"]["score"] == 1.0
        assert "decision_routes" in res["profile"]["evaluation"]["semantic"]["evidence"]
