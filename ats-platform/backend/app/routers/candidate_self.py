"""Candidate self-service: own profile, applications, apply, resume, deletion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Principal, require_candidate
from ..models import (
    Application,
    CandidateProfile,
    DeletionRequest,
    Job,
    Resume,
    utcnow,
)
from ..schemas import CandidateOut, CandidateUpdate
from ..services import audit, storage, text_extract
from ..services.processing import enqueue_resume, match_application

router = APIRouter(prefix="/me", tags=["candidate-self"])


def _profile_for_org(db: Session, user_id: str, org_id: str, full_name: str, email: str) -> CandidateProfile:
    c = db.scalar(
        select(CandidateProfile).where(
            CandidateProfile.user_id == user_id, CandidateProfile.org_id == org_id
        )
    )
    if c:
        return c
    c = CandidateProfile(org_id=org_id, user_id=user_id, full_name=full_name, email=email)
    db.add(c)
    db.flush()
    return c


@router.get("/profile")
def my_profile(p: Principal = Depends(require_candidate), db: Session = Depends(get_db)):
    profiles = list(db.scalars(select(CandidateProfile).where(CandidateProfile.user_id == p.user.id)))
    return {
        "user": {"id": p.user.id, "email": p.user.email, "full_name": p.user.full_name},
        "profiles": [CandidateOut.model_validate(c).model_dump() for c in profiles],
    }


@router.patch("/profile", response_model=CandidateOut)
def update_my_profile(
    payload: CandidateUpdate, p: Principal = Depends(require_candidate), db: Session = Depends(get_db)
):
    c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == p.user.id))
    if not c:
        c = CandidateProfile(user_id=p.user.id, org_id=None, full_name=p.user.full_name, email=p.user.email)
        db.add(c)
        db.flush()
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.get("/applications")
def my_applications(p: Principal = Depends(require_candidate), db: Session = Depends(get_db)):
    profiles = list(db.scalars(select(CandidateProfile).where(CandidateProfile.user_id == p.user.id)))
    ids = [c.id for c in profiles]
    out = []
    if ids:
        for a in db.scalars(select(Application).where(Application.candidate_id.in_(ids)).order_by(Application.applied_at.desc())):
            job = db.get(Job, a.job_id)
            out.append(
                {
                    "application_id": a.id,
                    "job_id": a.job_id,
                    "job_title": job.title if job else "",
                    "company": job.company if job else "",
                    "stage": a.stage,
                    "status": a.status,
                    "applied_at": a.applied_at,
                    # Feedback only shown when the employer enabled it.
                    "feedback": a.candidate_feedback if a.feedback_enabled else None,
                }
            )
    return out


@router.post("/apply", status_code=201)
def apply_to_job(
    job_id: str = Form(...),
    cover_letter: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    p: Principal = Depends(require_candidate),
    db: Session = Depends(get_db),
):
    job = db.get(Job, job_id)
    if not job or job.status != "open":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found or not open")

    cand = _profile_for_org(db, p.user.id, job.org_id, p.user.full_name, p.user.email)

    existing = db.scalar(
        select(Application).where(Application.job_id == job.id, Application.candidate_id == cand.id)
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already applied to this job")

    resume_id = None
    if file is not None and file.filename:
        data = file.file.read()
        if len(data) > 15 * 1024 * 1024:
            raise HTTPException(413, "Resume too large (max 15 MB)")
        kind, err = text_extract.sniff_kind(file.filename, file.content_type or "", data)
        if err:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, err)
        resume = Resume(
            org_id=job.org_id,
            candidate_id=cand.id,
            uploaded_by=p.user.id,
            filename=storage.sanitize_filename(file.filename),
            storage_key="",
            mime_type=file.content_type or "",
            size_bytes=len(data),
            sha256=storage.compute_sha256(data),
            status="pending",
        )
        db.add(resume)
        db.flush()
        resume.storage_key = storage.save_bytes(job.org_id, resume.id, file.filename, data)
        resume_id = resume.id

    app = Application(
        org_id=job.org_id,
        job_id=job.id,
        candidate_id=cand.id,
        resume_id=resume_id,
        source="candidate_apply",
        cover_letter=cover_letter,
        feedback_enabled=job.feedback_enabled,
    )
    db.add(app)
    db.flush()
    if resume_id:
        match_application(db, app.id)
    audit.record(db, org_id=job.org_id, actor_id=p.user.id, action="application.submitted", entity_type="application", entity_id=app.id)
    db.commit()
    if resume_id:
        enqueue_resume(resume_id)
    return {"application_id": app.id, "stage": app.stage, "match_score": app.match_score}


@router.post("/delete-request", status_code=201)
def request_deletion(p: Principal = Depends(require_candidate), db: Session = Depends(get_db)):
    c = db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == p.user.id))
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No candidate profile found")
    req = DeletionRequest(candidate_id=c.id, reason="candidate request")
    db.add(req)
    audit.record(db, org_id=c.org_id, actor_id=p.user.id, action="candidate.deletion_requested", entity_type="candidate", entity_id=c.id)
    db.commit()
    return {"id": req.id, "status": req.status}
