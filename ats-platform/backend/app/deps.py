"""FastAPI dependencies: authentication, org scoping and role-based access.

Permissions are enforced here, on the server, not merely hidden in the UI.
Every org-scoped route resolves the caller's membership and filters queries by
org_id, so one organization can never read another's records.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import (
    ROLE_ADMIN,
    ROLE_CANDIDATE,
    ROLE_RECRUITER,
    ROLE_SUPERADMIN,
    OrganizationMembership,
    User,
)
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user: User
    org_id: str | None
    role: str | None  # recruiter | admin | candidate | superadmin

    @property
    def is_admin(self) -> bool:
        return self.role in (ROLE_ADMIN, ROLE_SUPERADMIN) or self.user.is_superadmin

    @property
    def is_recruiter(self) -> bool:
        return self.role in (ROLE_RECRUITER, ROLE_ADMIN, ROLE_SUPERADMIN) or self.user.is_superadmin

    @property
    def is_candidate(self) -> bool:
        return self.role == ROLE_CANDIDATE

    @property
    def is_superadmin(self) -> bool:
        return self.user.is_superadmin or self.role == ROLE_SUPERADMIN


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    data = decode_token(creds.credentials)
    if not data or not data.get("sub"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, data["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def get_principal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> Principal:
    """Resolve the caller's active organization + role.

    The active org is taken from the X-Org-Id header when the user is a member
    of it, otherwise the user's first membership. Candidates have no membership
    and therefore no org scope.
    """
    memberships = list(
        db.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id
            )
        )
    )
    if user.is_superadmin:
        if x_org_id and any(m.org_id == x_org_id for m in memberships):
            m = next(m for m in memberships if m.org_id == x_org_id)
            return Principal(user=user, org_id=m.org_id, role=ROLE_SUPERADMIN)
        if x_org_id:
            return Principal(user=user, org_id=x_org_id, role=ROLE_SUPERADMIN)
        if memberships:
            return Principal(user=user, org_id=memberships[0].org_id, role=ROLE_SUPERADMIN)
        return Principal(user=user, org_id=None, role=ROLE_SUPERADMIN)

    if x_org_id:
        m = next((m for m in memberships if m.org_id == x_org_id), None)
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of that organization")
        return Principal(user=user, org_id=m.org_id, role=m.role)

    if memberships:
        return Principal(user=user, org_id=memberships[0].org_id, role=memberships[0].role)

    # No membership -> candidate (or an unaffiliated user).
    return Principal(user=user, org_id=None, role=ROLE_CANDIDATE)


def require_recruiter(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_recruiter or not p.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Recruiter access required")
    return p


def require_admin(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required")
    return p


def require_superadmin(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform administrator access required")
    return p


def require_candidate(p: Principal = Depends(get_principal)) -> Principal:
    if not p.is_candidate:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Candidate access required")
    return p
