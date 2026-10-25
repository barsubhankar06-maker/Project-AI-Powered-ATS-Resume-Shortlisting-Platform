<div align="center">

🔎 TalentLens
AI-Powered Applicant Tracking & Resume Intelligence
Turn resumes into explainable hiring insights — while keeping humans in control.

TalentLens is a full-stack applicant-tracking platform that helps recruiters analyze resumes, compare candidates against job requirements, manage hiring pipelines, and generate reports. Candidates can apply for roles and track their applications, while administrators oversee users, organizations, and audit activity.
<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React 18" />
  <img src="https://img.shields.io/badge/TypeScript-Frontend-3178C6?logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/License-Add%20your%20license-lightgrey" alt="License placeholder" />
</p>


Explainable matching · Role-based access · Candidate self-service · Human-led decisions
</div>

✨ Why TalentLens?
Hiring teams often need to review many resumes against changing job requirements. TalentLens streamlines that workflow and makes the reasons behind a match score visible.
- 🎯 Explainable candidate matching — see matched, partially matched, missing, and unverified requirements.
- 📄 Resume parsing — extract structured information from PDF and DOCX files.
- 🧠 AI-assisted job analysis — optionally use an OpenAI-compatible LLM to enrich job and resume analysis.
- 🧑‍💼 Recruiter workspace — rank, filter, shortlist, and move candidates through hiring stages.
- 👤 Candidate portal — apply for roles, update profile details, and track application status.
- 📊 Live analytics and exports — view database-driven dashboard metrics and export reports to CSV.
- 🛡️ Privacy-conscious design — private file storage, organization-scoped access, audit logs, and candidate deletion requests.
- 🤝 Human-in-the-loop hiring — a score supports a decision; it does not automatically reject a candidate.
Responsible AI principle: TalentLens is designed to support hiring decisions, not make consequential decisions on a recruiter's behalf. Fairness safeguards reduce risk, but do not guarantee unbiased outcomes.

🧭 Table of Contents
- Core Features
- How It Works
- Architecture
- Technology Stack
- Quick Start
- Environment Configuration
- Database and Migrations
- Demo Accounts
- Matching Methodology
- API Overview
- Testing
- Docker Deployment
- Security, Privacy & Fairness
- Configuration Notes
- Project Structure
🚀 Core Features
For Recruiters
- Create and manage job openings.
- Upload job descriptions and extract requirements with optional AI assistance.
- Bulk-upload PDF and DOCX resumes.
- Review candidate match scores with supporting evidence and uncertainty indicators.
- Search, sort, filter, rank, and shortlist candidates.
- Track application stages, notes, interview feedback, and stage history.
- View analytics dashboards and export CSV reports.
For Candidates
- Register and manage a profile.
- Browse available jobs and submit applications with a resume.
- Track application status.
- Request deletion of personal data.
For Administrators
- Manage users, roles, and organizations.
- Review audit logs and system health.
- Monitor processing and configuration issues.
🔄 How It Works
1. Create a job — add a role and define required and preferred qualifications.
2. Upload resumes — files are validated, hashed for duplicate detection, and stored privately.
3. Extract information — the processing pipeline extracts text and parses relevant resume fields.
4. Calculate a match — the engine compares resume evidence with the job requirements.
5. Review the explanation — recruiters see matched, partial/transferable, missing, or unverified requirements.
6. Manage the hiring process — update stages, record feedback, and review analytics.
🏗️ Architecture
┌──────────────────────────────────┐
│       React + TypeScript         │
│       Vite + Tailwind CSS        │
│ Recruiter · Candidate · Admin UI │
└─────────────────┬────────────────┘
                  │ HTTP / JSON
┌─────────────────▼────────────────┐
│           FastAPI API            │
│ Auth · Jobs · Resumes · Reports  │
│ Candidates · Applications · Admin│
└───────┬──────────────┬───────────┘
        │              │
┌───────▼────────┐ ┌───▼────────────────┐
│ SQLite /       │ │ Processing Services │
│ PostgreSQL     │ │ Parsing · Matching  │
└────────────────┘ │ Optional LLM · OCR  │
                   └─────────┬──────────┘
                             │
                   ┌─────────▼──────────┐
                   │ Private File Storage│
                   │ Local disk / S3     │
                   └────────────────────┘
