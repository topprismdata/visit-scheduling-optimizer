"""Decision Scenario Synthesizer for SVDE-Bench v0.2.

Synthesizes decision scenarios from domain decision pattern templates rather than random data.
Generates multi-file case directories strictly conforming to Layer 1 schemas with pattern_id preservation.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


class DecisionScenarioSynthesizer:
    def __init__(self, templates_file: Optional[Path] = None):
        if templates_file and templates_file.exists():
            self.templates_file = templates_file
        else:
            default_tpl = Path(__file__).resolve().parents[2] / "domains" / "delivery" / "scenario_templates.yaml"
            self.templates_file = default_tpl if default_tpl.exists() else None

    def load_templates(self) -> List[Dict[str, Any]]:
        if not self.templates_file or not self.templates_file.exists():
            return []
        with open(self.templates_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("templates", [])

    def synthesize_from_template(
        self,
        tpl: Dict[str, Any],
        target_dir: Path,
        case_id: Optional[str] = None,
        difficulty: str = "L2",
    ) -> Path:
        cid = case_id or tpl.get("case_code", "CASE-SYNTH-001")
        pattern_id = tpl.get("pattern_id", "PATTERN-UNKNOWN")
        variant_name = tpl.get("variant_name", "")
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Metadata with pattern_id preserved
        metadata = {
            "case_id": cid,
            "domain": "delivery",
            "version": "1.0",
            "created_at": "2026-08-24",
            "tags": ["extended", "v0.2", pattern_id.lower(), f"variant:{variant_name.lower().replace(' ', '_')}"],
            "difficulty": difficulty,
            "pattern": {
                "id": pattern_id,
                "variant_name": variant_name,
                "dilemma": tpl.get("decision_dilemma", ""),
            },
        }

        # 2. Intent
        intent = tpl.get("intent", {})

        # 3. World State (entities + relationships)
        world_raw = tpl.get("world_state", {})
        fleet = world_raw.get("fleet", [])
        customers = world_raw.get("customers", [])
        orders = world_raw.get("orders", [])

        # Construct relationships
        planned_orders = [o["id"] for o in orders if o.get("is_locked")]
        vehicle_id = fleet[0]["id"] if fleet else "VEH_01"
        relationships = {
            "vehicle_route": [{"vehicle": vehicle_id, "planned_orders": planned_orders}],
            "customer_priority": [{"customer": c["id"], "commitment": "sla_commitment"} for c in customers if c.get("priority") == "vip"],
        }
        world_state = {
            "entities": {
                "vehicles": fleet,
                "customers": customers,
                "orders": orders,
            },
            "relationships": relationships,
        }

        # 4. Constraints
        constraints = tpl.get("constraints", {"hard": [], "soft": [], "preference": []})

        # 5. Decision Space
        decision_space = tpl.get("decision_space", {
            "objective": "lexicographic_max_fulfilled_then_min_disruption",
            "candidate_solutions_count": 2,
            "parallel_options": [],
        })

        # 6. Evaluation
        evaluation = tpl.get("evaluation", {
            "expected_difficulty": "medium",
            "expected_agent_separation": True,
            "separation_dimensions": ["semantic", "feasibility"],
            "success_threshold": {"semantic_min": 0.9, "commitment_survival_min": 1.0},
        })

        files = {
            "metadata.yaml": metadata,
            "intent.yaml": intent,
            "world_state.yaml": world_state,
            "constraints.yaml": constraints,
            "decision_space.yaml": decision_space,
            "evaluation.yaml": evaluation,
        }

        for filename, content in files.items():
            with open(target_dir / filename, "w", encoding="utf-8") as f:
                yaml.dump(content, f, sort_keys=False)

        return target_dir

    def synthesize_from_pattern(
        self,
        pattern_id: str,
        target_dir: Path,
        case_id: Optional[str] = None,
        difficulty: str = "L2",
    ) -> Path:
        templates = self.load_templates()
        tpl = next((t for t in templates if t.get("pattern_id") == pattern_id), None)
        if not tpl:
            raise ValueError(f"Pattern ID '{pattern_id}' not found in templates ({self.templates_file})")
        return self.synthesize_from_template(tpl, target_dir, case_id=case_id, difficulty=difficulty)

    def synthesize_minimal_delivery_case(self, target_dir: Path, case_id: str = "SYNTH-DELIVERY-001") -> Path:
        templates = self.load_templates()
        if templates:
            return self.synthesize_from_template(templates[0], target_dir, case_id=case_id)
        # Fallback if no templates found
        target_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "metadata.yaml": {"case_id": case_id, "domain": "delivery", "version": "1.0", "created_at": "2026-08-24", "tags": ["fallback"], "difficulty": "L2"},
            "intent.yaml": {"primary_objective": "maximize_fulfilled", "secondary_objectives": [], "priority_rules": {"vip_customer": "high", "cost": "medium"}},
            "world_state.yaml": {"entities": {"vehicles": [], "customers": [], "orders": []}, "relationships": {}},
            "constraints.yaml": {"hard": [], "soft": [], "preference": []},
            "decision_space.yaml": {"objective": "cost", "candidate_solutions_count": 1, "parallel_options": []},
            "evaluation.yaml": {"expected_difficulty": "easy", "expected_agent_separation": False, "separation_dimensions": [], "success_threshold": {}},
        }
        for filename, content in files.items():
            with open(target_dir / filename, "w", encoding="utf-8") as f:
                yaml.dump(content, f, sort_keys=False)
        return target_dir

    def synthesize_by_case_code(self, case_code: str, target_dir: Path) -> Path:
        templates = self.load_templates()
        tpl = next((t for t in templates if t.get("case_code") == case_code), None)
        if not tpl:
            raise ValueError(f"Case code '{case_code}' not found in templates")
        return self.synthesize_from_template(tpl, target_dir, case_id=f"CASE-{case_code}")

    def synthesize_all_cases(self, base_dir: Path) -> List[Path]:
        templates = self.load_templates()
        generated_paths = []
        for tpl in templates:
            code = tpl.get("case_code", "DXX")
            case_dir = base_dir / code
            p = self.synthesize_from_template(tpl, case_dir, case_id=f"CASE-{code}")
            generated_paths.append(p)
        return generated_paths
