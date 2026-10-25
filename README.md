TalentLens — AI-Powered ATS & Resume Shortlisting Platform
A production-oriented applicant-tracking system that parses resumes, matches them against job requirements, and produces an explainable match score recruiters can defend. AI is decision support — the platform never auto-rejects a candidate on a score alone.

Built as a real, runnable full-stack app: a FastAPI backend, a SQLAlchemy schema with Alembic migrations, and a React + TypeScript + Tailwind single-page frontend that the API serves in production.

Table of contents
What it does
Architecture
Tech stack
Quick start (5 minutes)
Environment variables
Database setup & migrations
Demo accounts & data
The matching engine
API reference
Testing
Deployment
Security, privacy & fairness
What is intentionally left unconfigured
Project layout
What it does
Recruiters create jobs, upload job descriptions (with AI-assisted requirement extraction), bulk-upload PDF/DOCX resumes, review explainable match scores, rank/filter/shortlist candidates, move them through a hiring pipeline, and export reports.
Candidates register, apply to open roles with a resume, track application status, edit their profile and request data deletion.
Administrators manage users and roles, monitor processing failures and platform configuration, and review audit logs.
All dashboard and report figures are computed live from the database — nothing is hardcoded. Demo data lives in its own clearly-labelled organization and is never mixed with real records.

Architecture
┌────────────────────────────┐        ┌─────────────────────────────────────┐
│  React + TypeScript SPA    │  HTTP  │  FastAPI backend (app/)             │
│  (Vite + Tailwind)         │ ─────► │                                     │
│  • marketing pages         │  /api  │  routers/  auth jobs resumes ...    │
│  • recruiter dashboard     │ ◄───── │  deps.py   authn + RBAC + org scope │
│  • candidate dashboard     │  JSON  │  services/ parsing · matching · AI  │
│  • admin console           │        │  models.py SQLAlchemy schema        │
└────────────────────────────┘        └───────────────┬─────────────────────┘
                                                      │
                        ┌─────────────────────────────┼───────────────────────────┐
                        │                             │                           │
                 ┌──────▼──────┐            ┌─────────▼─────────┐       ┌─────────▼─────────┐
                 │  Database   │            │  Private storage  │       │  LLM provider     │
                 │ SQLite /    │            │ local disk / S3   │       │ OpenAI-compatible │
                 │ PostgreSQL  │            │ signed URLs only  │       │ (optional)        │
                 └─────────────┘            └───────────────────┘       └───────────────────┘
Request flow for screening: recruiter uploads resumes → each file is validated (extension + magic bytes), hashed for duplicate detection, stored privately, and queued → a worker extracts text (PDF/DOCX, optional OCR) and parses it into structured fields → the resume is matched against every job it was applied to → an explainable MatchResult is stored and the candidate's score updated → the recruiter reviews the breakdown and makes the call.

The AI logic is fully separated into reusable services (resume_parser, job_parser, skill_normalization, matching, reports, llm), each usable independently and each degrading gracefully when no AI provider is configured.

Tech stack
Layer	Choice
Frontend	React 18 + TypeScript, Vite, Tailwind CSS, Recharts, React Router
Backend	Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0
Database	SQLite (default, zero-config) — PostgreSQL / Supabase ready
Migrations	Alembic
Auth	JWT (python-jose) + bcrypt, server-enforced role-based access
Parsing	pypdf (PDF), python-docx (DOCX), optional Tesseract OCR
AI	OpenAI-compatible chat completions, optional, server-side only
Storage	Private local disk (default) or S3 interface
Charts	Recharts
Tests	pytest + FastAPI TestClient
Quick start (5 minutes)
1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate     # optional
pip install -r requirements.txt

cp ../.env.example ../.env                            # then edit if needed
export DATABASE_URL="sqlite:///./ats.db"              # or just rely on .env

uvicorn app.main:app --reload --port 8000
The API is now at http://localhost:8000 (docs at /docs). On first start it creates the schema and seeds clearly-labelled demo data.

2. Frontend (dev)
cd frontend
npm install
npm run dev            # http://localhost:5173, proxies /api to :8000
3. Or run the built app served by the API (single origin)
cd frontend && npm install && npm run build            # emits frontend/dist
cd ../backend && uvicorn app.main:app --port 8000      # serves the SPA too
# open http://localhost:8000
Note on constrained environments: if npm run build fails with an out-of-memory error from esbuild, raise the virtual-memory limit first: bash -c 'ulimit -v unlimited; npm run build'.

