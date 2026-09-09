"""Stage 1 语义编译 v2 — 日历无关的节奏式问题定义.

核心理念: 拜访计划 = 抽象拜访日序列上的节奏 (period + phase + visits_per_period),
真实日历只是投放窗口, 独立输出为 calendar_map. 问题定义里不出现任何日期.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from math import gcd

import numpy as np

from svc.hashing import sha256_of

_SENTINEL = 1e9


def _iso(d) -> str:
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def _derive_rhythm(day_idxs: list, n_days: int) -> dict:
    """从拜访日序号反推节奏: period / phase / visits_per_period.

    day_idxs: 1-based 升序拜访日序号. phase = 首次拜访日序号.
    ambiguous=True 表示节奏断裂 (缺访/新签/流失), 不硬猜.
    """
    v = sorted(day_idxs)
    if len(v) == 1:
        # 全周期仅 1 次 = 月访 (次/周期)
        return {"period": n_days, "phase": v[0], "visits_per_period": 1,
                 "ambiguous": False, "source": "derived"}
    diffs = [b - a for a, b in zip(v, v[1:])]
    period = diffs[0]
    for d in diffs[1:]:
        period = gcd(period, d)
    phase = v[0]
    expected = len(range(phase, n_days + 1, period))
    return {"period": period, "phase": phase, "visits_per_period": 1,
             "ambiguous": expected != len(v), "source": "derived"}


def build_spec_from_df(line_df, line_id: str, D: np.ndarray) -> dict:
    line_df = line_df.copy()
    line_df["客户编码"] = line_df["客户编码"].astype(str)   # Excel 数值编码统一为 str
    dates_raw = sorted(line_df["date"].unique())
    day_of = {d: i + 1 for i, d in enumerate(dates_raw)}     # 日期 → 拜访日序号 (1-based)
    n_days = len(dates_raw)
    codes = sorted(line_df["客户编码"].unique())
    idx = {c: i for i, c in enumerate(codes)}

    pts = (line_df.dropna(subset=["经度", "纬度"])
           .drop_duplicates("客户编码", keep="first")
           .set_index("客户编码"))

    # 按拜访日序号重组分配; 收集每店的拜访日序号
    assignment_idx = {str(i): [] for i in range(1, n_days + 1)}
    visits_by_store = {c: [] for c in codes}
    for d in dates_raw:
        di = day_of[d]
        rows = line_df[line_df["date"] == d].sort_values("拜访顺序")
        for c in rows["客户编码"]:
            if c in idx:
                assignment_idx[str(di)].append(idx[c])
                visits_by_store[c].append(di)

    stores = []
    for c in codes:
        sid = idx[c]
        r = _derive_rhythm(visits_by_store[c], n_days)
        stores.append({
            "id": sid, "code": c,
            "lon": float(pts.loc[c, "经度"]), "lat": float(pts.loc[c, "纬度"]),
            "rhythm": r,
        })

    spec = {
        "schema": "visitflow/problem", "version": "2.0",
        "inputs_hash": "PENDING", "line_id": line_id,
        "cycle": {"n_days": n_days},
        "stores": stores,
        "corridor": {"min_daily": int(min(len(v) for v in assignment_idx.values())),
                      "max_daily": int(max(len(v) for v in assignment_idx.values()))},
        "original_assignment_idx": assignment_idx,
        "distance": {
            "kind": "osm_cycling", "scope": "per-line",
            "matrix_ref": "PENDING", "format": "npz", "n": len(codes),
            "unreachable_sentinel": _SENTINEL,
        },
        "meta": {"n_stores": len(codes),
                  "n_visits": int(sum(len(v) for v in assignment_idx.values()))},
    }
    spec["inputs_hash"] = sha256_of(spec)
    spec["distance"]["matrix_ref"] = "sha256:" + hashlib.sha256(
        np.ascontiguousarray(D).tobytes()).hexdigest()
    return spec


def build_calendar_map(line_df, line_id: str) -> dict:
    """独立产物: 拜访日序号 → 真实日历 (投放层, 与问题定义无关)."""
    import pandas as pd
    dates_raw = sorted(line_df["date"].unique())
    wd_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    mapping = []
    for i, d in enumerate(dates_raw):
        d = d.date() if hasattr(d, "date") and callable(d.date) else d
        ts = pd.Timestamp(d)
        mapping.append({"day": i + 1, "date": _iso(d),
                         "weekday": wd_names[ts.weekday()]})
    return {"schema": "visitflow/calendar-map", "version": "1.0",
             "line_id": line_id, "mapping": mapping}


def build_spec_from_line(line, line_id: str, D, matrix_ref: str) -> dict:
    """从 LineData 组装 ProblemSpec v2.

    铁律: 店顺序保持 line.codes 原序 (与 road_dist_<line>.npy 行列一一对应),
    禁止重排 — 排序错位曾致 km 326→395 假解. code 统一 str.
    line.days_orig 的值已是位置索引; line.dates 的顺序即拜访日序号.
    """
    codes_orig = list(line.codes)
    codes_str = [str(c) for c in codes_orig]

    assignment_idx = {i + 1: [int(c) for c in line.days_orig[dd]]
                       for i, dd in enumerate(line.dates)}

    visits_by_store = {i: [] for i in range(len(codes_orig))}
    for di, dd in enumerate(line.dates):
        for c in line.days_orig[dd]:
            visits_by_store[c].append(di + 1)

    stores = []
    for i in range(len(codes_orig)):
        r = _derive_rhythm(visits_by_store[i], len(line.dates))
        stores.append({
            "id": i, "code": codes_str[i],
            "lon": float(line.lon[i]), "lat": float(line.lat[i]),
            "rhythm": r,
        })

    spec = {
        "schema": "visitflow/problem", "version": "2.0",
        "inputs_hash": "PENDING", "line_id": line_id,
        "cycle": {"n_days": len(line.dates)},
        "stores": stores,
        "corridor": {"min_daily": int(min(len(v) for v in assignment_idx.values())),
                      "max_daily": int(max(len(v) for v in assignment_idx.values()))},
        "original_assignment_idx": assignment_idx,
        "distance": {
            "kind": "osm_cycling", "scope": "per-line",
            "matrix_ref": matrix_ref, "format": "npz", "n": len(codes_orig),
            "unreachable_sentinel": _SENTINEL,
        },
        "meta": {"n_stores": len(codes_orig), "n_visits": int(line.visits)},
    }
    spec["inputs_hash"] = sha256_of(spec)
    return spec


def build_calendar_map_from_line(line, line_id: str) -> dict:
    import pandas as pd
    wd_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    mapping = [{"day": i + 1,
                 "date": _iso(dd),
                 "weekday": wd_names[pd.Timestamp(dd).weekday()]}
                for i, dd in enumerate(line.dates)]
    return {"schema": "visitflow/calendar-map", "version": "1.0",
             "line_id": line_id, "mapping": mapping}
