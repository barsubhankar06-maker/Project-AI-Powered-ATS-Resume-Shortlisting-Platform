"""Clearly-labelled demo data.

Seeds one demo organization with fictional jobs and candidate resumes so the
whole workflow can be exercised. Demo records live in their own organization
(is_demo=True) and are never mixed with real customer data. Disable by running
with ENVIRONMENT=production or by not calling ensure_demo_data().
"""
from __future__ import annotations

import io

from sqlalchemy import select

from .database import SessionLocal
from .models import (
    Application,
    CandidateProfile,
    Job,
    JobRequirement,
    Organization,
    OrganizationMembership,
    Resume,
    User,
)
from .security import hash_password
from .services import matching, storage
from .services.processing import process_resume

DEMO_EMAIL = "recruiter@demo.com"
DEMO_PASSWORD = "demo12345"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin12345"
SUPER_EMAIL = "superadmin@platform.local"
SUPER_PASSWORD = "superadmin12345"

DEMO_RESUME_TEXTS = {
    "Aarav Sharma": """Aarav Sharma
Bengaluru, India | aarav.sharma@example.com | +91 98765 43210

Summary
Backend engineer with 6 years building high-throughput APIs and microservices.

Experience
Senior Backend Engineer, Nimbus Cloud (Jan 2020 - Present)
- Designed REST APIs in Python and FastAPI serving 40k requests per second.
- Migrated monolith to microservices on Docker and Kubernetes.
- Tuned PostgreSQL queries and added Redis caching, cutting p95 latency 60%.
- Set up CI/CD pipelines and deployed to AWS.

Software Engineer, Falcon Systems (Jul 2018 - Dec 2019)
- Built internal services in Python and Django with MySQL.
- Containerized legacy apps with Docker.

Skills
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, AWS, REST, CI/CD, Git, Linux, Microservices

Education
B.Tech in Computer Science, IIT Delhi, 2018

Certifications
AWS Certified Solutions Architect

Projects
- Built an event-driven order service with Kafka and Python.
""",
    "Meera Iyer": """Meera Iyer
Pune, India | meera.iyer@example.com | +91 91234 56780

Summary
Data engineer focused on analytics pipelines and SQL data models, 3 years.

Experience
Data Engineer, Insight Labs (Jun 2021 - Present)
- Built ETL pipelines with Python and Airflow loading into PostgreSQL.
- Modelled analytics tables and wrote complex SQL.
- Used Docker for reproducible environments.

Analyst, BrightRetail (Aug 2020 - May 2021)
- Automated reports with Python and Excel.

Skills
Python, SQL, PostgreSQL, Airflow, Docker, Git, Data Engineering, ETL, Excel, Data Analysis

Education
B.Sc Statistics, Fergusson College, 2020

Projects
- Sales forecasting dashboard using pandas.
""",
    "Rohan Verma": """Rohan Verma
Hyderabad, India | rohan.verma@example.com | +91 99887 76655

Summary
Frontend developer with 2 years of experience in React and TypeScript.

Experience
Frontend Developer, PixelWorks (Mar 2022 - Present)
- Built responsive UIs with React, TypeScript and Tailwind CSS.
- Consumed REST and GraphQL APIs.

Intern, PixelWorks (Jun 2021 - Feb 2022)
- Fixed UI bugs and wrote unit tests.

Skills
JavaScript, TypeScript, React, Next.js, HTML, CSS, Tailwind, Git, Testing, GraphQL

Education
B.E Information Technology, Osmania University, 2021
""",
    "Sara Khan": """Sara Khan
Remote | sara.khan@example.com | +91 90000 11122

Summary
Machine learning engineer, 4 years, NLP and deep learning.

Experience
ML Engineer, Lumen AI (Feb 2021 - Present)
- Trained transformer models with PyTorch for NLP tasks.
- Built Python services with FastAPI to serve models.
- Deployed training jobs on AWS with Docker.

Data Scientist, Cipher (Jan 2020 - Jan 2021)
- Built scikit-learn models and SQL pipelines.

Skills
Python, PyTorch, TensorFlow, Machine Learning, Deep Learning, NLP, SQL, Docker, AWS, FastAPI, pandas, numpy

Education
M.Tech in Artificial Intelligence, IIIT Hyderabad, 2019

Certifications
TensorFlow Developer Certificate

Projects
- Retrieval-augmented chatbot using LLM embeddings.
""",
    "Vikram Nair": """Vikram Nair
Chennai, India | vikram.nair@example.com | +91 98450 33221

Summary
Java backend developer, 5 years, payments domain.

Experience
Senior Engineer, PayFlux (May 2019 - Present)
- Built services in Java and Spring Boot.
- Worked with MySQL, Kafka and Redis.
- Deployed on AWS with Docker.

Engineer, CoreBank (Jul 2017 - Apr 2019)
- Maintained SOAP and REST integrations.

Skills
Java, Spring, MySQL, Kafka, Redis, Docker, AWS, REST, Microservices, Git

Education
B.Tech Computer Science, Anna University, 2017
""",
    "Ananya Rao": """Ananya Rao
Varanasi, India | ananya.rao@example.com | +91 77777 88899

Summary
Ceramic engineer with 3 years in process development and quality control.

Experience
Process Engineer, Bharat Ceramics (Aug 2021 - Present)
- Developed sintering and heat treatment cycles for advanced ceramics.
- Ran quality control and Six Sigma improvement projects.
- Used kiln and furnace operation protocols and CAD for tooling.

Intern, Refractory Works (Jan 2021 - Jul 2021)
- Supported refractories testing and materials characterization.

Skills
Ceramics, Materials Science, Process Engineering, Quality Control, Six Sigma, Heat Treatment, CAD, SolidWorks, Excel

Education
B.Tech Ceramic Engineering, IIT (BHU) Varanasi, 2021

Projects
- Reduced kiln rejects by 12% via statistical process control.
""",
}

