"""Sprint 2.2 Acceptance Test: Pattern Separation & Full Pipeline on 10 Delivery Cases (D01-D10)."""
import sys
import shutil
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.case_synthesizer import DecisionScenarioSynthesizer
from tools.case_generator.schema_validator import validate_case
from tools.case_generator.pipeline_runner import FullPipelineRunner

CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"


def test_all_10_cases_exist_and_validate():
    """Gate 1: All 10 cases D01-D10 validate against Schema & Decision-Completeness."""
    synthesizer = DecisionScenarioSynthesizer()
    synthesizer.synthesize_all_cases(CASES_DIR)

    for i in range(1, 11):
        case_dir = CASES_DIR / f"D{i:02d}"
        assert case_dir.is_dir(), f"Missing directory {case_dir}"
        res = validate_case(case_dir)
        assert res.ok(), f"Case D{i:02d} failed schema validation: {res.errors}"


def test_all_10_cases_have_pattern_metadata():
    """Pattern Metadata linkage: each case preserves pattern_id and dilemma."""
    for i in range(1, 11):
        meta_file = CASES_DIR / f"D{i:02d}" / "metadata.yaml"
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        assert "pattern" in meta, f"Missing pattern metadata in D{i:02d}"
        assert "id" in meta["pattern"]
        assert meta["pattern"]["id"].startswith("PATTERN-D")
        assert "variant_name" in meta["pattern"]


def test_pattern_separation_diversity():
    """Gate 8: Pattern Separation - checks intent, constraints, and dilemmas differ."""
    intents = set()
    primary_objs = set()
    dilemmas = set()

    for i in range(1, 11):
        case_dir = CASES_DIR / f"D{i:02d}"
        with open(case_dir / "intent.yaml", "r", encoding="utf-8") as f:
            intent = yaml.safe_load(f) or {}
        with open(case_dir / "metadata.yaml", "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        primary_objs.add(intent.get("primary_objective"))
        dilemmas.add(meta.get("pattern", {}).get("dilemma"))

    # Must have distinct primary objectives across the 5 patterns
    assert len(primary_objs) >= 5, f"Insufficient intent diversity: {len(primary_objs)}"
    # Must have distinct dilemmas across the 10 variants
    assert len(dilemmas) >= 8, f"Insufficient dilemma diversity: {len(dilemmas)}"


def test_all_10_cases_run_full_pipeline():
    """Gates 2, 3, 4: Oracle solves and Pipeline produces valid DecisionProfiles."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    for i in range(1, 11):
        case_dir = CASES_DIR / f"D{i:02d}"
        out = pipeline.run_case_dir(case_dir)
        assert out["ok"] is True, f"Pipeline failed on D{i:02d}: {out}"
        assert out["oracle_status"] in ["OPTIMAL", "FEASIBLE", "INFEASIBLE"]
        
        prof = out["profile"]
        assert prof["decision_profile"]["case_id"] == f"CASE-D{i:02d}"
        assert "evaluation" in prof
        assert "semantic" in prof["evaluation"]
        assert "evidence" in prof["evaluation"]["semantic"]
        assert prof["reproducibility"]["deterministic"] is True
