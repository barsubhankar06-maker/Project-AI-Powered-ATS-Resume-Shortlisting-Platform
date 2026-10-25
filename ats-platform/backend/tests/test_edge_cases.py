"""Edge cases: bad uploads, duplicates, empty/scanned resumes, AI failure fallback."""
from tests.conftest import (
    add_requirements,
    create_job,
    make_docx,
    make_pdf,
    register,
    upload_resume,
)


def test_empty_file_rejected(client):
    rec = register(client)
    files = {"files": ("empty.docx", b"", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = client.post("/api/resumes/upload", files=files, headers=rec["headers"])
    assert res.status_code == 201
    assert res.json()["results"][0].get("error")  # empty files are reported per-file


def test_unsupported_extension_rejected(client):
    rec = register(client)
    files = {"files": ("virus.exe", b"MZ\x90\x00", "application/octet-stream")}
    res = client.post("/api/resumes/upload", files=files, headers=rec["headers"])
    assert res.status_code == 201
    assert "Unsupported" in res.json()["results"][0]["error"]


def test_masquerading_file_rejected(client):
    """A .pdf extension with non-PDF bytes must be refused (magic-byte check)."""
    rec = register(client)
    files = {"files": ("fake.pdf", b"this is not a pdf at all", "application/pdf")}
    res = client.post("/api/resumes/upload", files=files, headers=rec["headers"])
    assert "not look like a valid PDF" in res.json()["results"][0]["error"]


def test_duplicate_detection(client):
    rec = register(client)
    job = create_job(client, rec["headers"])
    add_requirements(client, rec["headers"], job["id"])
    first = upload_resume(client, rec["headers"], "Same content here", filename="a.docx", job_id=job["id"])
    second = upload_resume(client, rec["headers"], "Same content here", filename="b.docx", job_id=job["id"])
    assert second["duplicate"] is True
    assert second["resume_id"] == first["resume_id"]


def test_oversized_file_rejected(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_upload_mb", 0)  # force the limit to trip
    rec = register(client)
    files = {"files": ("big.docx", make_docx("some content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = client.post("/api/resumes/upload", files=files, headers=rec["headers"])
    assert "exceeds" in res.json()["results"][0]["error"]


def test_scanned_pdf_without_text_layer_reports_failure(client):
    """A PDF with no text layer and OCR disabled must fail clearly, not silently."""
    rec = register(client)
    # A valid PDF whose page has an empty text layer (as a scanned page would).
    scanned = make_pdf("")
    files = {"files": ("scan.pdf", scanned, "application/pdf")}
    res = client.post("/api/resumes/upload", files=files, headers=rec["headers"])
    rid = res.json()["results"][0]["resume_id"]
    detail = client.get(f"/api/resumes/{rid}", headers=rec["headers"]).json()
    assert detail["status"] == "failed"
    assert "text" in detail["error"].lower()


def test_ai_unavailable_falls_back_to_deterministic():
    from app.services import matching, resume_parser

    # use_llm=True while no provider is configured must degrade gracefully.
    parsed = resume_parser.parse_resume("Jane\nSkills: Python", use_llm=True)
    assert parsed.parser in ("heuristic", "hybrid")
    assert any("unavailable" in u.lower() or "deterministic" in u.lower() for u in parsed.uncertainties)

    out = matching.match_resume_to_job(
        resume_data={"skills": ["python"], "total_experience_years": 3.0, "experience_highlights": [], "projects": [], "education": []},
        requirements=[{"kind": "required_skill", "text": "python", "normalized_skill": "python"}],
        job={"experience_min": 2, "experience_max": 5, "description": "", "responsibilities": ""},
        use_llm=True,
    )
    assert out.method == "deterministic"  # clearly labelled


def test_malformed_docx_fails_gracefully(client):
    rec = register(client)
    files = {"files": ("broken.docx", b"PK\x03\x04 not really a docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = client.post("/api/resumes/upload", files=files, headers=rec["headers"])
    rid = res.json()["results"][0]["resume_id"]
    detail = client.get(f"/api/resumes/{rid}", headers=rec["headers"]).json()
    assert detail["status"] == "failed"


def test_resume_with_no_skills_does_not_break_matching(client):
    rec = register(client)
    job = create_job(client, rec["headers"])
    add_requirements(client, rec["headers"], job["id"])
    upload_resume(client, rec["headers"], "Just a name\nAnd nothing else useful", job_id=job["id"])
    rows = client.get(f"/api/jobs/{job['id']}/candidates", headers=rec["headers"]).json()
    assert rows["total"] == 1  # scored without crashing
    assert rows["items"][0]["match_score"] is not None