The AI-related logic is separated into reusable services for parsing, skill normalization, matching, reports, storage, and LLM integration. The deterministic matching engine works without an external AI provider; optional LLM functionality can enrich selected parts of the analysis.
🧰 Technology Stack
Layer	Technologies
Frontend	React 18, TypeScript, Vite, Tailwind CSS, React Router, Recharts
Backend	Python 3.12, FastAPI, Pydantic v2
Database	SQLite by default; PostgreSQL/Supabase-compatible configuration
ORM & migrations	SQLAlchemy 2.0, Alembic
Authentication	JWT, python-jose, bcrypt, role-based access control
Resume parsing	pypdf, python-docx, optional Tesseract OCR
AI integration	Optional OpenAI-compatible chat completions API
Storage	Private local storage by default; S3 interface
Testing	pytest, FastAPI TestClient
Deployment	Docker, Docker Compose


⚡ Quick Start
Prerequisites
- Python 3.12
- Node.js and npm
- Git
1. Clone the repository
git clone <YOUR_REPOSITORY_URL>
cd ats-platform
Replace <YOUR_REPOSITORY_URL> with your repository URL.
2. Set up the backend
cd backend
python -m venv .venv
Activate the virtual environment:
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
Install dependencies and configure the environment:
pip install -r requirements.txt
cp ../.env.example ../.env
On Windows, copy .env.example to ..\.env manually if cp is unavailable.

Start the API:
uvicorn app.main:app --reload --port 8000
The API runs at http://localhost:8000. Interactive API documentation is available at http://localhost:8000/docs.
3. Start the frontend in development mode
Open a second terminal from the repository root:
cd frontend
npm install
npm run dev
Open http://localhost:5173. The Vite development server proxies API requests to the backend.
4. Or run the built application from FastAPI
cd frontend
npm install
npm run build

cd ../backend
uvicorn app.main:app --port 8000
Then open http://localhost:8000.
Tip: A root-level Makefile includes shortcuts such as make install, make dev-api, make dev-web, make build, make test, and make migrate.

⚙️ Environment Configuration
Configuration can be provided through environment variables or the .env file. See .env.example for the complete list.
Variable	Default	Purpose
SECRET_KEY	Development placeholder	Signs JWTs and download tokens; replace before production
DATABASE_URL	sqlite:///./ats.db	Database connection string
BACKEND_CORS_ORIGINS	http://localhost:5173	Allowed frontend origins
STORAGE_BACKEND	local	Select local or s3 storage
STORAGE_DIR	./storage	Private local upload directory
MAX_UPLOAD_MB	10	Maximum upload size per file
LLM_ENABLED	false	Enables optional LLM enrichment
LLM_API_KEY	Empty	Server-side AI provider key
LLM_BASE_URL / LLM_MODEL	Provider defaults / gpt-4o-mini	LLM endpoint and model
OCR_ENABLED	false	Enables OCR when Tesseract is installed
PROCESSING_MODE	background	inline runs processing synchronously
RESUME_RETENTION_DAYS	365	Configurable resume retention period


Keep secrets server-side. The frontend communicates with the application's API; it should never receive the LLM API key.
🗄️ Database and Migrations
SQLite is the default for local development. To use PostgreSQL or Supabase, configure DATABASE_URL, then apply migrations:
# Example only — replace credentials and host with your own
export DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/ats"

cd backend
alembic upgrade head
For production, use migrations and set ENVIRONMENT=production. Startup schema creation supports local development, while production should use controlled migrations.

The schema includes entities for organizations, users, memberships, jobs, job requirements, candidate profiles, resumes, parsed resume data, applications, match results, stage history, recruiter notes, interview feedback, audit logs, consent records, and deletion requests.
🧪 Demo Accounts
Non-production environments seed fictional demo data for exploration.
Role	Email	Password
Recruiter	recruiter@demo.com	demo12345
Admin	admin@demo.com	admin12345
Superadmin	superadmin@platform.local	superadmin12345


Demo data includes three sample roles — Senior Backend Engineer, Machine Learning Engineer, and Ceramic Process Engineer — plus six fictional candidate resumes.
Security: These credentials are for local demonstration only. Never use demo credentials or development secrets in a production deployment.

🎯 Matching Methodology
The default match score combines five configurable components. The weights are validated to total 100% for each job.
Component	Default weight	What it evaluates
Required skills	40%	Required skills identified in the parsed resume, including transferable credit
Experience & responsibilities	25%	Responsibility overlap and experience-duration fit
Preferred skills	15%	Additional desirable skills
Projects & achievements	10%	Evidence from relevant projects and accomplishments
Qualifications & certifications	10%	Education and certifications against job requirements


