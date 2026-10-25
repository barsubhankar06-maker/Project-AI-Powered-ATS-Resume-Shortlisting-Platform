"""Cross-organization data isolation."""
from tests.conftest import (
    STRONG_RESUME,
    add_requirements,
    create_job,
    register,
    upload_resume,
)


def test_jobs_are_isolated_between_orgs(client):
    a = register(client, role="recruiter", org="Alpha")
    b = register(client, role="recruiter", org="Beta")
    ja = create_job(client, a["headers"], title="Alpha Role")
    jb = create_job(client, b["headers"], title="Beta Role")
    titles_a = [j["title"] for j in client.get("/api/jobs", headers=a["headers"]).json()]
    titles_b = [j["title"] for j in client.get("/api/jobs", headers=b["headers"]).json()]
    assert "Alpha Role" in titles_a and "Beta Role" not in titles_a
    assert "Beta Role" in titles_b and "Alpha Role" not in titles_b


def test_candidates_are_isolated_between_orgs(client):
    a = register(client, role="recruiter", org="Gamma")
    b = register(client, role="recruiter", org="Delta")
    job = create_job(client, a["headers"])
    add_requirements(client, a["headers"], job["id"])
    upload_resume(client, a["headers"], STRONG_RESUME, job_id=job["id"])

    cands_a = client.get("/api/candidates", headers=a["headers"]).json()
    cands_b = client.get("/api/candidates", headers=b["headers"]).json()
    assert len(cands_a) >= 1
    assert cands_b == []


def test_application_detail_denied_across_orgs(client):
    a = register(client, role="recruiter", org="Epsilon")
    b = register(client, role="recruiter", org="Zeta")
    job = create_job(client, a["headers"])
    add_requirements(client, a["headers"], job["id"])
    upload_resume(client, a["headers"], STRONG_RESUME, job_id=job["id"])
    app_id = client.get(f"/api/jobs/{job['id']}/candidates", headers=a["headers"]).json()["items"][0]["application_id"]
    assert client.get(f"/api/applications/{app_id}", headers=b["headers"]).status_code == 404
    assert client.post(f"/api/applications/{app_id}/stage", json={"stage": "hired"}, headers=b["headers"]).status_code == 404


def test_resume_detail_denied_across_orgs(client):
    a = register(client, role="recruiter", org="Eta")
    b = register(client, role="recruiter", org="Theta")
    job = create_job(client, a["headers"])
    add_requirements(client, a["headers"], job["id"])
    res = upload_resume(client, a["headers"], STRONG_RESUME, job_id=job["id"])
    assert client.get(f"/api/resumes/{res['resume_id']}", headers=b["headers"]).status_code == 404
    assert client.get(f"/api/resumes/{res['resume_id']}/download-url", headers=b["headers"]).status_code == 404


def test_audit_logs_are_org_scoped(client):
    a = register(client, role="recruiter", org="Iota")
    create_job(client, a["headers"], title="Audited Role")
    logs = client.get("/api/admin/audit-logs", headers=a["headers"]).json()
    assert any(l["action"] == "job.created" for l in logs)
    # Every returned log belongs to the caller's org.
    org_id = client.get("/api/auth/me", headers=a["headers"]).json()["active_org_id"]
    assert all(l["org_id"] == org_id for l in logs)
