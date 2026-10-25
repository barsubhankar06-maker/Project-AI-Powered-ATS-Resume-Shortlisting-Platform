"""Candidate profiles: list, detail, edits and manual matching re-run."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Principal, require_recruiter
from ..models import Application, CandidateProfile, Job, MatchResult, ParsedResume, Resume
from ..schemas import CandidateOut, CandidateUpdate, MatchResultOut
from ..services import audit
from ..services.processing import match_application

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _get_candidate(db: Session, org_id: str, cid: str) -> CandidateProfile:
    c = db.get(CandidateProfile, cid)
    if not c or c.org_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")
    return c


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
    q: str | None = None,
    job_id: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
):
    stmt = select(CandidateProfile).where(CandidateProfile.org_id == p.org_id)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            (CandidateProfile.full_name.ilike(like)) | (CandidateProfile.email.ilike(like))
        )
    if job_id:
        cand_ids = [a.candidate_id for a in db.scalars(select(Application).where(Application.job_id == job_id))]
        stmt = stmt.where(CandidateProfile.id.in_(cand_ids))
    stmt = stmt.order_by(CandidateProfile.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt))


@router.get("/{candidate_id}")
def candidate_detail(candidate_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    c = _get_candidate(db, p.org_id, candidate_id)
    apps = []
    for a in db.scalars(select(Application).where(Application.candidate_id == c.id)):
        job = db.get(Job, a.job_id)
        mr = db.scalar(
            select(MatchResult).where(MatchResult.application_id == a.id).order_by(MatchResult.created_at.desc())
        )
        apps.append(
            {
                "application_id": a.id,
                "job_id": a.job_id,
                "job_title": job.title if job else "",
                "stage": a.stage,
                "status": a.status,
                "match_score": a.match_score,
                "applied_at": a.applied_at,
                "resume_id": a.resume_id,
                "latest_match": MatchResultOut.model_validate(mr).model_dump() if mr else None,
            }
        )
    resumes = [
        {"id": r.id, "filename": r.filename, "status": r.status, "version": r.version, "created_at": r.created_at}
        for r in db.scalars(select(Resume).where(Resume.candidate_id == c.id))
    ]
    return {"candidate": CandidateOut.model_validate(c).model_dump(), "applications": apps, "resumes": resumes}


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    c = _get_candidate(db, p.org_id, candidate_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="candidate.updated", entity_type="candidate", entity_id=c.id)
    db.commit()
    db.refresh(c)
    return c


@router.post("/applications/{application_id}/rematch")
def rematch(application_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    a = db.get(Application, application_id)
    if not a or a.org_id != p.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    mr = match_application(db, a.id)
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="match.rerun", entity_type="application", entity_id=a.id)
    db.commit()
    if not mr:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to match (missing resume or job)")
    db.refresh(mr)
    return MatchResultOut.model_validate(mr)


@router.get("/applications/{application_id}/parsed")
def application_parsed(application_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    a = db.get(Application, application_id)
    if not a or a.org_id != p.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if not a.resume_id:
        return {"parsed": None}
    parsed = db.scalar(select(ParsedResume).where(ParsedResume.resume_id == a.resume_id))
    return {"parsed": parsed.data if parsed else None, "uncertainties": parsed.uncertainties if parsed else []}
