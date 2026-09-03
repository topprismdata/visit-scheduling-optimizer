"""Day 1 Acceptance Test: minimal fixture passes full schema validation.
This is the single most important test for Day 1 — it proves the schema+validator
pipeline actually works before adding any more abstractions.
"""
import subprocess, sys
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_case"

def test_minimal_fixture_validates_cleanly():
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "schema_validator.py"), str(FIXTURE)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"validator failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert "ok" in result.stdout

def test_validator_rejects_missing_file():
    incomplete = FIXTURE.parent / "incomplete_case"
    incomplete.mkdir(exist_ok=True)
    (incomplete / "metadata.yaml").write_text("case_id: X\n")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "schema_validator.py"), str(incomplete)],
        capture_output=True, text=True
    )
    assert result.returncode != 0, "validator should have failed on incomplete case"
    assert "errors" in result.stdout or "missing" in result.stdout

def test_validator_rejects_incomplete_vip_metadata():
    """Decision Completeness Check: VIP lock without priority_rules.vip_customer → error."""
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
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "schema_validator.py"), str(bad_case)],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "Decision completeness" in result.stdout or "vip_customer" in result.stdout

def test_validator_output_is_deterministic():
    """Reproducibility: same case, two runs → identical output."""
    r1 = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "schema_validator.py"), str(FIXTURE)],
        capture_output=True, text=True
    )
    r2 = subprocess.run(
        [sys.executable, str(Path(__file__).parent.parent / "schema_validator.py"), str(FIXTURE)],
        capture_output=True, text=True
    )
    assert r1.stdout == r2.stdout, "validator output not deterministic"
