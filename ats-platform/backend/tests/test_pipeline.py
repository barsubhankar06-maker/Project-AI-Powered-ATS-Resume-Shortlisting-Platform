"""Pipeline stage changes, history, bulk actions and analytics."""
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
    a = upload_resume(client, rec["headers"], STRONG_RESUME, filename="s.docx", job_id=job["id"])
    b = upload_resume(client, rec["headers"], WEAK_RESUME, filename="w.docx", job_id=job["id"])
    return rec, job, a, b


def test_stage_change_records_history(client):
    rec, job, a, _ = _setup(client)
    app_id = client.get(f"/api/jobs/{job['id']}/candidates", headers=rec["headers"]).json()["items"][0]["application_id"]
    res = client.post(f"/api/applications/{app_id}/stage", json={"stage": "shortlisted", "note": "strong"}, headers=rec["headers"])
    assert res.status_code == 200 and res.json()["stage"] == "shortlisted"
    timeline = client.get(f"/api/applications/{app_id}/timeline", headers=rec["headers"]).json()
    assert timeline[-1]["to"] == "shortlisted"


def test_invalid_stage_rejected(client):
    rec, job, a, _ = _setup(client)
    app_id = client.get(f"/api/jobs/{job['id']}/candidates", headers=rec["headers"]).json()["items"][0]["application_id"]
    res = client.post(f"/api/applications/{app_id}/stage", json={"stage": "not_a_stage"}, headers=rec["headers"])
    assert res.status_code == 422


def test_bulk_shortlist_and_reject(client):
    rec, job, a, b = _setup(client)
    rows = client.get(f"/api/jobs/{job['id']}/candidates", headers=rec["headers"]).json()["items"]
    ids = [r["application_id"] for r in rows]
    res = client.post(f"/api/jobs/{job['id']}/bulk", json={"application_ids": ids, "action": "shortlist"}, headers=rec["headers"])
    assert res.json()["updated"] == 2
    rows = client.get(f"/api/jobs/{job['id']}/candidates?stage=shortlisted", headers=rec["headers"]).json()
    assert rows["total"] == 2
    res = client.post(f"/api/jobs/{job['id']}/bulk", json={"application_ids": [ids[0]], "action": "reject"}, headers=rec["headers"])
    assert res.json()["updated"] == 1


def test_pipeline_columns(client):
    rec, job, a, b = _setup(client)
    res = client.get(f"/api/applications/pipeline/{job['id']}", headers=rec["headers"]).json()
    assert res["columns"]["applied"]  # candidates start in applied
    assert "shortlisted" in res["columns"]


def test_dashboard_and_reports_reflect_real_data(client):
    rec, job, a, b = _setup(client)
    dash = client.get("/api/analytics/dashboard", headers=rec["headers"]).json()
    assert dash["active_jobs"] >= 1
    assert dash["total_applications"] >= 2
    assert dash["resumes_processed"] >= 2
    assert dash["avg_match_score"] is not None

    rep = client.get("/api/analytics/reports", headers=rec["headers"]).json()
    assert rep["totals"]["applications"] >= 2
    assert rep["parsing"]["total"] >= 2
    assert sum(rep["score_distribution"].values()) == rep["totals"]["scored"]


def test_csv_export(client):
    rec, job, a, b = _setup(client)
    res = client.get(f"/api/analytics/export.csv?job_id={job['id']}", headers=rec["headers"])
    assert res.status_code == 200
    assert "Candidate,Email,Job,MatchScore" in res.text.splitlines()[0]
    assert len(res.text.splitlines()) >= 3


def test_notes_and_feedback(client):
    rec, job, a, _ = _setup(client)
    app_id = client.get(f"/api/jobs/{job['id']}/candidates", headers=rec["headers"]).json()["items"][0]["application_id"]
    assert client.post(f"/api/applications/{app_id}/notes", json={"body": "Great comms"}, headers=rec["headers"]).status_code == 201
    assert len(client.get(f"/api/applications/{app_id}/notes", headers=rec["headers"]).json()) == 1
    assert client.post(f"/api/applications/{app_id}/feedback", json={"rating": 4, "strengths": "depth"}, headers=rec["headers"]).status_code == 201
    assert len(client.get(f"/api/applications/{app_id}/feedback", headers=rec["headers"]).json()) == 1
