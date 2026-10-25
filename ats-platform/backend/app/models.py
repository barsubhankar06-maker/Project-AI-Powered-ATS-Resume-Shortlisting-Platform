"""SQLAlchemy ORM models — the full relational schema.

Portable across SQLite and PostgreSQL. Identifiers are opaque UUID strings so
records cannot be enumerated by guessing sequential ids.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


# --- Role / stage vocabularies (kept as plain strings for portability) ---
ROLE_ADMIN = "admin"          # organization administrator
ROLE_RECRUITER = "recruiter"  # employer / hiring team member
ROLE_CANDIDATE = "candidate"  # job seeker
ROLE_SUPERADMIN = "superadmin"  # platform operator

STAGES = [
    "applied",
    "resume_review",
    "shortlisted",
    "interview",
    "assessment",
    "offer",
    "hired",
    "rejected",
]

RESUME_STATUSES = ["pending", "processing", "completed", "failed"]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    # Configurable default scoring weights for new jobs.
    default_weights: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "required_skills": 40,
            "experience": 25,
            "preferred_skills": 15,
            "projects": 10,
            "qualifications": 10,
        },
    )
    retention_days: Mapped[int] = mapped_column(Integer, default=365)

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OrganizationMembership(Base, TimestampMixin):
    """Links a user to an organization with a role. Source of truth for RBAC."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    org_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # recruiter | admin

    user: Mapped["User"] = relationship(back_populates="memberships")
    organization: Mapped["Organization"] = relationship(back_populates="memberships")


class CandidateProfile(Base, TimestampMixin):
    """A candidate belongs to one organization (data isolation boundary).

    A candidate may optionally be linked to a login user account.
    """

    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    # Nullable: a candidate account exists before it is attached to any org
    # (e.g. self-registered candidates who have not yet applied anywhere).
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    phone: Mapped[str] = mapped_column(String(60), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    headline: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    # Anonymized screening: when true, identity fields are hidden from scoring UI.
    anonymized: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=True)

    applications: Mapped[list["Application"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(200), default="")
    department: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    employment_type: Mapped[str] = mapped_column(String(50), default="full_time")
    experience_min: Mapped[float] = mapped_column(Float, default=0)
    experience_max: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[str] = mapped_column(Text, default="")
    min_qualifications: Mapped[str] = mapped_column(Text, default="")
    preferred_qualifications: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | closed | draft
    # Versioning: bumped whenever the description/requirements change so we can
    # tell whether a stored score used the latest version.
    version: Mapped[int] = mapped_column(Integer, default=1)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    hard_requirements: Mapped[list] = mapped_column(JSON, default=list)
    auto_exclude_below: Mapped[float | None] = mapped_column(Float)
    blind_screening: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobRequirement(Base, TimestampMixin):
    """Structured requirement extracted from (or added to) a job description."""

    __tablename__ = "job_requirements"
    __table_args__ = (Index("ix_jobreq_job_kind", "job_id", "kind"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    # required_skill | preferred_skill | responsibility | qualification |
    # certification | education | tool
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_skill: Mapped[str] = mapped_column(String(120), default="")
    is_hard: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | ai

    job: Mapped["Job"] = relationship(back_populates="requirements")


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(400), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error: Mapped[str] = mapped_column(Text, default="")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False)
    parser: Mapped[str] = mapped_column(String(50), default="")

    parsed: Mapped["ParsedResume | None"] = relationship(
        back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )


class ParsedResume(Base, TimestampMixin):
    __tablename__ = "parsed_resumes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    resume_id: Mapped[str] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, index=True
    )
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # structured fields
    confidence: Mapped[dict] = mapped_column(JSON, default=dict)  # per-field confidence
    uncertainties: Mapped[list] = mapped_column(JSON, default=list)
    parser: Mapped[str] = mapped_column(String(50), default="heuristic")
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    resume: Mapped["Resume"] = relationship(back_populates="parsed")


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),
        Index("ix_app_job_stage", "job_id", "stage"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    resume_id: Mapped[str | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"))
    stage: Mapped[str] = mapped_column(String(30), default="applied", index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")  # active | rejected | hired
    source: Mapped[str] = mapped_column(String(40), default="recruiter_upload")
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    match_score: Mapped[float | None] = mapped_column(Float, index=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    feedback_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    candidate_feedback: Mapped[str] = mapped_column(Text, default="")

    candidate: Mapped["CandidateProfile"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    match_results: Mapped[list["MatchResult"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    stage_history: Mapped[list["StageHistory"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    notes: Mapped[list["RecruiterNote"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    feedback: Mapped[list["InterviewFeedback"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class MatchResult(Base, TimestampMixin):
    """An explainable match result for one (resume version, job version) pair."""

    __tablename__ = "match_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[str | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"))
    resume_version: Mapped[int] = mapped_column(Integer, default=1)
    job_version: Mapped[int] = mapped_column(Integer, default=1)
    method: Mapped[str] = mapped_column(String(20), default="deterministic")  # ai | deterministic | hybrid
    total_score: Mapped[float] = mapped_column(Float, default=0)
    breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    matched: Mapped[list] = mapped_column(JSON, default=list)
    partial: Mapped[list] = mapped_column(JSON, default=list)
    missing: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    transferable: Mapped[list] = mapped_column(JSON, default=list)
    uncertainties: Mapped[list] = mapped_column(JSON, default=list)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")

    application: Mapped["Application"] = relationship(back_populates="match_results")


class StageHistory(Base, TimestampMixin):
    __tablename__ = "stage_history"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    from_stage: Mapped[str] = mapped_column(String(30), default="")
    to_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    note: Mapped[str] = mapped_column(Text, default="")

    application: Mapped["Application"] = relationship(back_populates="stage_history")


class RecruiterNote(Base, TimestampMixin):
    __tablename__ = "recruiter_notes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="notes")


class InterviewFeedback(Base, TimestampMixin):
    __tablename__ = "interview_feedback"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    stage: Mapped[str] = mapped_column(String(30), default="interview")
    rating: Mapped[int] = mapped_column(Integer, default=0)  # 0..5
    strengths: Mapped[str] = mapped_column(Text, default="")
    weaknesses: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    application: Mapped["Application"] = relationship(back_populates="feedback")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), default="")
    entity_id: Mapped[str] = mapped_column(String(32), default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(60), default="data_processing")
    granted: Mapped[bool] = mapped_column(Boolean, default=True)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DeletionRequest(Base):
    __tablename__ = "deletion_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | completed
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
