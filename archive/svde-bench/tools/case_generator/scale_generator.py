"""Scalable Stress Benchmark Generator for SVDE-Bench v0.5 (Sprint 5.2).

Generates realistic, scalable combinatorial stress cases beyond toy scale:
- Small (N=10 tasks, 3 resources): Fast sanity check and semantic logic verification.
- Medium (N=50 tasks, 10 resources): Combinatorial contention, dense time windows, and multi-vehicle routing.
- Large (N=200 tasks, 30 resources): City-scale distribution stress benchmark with capacity and SLA constraints.
- Stress (N=500 tasks, 60 resources): Massive enterprise scale testing solver timeout and heuristic degradation.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import random
import yaml


class ScalableBenchmarkGenerator:
    """Generates parameterized large-scale decision benchmark cases conforming to Layer 1 schemas."""
    
    def __init__(self, random_seed: int = 42):
        self.random_seed = random_seed
        random.seed(random_seed)

    def generate_delivery_stress_case(
        self,
        task_count: int,
        resource_count: int,
        target_dir: Path,
        case_id: Optional[str] = None,
        vip_ratio: float = 0.20,
        cold_ratio: float = 0.25,
        horizon_minutes: int = 480
    ) -> Path:
        cid = case_id or f"STRESS-DELIVERY-N{task_count}-R{resource_count}"
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Metadata
        difficulty = "L2" if task_count <= 20 else ("L3" if task_count <= 100 else "L4")
        metadata = {
            "case_id": cid,
            "domain": "delivery",
            "version": "1.0",
            "created_at": "2026-08-24",
            "tags": ["stress_benchmark", f"scale_N{task_count}", f"fleet_R{resource_count}"],
            "difficulty": difficulty,
            "scale_profile": {
                "task_count": task_count,
                "resource_count": resource_count,
                "vip_ratio": vip_ratio,
                "cold_ratio": cold_ratio,
            }
        }

        # 2. Intent
        intent = {
            "primary_objective": "maximize_vip_commitment_fulfillment_then_min_distance",
            "secondary_objectives": ["minimize_fleet_count", "balance_driver_shifts"],
            "priority_rules": {
                "vip_customer": "high",
                "cost": "medium",
                "service_level": "high"
            }
        }

        # 3. World State (Parameterized Generation)
        fleet: List[Dict[str, Any]] = []
        cold_resource_count = max(1, int(resource_count * cold_ratio))
        
        for r_idx in range(1, resource_count + 1):
            is_cold = r_idx <= cold_resource_count
            v_type = "COLD_REFRIGERATED" if is_cold else "STANDARD_VAN"
            cap = 1200 if is_cold else 1000
            fleet.append({
                "id": f"VEH_{r_idx:03d}",
                "type": v_type,
                "capacity_kg": cap,
                "status": "AVAILABLE"
            })

        customers: List[Dict[str, Any]] = []
        orders: List[Dict[str, Any]] = []
        hard_constraints: List[Dict[str, Any]] = []

        hard_constraints.append({
            "id": "C_CAP_GLOBAL",
            "name": "GlobalFleetCapacityLimit",
            "type": "VEHICLE_CAPACITY",
            "hardness": "HARD",
            "relaxable": False
        })
        hard_constraints.append({
            "id": "C_COLD_GLOBAL",
            "name": "GlobalColdChainCompartmentMatch",
            "type": "COLD_CHAIN_MATCH",
            "hardness": "HARD",
            "relaxable": False
        })

        for t_idx in range(1, task_count + 1):
            c_id = f"CUST_{t_idx:03d}"
            is_vip = (random.random() < vip_ratio)
            req_cold = (random.random() < cold_ratio)
            weight = random.randint(30, 200)

            # Staggered realistic time-windows across horizon
            tw_start = random.randint(0, max(0, horizon_minutes - 180))
            tw_window_len = 120 if is_vip else 240
            tw_end = min(horizon_minutes, tw_start + tw_window_len)

            customers.append({
                "id": c_id,
                "name": f"Enterprise Client {t_idx}",
                "priority": "vip" if is_vip else "standard"
            })

            orders.append({
                "id": f"ORD_{t_idx:03d}",
                "weight_kg": weight,
                "req_cold": req_cold,
                "is_locked": is_vip,
                "is_vip": is_vip,
                "tw_early": tw_start,
                "tw_late": tw_end
            })

            if is_vip:
                hard_constraints.append({
                    "id": f"C_LOCK_ORD_{t_idx:03d}",
                    "name": f"VIPTimeLock_{t_idx:03d}",
                    "type": "TIME_WINDOW_LOCKED",
                    "hardness": "HARD_COMMITMENT",
                    "target_order": f"ORD_{t_idx:03d}",
                    "locked_window": [tw_start, tw_end],
                    "relaxable": False
                })

        world_state = {
            "entities": {
                "vehicles": fleet,
                "customers": customers,
                "orders": orders,
            },
            "relationships": {
                "vehicle_route": [{"vehicle": fleet[0]["id"], "planned_orders": [o["id"] for o in orders if o["is_locked"]]}],
                "customer_priority": [{"customer": c["id"], "commitment": "sla_lock"} for c in customers if c["priority"] == "vip"],
            }
        }

        # 4. Constraints
        constraints = {
            "hard": hard_constraints,
            "soft": [{"id": "C_DISTANCE_OPT", "name": "MinimizeFleetDistance", "weight": 1.0}],
            "preference": [{"description": "Prioritize on-time VIP fulfillment over dense route consolidation"}],
        }

        # 5. Decision Space
        decision_space = {
            "objective": "lexicographic_vip_fulfillment_then_cost",
            "candidate_solutions_count": 5,
            "parallel_options": [
                {"id": "opt_sla_first", "description": "Prioritize all VIP windows with dedicated fleet routing"},
                {"id": "opt_dense_cluster", "description": "Cluster by geographic proximity risking window delay"}
            ]
        }

        # 6. Evaluation
        evaluation = {
            "expected_difficulty": difficulty,
            "expected_agent_separation": True,
            "separation_dimensions": ["semantic", "feasibility", "runtime"],
            "success_threshold": {
                "semantic_min": 0.90,
                "commitment_survival_min": 1.0
            }
        }

        # Write out Layer 1 files
        files = {
            "metadata.yaml": metadata,
            "intent.yaml": intent,
            "world_state.yaml": world_state,
            "constraints.yaml": constraints,
            "decision_space.yaml": decision_space,
            "evaluation.yaml": evaluation,
        }

        for fname, content in files.items():
            with open(target_dir / fname, "w", encoding="utf-8") as f:
                yaml.dump(content, f, sort_keys=False)

        return target_dir

    def generate_suite_matrix(self, base_dir: Path) -> List[Path]:
        """Generates a standard scale benchmark suite: Small(10), Medium(50), Large(100)."""
        scales = [
            ("SCALE-S-N10", 10, 3),
            ("SCALE-M-N50", 50, 10),
            ("SCALE-L-N100", 100, 20),
        ]
        generated: List[Path] = []
        for name, n_tasks, n_res in scales:
            p = base_dir / name
            self.generate_delivery_stress_case(
                task_count=n_tasks,
                resource_count=n_res,
                target_dir=p,
                case_id=name
            )
            generated.append(p)
        return generated
