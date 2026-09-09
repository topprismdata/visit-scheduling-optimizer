"""FastAPI 异步壳 — 业务零逻辑, 全部转发 stages."""
from __future__ import annotations

import threading
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="visitflow", version="1.0")
_JOBS: dict[str, dict] = {}


class SolveReq(BaseModel):
    line_id: str
    seeds: list[int] = [42]
    budget_s: float = 600.0
    cp_timeout: float = 30.0


def solve_line(line_id: str, seeds, budget, cp_timeout) -> dict:
    """真实求解入口 (heavy): load_plan + 三阶段. 测试中 monkeypatch."""
    from svc.run import solve_line_sync
    return solve_line_sync(line_id, seeds, budget, cp_timeout)


def _run(job_id: str, req: SolveReq):
    try:
        result = solve_line(req.line_id, req.seeds, req.budget_s, req.cp_timeout)
        _JOBS[job_id] = {"status": "done", "result": result}
    except Exception as e:      # noqa: BLE001 — 作业失败也要落状态
        _JOBS[job_id] = {"status": "failed", "error": str(e)}


@app.post("/v1/jobs", status_code=202)
def create_job(req: SolveReq):
    job_id = uuid.uuid4().hex[:12]
    _JOBS[job_id] = {"status": "running"}
    threading.Thread(target=_run, args=(job_id, req), daemon=True).start()
    return {"job_id": job_id}


@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(404, "unknown job")
    return _JOBS[job_id]
