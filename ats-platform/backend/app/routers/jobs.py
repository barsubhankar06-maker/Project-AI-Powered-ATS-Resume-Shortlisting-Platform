"""Jobs, requirements, JD analysis, ranked candidate table and bulk actions."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Principal, require_recruiter
from ..models import (
    Application,
    CandidateProfile,
    Job,
    JobRequirement,
    MatchResult,
    ParsedResume,
    Resume,
    utcnow,
)
from ..schemas import (
    AnalyzeJdRequest,
    AnalyzeJdResponse,
    BulkActionRequest,
    CandidateRow,
    JobCreate,
    JobDetail,
    JobOut,
    JobUpdate,
    RequirementIn,
    RequirementOut,
)
from ..services import audit, job_parser, matching
from ..services.processing import match_application

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_job(db: Session, org_id: str, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job or job.org_id != org_id:
        # 404 (not 403) so ids cannot be probed across organizations.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
):
    stmt = select(Job).where(Job.org_id == p.org_id)
    if status_filter:
        stmt = stmt.where(Job.status == status_filter)
    return list(db.scalars(stmt.order_by(Job.created_at.desc())))


@router.post("", response_model=JobDetail, status_code=201)
def create_job(payload: JobCreate, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    # Use supplied weights, else the organization's defaults, else the standard model.
    from ..models import Organization

    if payload.weights:
        weights = dict(payload.weights)
    else:
        org = db.get(Organization, p.org_id)
        weights = dict((org.default_weights if org else None) or matching.DEFAULT_WEIGHTS)

    validated, err = matching.validate_weights(weights)
    if err:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, err)

    job = Job(
        org_id=p.org_id,
        created_by=p.user.id,
        title=payload.title.strip(),
        company=payload.company,
        department=payload.department,
        location=payload.location,
        employment_type=payload.employment_type,
        experience_min=payload.experience_min,
        experience_max=payload.experience_max,
        description=payload.description,
        responsibilities=payload.responsibilities,
        min_qualifications=payload.min_qualifications,
        preferred_qualifications=payload.preferred_qualifications,
        status=payload.status,
        weights=validated,
        hard_requirements=payload.hard_requirements,
        auto_exclude_below=payload.auto_exclude_below,
        blind_screening=payload.blind_screening,
        feedback_enabled=payload.feedback_enabled,
    )
    db.add(job)
    db.flush()
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="job.created", entity_type="job", entity_id=job.id)
    db.commit()
    db.refresh(job)
    return JobDetail(**JobOut.model_validate(job).model_dump(), requirements=[])


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = _get_job(db, p.org_id, job_id)
    reqs = list(db.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)))
    return JobDetail(
        **JobOut.model_validate(job).model_dump(),
        requirements=[RequirementOut.model_validate(r) for r in reqs],
    )


@router.patch("/{job_id}", response_model=JobDetail)
def update_job(
    job_id: str, payload: JobUpdate, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)
):
    job = _get_job(db, p.org_id, job_id)
    data = payload.model_dump(exclude_unset=True)
    if "weights" in data and data["weights"] is not None:
        validated, err = matching.validate_weights(data["weights"])
        if err:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, err)
        data["weights"] = validated
    version_bump = any(k in data for k in ("description", "responsibilities", "experience_min", "experience_max"))
    for k, v in data.items():
        setattr(job, k, v)
    if version_bump:
        job.version += 1
        # Existing scores may now be stale.
        for mr in db.scalars(select(MatchResult).where(MatchResult.job_id == job.id)):
            mr.is_stale = True
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="job.updated", entity_type="job", entity_id=job.id)
    db.commit()
    db.refresh(job)
    reqs = list(db.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)))
    return JobDetail(
        **JobOut.model_validate(job).model_dump(),
        requirements=[RequirementOut.model_validate(r) for r in reqs],
    )


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = _get_job(db, p.org_id, job_id)
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="job.deleted", entity_type="job", entity_id=job.id)
    db.delete(job)
    db.commit()


@router.post("/analyze-jd", response_model=AnalyzeJdResponse)
def analyze_jd(payload: AnalyzeJdRequest, p: Principal = Depends(require_recruiter)):
    result = job_parser.analyze_jd(payload.description, payload.title)
    return AnalyzeJdResponse(
        requirements=[RequirementIn(**r) for r in result.requirements],
        suggested=result.suggested,
        method=result.method,
    )


# --- Requirements ---------------------------------------------------------


@router.get("/{job_id}/requirements", response_model=list[RequirementOut])
def list_requirements(job_id: str, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    job = _get_job(db, p.org_id, job_id)
    return list(db.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)))


@router.post("/{job_id}/requirements", response_model=list[RequirementOut], status_code=201)
def replace_requirements(
    job_id: str,
    payload: list[RequirementIn],
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    """Replace the full requirement set (used after recruiter review/edit)."""
    job = _get_job(db, p.org_id, job_id)
    for r in db.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)):
        db.delete(r)
    db.flush()
    created = []
    for item in payload:
        from ..services import skill_normalization as sn

        req = JobRequirement(
            job_id=job.id,
            kind=item.kind,
            text=item.text.strip(),
            normalized_skill=item.normalized_skill or sn.normalize(item.text),
            is_hard=item.is_hard,
            source=item.source,
        )
        db.add(req)
        created.append(req)
    job.version += 1
    for mr in db.scalars(select(MatchResult).where(MatchResult.job_id == job.id)):
        mr.is_stale = True
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="job.requirements_updated", entity_type="job", entity_id=job.id)
    db.commit()
    for c in created:
        db.refresh(c)
    return [RequirementOut.model_validate(c) for c in created]


# --- Ranked candidate table ----------------------------------------------


def _latest_match(db: Session, app_id: str) -> MatchResult | None:
    return db.scalar(
        select(MatchResult)
        .where(MatchResult.application_id == app_id)
        .order_by(MatchResult.created_at.desc())
    )


@router.get("/{job_id}/candidates")
def ranked_candidates(
    job_id: str,
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
    score_min: float | None = None,
    score_max: float | None = None,
    coverage_min: float | None = None,
    exp_min: float | None = None,
    exp_max: float | None = None,
    skill: str | None = None,
    stage: str | None = None,
    parsing_status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = Query(default="score", pattern="^(score|applied_at|name)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
):
    job = _get_job(db, p.org_id, job_id)
    apps = list(db.scalars(select(Application).where(Application.job_id == job.id)))
    rows: list[CandidateRow] = []
    for a in apps:
        cand = db.get(CandidateProfile, a.candidate_id)
        resume = db.get(Resume, a.resume_id) if a.resume_id else None
        mr = _latest_match(db, a.id)
        parsed = None
        if resume:
            parsed = db.scalar(select(ParsedResume).where(ParsedResume.resume_id == resume.id))
        exp_years = (parsed.data.get("total_experience_years") if parsed else None) or 0
        coverage = None
        if mr and mr.breakdown.get("components", {}).get("required_skills"):
            coverage = mr.breakdown["components"]["required_skills"].get("score")
        display = (cand.full_name if cand else "") or (parsed.data.get("name") if parsed else "") or "Unnamed"
        if (job.blind_screening or (cand and cand.anonymized)) and cand:
            display = f"Candidate {cand.id[:6]}"
        rows.append(
            CandidateRow(
                application_id=a.id,
                candidate_id=a.candidate_id,
                display_name=display,
                email="" if (job.blind_screening or (cand and cand.anonymized)) else (cand.email if cand else ""),
                resume_filename=resume.filename if resume else None,
                match_score=a.match_score,
                required_coverage=coverage,
                experience_summary=(
                    f"{exp_years}y" if parsed and parsed.data.get("total_experience_years") is not None else "unknown"
                ),
                missing=(mr.missing if mr else []),
                applied_at=a.applied_at,
                stage=a.stage,
                status=a.status,
                parsing_status=resume.status if resume else "none",
                method=mr.method if mr else None,
                is_stale=bool(mr.is_stale) if mr else False,
            )
        )

    # Filters
    if score_min is not None:
        rows = [r for r in rows if r.match_score is not None and r.match_score >= score_min]
    if score_max is not None:
        rows = [r for r in rows if r.match_score is not None and r.match_score <= score_max]
    if coverage_min is not None:
        rows = [r for r in rows if r.required_coverage is not None and r.required_coverage >= coverage_min]
    if stage:
        rows = [r for r in rows if r.stage == stage]
    if parsing_status:
        rows = [r for r in rows if r.parsing_status == parsing_status]
    if exp_min is not None or exp_max is not None:
        filtered = []
        for r in rows:
            try:
                y = float(r.experience_summary.rstrip("y")) if r.experience_summary != "unknown" else None
            except ValueError:
                y = None
            if y is None:
                continue
            if exp_min is not None and y < exp_min:
                continue
            if exp_max is not None and y > exp_max:
                continue
            filtered.append(r)
        rows = filtered
    if skill:
        from ..services import skill_normalization as sn

        want = sn.normalize(skill)
        keep = []
        for r in rows:
            mr = _latest_match(db, r.application_id)
            skillset = set(sn.normalize(s) for s in (mr.matched if mr else []) + (mr.partial and [] or []))
            if want in skillset or skill.lower() in " ".join(mr.matched if mr else []).lower():
                keep.append(r)
        rows = keep
    if date_from:
        try:
            d = datetime.fromisoformat(date_from)
            rows = [r for r in rows if r.applied_at and r.applied_at >= d]
        except ValueError:
            pass
    if date_to:
        try:
            d = datetime.fromisoformat(date_to)
            rows = [r for r in rows if r.applied_at and r.applied_at <= d]
        except ValueError:
            pass

    reverse = order == "desc"
    if sort == "score":
        rows.sort(key=lambda r: (r.match_score if r.match_score is not None else -1), reverse=reverse)
    elif sort == "applied_at":
        rows.sort(key=lambda r: r.applied_at or datetime.min.replace(tzinfo=None), reverse=reverse)
    else:
        rows.sort(key=lambda r: r.display_name.lower(), reverse=reverse)

    total = len(rows)
    start = (page - 1) * page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [r.model_dump() for r in rows[start : start + page_size]],
    }


@router.post("/{job_id}/bulk")
def bulk_action(
    job_id: str, payload: BulkActionRequest, p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)
):
    job = _get_job(db, p.org_id, job_id)
    mapping = {"shortlist": "shortlisted", "review": "resume_review", "reject": "rejected"}
    updated = 0
    for app_id in payload.application_ids:
        a = db.get(Application, app_id)
        if not a or a.job_id != job.id or a.org_id != p.org_id:
            continue
        if payload.action in mapping:
            from ..models import StageHistory

            new_stage = mapping[payload.action]
            db.add(
                StageHistory(
                    application_id=a.id,
                    from_stage=a.stage,
                    to_stage=new_stage,
                    changed_by=p.user.id,
                    note=payload.note or f"bulk {payload.action}",
                )
            )
            a.stage = new_stage
            if new_stage == "rejected":
                a.status = "rejected"
            updated += 1
        elif payload.action == "export":
            updated += 1
    audit.record(
        db,
        org_id=p.org_id,
        actor_id=p.user.id,
        action=f"candidates.bulk_{payload.action}",
        entity_type="job",
        entity_id=job.id,
        meta={"count": updated},
    )
    db.commit()
    return {"updated": updated, "action": payload.action}
