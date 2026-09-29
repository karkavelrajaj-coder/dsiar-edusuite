# Deploying Checkpoint 2 to GitHub + Render (free tier)

This is the **multi-tenant / white-label** build. One deployment serves
every client company — each gets their own database inside the same Atlas
cluster, picked automatically at login by the company code they enter. You
manage everything (creating client companies, their admins, plan/seat
limits, feature flags) through the **Super Admin console** at `/platform`
— there is no seed script anymore.

Two independently-deployed services from one repo:

- **`dsiar-edusuite-backend`** — FastAPI, deployed as a Render **Web Service**
  built from the root `Dockerfile`.
- **`dsiar-edusuite-frontend`** — the React/Vite app, deployed as a Render
  **Static Site** (no Docker — Render runs `npm run build` and serves
  `dist/` over its CDN, free with no sleep).

Both are defined in `render.yaml`, so Render can create them together as a
single **Blueprint**.

## 0. Push this repo to a new GitHub repo

```bash
cd dsiar-lms-v2-checkpoint2
git branch -M main
git remote add origin https://github.com/<you>/<new-repo-name>.git
git push -u origin main
```

This is a **brand-new repo**, separate from both the original Streamlit
app's repo and Checkpoint 1's repo — neither is touched by this.

## 1. Deploy the Blueprint on Render

1. Render dashboard → **New** → **Blueprint**.
2. Pick the new GitHub repo. Render reads `render.yaml` and shows both
   services (`dsiar-edusuite-backend`, `dsiar-edusuite-frontend`).
3. Click **Apply**. Render asks you to fill in every env var marked
   `sync: false` — for the first deploy you can leave `CORS_ORIGINS` and
   `VITE_API_BASE_URL` blank; you'll set those in step 4 once both
   services have URLs.
4. Fill in at minimum:
   - `MONGO_URI` — same Atlas connection string as your other apps (see
     **Database** below — this build never touches their databases).
   - `PLATFORM_SUPER_ADMIN_EMAIL`, `PLATFORM_SUPER_ADMIN_PASSWORD` — your
     own Super Admin login, created automatically on first boot. Set these
     once; they're only read if no Super Admin exists yet.
   - `DIGITALSAMBA_TEAM_ID`, `DIGITALSAMBA_DEVELOPER_KEY` — only needed for
     clients with the Live Sessions feature flag turned on; safe to leave
     blank otherwise.

## 2. Database — same free Atlas cluster, brand-new per-tenant databases

`render.yaml` sets `DB_NAME=lms_fallback_unused` — this build never uses
one fixed database. Every client company gets its **own** database inside
the same `Cluster0` free cluster, named whatever `db_name` you give them
when you create the tenant in the Super Admin console (e.g. `lms_dsiar`,
`lms_<clientcode>`). None of this touches the Streamlit app's `dsiar_lms`
database or Checkpoint 1's `dsiar_lms_v2` database — all three coexist
safely in the same cluster.

Atlas Network Access must allow Render's IPs — keep (or add) `0.0.0.0/0`
in Atlas → Network Access, same as your other apps already need.

## 3. Wait for both builds to finish

- Backend build: installs `backend/requirements.txt` inside the Docker
  image, then starts `uvicorn app:app`. Watch the Render logs for
  `Application startup complete.`
- Frontend build: `npm install && npm run build` inside `frontend/`.

## 4. Wire the two services together

Once both have URLs (e.g. `https://dsiar-edusuite-backend.onrender.com` and
`https://dsiar-edusuite-frontend.onrender.com`):

1. Backend service → Environment → set `CORS_ORIGINS` to the frontend's
   URL (exactly, no trailing slash) → save (triggers a redeploy).
2. Frontend service → Environment → set `VITE_API_BASE_URL` to the
   backend's URL **plus `/api`** (e.g.
   `https://dsiar-edusuite-backend.onrender.com/api`) → save (triggers a
   rebuild — Vite bakes env vars in at build time).

## 5. Onboard your first real client (D'siar Tech itself)

1. Open `https://<your-frontend>.onrender.com/platform/login`.
2. Log in with `PLATFORM_SUPER_ADMIN_EMAIL` / `PLATFORM_SUPER_ADMIN_PASSWORD`.
3. Super Admin console → **New tenant**: pick a `company_code` (short,
   lowercase, no spaces — this is what every user of that company types at
   login, e.g. `dsiar`), a `db_name` (e.g. `lms_dsiar`), display name,
   plan, and max users. This also creates that company's first admin
   account in the same call.
4. If this client is D'siar Tech's own account and needs Live Sessions,
   turn that feature flag on for this tenant (off by default for everyone
   else, per your earlier decision).
5. Log out of `/platform`, go to the normal login page, log in as that
   tenant's admin with its `company_code` + the admin email/password you
   just set.

## 6. Verify

1. Log in as the tenant admin → Manage Users → create an instructor and a
   student.
2. Manage Courses → create a course (set its track here — it applies to
   every student enrolled, not per-student).
3. Add a module and a lesson, either one at a time or via **Bulk import**
   (Excel).
4. Manage Users → enroll the student (one at a time, or bulk-import
   enrollments).
5. Log in as the student, complete the lesson, submit the assignment (if
   any), grade it as the instructor, confirm the certificate image renders
   — it should show this client's own logo (or their company name in text,
   if you haven't dropped a `{company_code}_logo.png` into `backend/assets/`
   yet) with no MSME block.
6. Try creating a **second** tenant and confirm its users only ever see
   that tenant's own data — this is the multi-tenant isolation the whole
   build is verified against.

## Adding a client's logo/signature later

Drop `backend/assets/{company_code}_logo.png` and/or
`{company_code}_signature.png` into the repo (GitHub web UI works fine —
no redeploy of code needed, just commit the file) and it's picked up on
the next certificate request automatically. No file yet → their plain
company name renders in text instead, so nothing breaks in the meantime.

## Notes on Render's free tier

- Free **Web Services** (the backend) spin down after ~15 minutes of no
  traffic and take ~30–60s to wake back up on the next request.
- Free **Static Sites** (the frontend) don't sleep and are served from
  Render's CDN.
- No credit card required for either, same as your Atlas M0 cluster.
- One free Render account can host both services from this repo alongside
  whatever you already have deployed there — they're independent services,
  not extra accounts.
