"""Applications, pipeline, stage changes, notes, feedback and timeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Principal, require_recruiter
from ..models import (
    STAGES,
    Application,
    CandidateProfile,
    InterviewFeedback,
    Job,
    MatchResult,
    RecruiterNote,
    Resume,
    StageHistory,
)
from ..schemas import (
    ApplicationDetail,
    ApplicationOut,
    CandidateOut,
    FeedbackCreate,
    JobOut,
    MatchResultOut,
    NoteCreate,
    StageChangeRequest,
)
from ..services import audit

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_app(db: Session, org_id: str, app_id: str) -> Application:
    a = db.get(Application, app_id)
    if not a or a.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return a


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
    job_id: str | None = None,
    stage: str | None = None,
    limit: int = Query(default=200, le=1000),
):
    stmt = select(Application).where(Application.org_id == p.org_id)
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if stage:
        stmt = stmt.where(Application.stage == stage)
    return list(db.scalars(stmt.order_by(Application.applied_at.desc()).limit(limit)))


@router.get("/{application_id}", response_model=ApplicationDetail)
def application_detail(application_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    a = _get_app(db, p.org_id, application_id)
    cand = db.get(CandidateProfile, a.candidate_id)
    job = db.get(Job, a.job_id)
    mr = db.scalar(
        select(MatchResult).where(MatchResult.application_id == a.id).order_by(MatchResult.created_at.desc())
    )
    return ApplicationDetail(
        **ApplicationOut.model_validate(a).model_dump(),
        candidate=CandidateOut.model_validate(cand),
        job=JobOut.model_validate(job),
        latest_match=MatchResultOut.model_validate(mr) if mr else None,
    )


@router.post("/{application_id}/stage", response_model=ApplicationOut)
def change_stage(
    application_id: str,
    payload: StageChangeRequest,
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    a = _get_app(db, p.org_id, application_id)
    if a.stage == payload.stage and not payload.note:
        return a
    db.add(
        StageHistory(
            application_id=a.id,
            from_stage=a.stage,
            to_stage=payload.stage,
            changed_by=p.user.id,
            note=payload.note,
        )
    )
    a.stage = payload.stage
    if payload.stage == "rejected":
        a.status = "rejected"
    elif payload.stage == "hired":
        a.status = "hired"
    else:
        a.status = "active"
    audit.record(
        db,
        org_id=p.org_id,
        actor_id=p.user.id,
        action="application.stage_changed",
        entity_type="application",
        entity_id=a.id,
        meta={"from": payload.stage, "note": payload.note},
    )
    db.commit()
    db.refresh(a)
    return a


@router.get("/{application_id}/timeline")
def timeline(application_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    a = _get_app(db, p.org_id, application_id)
    events = list(
        db.scalars(
            select(StageHistory).where(StageHistory.application_id == a.id).order_by(StageHistory.created_at)
        )
    )
    return [
        {
            "from": e.from_stage,
            "to": e.to_stage,
            "note": e.note,
            "changed_by": e.changed_by,
            "at": e.created_at,
        }
        for e in events
    ]


@router.get("/{application_id}/notes")
def list_notes(application_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    a = _get_app(db, p.org_id, application_id)
    notes = list(db.scalars(select(RecruiterNote).where(RecruiterNote.application_id == a.id).order_by(RecruiterNote.created_at.desc())))
    return [{"id": n.id, "body": n.body, "author_id": n.author_id, "at": n.created_at} for n in notes]


@router.post("/{application_id}/notes", status_code=201)
def add_note(
    application_id: str, payload: NoteCreate, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)
):
    a = _get_app(db, p.org_id, application_id)
    n = RecruiterNote(application_id=a.id, author_id=p.user.id, body=payload.body.strip())
    db.add(n)
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="note.added", entity_type="application", entity_id=a.id)
    db.commit()
    db.refresh(n)
    return {"id": n.id, "body": n.body, "at": n.created_at}


@router.get("/{application_id}/feedback")
def list_feedback(application_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    a = _get_app(db, p.org_id, application_id)
    rows = list(db.scalars(select(InterviewFeedback).where(InterviewFeedback.application_id == a.id)))
    return [
        {
            "id": f.id,
            "stage": f.stage,
            "rating": f.rating,
            "strengths": f.strengths,
            "weaknesses": f.weaknesses,
            "notes": f.notes,
            "at": f.created_at,
        }
        for f in rows
    ]


@router.post("/{application_id}/feedback", status_code=201)
def add_feedback(
    application_id: str, payload: FeedbackCreate, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)
):
    a = _get_app(db, p.org_id, application_id)
    f = InterviewFeedback(
        application_id=a.id,
        author_id=p.user.id,
        stage=payload.stage,
        rating=payload.rating,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        notes=payload.notes,
    )
    db.add(f)
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="feedback.added", entity_type="application", entity_id=a.id)
    db.commit()
    db.refresh(f)
    return {"id": f.id, "rating": f.rating, "at": f.created_at}


@router.get("/pipeline/{job_id}")
def pipeline(job_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or job.org_id != p.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    columns = {stage: [] for stage in STAGES}
    for a in db.scalars(select(Application).where(Application.job_id == job.id)):
        cand = db.get(CandidateProfile, a.candidate_id)
        resume = db.get(Resume, a.resume_id) if a.resume_id else None
        display = (cand.full_name if cand else "") or "Unnamed"
        if job.blind_screening:
            display = f"Candidate {a.candidate_id[:6]}"
        columns[a.stage].append(
            {
                "application_id": a.id,
                "candidate_id": a.candidate_id,
                "display_name": display,
                "score": a.match_score,
                "resume_filename": resume.filename if resume else None,
                "parsing_status": resume.status if resume else "none",
            }
        )
    return {"job_id": job.id, "job_title": job.title, "columns": columns}
