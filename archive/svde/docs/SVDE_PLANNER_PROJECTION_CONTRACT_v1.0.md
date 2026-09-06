# SVDE 规划器状态投影契约规范 v1.0 (Planner State Projection Contract)
**Document ID:** SVDE-PLANNER-PROJECTION-CONTRACT-v1.0  
**Date:** 2026-08-24  
**层级定位:** L6: 规划器投影契约层 (Planner Projection Layer)  
**前置基础:** `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md` (L1), `SVDE_STATE_TRANSITION_ENGINE_SPEC_v1.0.md` (L3)  
**核心原则:** 语义隔离与确定性编译。规划求解器 (OR Solvers) 绝不直接依赖复杂领域对象，仅消费严格形式化的轻量纯数学投影载荷；求解结果通过反向投影生成富语义决策候选。

---

## 1. 投影契约的架构隔离定位 (Architectural Decoupling)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   富语义运营决策世界模型 (Rich WorldState)              │
│  (包含 246 门店主数据, 13 KA总部, 18 大仓网络, 双时态生效期, 历史事实流) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼ [PlannerStateProjectionCompiler 前向编译]
┌────────────────────────────────────────────────────────────────────────┐
│                 纯数学规划器投影载荷 (PlannerStateProjection)           │
│  (纯节点索引 0..N, N*N 真实路网耗时矩阵, 严格候选模式空间 P_i, 容量预算)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼ [OR 求解引擎执行优化: CP-SAT / Held-Karp]
┌────────────────────────────────────────────────────────────────────────┐
│                     原始运筹求解序列 (Raw Solver Output)                │
│             (每日时间槽 (w, k) -> 节点索引序列 [0, i_1, i_2, ..., 0])    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼ [Backward Projection 反向语义重塑]
┌────────────────────────────────────────────────────────────────────────┐
│                  富语义候选计划契约 (CandidatePlan & Stops)             │
│      (包含门店编码、门店名称、行政区县、在店动作明细、往返通勤时间)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 前向投影数据契约 (Forward Projection Data Contract)

```python
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any

@dataclass(frozen=True)
class PlannerNodeTopology:
    node_index: int                             # 0 代表 Depot, 1..N 代表客户节点
    domain_entity_id: str                       # 真实业务主键 (如 store_code)
    spatial_coordinate: Tuple[float, float]     # (longitude, latitude)
    service_duration_min: float                 # 动作合成在店时长
    is_depot: bool = False

@dataclass(frozen=True)
class PlannerStateProjection:
    """规划求解器消费的确定性纯数学投影切片"""
    projection_id: str
    target_agent_id: str
    time_slots_count: int                       # 如 20 个时间槽 (4周 x 5工作日)
    
    # 纯数学节点拓扑
    nodes: List[PlannerNodeTopology]
    node_index_lookup: Dict[str, int]           # entity_id -> node_index
    
    # 纯数学距离与通勤矩阵 (由真实路网生成)
    travel_cost_matrix: List[List[float]]       # In-transit time (min)
    travel_distance_matrix: List[List[float]]   # In-transit distance (km)
    
    # 严格候选模式空间 P_i
    candidate_pattern_space: Dict[int, List[List[Tuple[int, int]]]] # node_index -> List of (w, k) patterns
    
    # 刚性锁定掩码 (已承诺不可变时隙)
    locked_commitments_mask: Dict[Tuple[int, int], List[int]]       # (w, k) -> List of node_index
    
    # 容量与工时红线
    daily_stop_capacity: int = 6
    daily_workload_budget_min: float = 480.0
    
    # 编译门禁自检状态
    is_projection_clean: bool = True
    unplannable_nodes_excluded: List[str] = field(default_factory=list)
```

---

## 3. 前向编译管道与数据质量门禁 (Compilation Pipeline & Gateways)

前向编译管道在将 `WorldState` 转化为 `PlannerStateProjection` 时，必须强制执行三大质量门禁：

1. **坐标完整性门禁 (Spatial Gateway)**:
   - 只有 `geo_quality == EXACT_MATCH` 且坐标非空的门店方可编入 `nodes` 列表；
   - 坐标缺失门店直接放入 `unplannable_nodes_excluded` 清单并发出 `DATA_QUALITY_ALERT`，**严禁静默替换为 Depot 坐标**！
2. **模式空间穷尽门禁 (Pattern Completeness Gateway)**:
   - 每个被编入的节点必须至少具备 1 个合法的严格同周几模式；
   - 若某节点无合法模式，编译直接失败并阻断求解。
3. **路网矩阵对称性与三角不等式校验 (Matrix Integrity Gateway)**:
   - 对称路网保证 $C_{ii} = 0$ 且 $C_{ij} \ge 0$。

---

## 4. 反向投影与语义后状态生成 (Backward Projection Pipeline)

当求解器完成优化后，反向投影管道负责将纯数字索引序列还原为富语义决策产物：

```python
def backward_project_to_candidate_plan(
    raw_solver_solution: Dict[Tuple[int, int], List[int]], # (w, k) -> [0, i_1, ..., 0]
    projection: PlannerStateProjection,
    world_state: WorldStateSnapshot,
    solver_meta: Dict[str, Any]
) -> CandidatePlan:
    """
    1. 根据 projection.node_index_lookup 将节点索引还原为真实 CustomerEntity
    2. 提取门店名称、行政区县、在店动作组合 (InStoreAction)
    3. 计算从 Depot 出发、每段通勤、返回 Depot 的真实工时账本
    4. 组装具备生产审计价值的 CandidatePlan 数据结构
    """
    pass
```
