# -*- coding: utf-8 -*-
"""Pricing Contract 层 — Column Contract / PricingCertificate / CG 终止契约.

设计: docs/design/ESPPRC_PRICING_DESIGN_v0.4.md §3 §4.2a §4.5
不变量:
  1. 定价产出 (ColumnCandidate) 禁止直接进 RMP——必须经 Normalizer → Validator。
  2. CG 仅在 proof_level == EXACT 且无负列时声明收敛 (EXACT_NO_NEGATIVE_RC);
     relaxed/heuristic 无候选一律 RELAXED_*, 绝不签发证明。
  3. 每个 MasterColumn 携带 lineage, 可回溯来源与验证结果。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PricingStatus(Enum):
    EXACT_NO_COLUMN = "exact_pricing_proven_no_negative_rc"
    EXACT_COLUMN_FOUND = "exact_pricing_found_negative_rc"
    RELAXED_COLUMN_FOUND = "relaxed_pricing_found_negative_rc"
    HEURISTIC_COLUMN_FOUND = "heuristic_pricing_found_negative_rc"
    TIMEOUT_WITH_INCUMBENT = "timed_out_with_best_incumbent_route"


class ProofLevel(Enum):
    EXACT = "EXACT"
    RELAXED = "RELAXED"
    HEURISTIC = "HEURISTIC"
    UNKNOWN = "UNKNOWN"


class CGTerminationStatus(Enum):
    EXACT_NO_NEGATIVE_RC = "exact_pricing_proven_no_negative_rc"
    RELAXED_NO_CANDIDATE = "relaxed_pricing_found_no_candidate_not_a_proof"
    RELAXED_ONLY_INVALID = "relaxed_candidates_all_invalidated_by_validator"
    TIMEOUT_UNKNOWN = "timed_out_convergence_state_unknown"


@dataclass
class PricingCertificate:
    has_negative_column: bool
    proof_level: ProofLevel

    @property
    def certifies_convergence(self) -> bool:
        return self.proof_level is ProofLevel.EXACT and not self.has_negative_column


@dataclass
class ColumnCandidate:
    route: list            # 定价原始路径 (store idx 序列)
    reduced_cost: float
    source: str            # EXACT / NG / HEURISTIC


@dataclass
class ColumnLineage:
    column_id: int
    source_oracle: str
    candidate_rc: float
    validated_at: str
    validator_result: str   # PASS / NORMALIZED / DISCARD


class ColumnValidator:
    """合法性闸: elementary / 合同合法域 / 走廊. 通过后才有资格进 RMP."""

    def __init__(self, legal, min_daily, max_daily):
        self.legal = legal              # {store: set(date)}
        self.min_daily = min_daily
        self.max_daily = max_daily
        self.rejects = {"non_elementary": 0, "illegal_store": 0, "corridor": 0}

    def validate(self, cand: ColumnCandidate, dd):
        """返回 (route 或 None, result 字符串)."""
        route = CandidateNormalizer.elementary_repair(cand.route)
        if len(route) != len(set(route)):
            self.rejects["non_elementary"] += 1
            return None, "DISCARD"
        legal = self.legal
        if any(dd not in legal.get(c, ()) for c in route):
            self.rejects["illegal_store"] += 1
            return None, "DISCARD"
        lo = max(2, self.min_daily)
        if not (lo <= len(route) <= self.max_daily):
            self.rejects["corridor"] += 1
            return None, "DISCARD"
        result = "PASS" if list(route) == list(cand.route) else "NORMALIZED"
        return list(route), result


class CandidateNormalizer:
    @staticmethod
    def elementary_repair(route):
        """去除重复访问 (保序首次出现). 空转/自环候选由此修复或变短后被走廊闸淘汰."""
        seen, out = set(), []
        for c in route:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out


@dataclass
class MasterColumn:
    date: object
    route: list
    km: float
    is_elementary: bool
    source: str
    lineage: ColumnLineage
