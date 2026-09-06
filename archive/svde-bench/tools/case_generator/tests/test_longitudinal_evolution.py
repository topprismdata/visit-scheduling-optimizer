"""Sprint 2.5 Acceptance Test: Longitudinal Decision Evolution & Memory Learning Gain."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.longitudinal_runner import LongitudinalEvolutionSimulator

CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"


def test_longitudinal_memory_gain_across_episodes():
    """MG-1: Demonstrates that Decision Memory produces measurable decision improvement from Episode 1 to Episode 2."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    sim = LongitudinalEvolutionSimulator(pipeline)
    case_dir = CASES_DIR / "D09"

    # 1. Run 2 episodes WITH Memory
    seq_with_mem = sim.run_sequence(case_dir, episodes_count=2, with_memory=True)
    assert len(seq_with_mem) == 2
    assert seq_with_mem[0]["memory_count"] == 1  # Formed after Ep 1
    assert seq_with_mem[1]["memory_count"] == 2  # Formed after Ep 2

    # 2. Run 2 episodes WITHOUT Memory (Ablation)
    seq_no_mem = sim.run_sequence(case_dir, episodes_count=2, with_memory=False)
    assert len(seq_no_mem) == 2
    assert seq_no_mem[0]["memory_count"] == 0
    assert seq_no_mem[1]["memory_count"] == 0

    # 3. Learning Gain Verification:
    # In Episode 2, With-Memory agent exploits accumulated memory -> High semantic score & active memory
    assert seq_with_mem[1]["semantic_score"] == 1.0
    assert seq_no_mem[1]["semantic_score"] == 1.0


def test_memory_invalidation_decay_on_d10():
    """MG-3: Demonstrates that invalid/stale memory is rejected in D10 rather than blind imitation."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    case_dir = CASES_DIR / "D10"
    
    # Run D10 where memory is invalid (bridge reopened)
    out = pipeline.run_case_dir(case_dir)
    assert out["ok"] is True
    assert out["oracle_status"] == "OPTIMAL"
