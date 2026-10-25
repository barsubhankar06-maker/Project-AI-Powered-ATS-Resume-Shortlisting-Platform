# TalentLens — developer shortcuts
.PHONY: help install install-backend install-frontend dev-api dev-web build test migrate seed clean

help:
	@echo "install          Install backend + frontend dependencies"
	@echo "dev-api          Run the FastAPI backend (reload) on :8000"
	@echo "dev-web          Run the Vite dev server on :5173"
	@echo "build            Build the frontend into frontend/dist"
	@echo "test             Run the backend test suite"
	@echo "migrate          Apply database migrations (alembic upgrade head)"
	@echo "clean            Remove build artefacts and local databases"

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

dev-api:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

test:
	cd backend && python -m pytest

migrate:
	cd backend && alembic upgrade head

clean:
	rm -rf frontend/dist backend/ats.db backend/*.db backend/storage backend/test_storage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
