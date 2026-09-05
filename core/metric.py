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