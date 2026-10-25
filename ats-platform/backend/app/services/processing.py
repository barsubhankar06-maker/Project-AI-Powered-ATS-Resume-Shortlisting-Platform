"""Background processing: resume parsing + matching orchestration.

A resume is processed in two steps: (1) extract text and parse structured
fields, (2) match it against every job it has been applied to and store an
explainable MatchResult. Bulk uploads run through a small in-process worker
pool; for production swap PROCESSING_MODE to use Celery/RQ (the function
`process_resume` is the unit of work either way).
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models import (
    Application,
    Job,
    JobRequirement,
    MatchResult,
    ParsedResume,
    Resume,
)
from . import matching, resume_parser, storage, text_extract

log = logging.getLogger("ats.processing")

_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max(1, settings.worker_threads))
    return _executor


def enqueue_resume(resume_id: str) -> None:
    if settings.processing_mode == "inline":
        process_resume(resume_id)
    else:
        _get_executor().submit(process_resume, resume_id)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def process_resume(resume_id: str) -> None:
    db = SessionLocal()
    try:
        resume = db.get(Resume, resume_id)
        if not resume:
            return
        resume.status = "processing"
        resume.error = ""
        db.commit()

        try:
            data = storage.read_bytes(resume.storage_key)
        except Exception as exc:  # noqa: BLE001
            _fail(db, resume, f"Stored file could not be read: {exc}")
            return

        extracted = text_extract.extract_text(resume.filename, resume.mime_type, data)
        if not extracted.ok or not extracted.text.strip():
            _fail(db, resume, extracted.error or "No text could be extracted from this file")
            resume.ocr_used = extracted.ocr_used
            db.commit()
            return

        resume.extracted_text = extracted.text
        resume.ocr_used = extracted.ocr_used

        parsed = resume_parser.parse_resume(extracted.text)
        parsed.data["_uncertainties"] = parsed.uncertainties
        existing = db.scalar(select(ParsedResume).where(ParsedResume.resume_id == resume.id))
        if existing and existing.manually_edited:
            # Do not clobber recruiter corrections on re-parse unless forced.
            parsed.data = {**parsed.data, **existing.data}
            existing.confidence = parsed.confidence
            existing.parser = parsed.parser
            existing.uncertainties = parsed.uncertainties
        elif existing:
            existing.data = parsed.data
            existing.confidence = parsed.confidence
            existing.uncertainties = parsed.uncertainties
            existing.parser = parsed.parser
        else:
            db.add(
                ParsedResume(
                    resume_id=resume.id,
                    data=parsed.data,
                    confidence=parsed.confidence,
                    uncertainties=parsed.uncertainties,
                    parser=parsed.parser,
                )
            )

        # Backfill candidate identity fields when empty.
        if resume.candidate_id:
            from ..models import CandidateProfile

            cand = db.get(CandidateProfile, resume.candidate_id)
            if cand:
                cand.full_name = cand.full_name or (parsed.data.get("name") or "")
                cand.email = cand.email or (parsed.data.get("email") or "")
                cand.phone = cand.phone or (parsed.data.get("phone") or "")
                cand.location = cand.location or (parsed.data.get("location") or "")
                cand.summary = cand.summary or (parsed.data.get("summary") or "")

        resume.status = "completed"
        resume.parser = parsed.parser
        db.commit()

        # Re-match every application that references this resume.
        apps = list(db.scalars(select(Application).where(Application.resume_id == resume.id)))
        for app in apps:
            try:
                match_application(db, app.id)
            except Exception as exc:  # noqa: BLE001
                log.warning("matching failed for application %s: %s", app.id, exc)
        db.commit()
    finally:
        db.close()


def _fail(db: Session, resume: Resume, message: str) -> None:
    resume.status = "failed"
    resume.error = message[:500]
    db.commit()


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


def match_application(db: Session, application_id: str, use_llm: bool | None = None) -> MatchResult | None:
    app = db.get(Application, application_id)
    if not app:
        return None
    job = db.get(Job, app.job_id)
    if not job:
        return None

    resume_data: dict = {}
    resume = db.get(Resume, app.resume_id) if app.resume_id else None
    if resume:
        parsed = db.scalar(select(ParsedResume).where(ParsedResume.resume_id == resume.id))
        if parsed:
            resume_data = dict(parsed.data)
            resume_data["_uncertainties"] = parsed.uncertainties or []

    reqs = list(db.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id)))
    requirements = [
        {"kind": r.kind, "text": r.text, "normalized_skill": r.normalized_skill} for r in reqs
    ]
    job_dict = {
        "description": job.description,
        "responsibilities": job.responsibilities,
        "experience_min": job.experience_min,
        "experience_max": job.experience_max,
    }

    outcome = matching.match_resume_to_job(
        resume_data=resume_data,
        requirements=requirements,
        job=job_dict,
        weights=job.weights or None,
        use_llm=use_llm,
    )

    # Supersede prior results for this application (keep history, mark stale).
    for old in db.scalars(select(MatchResult).where(MatchResult.application_id == app.id)):
        old.is_stale = True

    result = MatchResult(
        application_id=app.id,
        job_id=job.id,
        resume_id=app.resume_id,
        resume_version=resume.version if resume else 1,
        job_version=job.version,
        method=outcome.method,
        total_score=outcome.total_score,
        breakdown=outcome.breakdown,
        matched=outcome.matched,
        partial=outcome.partial,
        missing=outcome.missing,
        evidence=outcome.evidence,
        transferable=outcome.transferable,
        uncertainties=outcome.uncertainties,
    )
    db.add(result)
    app.match_score = outcome.total_score
    db.flush()
    return result
