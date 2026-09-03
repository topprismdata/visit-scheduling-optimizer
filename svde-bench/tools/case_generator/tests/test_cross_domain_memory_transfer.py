"""Sprint 3.3 Acceptance Test: Cross-Domain Memory Transfer & Negative Transfer Defense."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.cross_domain_transfer_runner import CrossDomainTransferSimulator

VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_abstract_decision_principle_transfer():
    """Experiment 3: Validates abstract decision principle transfer from Delivery domain to Visit domain (V04)."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    sim = CrossDomainTransferSimulator(pipeline)
    
    target_case_dir = VISIT_CASES_DIR / "V04"
    res = sim.run_abstract_principle_transfer(target_case_dir)

    assert res["ok"] is True
    assert res["oracle_status"] == "OPTIMAL"
    
    prof = res["profile"]
    assert prof["evaluation"]["semantic"]["score"] == 1.0
    
    # Verify 5th dimension Generalization extension
    gen = prof["evaluation"]["extensions"]["generalization"]
    assert gen["transfer_type"] == "CROSS_DOMAIN_PRINCIPLE"
    assert gen["transfer_decision"] == "ACCEPT"
    assert gen["source_domain"] == "delivery"
    assert gen["target_domain"] == "visit"
    assert gen["negative_transfer_resisted"] is True


def test_negative_memory_injection_and_rejection_defense():
    """Experiment 2 & Gate 16: Negative memory injection fails context check and is rejected on V10."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    sim = CrossDomainTransferSimulator(pipeline)

    target_case_dir = VISIT_CASES_DIR / "V10"
    res = sim.run_negative_memory_injection(target_case_dir)

    assert res["ok"] is True
    assert res["oracle_status"] == "OPTIMAL"

    prof = res["profile"]
    gen = prof["evaluation"]["extensions"]["generalization"]
    assert gen["transfer_type"] == "NEGATIVE_MEMORY_INJECTION"
    assert gen["transfer_decision"] == "REJECT"
    assert gen["negative_transfer_resisted"] is True
    assert "Context boundary mismatch" in gen["rejection_reason"]
