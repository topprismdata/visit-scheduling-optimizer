"""规范化 JSON + sha256 —— 全仓唯一哈希实现 (spec v0.2 §2)."""
import hashlib
import json
def _trunc(obj):
    import numpy as _np
    if isinstance(obj, (_np.integer,)):
        return int(obj)
    if isinstance(obj, (_np.floating,)):
        return round(float(obj), 9)
    if isinstance(obj, float):
        return round(obj, 9)
    if isinstance(obj, dict):
        return {k: _trunc(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_trunc(v) for v in obj]
    return obj


def canonical_json(obj) -> str:
    return json.dumps(_trunc(obj), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def sha256_of(obj) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
