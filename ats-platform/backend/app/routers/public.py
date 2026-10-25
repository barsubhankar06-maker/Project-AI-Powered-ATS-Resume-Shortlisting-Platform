"""Public, unauthenticated endpoints for the marketing site and careers page.

Only non-sensitive fields are exposed. No candidate data is ever public.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Application, Job, Organization, Resume

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/config")
def public_config():
    """Feature flags the frontend uses to label the matching method."""
    return {
        "app_name": settings.app_name,
        "ai_configured": settings.llm_configured,
        "ai_model": settings.llm_model if settings.llm_configured else None,
        "ocr_enabled": settings.ocr_enabled,
        "storage_backend": settings.storage_backend,
        "environment": settings.environment,
        "scoring_weights": {
            "required_skills": 40,
            "experience": 25,
            "preferred_skills": 15,
            "projects": 10,
            "qualifications": 10,
        },
    }


@router.get("/stats")
def public_stats(db: Session = Depends(get_db)):
    """Live platform counters (computed from the database, not hardcoded)."""
    return {
        "jobs": db.scalar(select(func.count()).select_from(Job).where(Job.status == "open")) or 0,
        "resumes_processed": db.scalar(
            select(func.count()).select_from(Resume).where(Resume.status == "completed")
        ) or 0,
        "applications": db.scalar(select(func.count()).select_from(Application)) or 0,
        "organizations": db.scalar(select(func.count()).select_from(Organization)) or 0,
    }


@router.get("/jobs")
def public_jobs(db: Session = Depends(get_db)):
    """Open roles for the public careers page."""
    jobs = list(db.scalars(select(Job).where(Job.status == "open").order_by(Job.created_at.desc()).limit(100)))
    out = []
    for j in jobs:
        org = db.get(Organization, j.org_id)
        out.append(
            {
                "id": j.id,
                "title": j.title,
                "company": j.company or (org.name if org else ""),
                "department": j.department,
                "location": j.location,
                "employment_type": j.employment_type,
                "experience_min": j.experience_min,
                "experience_max": j.experience_max,
                "description": j.description[:1500],
                "created_at": j.created_at,
            }
        )
    return out