Each result can include:
- Matched requirements
- Partial or transferable matches
- Missing or unverified requirements
- Supporting evidence from the resume
- Parsing uncertainties
Unknown is not the same as missing. If the resume does not provide enough information to verify a requirement, the engine can mark it as unknown rather than automatically treating it as a capability gap.

A deterministic engine works offline. If an OpenAI-compatible provider is configured, an optional hybrid mode can refine responsibility coverage and identify transferable skills. If the provider fails or returns invalid output, the deterministic result is used instead.
🔌 API Overview
All API routes are under /api. Authenticated endpoints use a Bearer token. Organization scoping can use the X-Org-Id header.
Area	Example endpoints
Authentication	POST /auth/register, POST /auth/login, GET /auth/me
Public	GET /public/config, GET /public/stats, GET /public/jobs
Jobs	GET /jobs, POST /jobs, POST /jobs/analyze-jd
Resumes	POST /resumes/upload, GET /resumes, POST /resumes/{id}/reprocess
Candidates	GET /candidates, GET /candidates/{id}
Applications	GET /applications, POST /applications/{id}/stage
Analytics	GET /analytics/dashboard, GET /analytics/reports, GET /analytics/export.csv
Administration	GET /admin/users, GET /admin/audit-logs, GET /admin/system-health
Candidate self-service	GET /me/applications, POST /me/apply, POST /me/delete-request


This is a high-level route overview, not an exhaustive endpoint list. Explore the complete interactive API documentation at /docs while the backend is running.
✅ Testing
Run the backend test suite:
cd backend
python -m pytest
The project README reports 56 tests covering authentication, permissions, organization isolation, resume parsing, match-score calculations, ranking and filtering, application-stage history, private file access, file validation, duplicate detection, malformed documents, prompt-injection text, and AI-provider failure fallback.

Tests use an isolated temporary SQLite database with synchronous processing and demo seeding disabled.
🐳 Docker Deployment
The repository includes a Dockerfile and docker-compose.yml for the application and PostgreSQL.
docker compose up --build
Then visit http://localhost:8000.
Production checklist
- [ ] Set a strong SECRET_KEY and ENVIRONMENT=production.
- [ ] Configure managed PostgreSQL/Supabase and apply Alembic migrations.
- [ ] Configure private S3 storage or a private persistent volume.
- [ ] Terminate HTTPS at a reverse proxy.
- [ ] Use a shared rate-limit store, such as Redis, when running multiple replicas.
- [ ] Replace the in-process worker with Celery/RQ for larger bulk-processing workloads.
- [ ] Review retention, access, logging, and deletion policies for your deployment.
🔐 Security, Privacy & Fairness
TalentLens includes several safeguards intended to reduce common risks:
- JWT authentication and bcrypt password hashing.
- Server-side permission checks and organization-scoped database queries.
- File extension and magic-byte validation, upload size limits, and SHA-256 duplicate detection.
- Private file storage with short-lived signed download URLs.
- Authentication rate limiting, input validation, and safe error handling.
- Audit logging for logins, uploads, stage changes, and administrative actions.
- Configurable resume retention and candidate deletion requests.
- Exclusion of protected attributes from scoring, with optional blind screening.
- No use of graduation dates to infer age and no personality or culture-fit inference.
- Uploaded documents are treated as untrusted input; embedded instructions are ignored and flagged.
These measures do not guarantee fairness or eliminate bias. Recruiters should review the evidence, consider context, and retain human oversight for all consequential hiring decisions.
🧩 Optional Integrations & Current Limitations
The application can run end-to-end without every external integration configured.
Area	Default state / requirement
LLM provider	Disabled by default; configure LLM_ENABLED=true and LLM_API_KEY to enable
OCR	Disabled by default; requires the Tesseract binary
Cloud storage	S3 interface requires AWS credentials; private local storage is the default
PostgreSQL	SQLite is the default; configure DATABASE_URL and run migrations
Billing	Pricing-page plans are sample content; no payment processor is connected
Contact form	Client-side validation only; submissions are not persisted


📁 Project Structure
ats-platform/
├── .env.example
├── README.md
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── deps.py
│   │   ├── seed.py
│   │   ├── routers/
│   │   └── services/
│   └── tests/
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── App.tsx
        ├── lib/
        ├── components/
        └── pages/
🌱 Future Improvements
Potential next steps include a dedicated background task queue for high-volume processing, expanded deployment automation, and additional monitoring for production workloads.
<div align="center">

TalentLens — clearer hiring insights, with people in control.

Built with React, TypeScript, FastAPI, and Python.
</div>
