"""CLI 编排: xlsx → problem.json / model.json / solution.json (哈希链闭环)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from svc.hashing import sha256_of


def _py(o):
    import numpy as _np
    if isinstance(o, (_np.integer,)):
        return int(o)
    if isinstance(o, (_np.floating,)):
        return float(o)
    raise TypeError(f"not serializable: {type(o)}")


def _write(path: Path, obj: dict):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=_py),
                    encoding="utf-8")


def _matrix_ref(D) -> str:
    return "sha256:" + hashlib.sha256(np.ascontiguousarray(D).tobytes()).hexdigest()


def solve_line_sync(line_id: str, seeds, budget, cp_timeout,
                    xlsx: str | None = None) -> dict:
    """单线全管道, 返回三 JSON dict 打包 (api 层与 CLI 共用)."""
    if xlsx:
        os.environ["SRP_PATH"] = xlsx   # 必须在首次 import data.loader 之前
    from data.loader import load_line, load_plan
    from svc.stages.model import build_manifest
    from svc.stages.semantic import (build_calendar_map_from_line,
                                      build_spec_from_line)
    from svc.stages.solve import solve_spec

    plan = load_plan(xlsx) if xlsx else load_plan()
    line = load_line(plan, line_id)
    D = np.load(Path("output") / f"road_dist_{line_id}.npy")
    spec = build_spec_from_line(line, line_id, D, _matrix_ref(D))
    calendar = build_calendar_map_from_line(line, line_id)
    model = build_manifest(spec)
    bundle = solve_spec(spec, D, seeds=list(seeds), budget_s=budget,
                         cp_timeout=cp_timeout, model_hash=sha256_of(model))
    return {"problem": spec, "model": model, "solution": bundle,
             "calendar_map": calendar}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=None)
    ap.add_argument("--line", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="42")
    ap.add_argument("--budget", type=float, default=600.0)
    ap.add_argument("--cp-timeout", type=float, default=30.0)
    args = ap.parse_args()

    pack = solve_line_sync(args.line, [int(s) for s in args.seeds.split(",")],
                            args.budget, args.cp_timeout, xlsx=args.xlsx)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "problem.json", pack["problem"])
    _write(out / "calendar_map.json", pack["calendar_map"])
    _write(out / "model.json", pack["model"])
    _write(out / "solution.json", pack["solution"])
    sol = pack["solution"]
    print(f"written: {out}/(problem|model|solution).json  "
          f"km={sol['totals']['km']} gates={all(sol['gates'].values())} "
          f"status={sol['status']}")


if __name__ == "__main__":
    main()
