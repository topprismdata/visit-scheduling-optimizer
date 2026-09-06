"""
test_oracle_calibration.py — Oracle Stability & Sanity Calibration Unit Tests (Sprint 4.5)
Covers:
  Test 1: Infeasible Case Detection (Case A)
  Test 2: Multiple Symmetrical Optimums Handling (Case B)
  Test 3: Multi-tier Objective Trade-off Stability (Case C)
  Test 4: Repeated Solve Determinism (Purity & Stability)
  Test 5: Constraint Coverage & Sanity Audit
"""
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.oracle.cpsat import CPSATExactOracle
from svdebench.calibration.oracle_audit import audit_oracle_sanity

CALIB_DIR = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "calibration"

def test_1_infeasible_case_detection():
    case_path = str(CALIB_DIR / "CALIB-CASE-A-INFEASIBLE.yaml")
    res = audit_oracle_sanity(case_path)
    
    assert res["case_id"] == "CALIB-CASE-A-INFEASIBLE"
    assert res["solver_status"] == "INFEASIBLE"
    assert res["feasibility_status"] == "INFEASIBLE"
    assert res["objective_value"] is None

def test_2_multiple_symmetrical_optimum_handling():
    case_path = str(CALIB_DIR / "CALIB-CASE-B-SYMMETRIC.yaml")
    
    # 两个独立 Oracle 实例求解对称问题
    oracle1 = CPSATExactOracle(random_seed=11)
    oracle2 = CPSATExactOracle(random_seed=99)
    
    case = load_case_yaml(case_path)
    ref1 = oracle1.solve(case)
    ref2 = oracle2.solve(case)
    
    # 对称解路径可能不同，但客观目标值必须绝对相同
    assert ref1.solver_status == "OPTIMAL"
    assert ref2.solver_status == "OPTIMAL"
    assert ref1.objective_value == ref2.objective_value

def test_3_objective_tradeoff_stability():
    case_path = str(CALIB_DIR / "CALIB-CASE-C-TRADEOFF.yaml")
    res = audit_oracle_sanity(case_path)
    
    assert res["solver_status"] == "OPTIMAL"
    assert res["feasibility_status"] == "FEASIBLE"
    assert res["objective_value"] > 0

def test_4_repeated_solve_determinism():
    case_path = str(CALIB_DIR / "CALIB-CASE-C-TRADEOFF.yaml")
    case = load_case_yaml(case_path)
    
    oracle = CPSATExactOracle(random_seed=42)
    results = [oracle.solve(case).objective_value for _ in range(5)]
    
    # 5 次重复求解目标值 100% 相同
    assert len(set(results)) == 1

def test_5_constraint_coverage_sanity():
    case_path = str(CALIB_DIR / "CALIB-CASE-B-SYMMETRIC.yaml")
    case = load_case_yaml(case_path)
    oracle = CPSATExactOracle()
    ref = oracle.solve(case)
    
    assert ref.constraint_summary["capacity_constraints"] == "SATISFIED"
