# Aeroflot Tool Management System

Unified system for managing tool issuance/return with automated visual recognition. The stack includes a React frontend, a FastAPI backend with Postgres and Alembic, and a simple ML microservice. Docker Compose orchestrates all services for local usage and demos.

### Contents
- Overview and Architecture
- Prerequisites
- Quickstart (Docker)
- Configuration
- Project Structure
- Local Development
- Database and Migrations
- API Quick Reference
- Frontend Workflow
- Troubleshooting
- Maintenance and Housekeeping

## Overview and Architecture

Services (Docker):
- `db`: Postgres 16, persistent volume `db_data`
- `ml`: FastAPI ML placeholder on port 8010 (`/health`, `/detect`)
- `backend`: FastAPI app on port 8001, runs Alembic migrations on start
- `frontend`: React app on port 3000

Traffic map (local):
- Backend API: `http://localhost:8001`
- Frontend: `http://localhost:3000`
- ML service: `http://localhost:8010`

## Prerequisites
- Docker and Docker Compose plugin (Docker Desktop, Rancher Desktop, Colima, or `docker-ce` + compose plugin)
- ~4 GB free disk space for images and Postgres volume

## Quickstart (Docker)
Build and start all services from the repository root:
```bash
docker compose up -d --build
```
Then open:
- Backend docs (OpenAPI): `http://localhost:8001/docs`
- Frontend UI: `http://localhost:3000`

Stop and remove containers (keep data volume):
```bash
docker compose down
```

Remove everything including volumes:
```bash
docker compose down -v
```

## Configuration

Environment variables (most are pre-wired in `docker-compose.yml`):
- `DATABASE_URL`: SQLAlchemy URL for Postgres
  - Example (compose): `postgresql+psycopg2://postgres:postgres@db:5432/tools`
  - Example (local): `postgresql+psycopg2://postgres:postgres@localhost:5432/tools`
- `MODEL_PATH`: Path to YOLO model inside backend container
  - Compose mounts `src/aeroflot_project/models/best_tools_detection.pt` to `/app/models/best_tools_detection.pt`
- `ML_SERVICE_URL`: URL the backend calls for detection
  - Compose uses internal URL `http://ml:8010`

Ports (host → container):
- `5432:5432` Postgres
- `8001:8001` Backend API
- `3000:3000` Frontend
- `8010:8010` ML service

Credentials (demo):
- `demo` / `password`
- `admin` / `admin`

## Project Structure
```
docker-compose.yml
docker/
  backend.Dockerfile
  frontend.Dockerfile
  ml.Dockerfile
app/
  schemas/working_api.py        # FastAPI app entrypoint
  warehouse-frontend/           # React app
ml_service_app/                 # ML placeholder service
alembic/                        # DB migrations
alembic.ini
requirements.txt                # Python deps for backend and ML images
src/aeroflot_project/models/best_tools_detection.pt  # YOLO model (mounted)
```

## Local Development

Run only the backend locally (optional):
```bash
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/tools
uvicorn app.schemas.working_api:app --host 0.0.0.0 --port 8001
```

Run ML service locally (optional):
```bash
uvicorn ml_service_app.main:app --host 0.0.0.0 --port 8010
```

Point backend to local ML:
```bash
export ML_SERVICE_URL=http://localhost:8010
```

Frontend development server (inside `app/warehouse-frontend`):
```bash
npm install
HTTPS=true npm start
```

## Database and Migrations
- Migrations live in `alembic/`; `alembic.ini` is configured.
- In Docker, the backend waits for Postgres and runs `alembic upgrade head` on start.

Run migrations locally:
```bash
alembic upgrade head
```

Create a new migration locally (example):
```bash
alembic revision -m "add new table"
```

## API Quick Reference
Base URL: `http://localhost:8001/api`

Auth
- `POST /auth/login` → `{ badge_id, password }` → `{ access_token, user }`
- `GET /auth/me` (Bearer token)

ML
- `POST /ml/detect` → `{ image_base64, confidence_threshold? }`
- `POST /ml/detect-upload` (multipart) → `file`, `confidence_threshold?`

Operations
- `POST /operations/start` → `{ engineer_name, operation_type, user_id, items? }`
- `POST /operations/confirm` → `{ session_id, image_base64? | accepted_tools? }`

Engineers/Tools CRUD
- `GET/POST/PUT/DELETE /engineers`
- `GET/POST/PUT/DELETE /tools`

For full schemas and examples, open Swagger UI: `http://localhost:8001/docs`.

## Frontend Workflow
1. Open `http://localhost:3000`
2. Sign in (demo/password or admin/admin)
3. Enter engineer name (ФИО), select type (Выдача/Прием), click “Начать операцию”
4. Capture from camera or upload an image
5. Click “Распознать инструменты”, adjust quantities if needed
6. Click “Подтвердить операцию” to see the summary

## Troubleshooting
- Containers keep restarting: check logs
  ```bash
  docker compose logs -f backend ml frontend db
  ```
- Backend cannot connect to DB: ensure port 5432 is free or not overridden; the backend waits for `db` to be ready.
- ML detection errors: verify `ML_SERVICE_URL` and that `ml` responds at `/health`.
- Model file missing: confirm `src/aeroflot_project/models/best_tools_detection.pt` exists; compose mounts it read-only.
- Frontend can’t reach API: ensure `backend` is on 8001 and `REACT_APP_API_BASE` is set (compose sets `http://localhost:8001`).

## Maintenance and Housekeeping
- To reset Postgres data locally, bring down with volumes:
  ```bash
  docker compose down -v
  ```
- For a clean rebuild:
  ```bash
  docker compose build --no-cache
  docker compose up -d
  ```
- Files and directories safe to ignore for Docker-based runs:
  - `datasets/`, `yolo_dataset/`, `labelImg/` (local data/tools)
  - `tools.db` (local SQLite; Docker uses Postgres)
  - `start.sh` (local non-Docker runner)
  - root `package-lock.json` (frontend uses lock inside `app/warehouse-frontend`)
