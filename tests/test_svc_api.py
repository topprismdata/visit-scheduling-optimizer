from fastapi.testclient import TestClient


def test_job_lifecycle(monkeypatch):
    import svc.api as api
    calls = {}

    def fake_solve(line_id, seeds, budget, cp_timeout):
        calls["line_id"] = line_id
        return {"status": "FEASIBLE", "totals": {"km": 1.0}}

    monkeypatch.setattr(api, "solve_line", fake_solve)
    client = TestClient(api.app)

    r = client.post("/v1/jobs", json={"line_id": "09", "seeds": [42],
                                       "budget_s": 1, "cp_timeout": 5})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    r2 = client.get(f"/v1/jobs/{job_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] in ("running", "done")
    if body["status"] == "done":
        assert body["result"]["totals"]["km"] == 1.0
    assert calls["line_id"] == "09"


def test_unknown_job_404():
    from svc.api import app
    client = TestClient(app)
    assert client.get("/v1/jobs/nope").status_code == 404
