"""Authentication: registration, login, tokens, password change, deactivation."""
from tests.conftest import register, unique_email


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_register_recruiter_creates_org_and_admin_membership(client):
    r = register(client, role="recruiter", org="Acme")
    me = client.get("/api/auth/me", headers=r["headers"]).json()
    assert me["user"]["email"] == r["email"]
    assert len(me["memberships"]) == 1
    assert me["memberships"][0]["org_name"] == "Acme"
    assert me["memberships"][0]["role"] == "admin"  # founder is org admin


def test_register_candidate_has_no_org(client):
    r = register(client, role="candidate")
    me = client.get("/api/auth/me", headers=r["headers"]).json()
    assert me["memberships"] == []
    assert me["active_role"] == "candidate"


def test_duplicate_email_rejected(client):
    r = register(client, role="recruiter")
    res = client.post(
        "/api/auth/register",
        json={"email": r["email"], "password": "password123", "full_name": "Dup", "role": "candidate"},
    )
    assert res.status_code == 409


def test_login_success_and_failure(client):
    r = register(client)
    ok = client.post("/api/auth/login", json={"email": r["email"], "password": r["password"]})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", json={"email": r["email"], "password": "wrong-password"})
    assert bad.status_code == 401
    missing = client.post("/api/auth/login", json={"email": unique_email(), "password": "whatever123"})
    assert missing.status_code == 401  # no account enumeration


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_password_too_short_rejected(client):
    res = client.post(
        "/api/auth/register",
        json={"email": unique_email(), "password": "short", "full_name": "X", "role": "candidate"},
    )
    assert res.status_code == 422


def test_change_password(client):
    r = register(client)
    bad = client.post(
        "/api/auth/change-password",
        json={"current_password": "nope", "new_password": "newpassword123"},
        headers=r["headers"],
    )
    assert bad.status_code == 400
    good = client.post(
        "/api/auth/change-password",
        json={"current_password": r["password"], "new_password": "newpassword123"},
        headers=r["headers"],
    )
    assert good.status_code == 204
    assert client.post("/api/auth/login", json={"email": r["email"], "password": "newpassword123"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": r["email"], "password": r["password"]}).status_code == 401