There is a Makefile at the repo root with shortcuts: make install, make dev-api, make dev-web, make build, make test, make migrate.

Environment variables
All configuration is read from the environment (or a .env file). See .env.example for the full annotated list. Key ones:

Variable	Default	Notes
SECRET_KEY	dev placeholder	Change in production. Signs JWTs and download tokens.
DATABASE_URL	sqlite:///./ats.db	Use postgresql+psycopg2://… for Postgres/Supabase.
BACKEND_CORS_ORIGINS	http://localhost:5173	Comma-separated allowed origins.
STORAGE_BACKEND	local	local or s3.
STORAGE_DIR	./storage	Private directory for uploaded files.
MAX_UPLOAD_MB	10	Per-file size limit.
LLM_ENABLED / LLM_API_KEY	false / empty	Enables optional AI enrichment.
LLM_BASE_URL / LLM_MODEL	OpenAI / gpt-4o-mini	Any OpenAI-compatible endpoint.
OCR_ENABLED	false	Needs the tesseract binary installed.
PROCESSING_MODE	background	inline processes synchronously (used by tests).
RESUME_RETENTION_DAYS	365	Configurable retention window.
Secrets live only on the server. The frontend never receives an API key and talks exclusively to our own /api.

Database setup & migrations
SQLite works out of the box. For PostgreSQL/Supabase:

export DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/ats"
cd backend
alembic upgrade head          # apply the schema
# alembic revision --autogenerate -m "your change"   # after model edits
Base.metadata.create_all() also runs on startup for frictionless local dev. For production, prefer migrations and set ENVIRONMENT=production (which also disables demo seeding).

The schema (17 tables) covers organizations, users, memberships, jobs, job requirements, candidate profiles, resumes, parsed resume data, applications, match results, stage history, recruiter notes, interview feedback, audit logs, consent records and deletion requests — with foreign keys, indexes, unique constraints and timestamps.

Demo accounts & data
Seeded automatically in non-production environments (all fictional):

Role	Email	Password
Recruiter	recruiter@demo.com	demo12345
Admin	admin@demo.com	admin12345
Superadmin	superadmin@platform.local	superadmin12345
Three demo jobs (Senior Backend Engineer, Machine Learning Engineer, Ceramic Process Engineer) and six fictional candidate resumes are parsed and scored on first run. Everything lives in the Demo Corp organization (is_demo = true).

The matching engine
Each resume is compared to a job across five weighted components. Weights are configurable per job and validated to total 100%:

Component	Default	What it measures
Required skills	40	Required skills matched against parsed resume skills (transferable credit).
Experience & responsibilities	25	Semantic overlap of responsibilities + an experience-duration fit check.
Preferred skills	15	Nice-to-have skills.
Projects & achievements	10	Relevant project/achievement evidence.
Qualifications & certifications	10	Education and certifications vs stated requirements.
For every candidate the engine returns matched, partial/transferable, missing/unverified requirements, supporting evidence lines and parsing uncertainties. A missing field is marked unknown, never treated as a capability gap. Protected attributes (name, photo, gender, age, ethnicity, religion, disability) and age proxies like graduation dates are never read.

A deterministic engine always runs offline. When an OpenAI-compatible provider is configured, an LLM refines responsibility coverage and flags transferable skills; each result is labelled deterministic or hybrid. If the provider times out, rate-limits or returns invalid JSON, the deterministic result is used and labelled accordingly.

