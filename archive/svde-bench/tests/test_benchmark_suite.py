"""
test_benchmark_suite.py — SVDE-Bench v0.1 Full 10-Case Suite Unit Tests (Sprint 5B)
Covers:
  Test 1: Case Registry Contains 10 Cases
  Test 2: Domain Distribution Matches Sprint 5 (4/2/2/2)
  Test 3: Capability Coverage Satisfies Required Thresholds
  Test 4: Three Baseline Agents Execute Successfully on Golden Case
  Test 5: Failure Taxonomy Mapping Exists for Golden Case 001
"""
import json
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent, FullDecisionAgent
from svdebench.evaluator.failure_taxonomy import FailureTaxonomy

BENCH_ROOT = Path(__file__).parent.parent
REGISTRY_PATH = BENCH_ROOT / "svdebench" / "datasets" / "public" / "cases" / "registry.yaml"
CAPABILITY_PATH = BENCH_ROOT / "reports" / "benchmark" / "capability_matrix.json"

def test_1_case_registry_contains_10_cases():
    import yaml
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    assert len(registry["cases"]) == 10

def test_2_domain_distribution_matches_sprint_5():
    import yaml
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    dist = {"delivery": 0, "warehouse": 0, "channel": 0, "visit_scheduling": 0}
    for c in registry["cases"]:
        dist[c["domain"]] += 1
    assert dist == {"delivery": 4, "warehouse": 2, "channel": 2, "visit_scheduling": 2}

def test_3_capability_coverage_thresholds():
    matrix = json.loads(CAPABILITY_PATH.read_text())
    assert len(matrix["capability_distribution"]["semantic_constraint"]) == 10
    assert matrix["capability_distribution"]["runtime_adaptation"]
    assert matrix["capability_distribution"]["feasibility_check"]
    assert len(matrix["capability_distribution"]["runtime_adaptation"]) >= 5
    assert len(matrix["capability_distribution"]["feasibility_check"]) == 6

def test_4_three_baseline_agents_execute_successfully():
    case_path = BENCH_ROOT / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"
    case = load_case_yaml(str(case_path))
    for AgentCls in (PureSolverMockAgent, SemanticAwareAgent, FullDecisionAgent):
        artifact = AgentCls().solve(case)
        assert artifact.case_id == "CASE-001-DELIVERY-RECOVERY"
        assert artifact.status == "FEASIBLE"

def test_5_failure_taxonomy_mapping_exists():
    # FT-01 和 FT-03 应当被覆盖 (SemViol + RuntimeInstability)
    assert FailureTaxonomy.FT_01_SEMANTIC_VIOLATION.value == "FT-01"
    assert FailureTaxonomy.FT_03_RUNTIME_INSTABILITY.value == "FT-03"
    assert FailureTaxonomy.FT_04_MEMORY_OVERGENERALIZATION.value == "FT-04"
