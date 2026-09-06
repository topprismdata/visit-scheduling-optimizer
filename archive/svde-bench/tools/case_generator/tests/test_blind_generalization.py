"""Sprint 3.4-C Acceptance Test: Blind Generalization Validation across Unseen Cases."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.blind_generalization_runner import BlindGeneralizationRunner

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_blind_generalization_held_out_evaluation():
    """Validates that Governed Principles outperform Raw Episodes on unseen held-out cases."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    runner = BlindGeneralizationRunner(pipeline)

    # 1. Training Set (Discovery): D01-D08 + V01-V06 (14 cases)
    training_cases = [DELIVERY_CASES_DIR / f"D{i:02d}" for i in range(1, 9)] + \
                     [VISIT_CASES_DIR / f"V{i:02d}" for i in range(1, 7)]

    governed_decisions = runner.run_training_discovery(training_cases)
    promoted = [d for d in governed_decisions if d.status == "PROMOTED"]
    assert len(promoted) >= 2, f"Expected >= 2 promoted principles, got {len(promoted)}"

    # 2. Held-out Validation Set: D09-D10 + V07-V10 (6 unseen cases)
    held_out_cases = [DELIVERY_CASES_DIR / f"D{i:02d}" for i in [9, 10]] + \
                     [VISIT_CASES_DIR / f"V{i:02d}" for i in range(7, 11)]

    matrix = runner.evaluate_held_out_cases(held_out_cases, governed_decisions)

    # 3. Decision Quality Lift Analysis:
    # Regime 2 (Raw Episode Memory) suffers negative transfer on D10/V10 -> Drops locked orders -> Grade F
    # Regime 3 (Governed Principle Memory) passes all held-out cases -> Grade A
    
    raw_grades = [p["overall"]["grade"] for p in matrix["raw_episode"]]
    gov_grades = [p["overall"]["grade"] for p in matrix["governed_principle"]]

    assert "F" in raw_grades, "Raw Episode Memory should suffer negative transfer on D10/V10"
    assert all(g == "A" for g in gov_grades), f"Governed Principles should achieve Grade A across held-out cases: {gov_grades}"

    # 4. Negative Transfer Poison Rate Check:
    # Raw Memory fails on 2/6 held-out cases (D10, V10) -> R_poison = 33.3%
    # Governed Principle has R_poison = 0.0%
    poison_raw_count = sum(1 for g in raw_grades if g == "F")
    poison_gov_count = sum(1 for g in gov_grades if g == "F")

    assert poison_raw_count == 2
    assert poison_gov_count == 0  # 100% negative transfer resistance
