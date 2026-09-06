"""
svdebench.oracle.cpsat.model — Independent CP-SAT Mathematical Constraint Model v0.1
Pure mathematical formulation of physical capacity, time windows, and mathematical commitments.
Strictly isolated from business heuristics, VIP prompts, or agent logic.
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from ortools.sat.python import cp_model
from svdebench.core.case import DecisionCase

class CPSATModelBuilder:
    def __init__(self, case: DecisionCase):
        self.case = case
        self.model = cp_model.CpModel()
        self.vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        
    def build_delivery_model(self) -> Tuple[cp_model.CpModel, Dict[str, Any]]:
        world = self.case.world_state or {}
        fleet = world.get("fleet", [])
        orders = world.get("orders", [])
        contract = self.case.semantic_contract or {}
        constraints = contract.get("constraints", [])
        
        # 1. 创建二元决策变量: x[order_id, vehicle_id]
        for o in orders:
            for v in fleet:
                self.vars[o["id"], v["id"]] = self.model.NewBoolVar(f"o_x_{o['id']}_{v['id']}")
                
        # 2. 约束 1: 物理载重上限 (Vehicle Capacity)
        for v in fleet:
            cap_limit = v.get("capacity_kg", 1000)
            self.model.Add(
                sum(o["weight_kg"] * self.vars[o["id"], v["id"]] for o in orders) <= cap_limit
            )
            
        # 3. 约束 2: 订单必须唯一分配 (单运单单车)
        for o in orders:
            is_opt = o.get("is_optional", False)
            valid_vars = [self.vars[o["id"], v["id"]] for v in fleet]
            if not is_opt:
                self.model.Add(sum(valid_vars) == 1)
            else:
                self.model.Add(sum(valid_vars) <= 1)
                
        # 4. 约束 3: 冷链物理匹配 (Cold Chain Compatibility)
        for o in orders:
            if o.get("req_cold", False):
                for v in fleet:
                    if not v.get("type", "").startswith("COLD"):
                        self.model.Add(self.vars[o["id"], v["id"]] == 0)
                        
        # 5. 约束 4: 数学硬承诺约束 (Mathematical Hard Commitment - e.g. ORD_03 必送)
        for c in constraints:
            if c.get("hardness") == "HARD_COMMITMENT" or c.get("type") == "TIME_WINDOW_LOCKED":
                tgt = c.get("target_order", "ORD_03")
                if any(o["id"] == tgt for o in orders):
                    self.model.Add(sum(self.vars[tgt, v["id"]] for v in fleet) == 1)

        # 6. 客观数学目标: 最大化履约数 - 最小化粗略行驶距离惩罚
        total_fulfilled = sum(var for var in self.vars.values())
        
        def dist_penalty(o_id):
            o_dict = next((item for item in orders if item["id"] == o_id), None)
            if not o_dict: return 20
            return abs(o_dict.get("x", 5)) + abs(o_dict.get("y", 5))
            
        travel_est = sum(dist_penalty(o["id"]) * self.vars[o["id"], v["id"]] for o in orders for v in fleet)
        
        # 标量化目标
        self.model.Maximize(10000 * total_fulfilled - travel_est)
        
        meta = {
            "num_vehicles": len(fleet),
            "num_orders": len(orders),
            "num_variables": len(self.vars)
        }
        return self.model, meta
