"""Recruitment analytics, reports and CSV export."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Principal, require_recruiter
from ..services import reports as reports_svc

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
def dashboard(p: Principal = Depends(require_recruiter), db: Session = Depends(get_db)):
    return reports_svc.dashboard_stats(db, p.org_id)


@router.get("/reports")
def reports(
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
    job_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    return reports_svc.reports(db, p.org_id, job_id, date_from, date_to)


@router.get("/export.csv", response_class=PlainTextResponse)
def export_csv(
    p: Principal = Depends(require_recruiter),
    db: Session = Depends(get_db),
    job_id: str | None = None,
):
    csv_text = reports_svc.export_candidates_csv(db, p.org_id, job_id)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=candidates.csv"},
    )
