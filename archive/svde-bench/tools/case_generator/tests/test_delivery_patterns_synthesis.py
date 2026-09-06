"""Sprint 2.1 Acceptance Test: 5 Delivery Decision Patterns produce valid scenarios."""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.case_synthesizer import DecisionScenarioSynthesizer
from tools.case_generator.schema_validator import validate_case
from tools.case_generator.pipeline_runner import FullPipelineRunner

TEMP_SYNTH_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synth_patterns_temp"

PATTERNS = [
    "PATTERN-D1-VIP-SLA-PROTECTION",
    "PATTERN-D2-DYNAMIC-REPLANNING",
    "PATTERN-D3-COST-SERVICE-TRADEOFF",
    "PATTERN-D4-CAPACITY-COLDCHAIN-ALLOCATION",
    "PATTERN-D5-MEMORY-GUIDED-ADAPTATION",
]


def setup_module():
    if TEMP_SYNTH_DIR.exists():
        shutil.rmtree(TEMP_SYNTH_DIR)


def teardown_module():
    if TEMP_SYNTH_DIR.exists():
        shutil.rmtree(TEMP_SYNTH_DIR)


def test_all_5_delivery_patterns_synthesize_and_validate():
    synthesizer = DecisionScenarioSynthesizer()
    for pid in PATTERNS:
        case_dir = TEMP_SYNTH_DIR / pid
        synthesizer.synthesize_from_pattern(pid, case_dir, case_id=f"CASE-{pid}")
        
        # 1. Validation check
        res = validate_case(case_dir)
        assert res.ok(), f"Pattern {pid} failed schema validation: {res.errors}"

        # 2. Pipeline execution check (Validation -> Oracle -> Evaluator -> Profile)
        pipeline = FullPipelineRunner(oracle_timeout_sec=30)
        out = pipeline.run_case_dir(case_dir)
        assert out["ok"] is True, f"Pattern {pid} failed full pipeline: {out}"
        assert out["oracle_status"] in ["OPTIMAL", "FEASIBLE"]
        
        prof = out["profile"]
        assert prof["decision_profile"]["case_id"] == f"CASE-{pid}"
        assert "evaluation" in prof
        assert "semantic" in prof["evaluation"]
        assert "feasibility" in prof["evaluation"]
        assert "runtime" in prof["evaluation"]
        assert "memory" in prof["evaluation"]
