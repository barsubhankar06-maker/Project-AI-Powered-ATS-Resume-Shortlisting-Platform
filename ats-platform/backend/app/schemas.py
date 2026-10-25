"""Pydantic request/response schemas with validation."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# --------------------------------------------------------------------------
# Auth / users
# --------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    # recruiter -> creates an organization; candidate -> standalone account
    role: str = Field(default="recruiter")
    organization_name: str = Field(default="", max_length=200)

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        if v not in {"recruiter", "candidate"}:
            raise ValueError("role must be 'recruiter' or 'candidate'")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    is_active: bool
    is_superadmin: bool
    created_at: datetime


class MembershipOut(BaseModel):
    org_id: str
    org_name: str
    role: str


class MeResponse(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
    active_org_id: str | None = None
    active_role: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# --------------------------------------------------------------------------
# Jobs & requirements
# --------------------------------------------------------------------------


class RequirementIn(BaseModel):
    kind: str
    text: str
    normalized_skill: str = ""
    is_hard: bool = False
    source: str = "manual"


class RequirementOut(RequirementIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class JobBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company: str = ""
    department: str = ""
    location: str = ""
    employment_type: str = "full_time"
    experience_min: float = 0
    experience_max: float = 0
    description: str = ""
    responsibilities: str = ""
    min_qualifications: str = ""
    preferred_qualifications: str = ""
    status: str = "open"
    hard_requirements: list[str] = []
    auto_exclude_below: float | None = None
    blind_screening: bool = False
    feedback_enabled: bool = False


class JobCreate(JobBase):
    weights: dict | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    experience_min: float | None = None
    experience_max: float | None = None
    description: str | None = None
    responsibilities: str | None = None
    min_qualifications: str | None = None
    preferred_qualifications: str | None = None
    status: str | None = None
    weights: dict | None = None
    hard_requirements: list[str] | None = None
    auto_exclude_below: float | None = None
    blind_screening: bool | None = None
    feedback_enabled: bool | None = None


class JobOut(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    org_id: str
    version: int
    weights: dict
    created_at: datetime
    updated_at: datetime


class JobDetail(JobOut):
    requirements: list[RequirementOut] = []


class AnalyzeJdRequest(BaseModel):
    description: str = Field(min_length=1)
    title: str = ""


class AnalyzeJdResponse(BaseModel):
    requirements: list[RequirementIn]
    suggested: dict
    method: str  # ai | heuristic


# --------------------------------------------------------------------------
# Candidates / resumes / applications
# --------------------------------------------------------------------------


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str
    email: str
    phone: str
    location: str
    headline: str
    summary: str
    anonymized: bool
    created_at: datetime


class CandidateUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    anonymized: bool | None = None


class ParsedResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    data: dict
    confidence: dict
    uncertainties: list
    parser: str
    manually_edited: bool


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    candidate_id: str | None
    filename: str
    mime_type: str
    size_bytes: int
    version: int
    is_current: bool
    status: str
    error: str
    ocr_used: bool
    created_at: datetime


class ResumeDetail(ResumeOut):
    parsed: ParsedResumeOut | None = None


class ParsedResumeUpdate(BaseModel):
    data: dict


class MatchResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    method: str
    total_score: float
    breakdown: dict
    matched: list
    partial: list
    missing: list
    evidence: list
    transferable: list
    uncertainties: list
    resume_version: int
    job_version: int
    is_stale: bool
    created_at: datetime


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_id: str
    candidate_id: str
    resume_id: str | None
    stage: str
    status: str
    match_score: float | None
    applied_at: datetime
    feedback_enabled: bool
    candidate_feedback: str


class ApplicationDetail(ApplicationOut):
    candidate: CandidateOut
    job: JobOut
    latest_match: MatchResultOut | None = None


class CandidateRow(BaseModel):
    """A row in the ranked candidate table for a job."""

    application_id: str
    candidate_id: str
    display_name: str
    email: str
    resume_filename: str | None
    match_score: float | None
    required_coverage: float | None
    experience_summary: str
    missing: list
    applied_at: datetime
    stage: str
    status: str
    parsing_status: str
    method: str | None
    is_stale: bool


class StageChangeRequest(BaseModel):
    stage: str
    note: str = ""

    @field_validator("stage")
    @classmethod
    def _stage(cls, v: str) -> str:
        from .models import STAGES

        if v not in STAGES:
            raise ValueError(f"stage must be one of {STAGES}")
        return v


class BulkActionRequest(BaseModel):
    application_ids: list[str] = Field(min_length=1)
    action: str  # shortlist | review | reject | export
    note: str = ""


class NoteCreate(BaseModel):
    body: str = Field(min_length=1)


class FeedbackCreate(BaseModel):
    stage: str = "interview"
    rating: int = Field(default=0, ge=0, le=5)
    strengths: str = ""
    weaknesses: str = ""
    notes: str = ""


class ApplyRequest(BaseModel):
    job_id: str
    cover_letter: str = ""


# --------------------------------------------------------------------------
# Admin / analytics
# --------------------------------------------------------------------------


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str
    is_demo: bool
    retention_days: int
    created_at: datetime


class AdminUserOut(UserOut):
    memberships: list[MembershipOut] = []


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = None


TokenResponse.model_rebuild()
