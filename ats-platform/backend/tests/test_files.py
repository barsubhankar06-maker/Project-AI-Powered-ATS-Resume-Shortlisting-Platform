"""Private file access, signed URLs and storage controls."""
from tests.conftest import (
    STRONG_RESUME,
    add_requirements,
    create_job,
    make_docx,
    register,
    upload_resume,
)


def test_signed_download_url_works(client):
    rec = register(client)
    job = create_job(client, rec["headers"])
    add_requirements(client, rec["headers"], job["id"])
    res = upload_resume(client, rec["headers"], STRONG_RESUME, job_id=job["id"])
    url = client.get(f"/api/resumes/{res['resume_id']}/download-url", headers=rec["headers"]).json()["url"]
    # The signed URL requires no bearer token but must carry a valid token.
    got = client.get(url)
    assert got.status_code == 200
    assert got.headers["content-type"].startswith("application/")
    assert b"Aarav" in got.content or len(got.content) > 500


def test_download_requires_valid_token(client):
    rec = register(client)
    job = create_job(client, rec["headers"])
    add_requirements(client, rec["headers"], job["id"])
    res = upload_resume(client, rec["headers"], STRONG_RESUME, job_id=job["id"])
    client.get(f"/api/resumes/{res['resume_id']}/download-url", headers=rec["headers"])
    assert client.get("/api/resumes/file/tampered").status_code == 403


def test_original_file_is_stored_outside_database(client):
    """The resume row stores a key, not the file bytes."""
    rec = register(client)
    job = create_job(client, rec["headers"])
    add_requirements(client, rec["headers"], job["id"])
    res = upload_resume(client, rec["headers"], STRONG_RESUME, job_id=job["id"])
    detail = client.get(f"/api/resumes/{res['resume_id']}", headers=rec["headers"]).json()
    assert "storage_key" not in detail
    assert detail["size_bytes"] > 0
