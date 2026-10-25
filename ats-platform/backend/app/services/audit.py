"""Audit logging helper."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AuditLog


def record(
    db: Session,
    *,
    org_id: str | None,
    actor_id: str | None,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    meta: dict | None = None,
    ip: str = "",
) -> AuditLog:
    entry = AuditLog(
        org_id=org_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        meta=meta or {},
        ip=ip,
    )
    db.add(entry)
    db.flush()
    return entry
