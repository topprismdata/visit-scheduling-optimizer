"""Stage 1 语义编译: line_df → ProblemSpec v1 (visitflow/problem)."""
from __future__ import annotations

import hashlib
from collections import Counter

import numpy as np

from svc.hashing import sha256_of

_SENTINEL = 1e9


def _iso(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def build_spec_from_df(line_df, line_id: str, D: np.ndarray) -> dict:
    dates_raw = sorted(line_df["date"].unique())   # 原始值 (Timestamp) 用于过滤
    dates = [d.date() if hasattr(d, "date") and callable(d.date) else d
             for d in dates_raw]                    # date 对象用于输出/引擎
    date_strs = [_iso(d) for d in dates]
    codes = sorted(line_df["客户编码"].unique())
    idx = {c: i for i, c in enumerate(codes)}

    pts = (line_df.dropna(subset=["经度", "纬度"])
           .drop_duplicates("客户编码", keep="first")
           .set_index("客户编码"))

    days_orig_date = {}
    for di, dd_raw in enumerate(dates_raw):   # 用原始值过滤 (Timestamp==date 恒 False!)
        rows = line_df[line_df["date"] == dd_raw].sort_values("拜访顺序")
        days_orig_date[dates[di]] = [idx[c] for c in rows["客户编码"]
                                      if c in idx]
    days_orig = {date_strs[di]: days_orig_date[dates[di]]
                 for di in range(len(dates))}

    freq = Counter(line_df["客户编码"])
    contracts = _contracts_from_days(days_orig_date, dates)

    stores = []
    for c in codes:
        sid = idx[c]
        legal_idx = contracts[sid].pop("_legal_idx")
        stores.append({
            "id": sid, "code": c,
            "lon": float(pts.loc[c, "经度"]), "lat": float(pts.loc[c, "纬度"]),
            "contract": {"kind": contracts[sid]["kind"],
                          "phase": contracts[sid]["phase"],
                          "required_visits": contracts[sid]["required_visits"]},
            "legal_dates_idx": legal_idx,
        })

    spec = {
        "schema": "visitflow/problem", "version": "1.0",
        "inputs_hash": "PENDING", "line_id": line_id,
        "calendar": {"dates": date_strs, "n_days": len(dates)},
        "stores": stores,
        "corridor": {"min_daily": int(min(len(v) for v in days_orig.values())),
                      "max_daily": int(max(len(v) for v in days_orig.values()))},
        "original_assignment": days_orig,
        "distance": {
            "kind": "osm_cycling", "scope": "per-line",
            "matrix_ref": "PENDING", "format": "npz", "n": len(codes),
            "unreachable_sentinel": _SENTINEL,
        },
        "meta": {"n_stores": len(codes),
                  "n_visits": int(sum(freq.values()))},
    }
    spec["inputs_hash"] = sha256_of(spec)
    spec["distance"]["matrix_ref"] = "sha256:" + hashlib.sha256(
        np.ascontiguousarray(D).tobytes()).hexdigest()
    return spec


def _kind_phase(c):
    """contract_of 每店返回结构归一化 -> (kind, phase).

    实测返回 ("W", None) | ("B", phi) — phase None 归一为 0 (schema enum [0,1]).
    """
    if isinstance(c, dict):
        kind, phase = c["kind"], c.get("phase", 0)
    else:
        kind, phase = c[0], (c[1] if len(c) > 1 else 0)
    return kind, (0 if phase is None else int(phase))


def _contracts_from_days(days_orig: dict, dates) -> dict:
    """合同 kind/phase/required_visits 派生 + 合法域 (core.contract 单一事实源).

    days_orig 键域 = date 对象 (contract_of 内部做 .weekday()).
    """
    from core.contract import contract_of, legal_date_map
    contracts = contract_of(days_orig, dates)
    legal = legal_date_map(contracts, dates)
    idx_of = {_iso(d): i for i, d in enumerate(dates)}
    stores = sorted({c for v in days_orig.values() for c in v})
    out = {}
    for sid in stores:
        kind, phase = _kind_phase(contracts[sid])
        req = sum(1 for v in days_orig.values() if sid in v)
        legal_idx = sorted(idx_of[_iso(dd)] for dd in legal.get(sid, ()))
        out[sid] = {"kind": kind, "phase": phase, "required_visits": req,
                     "_legal_idx": legal_idx}
    return out


def build_spec_from_line(line, line_id: str, D, matrix_ref: str) -> dict:
    """从 LineData (load_line 产物) 组装 ProblemSpec — 与 df 入口语义等价."""
    import pandas as pd
    rows = []
    for di, dd in enumerate(line.dates):
        for si, c in enumerate(line.days_orig[dd]):
            rows.append({"客户编码": c, "销售名称": line.line_name,
                          "经度": line.lon[c], "纬度": line.lat[c],
                          "拜访顺序": si + 1, "date": dd,
                          "拜访日期": dd.isoformat()})
    df = pd.DataFrame(rows)
    spec = build_spec_from_df(df, line_id, D)
    spec["distance"]["matrix_ref"] = matrix_ref
    spec["inputs_hash"] = sha256_of(spec)
    return spec
