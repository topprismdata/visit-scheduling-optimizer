# -*- coding: utf-8 -*-
"""Shared metrics for visit optimization."""
import numpy as np


def day_km(seq: list[int], D: list[list[float]]) -> float:
    """Open-chain route distance over store indices.
    
    Sums D[seq[k]][seq[k+1]] for k from 0 to len-2.
    Returns 0.0 for 0- or 1-store chains.
    """
    if len(seq) < 2:
        return 0.0
    return float(sum(D[seq[k]][seq[k+1]] for k in range(len(seq) - 1)))


def total_km(days: dict, D: list[list[float]]) -> float:
    """Sum day_km across all days."""
    return sum(day_km(seq, D) for seq in days.values())


def check_freq(days: dict, codes: list[str], freq_orig: dict[str, int]) -> bool:
    """Verify each store's total visit count matches original frequency."""
    cnt = {}
    for seq in days.values():
        for c in seq:
            key = codes[c]
            cnt[key] = cnt.get(key, 0) + 1
    return all(cnt.get(c, 0) == freq_orig.get(c, 0) for c in freq_orig)


def check_capacity(days: dict, max_daily: int, min_daily: int = 0) -> bool:
    """Verify all days fall within [min_daily, max_daily] operational corridor."""
    for seq in days.values():
        n = len(seq)
        if max_daily > 0 and n > max_daily:
            return False
        if min_daily > 0 and n < min_daily:
            return False
    return True


# ---- 周节奏原语 (R3, 业务语义: 频次单位=周, 节拍=槽位均匀铺) ----
import math
import itertools
from collections import defaultdict


def slot_index_map(dates):
    """{date: (weekday, 周序idx)}; 同星期几按序编号 (7月: 周一/二 k=4, 其余 k=5)."""
    by_wd = defaultdict(list)
    for dd in sorted(dates):
        by_wd[dd.weekday()].append(dd)
    m = {}
    for w, ds in by_wd.items():
        for i, dd in enumerate(ds):
            m[dd] = (w, i)
    return m


def slots_per_weekday(dates):
    n = defaultdict(int)
    for dd in dates:
        n[dd.weekday()] += 1
    return dict(n)


def _ok_gaps(k, f):
    return set(range(1, k + 1)) if f <= 1 else {k // f, -(-k // f)}


def legal_slot_sets(slots, f):
    """k 个升序槽位 + 频次 f → 合法(均匀节拍)子集列表. 圆形跨度全∈{⌊k/f⌋,⌈k/f⌉}."""
    k = len(slots)
    if f >= k:
        return [tuple(slots)] if f == k else []
    ok = _ok_gaps(k, f)
    out = []
    for combo in itertools.combinations(range(k), f):
        gaps = [combo[i+1] - combo[i] for i in range(f - 1)] + [combo[0] + k - combo[-1]]
        if all(g in ok for g in gaps):
            out.append(tuple(slots[c] for c in combo))
    return out


def illegal_slot_sets(slots, f):
    """全部非法 f-子集 (用于 SP 割)."""
    legal = {set(x) for x in legal_slot_sets(slots, f)}
    return [tuple(s) for s in itertools.combinations(slots, f) if set(s) not in legal]


def rhythm_ok_dates(ds, slot_of, spw):
    """单店日期集 R2'(单一星期几) + R3(均匀节拍)."""
    ds = list(ds)
    if not ds:
        return True
    ws = {slot_of[d][0] for d in ds}
    if len(ws) > 1:
        return False
    w = ws.pop()
    k = spw[w]
    idx = sorted(slot_of[d][1] for d in ds)
    f = len(idx)
    ok = _ok_gaps(k, f)
    gaps = [idx[i+1] - idx[i] for i in range(f - 1)] + [idx[0] + k - idx[-1]]
    return all(g in ok for g in gaps)


def check_rhythm(days, slot_of, spw):
    """全月解节奏验收 (返回违例店列表, 空=通过)."""
    shop = defaultdict(list)
    for dd, seq in days.items():
        for c in seq:
            shop[c].append(dd)
    return [c for c, ds in shop.items() if not rhythm_ok_dates(ds, slot_of, spw)]