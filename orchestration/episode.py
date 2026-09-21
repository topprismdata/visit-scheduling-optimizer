# -*- coding: utf-8 -*-
"""Decision Episode 组装 (v0.2 §7): 每次求解留痕, 将来可回答"这个结果怎么来的".

组装规则 (字段唯一出处):
- semantic_spec_*  ← VisitSemanticSpec.metadata
- instance_hash    ← VisitPlanningInstance.metadata["content_hash"]
- solver_*         ← SolveResult + SolverConfig (config_hash = 决定性序列化)
- exception_grant_ids ← VisitSemanticSpec.exceptions
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone as _tz
from typing import Optional

from visit_math_api import (
    DecisionEpisode,
    SolveResult,
    SolverConfig,
    VisitPlanningInstance,
    episode_hash,
)
from visit_semantic_api import VisitSemanticSpec


def _config_hash(config: SolverConfig) -> str:
    payload = {
        "backend": config.backend,
        "time_limit_s": config.time_limit_s,
        "params": dict(config.params),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def emit_episode(
    spec: VisitSemanticSpec,
    instance: VisitPlanningInstance,
    result: SolveResult,
    config: SolverConfig,
    solver_version: str = "unknown",
    solution_id: Optional[str] = None,
) -> DecisionEpisode:
    """一次求解 → 不可变留痕. spec/instance/result 任一缺失即不可复现, 拒绝组装."""
    md = spec.metadata
    if md is None:
        raise ValueError("spec 缺 SourceMetadata — 不可复现的求解不允许留痕 (G4)")
    ts = datetime.now(_tz.utc).isoformat(timespec="seconds")
    return DecisionEpisode(
        episode_id=uuid.uuid4().hex,
        source_snapshot_id=md.source_snapshot_id,
        semantic_spec_version=md.schema_version,
        semantic_spec_hash=md.content_hash,
        instance_hash=dict(instance.metadata).get("content_hash", ""),
        solver_backend=config.backend,
        solver_version=solver_version,
        solver_config_hash=_config_hash(config),
        seed=config.seed,
        solution_id=solution_id or result.instance_hash,
        status=result.status,
        termination_reason=result.termination_reason,
        exception_grant_ids=tuple(e.exception_id for e in spec.exceptions),
        decision_timestamp=ts,
    )


__all__ = ["emit_episode", "episode_hash"]
