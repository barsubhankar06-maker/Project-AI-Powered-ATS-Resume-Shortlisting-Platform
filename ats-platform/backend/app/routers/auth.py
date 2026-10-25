"""Authentication: registration, login, current user, password change."""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import Principal, get_current_user, get_principal
from ..models import (
    ROLE_ADMIN,
    ROLE_CANDIDATE,
    CandidateProfile,
    Organization,
    OrganizationMembership,
    User,
    utcnow,
)
from ..schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
    MembershipOut,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from ..security import create_access_token, hash_password, verify_password
from ..services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "org").lower()).strip("-")
    return (s or "org")[:60]


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        last_login_at=utcnow(),
    )
    db.add(user)
    db.flush()

    if payload.role == "recruiter":
        org_name = payload.organization_name.strip() or f"{payload.full_name.split()[0]}'s Company"
        slug = _slugify(org_name)
        # Ensure slug uniqueness.
        base, i = slug, 1
        while db.scalar(select(Organization).where(Organization.slug == slug)):
            i += 1
            slug = f"{base}-{i}"
        org = Organization(name=org_name, slug=slug)
        db.add(org)
        db.flush()
        # The founder is the organization administrator (also acts as recruiter).
        db.add(OrganizationMembership(user_id=user.id, org_id=org.id, role=ROLE_ADMIN))
        audit.record(
            db,
            org_id=org.id,
            actor_id=user.id,
            action="org.created",
            entity_type="organization",
            entity_id=org.id,
            ip=request.client.host if request.client else "",
        )
    else:
        # Candidate account: create a candidate profile within a shared demo-less pool.
        db.add(
            CandidateProfile(
                org_id=None,  # assigned when they apply / when an org imports them
                user_id=user.id,
                full_name=payload.full_name.strip(),
                email=payload.email.lower(),
            )
        )

    audit.record(
        db,
        org_id=None,
        actor_id=user.id,
        action="user.registered",
        entity_type="user",
        entity_id=user.id,
        ip=request.client.host if request.client else "",
    )
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.hashed_password):
        # Same message for both cases to avoid account enumeration.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")
    user.last_login_at = utcnow()
    audit.record(
        db,
        org_id=None,
        actor_id=user.id,
        action="user.login",
        entity_type="user",
        entity_id=user.id,
        ip=request.client.host if request.client else "",
    )
    db.commit()
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=MeResponse)
def me(p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    memberships = []
    for m in db.scalars(
        select(OrganizationMembership).where(OrganizationMembership.user_id == p.user.id)
    ):
        org = db.get(Organization, m.org_id)
        memberships.append(
            MembershipOut(org_id=m.org_id, org_name=org.name if org else "", role=m.role)
        )
    return MeResponse(
        user=UserOut.model_validate(p.user),
        memberships=memberships,
        active_org_id=p.org_id,
        active_role=p.role,
    )


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
