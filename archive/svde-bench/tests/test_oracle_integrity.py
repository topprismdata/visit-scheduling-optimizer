"""
test_oracle_integrity.py — Independent Oracle Integrity & Isolation Unit Tests (Sprint 4)
Covers:
  Test 1: Oracle 可以独立加载与独立求解
  Test 2: Oracle 绝对不引用 agents/ 包（AST import 级隔离扫描，Gate 1 执法）
  Test 3: Oracle 不输出 DecisionArtifact，仅输出 OracleReference（Gate 2 执法）
  Test 4: 相同 Case 重复求解结果 100% 确定性幂等一致
  Test 5: Golden Case 001 Oracle Reference 正确生成且达标 OPTIMAL
"""
import ast
from pathlib import Path
from svdebench.core import load_case_yaml
from svdebench.oracle.models import OracleReference
from svdebench.oracle.cpsat import CPSATExactOracle
from svdebench.core.artifact import DecisionArtifact

CASE_PATH = Path(__file__).parent.parent / "svdebench" / "datasets" / "public" / "cases" / "CASE-001-DELIVERY-RECOVERY.yaml"
ORACLE_DIR = Path(__file__).parent.parent / "svdebench" / "oracle"

def test_1_oracle_independent_execution():
    case = load_case_yaml(str(CASE_PATH))
    oracle = CPSATExactOracle()
    ref = oracle.solve(case)
    
    assert isinstance(ref, OracleReference)
    assert ref.case_id == "CASE-001-DELIVERY-RECOVERY"
    assert ref.feasibility_status == "FEASIBLE"
    assert ref.solver_status == "OPTIMAL"
    assert ref.objective_value is not None

def test_2_oracle_no_agent_import_ast_scan():
    # 静态 AST 分析：扫描 svdebench/oracle/ 下所有 .py 文件，严禁 import svdebench.agents
    for py_file in ORACLE_DIR.glob("**/*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "agents" not in alias.name, f"Forbidden import of agents in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert "agents" not in node.module, f"Forbidden from-import of agents in {py_file}"

def test_3_oracle_does_not_output_decision_artifact():
    case = load_case_yaml(str(CASE_PATH))
    oracle = CPSATExactOracle()
    ref = oracle.solve(case)
    
    # Oracle 只输出客观参考，绝不是决策产物
    assert not isinstance(ref, DecisionArtifact)
    assert not hasattr(ref, "decision")
    assert not hasattr(ref, "memory_patch")
    assert not hasattr(ref, "trace")

def test_4_oracle_determinism_and_idempotency():
    case = load_case_yaml(str(CASE_PATH))
    oracle1 = CPSATExactOracle(random_seed=42)
    oracle2 = CPSATExactOracle(random_seed=42)
    
    ref1 = oracle1.solve(case)
    ref2 = oracle2.solve(case)
    
    assert ref1.feasibility_status == ref2.feasibility_status
    assert ref1.objective_value == ref2.objective_value
    assert ref1.solver_status == ref2.solver_status == "OPTIMAL"

def test_5_golden_case_001_gold_reference_generation():
    case = load_case_yaml(str(CASE_PATH))
    oracle = CPSATExactOracle()
    ref = oracle.solve(case)
    
    assert ref.solver_status == "OPTIMAL"
    assert ref.objective_value > 0
    assert ref.solution_metadata["solver"] == "OR-Tools CP-SAT (Independent)"
    assert ref.constraint_summary["commitment_constraints"] == "SATISFIED"
    assert ref.constraint_summary["cold_chain_constraints"] == "SATISFIED"
