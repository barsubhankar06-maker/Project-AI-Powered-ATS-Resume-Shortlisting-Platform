"""Analytics, reporting and export service.

All figures are computed live from database records — nothing is hardcoded.
Descriptive statistics are clearly separated from any predictive estimate.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    STAGES,
    Application,
    CandidateProfile,
    Job,
    JobRequirement,
    MatchResult,
    ParsedResume,
    Resume,
    StageHistory,
)

SCORE_BUCKETS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]


def _app_filter(stmt, org_id: str, job_id: str | None, date_from: str | None, date_to: str | None):
    stmt = stmt.where(Application.org_id == org_id)
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if date_from:
        stmt = stmt.where(Application.applied_at >= _parse_date(date_from))
    if date_to:
        stmt = stmt.where(Application.applied_at <= _parse_date(date_to, end=True))
    return stmt


def _parse_date(value: str, end: bool = False) -> datetime:
    try:
        d = datetime.fromisoformat(value)
    except ValueError:
        d = datetime.utcnow()
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    if end:
        d = d + timedelta(days=1)
    return d


def dashboard_stats(db: Session, org_id: str) -> dict:
    active_jobs = db.scalar(
        select(func.count()).select_from(Job).where(Job.org_id == org_id, Job.status == "open")
    ) or 0
    total_apps = db.scalar(
        select(func.count()).select_from(Application).where(Application.org_id == org_id)
    ) or 0
    resumes_processed = db.scalar(
        select(func.count())
        .select_from(Resume)
        .where(Resume.org_id == org_id, Resume.status == "completed")
    ) or 0
    shortlisted = db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.org_id == org_id, Application.stage == "shortlisted")
    ) or 0
    awaiting_review = db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.org_id == org_id, Application.stage.in_(["applied", "resume_review"]))
    ) or 0
    avg_score = db.scalar(
        select(func.avg(Application.match_score)).where(
            Application.org_id == org_id, Application.match_score.is_not(None)
        )
    )
    hired = db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.org_id == org_id, Application.stage == "hired")
    ) or 0
    rejected = db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.org_id == org_id, Application.stage == "rejected")
    ) or 0

    stage_dist = dict(
        (stage, 0) for stage in STAGES
    )
    rows = db.execute(
        select(Application.stage, func.count())
        .where(Application.org_id == org_id)
        .group_by(Application.stage)
    ).all()
    for stage, count in rows:
        stage_dist[stage] = count

    # Job-wise stats.
    jobs = list(db.scalars(select(Job).where(Job.org_id == org_id)))
    job_stats = []
    for job in jobs:
        counts = dict(
            db.execute(
                select(Application.stage, func.count())
                .where(Application.job_id == job.id)
                .group_by(Application.stage)
            ).all()
        )
        total = sum(counts.values())
        avg = db.scalar(
            select(func.avg(Application.match_score)).where(
                Application.job_id == job.id, Application.match_score.is_not(None)
            )
        )
        job_stats.append(
            {
                "job_id": job.id,
                "title": job.title,
                "status": job.status,
                "applications": total,
                "shortlisted": counts.get("shortlisted", 0) + counts.get("interview", 0)
                + counts.get("assessment", 0) + counts.get("offer", 0) + counts.get("hired", 0),
                "rejected": counts.get("rejected", 0),
                "avg_score": round(avg, 1) if avg is not None else None,
            }
        )

    recent = list(
        db.scalars(
            select(Application)
            .where(Application.org_id == org_id)
            .order_by(Application.created_at.desc())
            .limit(8)
        )
    )
    recent_activity = []
    for a in recent:
        cand = db.get(CandidateProfile, a.candidate_id)
        job = db.get(Job, a.job_id)
        recent_activity.append(
            {
                "application_id": a.id,
                "candidate": cand.full_name or "Unnamed candidate" if cand else "Unknown",
                "job": job.title if job else "",
                "stage": a.stage,
                "score": a.match_score,
                "at": a.created_at,
            }
        )

    return {
        "active_jobs": active_jobs,
        "total_applications": total_apps,
        "resumes_processed": resumes_processed,
        "shortlisted": shortlisted,
        "awaiting_review": awaiting_review,
        "hired": hired,
        "rejected": rejected,
        "avg_match_score": round(avg_score, 1) if avg_score is not None else None,
        "stage_distribution": stage_dist,
        "job_stats": job_stats,
        "recent_activity": recent_activity,
    }


def reports(
    db: Session,
    org_id: str,
    job_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    apps = list(
        db.scalars(
            _app_filter(select(Application), org_id, job_id, date_from, date_to)
        )
    )
    total = len(apps)

    # Applications by job.
    by_job: dict[str, int] = {}
    for a in apps:
        job = db.get(Job, a.job_id)
        key = job.title if job else a.job_id
        by_job[key] = by_job.get(key, 0) + 1

    # Score distribution.
    buckets = {f"{lo}-{hi if hi <= 100 else 100}": 0 for lo, hi in SCORE_BUCKETS}
    scored = [a for a in apps if a.match_score is not None]
    for a in scored:
        for lo, hi in SCORE_BUCKETS:
            if lo <= a.match_score < hi:
                buckets[f"{lo}-{hi if hi <= 100 else 100}"] += 1
                break

    # Shortlisting / conversion.
    stage_counts = dict((s, 0) for s in STAGES)
    for a in apps:
        stage_counts[a.stage] = stage_counts.get(a.stage, 0) + 1
    progressed = sum(
        stage_counts[s] for s in ["shortlisted", "interview", "assessment", "offer", "hired"]
    )
    shortlist_rate = round(progressed / total * 100, 1) if total else 0.0
    conversion = {
        "applied_to_review": _pct(stage_counts, "resume_review", total),
        "review_to_shortlist": _pct(stage_counts, "shortlisted", max(stage_counts.get("resume_review", 0), total)),
        "shortlist_to_interview": _pct(stage_counts, "interview", max(stage_counts.get("shortlisted", 0), 1)),
        "interview_to_offer": _pct(stage_counts, "offer", max(stage_counts.get("interview", 0), 1)),
        "offer_to_hired": _pct(stage_counts, "hired", max(stage_counts.get("offer", 0), 1)),
    }

    # Parsing success/failure.
    resume_total = db.scalar(
        select(func.count()).select_from(Resume).where(Resume.org_id == org_id)
    ) or 0
    resume_failed = db.scalar(
        select(func.count())
        .select_from(Resume)
        .where(Resume.org_id == org_id, Resume.status == "failed")
    ) or 0
    resume_ok = db.scalar(
        select(func.count())
        .select_from(Resume)
        .where(Resume.org_id == org_id, Resume.status == "completed")
    ) or 0
    parse_stats = {
        "total": resume_total,
        "completed": resume_ok,
        "failed": resume_failed,
        "success_rate": round(resume_ok / resume_total * 100, 1) if resume_total else 0.0,
    }

    # Time in each stage (mean days between consecutive stage changes).
    stage_durations = _stage_durations(db, org_id, [a.id for a in apps])

    # Skills frequently found or missing among applicants.
    found_counter: dict[str, int] = {}
    missing_counter: dict[str, int] = {}
    for a in apps:
        mr = db.scalar(
            select(MatchResult)
            .where(MatchResult.application_id == a.id)
            .order_by(MatchResult.created_at.desc())
        )
        if not mr:
            continue
        for s in (mr.matched or []):
            found_counter[s] = found_counter.get(s, 0) + 1
        for s in (mr.missing or []):
            missing_counter[s] = missing_counter.get(s, 0) + 1

    top_found = sorted(found_counter.items(), key=lambda x: -x[1])[:12]
    top_missing = sorted(missing_counter.items(), key=lambda x: -x[1])[:12]

    return {
        "totals": {
            "applications": total,
            "scored": len(scored),
            "avg_score": round(sum(a.match_score for a in scored) / len(scored), 1) if scored else None,
            "shortlist_rate": shortlist_rate,
        },
        "applications_by_job": by_job,
        "score_distribution": buckets,
        "stage_distribution": stage_counts,
        "conversion_rates": conversion,
        "parsing": parse_stats,
        "stage_durations_days": stage_durations,
        "skills_found": [{"skill": s, "count": c} for s, c in top_found],
        "skills_missing": [{"skill": s, "count": c} for s, c in top_missing],
        "note": (
            "Descriptive statistics only. Conversion rates describe what happened "
            "in this pipeline; they are not predictive estimates of hiring success."
        ),
    }


def _pct(counts: dict, key: str, denom: int) -> float:
    if denom <= 0:
        return 0.0
    return round(counts.get(key, 0) / denom * 100, 1)


def _stage_durations(db: Session, org_id: str, app_ids: list[str]) -> dict:
    if not app_ids:
        return {}
    rows = list(
        db.scalars(
            select(StageHistory)
            .where(StageHistory.application_id.in_(app_ids))
            .order_by(StageHistory.application_id, StageHistory.created_at)
        )
    )
    by_app: dict[str, list] = {}
    for r in rows:
        by_app.setdefault(r.application_id, []).append(r)
    durations: dict[str, list[float]] = {}
    for app_id, events in by_app.items():
        for i in range(len(events) - 1):
            delta = (events[i + 1].created_at - events[i].created_at).total_seconds() / 86400
            durations.setdefault(events[i].to_stage, []).append(delta)
    return {
        stage: round(sum(vals) / len(vals), 2) for stage, vals in durations.items() if vals
    }


def export_candidates_csv(db: Session, org_id: str, job_id: str | None = None) -> str:
    stmt = select(Application).where(Application.org_id == org_id)
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    apps = list(db.scalars(stmt.order_by(Application.match_score.desc())))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Candidate",
            "Email",
            "Job",
            "MatchScore",
            "RequiredCoverage",
            "Stage",
            "Status",
            "MatchedSkills",
            "MissingSkills",
            "AppliedAt",
        ]
    )
    for a in apps:
        cand = db.get(CandidateProfile, a.candidate_id)
        job = db.get(Job, a.job_id)
        mr = db.scalar(
            select(MatchResult)
            .where(MatchResult.application_id == a.id)
            .order_by(MatchResult.created_at.desc())
        )
        writer.writerow(
            [
                (cand.full_name if cand else "") or "",
                (cand.email if cand else "") or "",
                job.title if job else "",
                a.match_score if a.match_score is not None else "",
                (mr.breakdown.get("components", {}).get("required_skills", {}) if mr else {}).get("score", "")
                if mr
                else "",
                a.stage,
                a.status,
                "; ".join(mr.matched or []) if mr else "",
                "; ".join(mr.missing or []) if mr else "",
                a.applied_at.isoformat() if a.applied_at else "",
            ]
        )
    return buf.getvalue()
