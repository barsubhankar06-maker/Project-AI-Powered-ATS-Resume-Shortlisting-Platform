"""FastAPI application entrypoint.

Serves the JSON API under /api and, when a production frontend build exists,
the compiled single-page app for everything else.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import (
    admin,
    analytics,
    applications,
    auth,
    candidate_self,
    candidates,
    jobs,
    public,
    resumes,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ats")

app = FastAPI(
    title=settings.app_name,
    description="AI-powered ATS and resume shortlisting platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Lightweight in-memory rate limiting ----------------------------------
# Suitable for a single process; use a shared store (Redis) behind a load
# balancer in production.
_HITS: dict[str, deque] = defaultdict(deque)
_RATE_LIMITED_PREFIXES = ("/api/auth/login", "/api/auth/register")


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    path = request.url.path
    if settings.rate_limit_enabled and any(path.startswith(p) for p in _RATE_LIMITED_PREFIXES):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _HITS[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:  # auth attempts per minute per IP
            return JSONResponse({"detail": "Too many requests. Please slow down."}, status_code=429)
        window.append(now)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):  # pragma: no cover
    log.exception("Unhandled error on %s", request.url.path)
    # Never leak stack traces or internals to the client.
    return JSONResponse({"detail": "An internal error occurred. Please try again."}, status_code=500)


# --- API routes -----------------------------------------------------------
for r in (auth, jobs, resumes, candidates, applications, analytics, admin, public, candidate_self):
    app.include_router(r.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


# --- Startup --------------------------------------------------------------
@app.on_event("startup")
def on_startup() -> None:
    # create_all keeps local dev / SQLite frictionless. In production use
    # Alembic migrations (`alembic upgrade head`) against PostgreSQL/Supabase.
    Base.metadata.create_all(bind=engine)
    if settings.environment != "production":
        try:
            from .seed import ensure_demo_data

            ensure_demo_data()
        except Exception as exc:  # noqa: BLE001
            log.warning("demo seed skipped: %s", exc)


# --- Static frontend (production build) -----------------------------------
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Serve real files directly; otherwise return index.html for client routing.
        candidate = _DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