DEMO_JOBS = [
    {
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "location": "Bengaluru, India",
        "experience_min": 4,
        "experience_max": 8,
        "description": """We are hiring a Senior Backend Engineer to build scalable APIs.

Required Skills
Python, FastAPI, PostgreSQL, Docker, AWS, REST, Microservices

Preferred Skills
Redis, Kubernetes, CI/CD

Responsibilities
- Design and build REST APIs and microservices.
- Tune database performance and add caching.
- Deploy and operate services on the cloud.

Qualifications
Bachelor's degree in Computer Science or related field.
""",
        "candidates": ["Aarav Sharma", "Vikram Nair", "Meera Iyer"],
    },
    {
        "title": "Machine Learning Engineer",
        "department": "AI",
        "location": "Hyderabad, India",
        "experience_min": 2,
        "experience_max": 6,
        "description": """Join our AI team to build and deploy machine learning systems.

Required Skills
Python, PyTorch, Machine Learning, NLP, SQL

Preferred Skills
LLM, Docker, AWS

Responsibilities
- Train and evaluate NLP models.
- Build Python services to serve models.
- Deploy training and inference jobs in the cloud.

Qualifications
Master's degree preferred.
""",
        "candidates": ["Sara Khan", "Meera Iyer"],
    },
    {
        "title": "Ceramic Process Engineer",
        "department": "Manufacturing",
        "location": "Varanasi, India",
        "experience_min": 2,
        "experience_max": 6,
        "description": """We are seeking a Ceramic Process Engineer for our advanced ceramics line.

Required Skills
Ceramics, Materials Science, Process Engineering, Quality Control, Heat Treatment

Preferred Skills
Six Sigma, CAD

Responsibilities
- Develop sintering and heat treatment processes.
- Run quality control and continuous improvement projects.
- Collaborate with production on furnace operation.

Qualifications
B.Tech in Ceramic or Materials Engineering.
""",
        "candidates": ["Ananya Rao", "Vikram Nair"],
    },
]


def _make_docx(text: str) -> bytes:
    from docx import Document

    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _add_requirements(db, job: Job, description: str) -> None:
    from .services import job_parser, skill_normalization as sn

    result = job_parser.parse_heuristic(description, job.title)
    for r in result.requirements:
        db.add(
            JobRequirement(
                job_id=job.id,
                kind=r["kind"],
                text=r["text"],
                normalized_skill=r["normalized_skill"] or sn.normalize(r["text"]),
                source="ai",
            )
        )


def ensure_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Organization).where(Organization.slug == "demo-corp")):
            return  # already seeded

        org = Organization(name="Demo Corp", slug="demo-corp", is_demo=True)
        db.add(org)
        db.flush()

        recruiter = User(
            email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD), full_name="Dana Recruiter"
        )
        admin = User(email=ADMIN_EMAIL, hashed_password=hash_password(ADMIN_PASSWORD), full_name="Alok Admin")
        superadmin = User(
            email=SUPER_EMAIL,
            hashed_password=hash_password(SUPER_PASSWORD),
            full_name="Platform Superadmin",
            is_superadmin=True,
        )
        db.add_all([recruiter, admin, superadmin])
        db.flush()
        db.add_all(
            [
                OrganizationMembership(user_id=recruiter.id, org_id=org.id, role="recruiter"),
                OrganizationMembership(user_id=admin.id, org_id=org.id, role="admin"),
            ]
        )
        db.flush()

        jobs_by_title: dict[str, Job] = {}
        for spec in DEMO_JOBS:
            job = Job(
                org_id=org.id,
                created_by=recruiter.id,
                title=spec["title"],
                company="Demo Corp",
                department=spec["department"],
                location=spec["location"],
                employment_type="full_time",
                experience_min=spec["experience_min"],
                experience_max=spec["experience_max"],
                description=spec["description"],
                weights=dict(matching.DEFAULT_WEIGHTS),
                feedback_enabled=True,
                status="open",
            )
            db.add(job)
            db.flush()
            _add_requirements(db, job, spec["description"])
            jobs_by_title[job.title] = job

        resume_ids: list[str] = []
        for name, text in DEMO_RESUME_TEXTS.items():
            cand = CandidateProfile(
                org_id=org.id, full_name=name, email=f"{name.split()[0].lower()}@example.com"
            )
            db.add(cand)
            db.flush()
            resume = Resume(
                org_id=org.id,
                candidate_id=cand.id,
                uploaded_by=recruiter.id,
                filename=f"{name.replace(' ', '_')}_Resume.docx",
                storage_key="",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                status="pending",
                sha256="",
            )
            db.add(resume)
            db.flush()
            data = _make_docx(text)
            resume.size_bytes = len(data)
            resume.sha256 = storage.compute_sha256(data)
            resume.storage_key = storage.save_bytes(org.id, resume.id, resume.filename, data)
            resume_ids.append(resume.id)

            for spec in DEMO_JOBS:
                if name in spec["candidates"]:
                    job = jobs_by_title[spec["title"]]
                    db.add(
                        Application(
                            org_id=org.id,
                            job_id=job.id,
                            candidate_id=cand.id,
                            resume_id=resume.id,
                            source="demo_seed",
                            feedback_enabled=True,
                        )
                    )
        db.commit()
    finally:
        db.close()

    # Parse + match through the real pipeline (each opens its own session).
    for rid in resume_ids:
        try:
            process_resume(rid)
        except Exception:  # noqa: BLE001 - seeding must never crash startup
            pass
