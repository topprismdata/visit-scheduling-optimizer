"""Sprint 3.2 Acceptance Test: Visit Domain Benchmark Validation & Cross-Domain Capability Transfer."""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.case_synthesizer import DecisionScenarioSynthesizer
from tools.case_generator.schema_validator import validate_case
from tools.case_generator.pipeline_runner import FullPipelineRunner
from svdebench.agents.baseline import (
    GeneralizedPureSolverAgent,
    ConstraintAwareAgent,
    GeneralizedSemanticAwareAgent,
    GeneralizedFullDecisionAgent,
)

VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"
VISIT_DOMAIN_DIR = Path(__file__).resolve().parents[3] / "domains" / "visit"


def test_gate12_all_10_visit_cases_synthesize_and_validate():
    """Gate 12: All 10 Visit cases V01-V10 synthesize cleanly and pass SchemaValidator."""
    synth = DecisionScenarioSynthesizer(templates_file=VISIT_DOMAIN_DIR / "scenario_templates.yaml")
    paths = synth.synthesize_all_cases(VISIT_CASES_DIR)
    assert len(paths) == 10

    for i in range(1, 11):
        case_dir = VISIT_CASES_DIR / f"V{i:02d}"
        assert case_dir.is_dir()
        res = validate_case(case_dir)
        assert res.ok(), f"Visit case V{i:02d} failed validation: {res.errors}"


def test_gate12_pattern_separation_diversity_visit():
    """Gate 12.2: Pattern Separation - verifies diverse primary objectives & dilemmas across V01-V10."""
    primary_objs = set()
    dilemmas = set()

    for i in range(1, 11):
        case_dir = VISIT_CASES_DIR / f"V{i:02d}"
        with open(case_dir / "intent.yaml", "r", encoding="utf-8") as f:
            intent = yaml.safe_load(f) or {}
        with open(case_dir / "metadata.yaml", "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        primary_objs.add(intent.get("primary_objective"))
        dilemmas.add(meta.get("pattern", {}).get("dilemma"))

    assert len(primary_objs) >= 5, f"Insufficient Visit intent diversity: {len(primary_objs)}"
    assert len(dilemmas) >= 8, f"Insufficient Visit dilemma diversity: {len(dilemmas)}"


def test_gate17_cross_domain_capability_transfer():
    """Gate 17: Validates that 4-tier agent continuum transfers to Visit domain with zero pipeline changes."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    
    for i in range(1, 11):
        case_dir = VISIT_CASES_DIR / f"V{i:02d}"
        out_pure = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedPureSolverAgent)
        out_ca = pipeline.run_case_dir(case_dir, agent_cls=ConstraintAwareAgent)
        out_sem = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedSemanticAwareAgent)
        out_full = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedFullDecisionAgent)

        # 1. PureSolver drops locked account visits to save transit miles -> Semantic 0.0, Grade F
        assert out_pure["profile"]["evaluation"]["semantic"]["score"] == 0.0
        assert out_pure["profile"]["overall"]["grade"] == "F"

        # 2. SemanticAware & FullDecision preserve locked accounts -> Semantic 1.0, Grade A
        assert out_sem["profile"]["evaluation"]["semantic"]["score"] == 1.0
        assert out_sem["profile"]["overall"]["grade"] == "A"
        assert out_full["profile"]["evaluation"]["semantic"]["score"] == 1.0
        assert out_full["profile"]["overall"]["grade"] == "A"

        # 3. FullDecisionAgent admits validated decision memory
        assert out_full["profile"]["evaluation"]["memory"]["score"] >= 0.95
        assert out_full["profile"]["evaluation"]["memory"]["admitted_memory"]["promotion_status"] == "PROMOTED"


def test_v09_v10_memory_transfer_readiness():
    """Validates V09 and V10 cases readiness for cross-case memory transfer and negative transfer defense."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    
    out_v09 = pipeline.run_case_dir(VISIT_CASES_DIR / "V09")
    out_v10 = pipeline.run_case_dir(VISIT_CASES_DIR / "V10")

    assert out_v09["ok"] is True
    assert out_v10["ok"] is True
    assert out_v09["oracle_status"] == "OPTIMAL"
    assert out_v10["oracle_status"] == "OPTIMAL"
