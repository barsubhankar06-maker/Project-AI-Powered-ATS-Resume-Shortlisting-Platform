"""Shared pytest fixtures.

Environment is configured BEFORE importing the app so the engine, storage and
processing mode used in tests are isolated from development.
"""
from __future__ import annotations

import io
import os
import shutil
import tempfile
import uuid

# --- Configure the environment before importing the app -------------------
_TMP = tempfile.mkdtemp(prefix="ats_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["STORAGE_DIR"] = f"{_TMP}/storage"
os.environ["PROCESSING_MODE"] = "inline"      # parse synchronously in tests
os.environ["ENVIRONMENT"] = "production"      # disable demo seed
os.environ["SECRET_KEY"] = "test-secret-key-please-change-0123456789"
os.environ["LLM_ENABLED"] = "false"
os.environ["OCR_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(scope="session")
def tmp_dir():
    return _TMP


# --- Helpers --------------------------------------------------------------


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"


def register(client, *, role="recruiter", org="Test Co", email=None, password="password123"):
    email = email or unique_email(role)
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test Person",
            "role": role,
            "organization_name": org,
        },
    )
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return {"email": email, "password": password, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def make_docx(text: str) -> bytes:
    from datetime import datetime

    from docx import Document

    doc = Document()
    # Fixed core properties so identical text yields identical bytes
    # (python-docx otherwise stamps a fresh created/modified time).
    doc.core_properties.created = datetime(2020, 1, 1)
    doc.core_properties.modified = datetime(2020, 1, 1)
    doc.core_properties.last_modified_by = "test"
    doc.core_properties.revision = 1
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_pdf(text: str) -> bytes:
    """Build a tiny single-page PDF with a real text layer."""
    content = f"BT /F1 12 Tf 72 720 Td ({text[:120]}) Tj ET"
    stream = content.encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return bytes(out)


SAMPLE_JD = (
    "Senior Backend Engineer.\n\n"
    "Required Skills\nPython, FastAPI, PostgreSQL, Docker, AWS, REST\n\n"
    "Preferred Skills\nRedis, Kubernetes\n\n"
    "Responsibilities\n"
    "- Design and build REST APIs and microservices.\n"
    "- Tune database performance and add caching.\n\n"
    "Qualifications\nBachelor's degree in Computer Science or related field."
)

STRONG_RESUME = """Aarav Sharma
Bengaluru, India | aarav@example.com | +91 98765 43210

Summary
Backend engineer with 6 years building high-throughput APIs.

Experience
Senior Backend Engineer, Nimbus Cloud (Jan 2020 - Present)
- Designed REST APIs in Python and FastAPI serving 40k rps.
- Migrated monolith to microservices on Docker and Kubernetes.
- Tuned PostgreSQL and added Redis caching.

Skills
Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS, REST

Education
B.Tech in Computer Science, IIT Delhi, 2018
"""

WEAK_RESUME = """Rohan Verma
Hyderabad, India | rohan@example.com

Summary
Frontend developer with 2 years of experience.

Experience
Frontend Developer, PixelWorks (Mar 2022 - Present)
- Built responsive UIs with React and TypeScript.

Skills
JavaScript, TypeScript, React, CSS, HTML

Education
B.E Information Technology, Osmania University, 2021
"""


def create_job(client, headers, **overrides):
    payload = {
        "title": overrides.pop("title", "Senior Backend Engineer"),
        "description": overrides.pop("description", SAMPLE_JD),
        "company": "Test Co",
        "experience_min": overrides.pop("experience_min", 4),
        "experience_max": overrides.pop("experience_max", 8),
        **overrides,
    }
    res = client.post("/api/jobs", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def add_requirements(client, headers, job_id):
    res = client.post("/api/jobs/analyze-jd", json={"description": SAMPLE_JD}, headers=headers)
    assert res.status_code == 200, res.text
    reqs = res.json()["requirements"]
    res = client.post(f"/api/jobs/{job_id}/requirements", json=reqs, headers=headers)
    assert res.status_code == 201, res.text
    return reqs


def upload_resume(client, headers, text, filename="resume.docx", job_id=None):
    files = {
        "files": (
            filename,
            make_docx(text),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    data = {"job_id": job_id} if job_id else {}
    res = client.post("/api/resumes/upload", files=files, data=data, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["results"][0]
