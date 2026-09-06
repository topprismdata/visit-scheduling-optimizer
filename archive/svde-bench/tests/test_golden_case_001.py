"""
test_golden_case_001.py — End-to-End Pipeline Unit Tests (Sprint 2)
Covers:
  Test 1: Case loading from YAML
  Test 2: Baseline Agent execution (Pure Solver vs Semantic Aware)
  Test 3: Artifact validation & Hard commitment checking
  Test 4: Trace generation & Causal rationale integrity
  Test 5: Memory patch validation & Semantic Law compliance
"""
import json
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent
from svdebench.runner import run_case_pipeline, validate_artifact_semantics

CASE_PATH = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"
REPORT_DIR = Path(__file__).parent.parent / "reports"

def test_1_case_loading():
    case = load_case_yaml(str(CASE_PATH))
    assert case.metadata.id == "CASE-001-DELIVERY-RECOVERY"
    assert case.metadata.domain == "Dynamic Fleet Route Logistics"
    assert len(case.world_state["fleet"]) == 3
    assert case.events[0]["event_type"] == "VEHICLE_MECHANICAL_BREAKDOWN"

def test_2_agent_execution_and_comparison():
    case = load_case_yaml(str(CASE_PATH))
    agent_a = PureSolverMockAgent()
    agent_b = SemanticAwareAgent()
    
    artifact_a = agent_a.solve(case)
    artifact_b = agent_b.solve(case)
    
    # Baseline A drops ORD_03 to save cost; Baseline B reallocates ORD_03 to VEH_03
    assert "ORD_03" not in artifact_a.decision["reassigned_routes"]["VEH_03"]
    assert "ORD_03" in artifact_b.decision["reassigned_routes"]["VEH_03"]
    assert artifact_a.decision["total_additional_cost"] < artifact_b.decision["total_additional_cost"]

def test_3_artifact_validation():
    case = load_case_yaml(str(CASE_PATH))
    agent_a = PureSolverMockAgent()
    agent_b = SemanticAwareAgent()
    
    artifact_a = agent_a.solve(case)
    artifact_b = agent_b.solve(case)
    
    val_a = validate_artifact_semantics(case, artifact_a)
    val_b = validate_artifact_semantics(case, artifact_b)
    
    # Baseline A fails decision feasibility due to broken commitment
    assert val_a["lock_commitment_honored"] is False
    assert val_a["decision_feasible"] is False
    assert val_a["verdict"] == "FAIL"
    
    # Baseline B passes decision feasibility
    assert val_b["lock_commitment_honored"] is True
    assert val_b["decision_feasible"] is True
    assert val_b["verdict"] == "PASS"

def test_4_trace_generation_integrity():
    case = load_case_yaml(str(CASE_PATH))
    agent_b = SemanticAwareAgent()
    artifact_b = agent_b.solve(case)
    
    assert artifact_b.trace.trace_id == "TR-SEMANTIC-CASE-001-DELIVERY-RECOVERY"
    assert len(artifact_b.trace.decision_chain) == 4
    assert artifact_b.trace.causal_rationale[0]["order"] == "ORD_03"
    assert artifact_b.trace.causal_rationale[0]["action"] == "REASSIGNED_TO_VEH_03"

def test_5_memory_patch_validation_and_report():
    case = load_case_yaml(str(CASE_PATH))
    agent_b = SemanticAwareAgent()
    
    # Run pipeline & generate report
    report = run_case_pipeline(case, agent_b)
    assert report["validation"]["verdict"] == "PASS"
    assert report["memory"]["memory_id"] == "DMEM-EPISODE-RECOVERY-001"
    assert report["memory"]["lifecycle"] == "CANDIDATE"
    
    # Save Golden Case 001 Report (Artifact 3)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / "golden_case_001_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    assert report_file.exists()
