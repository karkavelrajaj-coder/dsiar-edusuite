# D'siar Tech LMS — Enterprise Edition

A decoupled, production-grade rebuild of the D'siar Tech LMS: React
frontend + FastAPI backend, replacing the original Streamlit prototype
(kept running untouched, separately, on Streamlit Cloud).

```
dsiar-lms-v2/
├── backend/           FastAPI API (auth, courses, assignments, certificates,
│                       live sessions) — see backend/README.md
├── frontend/           React + Vite + Tailwind SPA — see frontend/README.md
├── Dockerfile          Builds the backend for Render
├── render.yaml         Render Blueprint (deploys backend + frontend together)
└── DEPLOYMENT.md        Step-by-step GitHub + Render deployment guide
```

## Why a separate app, not an upgrade in place

- Same free MongoDB Atlas cluster, but a **new database**
  (`dsiar_lms_v2`) — the Streamlit app's own data is never touched.
- Same Digital Samba account/keys — live sessions work identically.
- New GitHub repo, new Render deployment — the Streamlit Cloud deployment
  keeps running exactly as it does today.

## Local development

Two terminals:

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in MONGO_URI, JWT_SECRET, DIGITALSAMBA_*
uvicorn app:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api -> :8000
```

Log in with `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` from your `.env`
(created automatically on first backend boot, same as the Streamlit app).

## Deploying

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) — GitHub + Render, free tier, no
credit card.

## Feature parity with the Streamlit app

All three phases' backend + frontend code is written and ported
feature-for-feature from the working Streamlit app:

- **Auth & RBAC** — JWT in an httpOnly cookie, same admin/instructor/
  student rules as before (instructor scoped to `instructor_id`, no
  public sign-up).
- **Courses** — catalog, course/module/lesson CRUD, enrollment
  management, admin-preview self-enroll.
- **Learning** — lesson video/slides/Colab/dataset links, mark-complete
  progress tracking, My Learning progress bars.
- **Assignments** — lesson-completion gating, submission, grading,
  approve/reject with feedback, which auto-issues a certificate the same
  way `ensure_certificate()` did in the Streamlit app.
- **Certificates** — same Pillow-rendered design (bundled fonts, logo),
  served as a PNG from `/api/certificates/{cert_id}/image`.
- **Live sessions** — Digital Samba rooms, per-person signed join tokens,
  host start/end, multi-timezone scheduling — same UUID-vs-friendly_url
  handling and "always generate a fresh room name" rule as before.

**Verified so far:** the full flow (login → create course → enroll →
complete lesson → submit → grade → certificate → schedule live session)
passes end-to-end in `backend/tests/test_smoke.py`, run against an
in-memory Mongo. This sandbox's outbound network can't reach MongoDB
Atlas or the Digital Samba API directly, so the real `MONGO_URI` and
`DIGITALSAMBA_*` calls haven't been exercised from here yet — that's the
next step, either by running the backend on your own machine with real
credentials, or deploying to Render (which has normal outbound access)
and testing there. See [`DEPLOYMENT.md`](./DEPLOYMENT.md).
