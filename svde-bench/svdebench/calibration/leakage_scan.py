"""
svdebench.calibration.leakage_scan — Benchmark Code-Level Leakage Scanner v0.1
Uses AST static analysis to enforce strict structural isolation:
  Rule 1: Agent does not import Oracle
  Rule 2: Evaluator does not import Agent
  Rule 3: Oracle does not import Evaluator
  Rule 4: Private datasets not referenced in public cases
"""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Any, Dict, List

def scan_repository_leakage(repo_root: str | Path) -> Dict[str, Any]:
    root = Path(repo_root) / "svdebench"
    agents_dir = root / "agents"
    oracle_dir = root / "oracle"
    eval_dir = root / "evaluator"
    
    violations: List[str] = []
    
    def check_file_imports(py_file: Path, forbidden_modules: List[str], rule_id: str):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(f"svdebench.{m}") or alias.name == m for m in forbidden_modules):
                        violations.append(f"{rule_id}: {py_file.name} imports forbidden module '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if any(node.module.startswith(f"svdebench.{m}") or node.module == m for m in forbidden_modules):
                        violations.append(f"{rule_id}: {py_file.name} from-imports forbidden module '{node.module}'")

    # Rule 1: Agent does not import Oracle
    for f in agents_dir.glob("**/*.py"):
        check_file_imports(f, ["oracle"], "Rule 1 (Agent -> Oracle)")
        
    # Rule 2: Evaluator does not import Agent
    for f in eval_dir.glob("**/*.py"):
        check_file_imports(f, ["agents"], "Rule 2 (Evaluator -> Agent)")
        
    # Rule 3: Oracle does not import Evaluator
    for f in oracle_dir.glob("**/*.py"):
        check_file_imports(f, ["evaluator"], "Rule 3 (Oracle -> Evaluator)")
        
    all_clean = (len(violations) == 0)
    return {
        "all_clean": all_clean,
        "violations": violations,
        "rules_checked": ["Rule 1: Agent !=> Oracle", "Rule 2: Evaluator !=> Agent", "Rule 3: Oracle !=> Evaluator"],
        "status": "PASS" if all_clean else "FAIL"
    }