API reference
All routes are under /api. Authenticated routes take a Bearer token; org scoping uses an optional X-Org-Id header (defaults to the caller's first membership).

Auth — POST /auth/register, POST /auth/login, GET /auth/me, POST /auth/change-password

Public — GET /public/config, GET /public/stats, GET /public/jobs

Jobs — GET|POST /jobs, GET|PATCH|DELETE /jobs/{id}, POST /jobs/analyze-jd, GET|POST /jobs/{id}/requirements, GET /jobs/{id}/candidates (filter/sort/paginate), POST /jobs/{id}/bulk

Resumes — POST /resumes/upload (multi-file), GET /resumes, GET /resumes/{id}, PATCH /resumes/{id}/parsed, POST /resumes/{id}/reprocess, GET /resumes/{id}/download-url, GET /resumes/file/{token}, DELETE /resumes/{id}

Candidates — GET /candidates, GET /candidates/{id}, PATCH /candidates/{id}, POST /candidates/applications/{id}/rematch, GET /candidates/applications/{id}/parsed

Applications & pipeline — GET /applications, GET /applications/{id}, POST /applications/{id}/stage, GET /applications/{id}/timeline, GET|POST /applications/{id}/notes, GET|POST /applications/{id}/feedback, GET /applications/pipeline/{job_id}

Analytics — GET /analytics/dashboard, GET /analytics/reports, GET /analytics/export.csv

Admin — GET /admin/organizations, GET /admin/users, PATCH /admin/users/{id}, GET /admin/audit-logs, GET /admin/system-health

Candidate self-service — GET|PATCH /me/profile, GET /me/applications, POST /me/apply, POST /me/delete-request

Interactive docs are available at /docs when the server is running.

Testing
cd backend
python -m pytest            # 56 tests
Coverage includes: authentication and password handling; role permissions and cross-organization isolation; resume upload, text extraction and parsing; score calculations and weight validation; ranking and filtering; pipeline stage changes and history; private file access and signed URLs; and edge cases (empty/oversized/masquerading files, duplicates, scanned PDFs, malformed DOCX, prompt-injection text, and AI-provider failure fallback).

Tests run against an isolated temporary SQLite database with synchronous processing and demo seeding disabled.

Deployment
A Dockerfile and docker-compose.yml (app + PostgreSQL) are included:

docker compose up --build       # API + Postgres
# then visit http://localhost:8000
Production checklist:

Set a strong SECRET_KEY and ENVIRONMENT=production.
Point DATABASE_URL at managed PostgreSQL/Supabase and run alembic upgrade head.
Set STORAGE_BACKEND=s3 with private bucket credentials (or mount a private volume).
Terminate TLS at a reverse proxy; the app already sends security headers.
Move rate limiting to a shared store (e.g. Redis) if running multiple replicas.
Replace the in-process worker with Celery/RQ for large bulk uploads.
Security, privacy & fairness
JWT auth with bcrypt password hashing; identical error messages avoid account enumeration.
Server-side permission checks on every route; every query is scoped to the caller's organization.
File type + magic-byte validation, size limits, SHA-256 duplicate detection.
Private storage with short-lived signed URLs; originals are never public.
Rate limiting on auth endpoints, input validation, and safe error handling that never leaks internals.
Audit logging of logins, uploads, stage changes and admin actions.
Resume retention is configurable; candidates can request deletion.
Protected attributes are excluded from scoring; optional blind screening; graduation dates are never used to infer age; no personality/culture-fit inference.
Uploaded documents are treated as untrusted data — embedded instructions are ignored (and flagged).
Fairness note: these practices reduce risk but do not guarantee unbiased outcomes. Score explanations are decision support, not proof of fairness. Always keep a human in the loop for consequential decisions.

What is intentionally left unconfigured
The platform runs fully end-to-end today. The following are integration points that require credentials or infrastructure you may not have here:

Area	Status
LLM provider	Off by default. Set LLM_ENABLED=true + LLM_API_KEY. Deterministic engine runs otherwise.
OCR	Off. Needs the tesseract binary; scanned PDFs otherwise report a clear "no text layer" error.
Cloud storage	S3 code path is present but needs AWS_* credentials; local private disk is the default.
PostgreSQL	SQLite by default; set DATABASE_URL and run migrations to use Postgres/Supabase.
Billing	Pricing page plans are clearly-marked samples; no payment processor is wired.
Contact form	Validates client-side only; not persisted.
Project layout
ats-platform/
├── .env.example
├── README.md
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/            # migrations (env.py, versions/)
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py         # FastAPI app, CORS, rate limit, static SPA
│   │   ├── config.py       # settings from env
│   │   ├── database.py     # engine + session
│   │   ├── models.py       # SQLAlchemy schema (17 tables)
│   │   ├── schemas.py      # Pydantic request/response models
│   │   ├── security.py     # bcrypt + JWT + signed tokens
│   │   ├── deps.py         # authn, RBAC, org scoping
│   │   ├── seed.py         # labelled demo data
│   │   ├── routers/        # auth, jobs, resumes, candidates, applications,
│   │   │                   # analytics, admin, public, candidate_self
│   │   └── services/       # llm, skill_normalization, text_extract,
│   │                       # resume_parser, job_parser, matching, processing,
│   │                       # reports, storage, audit
│   └── tests/              # 56 tests across 9 modules
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── App.tsx         # routes
        ├── lib/            # api client, auth context
        ├── components/     # layout, UI kit, tables, uploaders
        └── pages/          # marketing, auth, recruiter, candidate, admin
TalentLens is a demonstration build. Sample plans and seeded data are fictional; review the legal templates with counsel before any production use.
