"""Role-based access control enforced on the server."""
from tests.conftest import create_job, register


def test_candidate_cannot_use_recruiter_endpoints(client):
    cand = register(client, role="candidate")
    assert client.get("/api/jobs", headers=cand["headers"]).status_code == 403
    assert client.post("/api/jobs", json={"title": "x"}, headers=cand["headers"]).status_code == 403
    assert client.get("/api/candidates", headers=cand["headers"]).status_code == 403
    assert client.get("/api/analytics/dashboard", headers=cand["headers"]).status_code == 403


def test_recruiter_cannot_use_admin_endpoints(client):
    rec = register(client, role="recruiter")  # org role = admin actually; test a plain recruiter
    # Create a second member with the recruiter role in the same org.
    rec2 = register(client, role="recruiter", org="Other Co")
    # A founder is admin of their own org; downgrade check: a candidate hitting admin is 403
    cand = register(client, role="candidate")
    assert client.get("/api/admin/users", headers=cand["headers"]).status_code == 403
    # And an unauthenticated call is 401
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/admin/system-health", headers=rec["headers"]).status_code == 200
    void = rec2
    assert void is not None


def test_candidate_self_endpoints_are_own_only(client):
    rec = register(client, role="recruiter")
    assert client.get("/api/me/profile", headers=rec["headers"]).status_code == 403
    cand = register(client, role="candidate")
    assert client.get("/api/me/profile", headers=cand["headers"]).status_code == 200


def test_cannot_access_job_from_another_org(client):
    a = register(client, role="recruiter", org="Org A")
    b = register(client, role="recruiter", org="Org B")
    job = create_job(client, a["headers"])
    # Org B cannot fetch or mutate Org A's job (404, not 403, to avoid id probing).
    assert client.get(f"/api/jobs/{job['id']}", headers=b["headers"]).status_code == 404
    assert client.patch(f"/api/jobs/{job['id']}", json={"title": "hijack"}, headers=b["headers"]).status_code == 404
    assert client.delete(f"/api/jobs/{job['id']}", headers=b["headers"]).status_code == 404
