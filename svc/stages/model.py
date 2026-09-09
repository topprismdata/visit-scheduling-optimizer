"""Stage 2 数学建模: ProblemSpec → ModelManifest v1 (visitflow/model).

纯净层: 不含引擎提示 (seeds/预算属 Stage 3 请求参数, spec v0.2 修正 4).
"""
from __future__ import annotations

from svc.hashing import sha256_of


def build_manifest(spec: dict) -> dict:
    n_stores = spec["meta"]["n_stores"]
    n_days = spec["cycle"]["n_days"]
    pairs_total = n_stores * n_days
    pairs_legal = pairs_total   # v2: 合法域由 rhythm 隐式定义, 无逐对禁用

    corridor_ok = spec["corridor"]["min_daily"] <= spec["corridor"]["max_daily"]

    manifest = {
        "schema": "visitflow/model", "version": "1.0",
        "problem_hash": sha256_of(spec),
        "formulation": {
            "kind": "fixed-row-v2",
            "vars": {"y_pairs": pairs_total},
        },
        "legal_domain": {
            "pairs_total": pairs_total, "pairs_legal": pairs_legal,
            "fixed": pairs_total - pairs_legal,
        },
        "feasibility_precheck": {
            "capacity_ok": True,
            "contract_ok": all(not s["frequency"]["ambiguous"]
                                for s in spec["stores"]),
            "corridor_ok": corridor_ok,
        },
        "meta": {"compile_ms": 0,
                  "ambiguous_stores": sum(1 for s in spec["stores"]
                                           if s["frequency"]["ambiguous"])},
    }
    return manifest
