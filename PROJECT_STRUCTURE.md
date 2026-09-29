# Project structure

```
dsiar-lms-v2/
├── Dockerfile                 Builds the backend image for Render
├── render.yaml                 Render Blueprint (backend Web Service + frontend Static Site)
├── DEPLOYMENT.md               GitHub + Render deployment walkthrough
├── README.md
├── .gitignore
│
├── backend/
│   ├── app.py                  FastAPI app: CORS, routers, static assets, startup (seed admin, indexes)
│   ├── config.py                Settings loaded from environment variables
│   ├── db.py                    MongoDB connection + collection accessors + ensure_indexes()
│   ├── security.py              Password hashing, JWT issue/verify, httpOnly cookie helpers, RBAC dependencies
│   ├── schemas.py                Pydantic request models
│   ├── serializers.py            Mongo-doc -> JSON-safe dict helpers
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   ├── modules/                  One router per feature area
│   │   ├── auth.py                /api/auth/*
│   │   ├── users.py               /api/users*, /api/timezones, /api/users/me/timezone
│   │   ├── courses.py             /api/courses*, /api/modules*, /api/lessons*, /api/my/learning
│   │   ├── enrollments.py         /api/enrollments*
│   │   ├── assignments.py         /api/assignments*, /api/submissions*, /api/my/assignments
│   │   ├── certificates.py        /api/certificates*
│   │   └── live_sessions.py       /api/live-sessions*, /api/my/live-sessions
│   ├── utils/                    Ported business logic (same behavior as the old utils/ in Streamlit)
│   │   ├── certificates.py        Eligibility + idempotent issuance
│   │   ├── certificate_image.py   Pillow certificate PNG rendering
│   │   ├── digital_samba.py       Digital Samba REST API wrapper
│   │   ├── live_sessions.py       Room naming, status windows, join gating
│   │   └── timezones.py           IANA timezone conversion helpers
│   ├── assets/                   Fonts, logo, course thumbnails (served at /api/static/*)
│   └── tests/
│       ├── test_smoke.py          Full-flow test against an in-memory Mongo (mongomock)
│       └── mock_server.py         Runs the real app over real HTTP for local/manual testing
│
└── frontend/
    ├── index.html
    ├── vite.config.js             Tailwind v4 plugin + dev proxy (/api -> :8000)
    ├── package.json
    ├── src/
    │   ├── main.jsx                 BrowserRouter + App
    │   ├── App.jsx                   Route table, role-based redirects
    │   ├── index.css                  Tailwind entry
    │   ├── api/client.js              Axios instance (withCredentials for the cookie)
    │   ├── context/AuthContext.jsx     Current user, login/logout
    │   ├── components/
    │   │   ├── ProtectedRoute.jsx      Route guard (login + optional role check)
    │   │   └── Layout.jsx               Sidebar nav (role-aware) + page frame
    │   └── pages/
    │       ├── Login.jsx
    │       ├── Catalog.jsx
    │       ├── MyLearning.jsx
    │       ├── CoursePlayer.jsx
    │       ├── Assignments.jsx
    │       ├── Certificates.jsx
    │       ├── LiveSessions.jsx
    │       └── admin/
    │           ├── ManageCourses.jsx
    │           ├── ManageUsers.jsx
    │           ├── Grading.jsx
    │           └── ManageLiveSessions.jsx
    └── dist/                       Build output (gitignored)
```
