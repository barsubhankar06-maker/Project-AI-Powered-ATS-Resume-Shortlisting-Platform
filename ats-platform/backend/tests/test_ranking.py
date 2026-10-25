"""Candidate ranking, filtering and sorting for a job."""
from tests.conftest import (
    STRONG_RESUME,
    WEAK_RESUME,
    add_requirements,
    create_job,
    register,
    upload_resume,
)


def _setup(client):
    rec = register(client)
    job = create_job(client, rec["headers"])
    add_requirements(client, rec["headers"], job["id"])
    upload_resume(client, rec["headers"], STRONG_RESUME, filename="strong.docx", job_id=job["id"])
    upload_resume(client, rec["headers"], WEAK_RESUME, filename="weak.docx", job_id=job["id"])
    return rec, job


def test_ranking_orders_by_score_desc(client):
    rec, job = _setup(client)
    res = client.get(f"/api/jobs/{job['id']}/candidates", headers=rec["headers"]).json()
    assert res["total"] == 2
    scores = [i["match_score"] for i in res["items"]]
    assert scores == sorted(scores, reverse=True)
    assert res["items"][0]["display_name"] == "Aarav Sharma"


def test_score_min_filter(client):
    rec, job = _setup(client)
    res = client.get(f"/api/jobs/{job['id']}/candidates?score_min=60", headers=rec["headers"]).json()
    assert all(i["match_score"] >= 60 for i in res["items"])


def test_stage_filter(client):
    rec, job = _setup(client)
    res = client.get(f"/api/jobs/{job['id']}/candidates?stage=applied", headers=rec["headers"]).json()
    assert res["total"] == 2
    res = client.get(f"/api/jobs/{job['id']}/candidates?stage=shortlisted", headers=rec["headers"]).json()
    assert res["total"] == 0


def test_sort_by_name(client):
    rec, job = _setup(client)
    res = client.get(f"/api/jobs/{job['id']}/candidates?sort=name&order=asc", headers=rec["headers"]).json()
    names = [i["display_name"] for i in res["items"]]
    assert names == sorted(names)


def test_pagination(client):
    rec, job = _setup(client)
    res = client.get(f"/api/jobs/{job['id']}/candidates?page=1&page_size=1", headers=rec["headers"]).json()
    assert len(res["items"]) == 1 and res["total"] == 2


def test_row_contains_explainability_fields(client):
    rec, job = _setup(client)
    row = client.get(f"/api/jobs/{job['id']}/candidates", headers=rec["headers"]).json()["items"][0]
    assert "missing" in row and "required_coverage" in row and "parsing_status" in row
    assert row["method"] in ("deterministic", "hybrid")
