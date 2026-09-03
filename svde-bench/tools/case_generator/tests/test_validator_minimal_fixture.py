"""Day 1 Acceptance: minimal fixture passes schema validation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.schema_validator import validate_case

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "minimal_case"

def test_minimal_fixture_validates_cleanly():
    res = validate_case(FIXTURE)
    assert res.ok(), f"errors: {res.errors}"
    assert res.warnings == []

def test_validator_rejects_missing_file():
    incomplete = FIXTURE.parent / "incomplete_case"
    incomplete.mkdir(exist_ok=True)
    (incomplete / "metadata.yaml").write_text("case_id: X\n")
    res = validate_case(incomplete)
    assert not res.ok()
    assert any("missing" in e for e in res.errors)

def test_validator_rejects_incomplete_vip_metadata():
    bad_case = FIXTURE.parent / "bad_vip_case"
    bad_case.mkdir(exist_ok=True)
    for sub, content in {
        "metadata.yaml": "case_id: BAD\ndomain: delivery\nversion: '1.0'\ncreated_at: '2026-08-24'\ntags: []\ndifficulty: L2\n",
        "intent.yaml": "primary_objective: 'x'\nsecondary_objectives: []\npriority_rules: {}\n",
        "world_state.yaml": "entities: {}\nrelationships: {}\n",
        "constraints.yaml": "hard:\n  - {id: 'C1', name: 'VIPLock', type: 'TIME_WINDOW_HARD', expression: 'x'}\n",
        "decision_space.yaml": "objective: 'x'\ncandidate_solutions_count: 1\nparallel_options: []\n",
        "evaluation.yaml": "expected_difficulty: 'easy'\nexpected_agent_separation: false\nseparation_dimensions: []\nsuccess_threshold: {}\n",
    }.items():
        (bad_case / sub).write_text(content)
    res = validate_case(bad_case)
    assert not res.ok()
    assert any("Decision completeness" in e or "vip_customer" in e for e in res.errors)

def test_validator_output_is_deterministic():
    r1 = validate_case(FIXTURE)
    r2 = validate_case(FIXTURE)
    assert r1.to_dict() == r2.to_dict(), "validator output not deterministic"
