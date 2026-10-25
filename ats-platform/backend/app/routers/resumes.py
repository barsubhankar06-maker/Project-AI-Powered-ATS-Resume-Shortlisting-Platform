"""Resume upload, parsing status, private download and parsed-data edits."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import Principal, require_recruiter
from ..models import Application, CandidateProfile, Job, ParsedResume, Resume
from ..schemas import ParsedResumeUpdate, ResumeDetail, ResumeOut
from ..security import create_signed_token, verify_signed_token
from ..services import audit, storage, text_extract
from ..services.processing import enqueue_resume, match_application, process_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _validate_and_read(file: UploadFile) -> tuple[bytes, str]:
    data = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{file.filename}' is empty")
    if len(data) > max_bytes:
        raise HTTPException(
            413,
            f"'{file.filename}' exceeds the {settings.max_upload_mb} MB limit",
        )
    kind, err = text_extract.sniff_kind(file.filename or "", file.content_type or "", data)
    if err:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"'{file.filename}': {err}")
    return data, kind


def _store_one(
    db: Session,
    p: Principal,
    filename: str,
    mime: str,
    data: bytes,
    job_id: str | None,
    candidate_id: str | None,
) -> dict:
    sha = storage.compute_sha256(data)
    dup = db.scalar(
        select(Resume).where(Resume.org_id == p.org_id, Resume.sha256 == sha)
    )
    if dup:
        # Link the existing resume to a new application if a job was given.
        if job_id and not db.scalar(
            select(Application).where(Application.job_id == job_id, Application.resume_id == dup.id)
        ):
            app = Application(
                org_id=p.org_id,
                job_id=job_id,
                candidate_id=dup.candidate_id,
                resume_id=dup.id,
                source="recruiter_upload",
            )
            db.add(app)
            db.flush()
            match_application(db, app.id)
        return {"filename": filename, "duplicate": True, "resume_id": dup.id, "status": dup.status}

    resume = Resume(
        org_id=p.org_id,
        candidate_id=candidate_id,
        uploaded_by=p.user.id,
        filename=storage.sanitize_filename(filename),
        storage_key="",
        mime_type=mime,
        size_bytes=len(data),
        sha256=sha,
        status="pending",
    )
    db.add(resume)
    db.flush()

    # Create a candidate profile if none supplied.
    if not resume.candidate_id:
        cand = CandidateProfile(org_id=p.org_id, full_name="", email="")
        db.add(cand)
        db.flush()
        resume.candidate_id = cand.id

    key = storage.save_bytes(p.org_id, resume.id, filename, data)
    resume.storage_key = key

    if job_id:
        job = db.get(Job, job_id)
        if not job or job.org_id != p.org_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
        app = Application(
            org_id=p.org_id,
            job_id=job_id,
            candidate_id=resume.candidate_id,
            resume_id=resume.id,
            source="recruiter_upload",
        )
        db.add(app)
        db.flush()
    db.flush()
    return {"filename": filename, "duplicate": False, "resume_id": resume.id, "status": "pending"}


@router.post("/upload", status_code=201)
def upload_resumes(
    request: Request,
    files: list[UploadFile] = File(...),
    job_id: str | None = Form(default=None),
    candidate_id: str | None = Form(default=None),
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    """Upload one or many resumes. Each is validated, stored privately, queued
    for parsing, and (if a job is given) matched."""
    if len(files) > 50:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "At most 50 files per request")
    results = []
    for f in files:
        try:
            data, _kind = _validate_and_read(f)
        except HTTPException as exc:
            results.append({"filename": f.filename, "error": exc.detail, "status": "failed"})
            continue
        results.append(_store_one(db, p, f.filename or "resume", f.content_type or "", data, job_id, candidate_id))
    audit.record(
        db,
        org_id=p.org_id,
        actor_id=p.user.id,
        action="resume.uploaded",
        entity_type="resume",
        meta={"count": len(results), "job_id": job_id},
        ip=request.client.host if request.client else "",
    )
    db.commit()

    # Queue parsing AFTER commit so workers see committed rows.
    for r in results:
        if r.get("resume_id") and not r.get("duplicate"):
            enqueue_resume(r["resume_id"])
    return {"results": results}


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
    job_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, le=500),
):
    stmt = select(Resume).where(Resume.org_id == p.org_id)
    if job_id:
        app_ids = [a.resume_id for a in db.scalars(select(Application).where(Application.job_id == job_id))]
        stmt = stmt.where(Resume.id.in_([a for a in app_ids if a]))
    if status_filter:
        stmt = stmt.where(Resume.status == status_filter)
    return list(db.scalars(stmt.order_by(Resume.created_at.desc()).limit(limit)))


def _get_resume(db: Session, org_id: str, resume_id: str) -> Resume:
    r = db.get(Resume, resume_id)
    if not r or r.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    return r


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    r = _get_resume(db, p.org_id, resume_id)
    parsed = db.scalar(select(ParsedResume).where(ParsedResume.resume_id == r.id))
    return ResumeDetail(
        **ResumeOut.model_validate(r).model_dump(),
        parsed=parsed,
    )


@router.patch("/{resume_id}/parsed", response_model=ResumeDetail)
def update_parsed(
    resume_id: str,
    payload: ParsedResumeUpdate,
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    """Recruiter corrections to parsed fields. Marks the record as edited and
    re-runs matching so scores reflect the correction."""
    r = _get_resume(db, p.org_id, resume_id)
    parsed = db.scalar(select(ParsedResume).where(ParsedResume.resume_id == r.id))
    if not parsed:
        parsed = ParsedResume(resume_id=r.id, data={}, confidence={}, uncertainties=[])
        db.add(parsed)
    merged = {**(parsed.data or {}), **payload.data}
    parsed.data = merged
    parsed.manually_edited = True
    # Sync candidate identity from corrections.
    cand = db.get(CandidateProfile, r.candidate_id) if r.candidate_id else None
    if cand:
        if payload.data.get("name"):
            cand.full_name = payload.data["name"]
        if payload.data.get("email"):
            cand.email = payload.data["email"]
        if payload.data.get("phone"):
            cand.phone = payload.data["phone"]
        if payload.data.get("summary"):
            cand.summary = payload.data["summary"]
    db.flush()
    for app in db.scalars(select(Application).where(Application.resume_id == r.id)):
        match_application(db, app.id)
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="resume.parsed_edited", entity_type="resume", entity_id=r.id)
    db.commit()
    db.refresh(r)
    db.refresh(parsed)
    return ResumeDetail(**ResumeOut.model_validate(r).model_dump(), parsed=parsed)


@router.post("/{resume_id}/reprocess", response_model=ResumeOut)
def reprocess(resume_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    r = _get_resume(db, p.org_id, resume_id)
    r.status = "pending"
    r.error = ""
    db.commit()
    if settings.processing_mode == "inline":
        process_resume(r.id)
    else:
        enqueue_resume(r.id)
    db.refresh(r)
    return ResumeOut.model_validate(r)


@router.get("/{resume_id}/download-url")
def download_url(resume_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    """Issue a short-lived signed URL for the private original file."""
    r = _get_resume(db, p.org_id, resume_id)
    external = storage.presigned_url(r.storage_key)
    if external:
        return {"url": external, "expires_in": settings.signed_url_ttl_seconds, "backend": "s3"}
    token = create_signed_token(f"{r.org_id}:{r.id}", settings.signed_url_ttl_seconds)
    return {
        "url": f"/api/resumes/file/{token}",
        "expires_in": settings.signed_url_ttl_seconds,
        "backend": "local",
    }


@router.get("/file/{token}")
def download_file(token: str, db: Session = Depends(get_db)):
    """Serve a private file given a valid, unexpired signed token.

    Declared BEFORE /{resume_id} would collide, so the path has two segments.
    """
    resource = verify_signed_token(token)
    if not resource or ":" not in resource:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid or expired link")
    org_id, resume_id = resource.split(":", 1)
    r = db.get(Resume, resume_id)
    if not r or r.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    if settings.storage_backend != "local":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Use the provider URL for this backend")
    path = storage.local_path(r.storage_key)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File no longer available")
    return FileResponse(path, filename=r.filename, media_type=r.mime_type or "application/octet-stream")


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    r = _get_resume(db, p.org_id, resume_id)
    try:
        storage.delete(r.storage_key)
    except Exception:  # noqa: BLE001
        pass
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="resume.deleted", entity_type="resume", entity_id=r.id)
    db.delete(r)
    db.commit()
