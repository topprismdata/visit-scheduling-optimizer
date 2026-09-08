# -*- coding: utf-8 -*-
"""Pricing Contract 层守卫 — ESPPRC_PRICING_DESIGN_v0.4.md §3 §4.2a §4.5."""
from datetime import date

import pytest

from algos.pricing_contract import (
    CGTerminationStatus, ColumnCandidate, ColumnValidator,
    PricingCertificate, ProofLevel)


D1 = date(2026, 7, 1)


def _validator(legal=None, lo=2, hi=35):
    return ColumnValidator(legal or {}, lo, hi)


# --- ColumnValidator: elementary / 合法域 / 走廊 / Normalizer repair ---

def test_repair_removes_duplicates():
    v = _validator(legal={1: {D1}, 2: {D1}, 3: {D1}}, lo=2, hi=5)
    cand = ColumnCandidate(route=[1, 2, 3, 2], reduced_cost=-5.0, source="NG")
    route, result = v.validate(cand, D1)
    assert route == [1, 2, 3]           # A-B-C-B-D → A-B-C
    assert result == "NORMALIZED"


def test_non_elementary_after_repair_discarded():
    v = _validator(legal={1: {D1}}, lo=2, hi=5)
    cand = ColumnCandidate(route=[1, 1], reduced_cost=-5.0, source="NG")
    route, result = v.validate(cand, D1)
    assert route is None and result == "DISCARD"
    assert v.rejects["corridor"] == 1   # repair 后长度 1 < 走廊下限


def test_illegal_store_discarded():
    v = _validator(legal={1: {D1}, 2: {D1}}, lo=2, hi=5)
    cand = ColumnCandidate(route=[1, 99], reduced_cost=-5.0, source="NG")
    route, result = v.validate(cand, D1)
    assert route is None and v.rejects["illegal_store"] == 1


def test_corridor_enforced():
    v = _validator(legal={i: {D1} for i in range(6)}, lo=3, hi=4)
    short = ColumnCandidate(route=[1, 2], reduced_cost=-1.0, source="NG")
    assert v.validate(short, D1)[0] is None
    long_r = ColumnCandidate(route=[1, 2, 3, 4, 5], reduced_cost=-1.0, source="NG")
    assert v.validate(long_r, D1)[0] is None
    assert v.rejects["corridor"] == 2
    ok = ColumnCandidate(route=[1, 2, 3], reduced_cost=-1.0, source="EXACT")
    assert v.validate(ok, D1)[0] == [1, 2, 3]


# --- PricingCertificate / CG 终止契约 ---

def test_certificate_convergence_only_exact_no_negative():
    assert PricingCertificate(False, ProofLevel.EXACT).certifies_convergence
    assert not PricingCertificate(True, ProofLevel.EXACT).certifies_convergence
    assert not PricingCertificate(False, ProofLevel.RELAXED).certifies_convergence
    assert not PricingCertificate(False, ProofLevel.HEURISTIC).certifies_convergence
    assert not PricingCertificate(False, ProofLevel.UNKNOWN).certifies_convergence


def test_termination_states_distinct():
    # relaxed 无候选绝不等于 exact 证明
    assert CGTerminationStatus.RELAXED_NO_CANDIDATE.value != \
        CGTerminationStatus.EXACT_NO_NEGATIVE_RC.value
    assert CGTerminationStatus.RELAXED_ONLY_INVALID.value != \
        CGTerminationStatus.EXACT_NO_NEGATIVE_RC.value


# --- bp 集成: add_columns 走契约层 + lineage ---

def _mini_bp():
    import numpy as np
    from algos.branch_and_price import BranchAndPrice
    from core.contract import contract_of, legal_date_map
    dates = [D1, date(2026, 7, 8), date(2026, 7, 15)]
    days_orig = {dd: [0, 1, 2, 3] for dd in dates}
    contracts = contract_of(days_orig, dates)
    legal = legal_date_map(contracts, dates)
    D = [[0.0, 2.0, 3.0, 3.5], [2.0, 0.0, 1.5, 2.8],
         [3.0, 1.5, 0.0, 1.2], [3.5, 2.8, 1.2, 0.0]]
    k_c = {0: 3, 1: 3, 2: 3, 3: 3}
    bp = BranchAndPrice(dates, k_c, D, contracts, days_orig, 2, 4,
                        time_budget=10, max_nodes=2, exact_pricing=False,
                        initial_days=days_orig)
    return bp, legal, dates



def test_add_columns_lineage_and_rejects():
    bp, legal, dates = _mini_bp()
    dd = dates[0]
    good = (dd, [0, 1, 2], 5.0)
    bad_store = (dd, [0, 99], 1.0)
    n0, l0 = len(bp.pool), len(bp.lineage)
    assert bp.add_columns([good, bad_store], source="EXACT") == 1
    assert len(bp.pool) == n0 + 1
    assert len(bp.lineage) == l0 + 1
    lin = bp.lineage[-1]
    assert lin.source_oracle == "EXACT"
    assert lin.validator_result in ("PASS", "NORMALIZED")
    assert lin.validated_at
    bp, legal, dates = _mini_bp()
    dd = dates[0]
    col = (dd, [0, 1, 2], 5.0)
    assert bp.add_columns([col], source="HEURISTIC") == 1
    assert bp.add_columns([col], source="HEURISTIC") == 0   # 同店集去重


def test_illegal_candidate_never_enters_pool():
    bp, legal, dates = _mini_bp()
    dd = dates[0]
    assert bp.add_columns([(dd, [0, 999], 1.0)], source="NG") == 0
    assert all(999 not in route for _d, route, _k in bp.pool)
