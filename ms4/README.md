# NeuroStream (MS4)

NeuroStream is a full-stack user workflow service for AI video processing.

- Backend: FastAPI + SQLAlchemy + PostgreSQL + Redis + AWS S3 (or S3-compatible storage)
- Frontend: Next.js 14 + TypeScript + Tailwind CSS + Framer Motion
- Local infrastructure: Docker Compose

## What This Service Does

- Registers and authenticates users with JWT
- Creates signed upload URLs for direct client uploads to object storage
- Verifies upload completion and queues processing jobs
- Tracks workflow status updates and callback events
- Supports library listing, video details, rename, and soft delete

## Repository Layout

```text
.
|-- docker-compose.yml
|-- README.md
|-- backend/
|   |-- pyproject.toml
|   |-- README.md
|   |-- .env.example
|   |-- app/
|   |   |-- main.py
|   |   |-- config.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   `-- routers/
|   `-- prisma/
|       `-- schema.prisma
`-- frontend/
    |-- package.json
    |-- .env.example
    `-- src/
        |-- app/
        |-- components/
        |-- hooks/
        |-- services/
        |-- styles/
        `-- types/
```

## Prerequisites

- Docker and Docker Compose
- Node.js 18+
- Python 3.11+
- `uv` for Python dependency management

## Quick Start

Run all commands from this `ms4/` directory unless noted.

### 1. Start local infrastructure

```bash
docker compose up -d
```

This starts:

- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- Optional local MinIO emulator API on `localhost:9000`
- Optional local MinIO Console on `http://localhost:9001`

### 2. Start backend (Terminal A)

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 4000
```

Optional seed data:

```bash
uv run python -m app.seed
```

### 3. Start frontend (Terminal B)

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Frontend: `http://localhost:3000`
Backend health check: `http://localhost:4000/health`
Backend docs: `http://localhost:4000/docs`

## Environment Files

- Backend config template: `backend/.env.example`
- Frontend config template: `frontend/.env.example`

Default local frontend API target:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:4000
```

## API Overview

Base URL: `http://localhost:4000`

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /api/upload/initiate`
- `POST /api/upload/complete`
- `GET /api/videos`
- `GET /api/videos/{video_id}`
- `PATCH /api/videos/{video_id}/rename`
- `DELETE /api/videos/{video_id}`
- `PATCH /internal/job-status` (requires `x-api-key`)

## Useful Commands

```bash
# Stop local infra
docker compose down

# Backend quick checks
cd backend && uv run ruff check app
cd backend && uv run python -m compileall app

# Frontend checks/build
cd frontend && npm run lint
cd frontend && npm run build
```

## Troubleshooting

- Upload URL failures usually indicate object storage endpoint/credentials mismatch.
- Frontend API failures usually indicate `NEXT_PUBLIC_API_BASE_URL` is incorrect or backend is not running.
- DB connection errors usually indicate PostgreSQL is down or `DATABASE_URL` is wrong.
- Internal callback failures usually indicate `x-api-key` does not match `INTERNAL_API_KEY`.

## Notes

- Backend tables are created automatically at startup via FastAPI lifespan.
- Storage bucket access is validated at startup.
- The frontend is focused on authenticated workflows: dashboard, upload, library, and video details.
