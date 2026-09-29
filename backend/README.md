# D'siar Tech LMS — Backend (FastAPI)

Enterprise API for the D'siar Tech LMS, ported feature-for-feature from the
original Streamlit app onto FastAPI + JWT (httpOnly cookie) auth, so it can
sit behind a real React frontend.

**Runs against a NEW MongoDB database** (`DB_NAME`, default `dsiar_lms_v2`)
in the same free Atlas cluster the Streamlit app already uses. The
Streamlit app's own `dsiar_lms` database/collections are never opened by
this code — the two apps are fully isolated from each other even though
they share a cluster.

## Local setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env   # fill in MONGO_URI, JWT_SECRET, DIGITALSAMBA_* etc.
uvicorn app:app --reload --port 8000
```

First boot auto-creates the admin account from `SEED_ADMIN_EMAIL` /
`SEED_ADMIN_PASSWORD` / `SEED_ADMIN_NAME`, exactly like the Streamlit app.

## Tests

```bash
pip install mongomock httpx
python tests/test_smoke.py
```

Runs the full auth → course → enrollment → lesson-completion → assignment
→ grading → certificate → live-session flow against an in-memory Mongo, so
it works even without real network access to Atlas.

## API surface

- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET/POST/PATCH/DELETE /api/users*`, `/api/users/me/timezone`
- `GET /api/courses` (catalog), `/api/courses/manage`, `/api/courses/{id}`,
  `/api/courses/{id}/modules`, `/api/modules/{id}/lessons`
- `POST /api/lessons/{id}/complete`, `GET /api/my/learning`
- `GET/POST /api/enrollments`, `POST /api/enrollments/preview/{course_id}`
- `GET/POST/PATCH/DELETE /api/assignments*`, `/api/my/assignments`,
  `/api/assignments/{id}/submit`, `/api/assignments/{id}/submissions`,
  `PATCH /api/submissions/{id}` (grade → auto-issues certificate)
- `GET /api/certificates`, `GET /api/certificates/{cert_id}/image`
- `GET/POST/PATCH/DELETE /api/live-sessions*`, `/start`, `/end`,
  `/api/my/live-sessions`, `/api/live-sessions/{id}/join`

Full interactive docs at `/docs` once running.
