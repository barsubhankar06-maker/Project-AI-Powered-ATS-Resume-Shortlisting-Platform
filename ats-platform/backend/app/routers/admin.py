"""Platform administration: organizations, users, audit logs, system health."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import Principal, require_admin
from ..models import (
    ROLE_ADMIN,
    ROLE_RECRUITER,
    Application,
    AuditLog,
    Job,
    Organization,
    OrganizationMembership,
    Resume,
    User,
)
from ..schemas import AdminUserUpdate, MembershipOut, OrganizationOut
from ..services import audit

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/organizations", response_model=list[OrganizationOut])
def organizations(p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if p.is_superadmin:
        return list(db.scalars(select(Organization)))
    org = db.get(Organization, p.org_id)
    return [org] if org else []


@router.get("/users")
def users(p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if p.is_superadmin:
        stmt = select(User)
    else:
        member_ids = [
            m.user_id
            for m in db.scalars(select(OrganizationMembership).where(OrganizationMembership.org_id == p.org_id))
        ]
        stmt = select(User).where(User.id.in_(member_ids))
    out = []
    for u in db.scalars(stmt.order_by(User.created_at.desc())):
        memberships = [
            MembershipOut(org_id=m.org_id, org_name=(db.get(Organization, m.org_id).name if db.get(Organization, m.org_id) else ""), role=m.role)
            for m in db.scalars(select(OrganizationMembership).where(OrganizationMembership.user_id == u.id))
        ]
        out.append(
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superadmin": u.is_superadmin,
                "created_at": u.created_at,
                "last_login_at": u.last_login_at,
                "memberships": [m.model_dump() for m in memberships],
            }
        )
    return out


@router.patch("/users/{user_id}")
def update_user(
    user_id: str, payload: AdminUserUpdate, p: Principal = Depends(require_admin), db: Session = Depends(get_db)
):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    # Org admins may only manage members of their own org, and never superadmins.
    if not p.is_superadmin:
        m = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id, OrganizationMembership.org_id == p.org_id
            )
        )
        if not m:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        if u.is_superadmin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot modify a platform administrator")
    if payload.is_active is not None:
        u.is_active = payload.is_active
    if payload.role:
        if payload.role not in (ROLE_RECRUITER, ROLE_ADMIN):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "role must be recruiter or admin")
        m = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id, OrganizationMembership.org_id == p.org_id
            )
        )
        if m:
            m.role = payload.role
    audit.record(db, org_id=p.org_id, actor_id=p.user.id, action="admin.user_updated", entity_type="user", entity_id=user_id)
    db.commit()
    return {"ok": True}


@router.get("/audit-logs")
def audit_logs(
    p: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
    action: str | None = None,
    limit: int = Query(default=100, le=500),
):
    stmt = select(AuditLog)
    if not p.is_superadmin:
        stmt = stmt.where(AuditLog.org_id == p.org_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    logs = list(db.scalars(stmt.order_by(AuditLog.created_at.desc()).limit(limit)))
    return [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "actor_id": l.actor_id,
            "org_id": l.org_id,
            "meta": l.meta,
            "at": l.created_at,
        }
        for l in logs
    ]


@router.get("/system-health")
def system_health(p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    """Processing failures and platform configuration status."""
    failed = db.scalar(
        select(func.count())
        .select_from(Resume)
        .where(Resume.status == "failed", *([] if p.is_superadmin else [Resume.org_id == p.org_id]))
    ) or 0
    processing = db.scalar(
        select(func.count())
        .select_from(Resume)
        .where(Resume.status.in_(["pending", "processing"]), *([] if p.is_superadmin else [Resume.org_id == p.org_id]))
    ) or 0
    total_resumes = db.scalar(
        select(func.count()).select_from(Resume).where(*([] if p.is_superadmin else [Resume.org_id == p.org_id]))
    ) or 0
    recent_failures = list(
        db.scalars(
            select(Resume)
            .where(Resume.status == "failed", *([] if p.is_superadmin else [Resume.org_id == p.org_id]))
            .order_by(Resume.updated_at.desc())
            .limit(10)
        )
    )
    return {
        "resumes_total": total_resumes,
        "resumes_failed": failed,
        "resumes_processing": processing,
        "recent_failures": [
            {"id": r.id, "filename": r.filename, "error": r.error, "at": r.updated_at} for r in recent_failures
        ],
        "config": {
            "database": "postgresql" if settings.database_url.startswith("postgres") else "sqlite",
            "storage_backend": settings.storage_backend,
            "llm_configured": settings.llm_configured,
            "llm_model": settings.llm_model if settings.llm_configured else None,
            "ocr_enabled": settings.ocr_enabled,
            "processing_mode": settings.processing_mode,
            "environment": settings.environment,
        },
        "counts": {
            "organizations": db.scalar(select(func.count()).select_from(Organization)) or 0,
            "users": db.scalar(select(func.count()).select_from(User)) or 0,
            "jobs": db.scalar(select(func.count()).select_from(Job).where(*([] if p.is_superadmin else [Job.org_id == p.org_id]))) or 0,
            "applications": db.scalar(select(func.count()).select_from(Application).where(*([] if p.is_superadmin else [Application.org_id == p.org_id]))) or 0,
        },
    }
