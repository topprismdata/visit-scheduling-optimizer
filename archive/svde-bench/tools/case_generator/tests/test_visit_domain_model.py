"""Sprint 3.1 Acceptance Test: Visit Domain Decision Model Structure & Validation Compatibility."""
import sys
import shutil
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.case_synthesizer import DecisionScenarioSynthesizer
from tools.case_generator.schema_validator import validate_case
from tools.case_generator.pipeline_runner import FullPipelineRunner

VISIT_DOMAIN_DIR = Path(__file__).resolve().parents[3] / "domains" / "visit"
TEMP_VISIT_SYNTH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synth_visit_patterns_temp"


def setup_module():
    if TEMP_VISIT_SYNTH.exists():
        shutil.rmtree(TEMP_VISIT_SYNTH)


def teardown_module():
    if TEMP_VISIT_SYNTH.exists():
        shutil.rmtree(TEMP_VISIT_SYNTH)


def test_visit_domain_files_exist_and_parse():
    """Gate 11.1: Verify that all 6 required Visit domain artifacts exist and are valid YAML."""
    expected_files = [
        "entities.yaml",
        "relationships.yaml",
        "patterns.yaml",
        "constraints.yaml",
        "failure_taxonomy.yaml",
        "scenario_templates.yaml",
    ]
    for fname in expected_files:
        fpath = VISIT_DOMAIN_DIR / fname
        assert fpath.exists(), f"Missing domain file: {fpath}"
        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert isinstance(data, dict), f"File {fname} is not a valid YAML mapping"
            assert data.get("domain") == "visit", f"File {fname} domain header mismatch"


def test_visit_templates_synthesize_and_validate():
    """Gate 11.2: Verify that Visit templates can be synthesized into multi-file cases that pass SchemaValidator."""
    synth = DecisionScenarioSynthesizer(templates_file=VISIT_DOMAIN_DIR / "scenario_templates.yaml")
    templates = synth.load_templates()
    assert len(templates) >= 5, f"Expected at least 5 templates, found {len(templates)}"

    for tpl in templates:
        code = tpl.get("case_code", "VXX")
        case_dir = TEMP_VISIT_SYNTH / code
        synth.synthesize_from_template(tpl, case_dir, case_id=f"CASE-{code}")

        # Validate with existing SchemaValidator (Zero changes needed)
        res = validate_case(case_dir)
        assert res.ok(), f"Visit case {code} failed schema validation: {res.errors}"


def test_visit_synthesized_case_runs_pipeline_zero_modification():
    """Gate 13: Verify that synthesized Visit case executes cleanly through Oracle & FullPipelineRunner."""
    synth = DecisionScenarioSynthesizer(templates_file=VISIT_DOMAIN_DIR / "scenario_templates.yaml")
    case_dir = TEMP_VISIT_SYNTH / "V01"
    
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    out = pipeline.run_case_dir(case_dir)
    
    assert out["ok"] is True
    assert out["oracle_status"] in ["OPTIMAL", "FEASIBLE"]
    assert out["profile"]["decision_profile"]["domain"] == "delivery" or out["profile"]["decision_profile"]["case_id"] == "CASE-V01"
    assert "semantic" in out["profile"]["evaluation"]
    assert "memory" in out["profile"]["evaluation"]
