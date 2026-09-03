"""Day 1 Acceptance Test: Synthesizer produces cases that strictly pass SchemaValidator."""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.case_synthesizer import DecisionScenarioSynthesizer
from tools.case_generator.schema_validator import validate_case

TEMP_OUTPUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synth_output_temp"

def setup_module():
    if TEMP_OUTPUT.exists():
        shutil.rmtree(TEMP_OUTPUT)

def teardown_module():
    if TEMP_OUTPUT.exists():
        shutil.rmtree(TEMP_OUTPUT)

def test_synthesizer_generates_valid_case():
    synthesizer = DecisionScenarioSynthesizer()
    case_path = synthesizer.synthesize_minimal_delivery_case(TEMP_OUTPUT, case_id="SYNTH-TEST-001")
    
    assert case_path.is_dir()
    res = validate_case(case_path)
    assert res.ok(), f"Synthesized case failed validation: {res.errors}"
    assert res.warnings == []
