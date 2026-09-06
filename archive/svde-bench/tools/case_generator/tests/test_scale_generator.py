"""Sprint 5.2 Acceptance Test: Scalable Stress Benchmark Generation & Pipeline Scaling."""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.scale_generator import ScalableBenchmarkGenerator
from tools.case_generator.schema_validator import validate_case
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.decision_runtime.governed_principle_agent import GovernedPrincipleDecisionAgent

TEMP_STRESS_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "stress_scale_temp"


def setup_module():
    if TEMP_STRESS_DIR.exists():
        shutil.rmtree(TEMP_STRESS_DIR)


def teardown_module():
    if TEMP_STRESS_DIR.exists():
        shutil.rmtree(TEMP_STRESS_DIR)


def test_scalable_stress_case_generation_and_validation():
    """Validates that ScalableBenchmarkGenerator generates N=10, 50, 100 cases that strictly pass SchemaValidator."""
    gen = ScalableBenchmarkGenerator(random_seed=42)
    suite = gen.generate_suite_matrix(TEMP_STRESS_DIR)
    assert len(suite) == 3

    for p in suite:
        assert p.is_dir()
        res = validate_case(p)
        assert res.ok(), f"Scale case {p.name} failed schema validation: {res.errors}"


def test_scalable_cases_solve_and_run_governed_agent():
    """Validates that scalable stress cases execute through OracleRunner and GovernedPrincipleDecisionAgent."""
    gen = ScalableBenchmarkGenerator(random_seed=42)
    case_path = gen.generate_delivery_stress_case(
        task_count=50,
        resource_count=10,
        target_dir=TEMP_STRESS_DIR / "TEST-N50",
        case_id="STRESS-TEST-N50"
    )

    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    agent = GovernedPrincipleDecisionAgent()

    res = pipeline.run_case_dir(case_path, agent_cls=lambda: agent)
    assert res["ok"] is True
    assert res["oracle_status"] in ["OPTIMAL", "FEASIBLE"]
    assert res["profile"]["decision_profile"]["case_id"] == "STRESS-TEST-N50"
    assert res["profile"]["evaluation"]["semantic"]["score"] == 1.0
    assert res["profile"]["overall"]["grade"] == "A"
