"""Oracle Manifest Generator - 输出 oracle_manifest.json"""
import json, ast
from pathlib import Path
from typing import Dict, Any
from datetime import datetime as dt

def _check_leakage(svde_root: Path) -> bool:
    """简单的 AST 静态扫描: 检查 oracle 子包是否导入 agents 或 evaluator"""
    oracle_dir = svde_root / "svdebench" / "oracle"
    forbidden_prefixes = ("svdebench.agents", "svdebench.evaluator")
    for f in oracle_dir.glob("**/*.py"):
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden_prefixes):
                        return False
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(forbidden_prefixes):
                    return False
    return True

def build_oracle_manifest(svde_root: Path, registry) -> Dict[str, Any]:
    leakage_ok = _check_leakage(svde_root)
    entries = registry.export()
    return {
        "manifest_version": "1.0",
        "generated_at": dt.now().isoformat(),
        "leakage_scan": "PASS" if leakage_ok else "FAIL",
        "registry_size": registry.size(),
        "entries": entries,
        "summary": {
            "total_cases": len(set(e["case_id"] for e in entries)),
            "optimal_count": sum(1 for e in entries if e["status"] == "OPTIMAL"),
            "feasible_count": sum(1 for e in entries if e["status"] == "FEASIBLE"),
            "infeasible_count": sum(1 for e in entries if e["status"] == "INFEASIBLE"),
        }
    }
