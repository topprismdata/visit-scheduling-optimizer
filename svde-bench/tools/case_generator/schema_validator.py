"""SVDE-Bench v0.2 — Schema Validator (Day 1 minimal fixture)

Validates that a multi-file case directory conforms to the schema structures
defined under schemas/case/. This is a Layer-1 + Decision-Completeness validator
NOT a full domain validator (Layer 2).
"""
from pathlib import Path
from typing import Dict, List, Any
import yaml

SCHEMA_FILES = {
    "metadata": ["case_id", "domain", "version", "created_at", "tags", "difficulty"],
    "intent": ["primary_objective", "secondary_objectives", "priority_rules"],
    "world_state": ["entities", "relationships"],
    "constraints": ["hard", "soft", "preference"],
    "decision_space": ["objective", "candidate_solutions_count", "parallel_options"],
    "evaluation": ["expected_difficulty", "expected_agent_separation", "separation_dimensions", "success_threshold"],
}

class ValidationResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def ok(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok(), "errors": self.errors, "warnings": self.warnings}


def validate_case(case_dir: Path) -> ValidationResult:
    res = ValidationResult()
    if not case_dir.is_dir():
        res.errors.append(f"case_dir {case_dir} is not a directory")
        return res

    # Load all sub-files
    yaml_data: Dict[str, Dict[str, Any]] = {}
    for sub in SCHEMA_FILES.keys():
        path = case_dir / f"{sub}.yaml"
        if not path.exists():
            res.errors.append(f"missing required sub-file: {path.name}")
            continue
        try:
            with open(path) as f:
                yaml_data[sub] = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            res.errors.append(f"yaml parse error in {path.name}: {e}")
            continue

    # Field-level checks (lightweight, no Pydantic yet)
    for sub, required_fields in SCHEMA_FILES.items():
        if sub not in yaml_data:
            continue
        data = yaml_data[sub]
        if not isinstance(data, dict):
            res.errors.append(f"{sub}.yaml must be a mapping at top level")
            continue
        for field in required_fields:
            if field not in data:
                res.errors.append(f"missing field in {sub}.yaml: {field}")

    # Decision-completeness cross-field check
    constraints = yaml_data.get("constraints", {})
    evaluation = yaml_data.get("evaluation", {})
    hard = constraints.get("hard", []) if isinstance(constraints.get("hard"), list) else []

    has_vip_lock = any("VIP" in str(c).upper() or "TIME_WINDOW_HARD" in str(c) for c in hard)
    if has_vip_lock:
        intent = yaml_data.get("intent", {})
        pr = intent.get("priority_rules", {}) if isinstance(intent.get("priority_rules"), dict) else {}
        if "vip_customer" not in pr:
            res.errors.append("Decision completeness: VIP lock exists but priority_rules.vip_customer not declared")
        success = evaluation.get("success_threshold", {}) if isinstance(evaluation.get("success_threshold"), dict) else {}
        if "commitment_survival_min" not in success:
            res.errors.append("Decision completeness: VIP lock exists but evaluation.success_threshold.commitment_survival_min not declared")

    return res


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: validate_case.py <case_dir>")
        sys.exit(1)
    case_dir = Path(sys.argv[1])
    res = validate_case(case_dir)
    import json
    print(json.dumps(res.to_dict(), indent=2))
    sys.exit(0 if res.ok() else 2)


if __name__ == "__main__":
    main()
