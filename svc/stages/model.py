"""Stage 2 数学建模: ProblemSpec → 完整数学模型清单 (visitflow/model).

把频次需求翻译为显式的整数规划定义 —— 集合/参数/变量/目标/约束一个不少.
这是"业务 → 数学"翻译的交付物: 任何一个求解器实现都以此为准.
"""
from __future__ import annotations

from svc.hashing import sha256_of


def build_manifest(spec: dict) -> dict:
    n_stores = spec["meta"]["n_stores"]
    n_days = spec["cycle"]["n_days"]
    corridor = spec["corridor"]

    # 每店模型参数
    store_params = []
    freq_rows = 0
    window_rows = 0
    total_visits = 0
    ambiguous = 0
    for s in spec["stores"]:
        f = s["frequency"]
        vt = _window_visits(f, n_days)
        total_visits += vt
        freq_rows += 1
        window_rows += max(1, n_days - f["horizon"] + 1)
        if f.get("ambiguous"):
            ambiguous += 1
        store_params.append({
            "id": s["id"], "code": s["code"],
            "horizon": f["horizon"], "visits_per_horizon": f["visits"],
            "visits_total_target": vt,
            "ambiguous": f.get("ambiguous", False),
        })

    # 可行性预检 (必要条件, 非充分)
    capacity_ok = total_visits <= n_days * corridor["max_daily"]
    capacity_min_ok = total_visits >= n_days * corridor["min_daily"]
    corridor_ok = corridor["min_daily"] <= corridor["max_daily"]

    manifest = {
        "schema": "visitflow/model", "version": "1.1",
        "problem_hash": sha256_of(spec),
        "formulation": {"kind": "sliding-window-frequency",
                          "vars": {"y_cd": n_stores * n_days}},
        "legal_domain": {"pairs_total": n_stores * n_days,
                          "pairs_legal": n_stores * n_days,
                          "pairs_available": n_stores * n_days,
                          "fixed": 0},

        # ---------- 集合 ----------
        "sets": {
            "D": {"size": n_days,
                   "desc": "拜访日序号集合 {1, 2, ..., %d} (抽象日, 与日历无关)" % n_days},
            "C": {"size": n_stores, "desc": "客户集合"},
        },

        # ---------- 参数 ----------
        "parameters": {
            "distance_matrix": {
                "desc": "骑行路网距离 D[i][j], 客户全序与矩阵行列一一对应",
                "matrix_ref": spec["distance"]["matrix_ref"],
                "unreachable_sentinel": spec["distance"]["unreachable_sentinel"],
            },
            "horizon_c": {"desc": "客户 c 的拜访周期 (工作日)",
                           "per_store": {str(s["id"]): s["frequency"]["horizon"]
                                          for s in spec["stores"]}},
            "visits_c": {"desc": "客户 c 每周期拜访次数",
                          "per_store": {str(s["id"]): s["frequency"]["visits"]
                                         for s in spec["stores"]}},
            "visits_total_c": {"desc": "客户 c 在窗口内的总拜访次数目标",
                                "per_store": {str(sp["id"]): sp["visits_total_target"]
                                               for sp in store_params}},
            "min_daily": corridor["min_daily"],
            "max_daily": corridor["max_daily"],
        },

        # ---------- 决策变量 ----------
        "decision_variables": {
            "y_cd": {
                "domain": "binary",
                "index": "(c ∈ C, d ∈ D)",
                "semantics": "客户 c 在拜访日 d 被服务 ⇔ y_cd = 1",
                "count": n_stores * n_days,
            },
        },

        # ---------- 目标 ----------
        "objective": {
            "sense": spec["objective"]["sense"],
            "metric": spec["objective"]["metric"],
            "expr": "Σ_{d∈D} route_km(D, {c ∈ C : y_cd = 1})",
            "note": "目标声明转抄自语义层 problem.objective (单一事实源); "
                    "route_km = 当日被服务客户集的精确最短开放路径 (内层 TSP, "
                    "共同重排口径); 距离取 OSM 路网矩阵",
        },

        # ---------- 约束 ----------
        "constraints": {
            # 1. 频次总数
            "frequency_total": {
                "expr": "Σ_{d∈D} y_cd == visits_total_c",
                "forall": "c ∈ C",
                "rows": n_stores,
                "desc": "窗口内总拜访次数等于频次需求折算值",
            },
            # 2. 间隔 (每 horizon 窗口内至多 visits 次)
            "spacing": {
                "expr": "∀窗口 s∈D: Σ_{d=s}^{s+horizon_c-1} y_cd ≤ visits_c",
                "forall": "c ∈ C, 滑动窗口起点 s",
                "rows": window_rows,
                "desc": "保证拜访间隔不小于周期 (隔周/隔月的'隔'字)",
            },
            # 3a. 走廊下限
            "corridor_min": {
                "expr": "Σ_{c∈C} y_cd ≥ min_daily",
                "forall": "d ∈ D",
                "rows": n_days,
                "desc": "每日最低拜访次数 (防闲置/出工不出力)",
            },
            # 3b. 走廊上限
            "corridor_max": {
                "expr": "Σ_{c∈C} y_cd ≤ max_daily",
                "forall": "d ∈ D",
                "rows": n_days,
                "desc": "每日最高拜访次数 (防过劳/物理不可行)",
            },
            # 4. 单相位 (R2')
            "r2_single_phase": {
                "expr": "∀c: 拜访日序列为等差数列, 公差 = horizon_c (相位唯一)",
                "forall": "c ∈ C",
                "desc": "整店换星期可以, 星期几分裂不可以",
            },
            # 5. 合法域
            "legality": {
                "expr": "拜访日 d 必须与客户 c 的历史节奏相位一致",
                "desc": "由频次反推, ambiguous 店不受此限",
            },
        },

        # ---------- 每店参数表 ----------
        "store_parameters": store_params,

        # ---------- 可行性预检 ----------
        "feasibility_precheck": {
            "capacity_max_ok": capacity_ok,
            "capacity_min_ok": capacity_min_ok,
            "corridor_ok": corridor_ok,
            "ambiguous_stores": ambiguous,
        },

        "meta": {
            "total_visits_target": total_visits,
            "ambiguous_stores": ambiguous,
            "compile_ms": 0,
        },
    }
    return manifest


def _window_visits(f: dict, n_days: int) -> int:
    """频次在窗口内的总拜访次数 (每 horizon 工作日 visits 次)."""
    return max(1, round(f["visits"] * n_days / f["horizon"]))
