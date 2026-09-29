# D'siar Tech LMS — Frontend (React + Vite + Tailwind)

Talks to the FastAPI backend over `/api/*` (proxied to `:8000` in dev, or
`VITE_API_BASE_URL` in production) using a JWT stored in an httpOnly
cookie — `axios` is configured with `withCredentials: true` so it's sent
automatically.

## Local development

```bash
npm install
npm run dev   # http://localhost:5173
```

Requires the backend running on `:8000` (see `../backend/README.md`).

## Build

```bash
npm run build   # outputs to dist/
```

## Environment variables

- `VITE_API_BASE_URL` — the backend's base URL including `/api`, e.g.
  `https://dsiar-edusuite-backend.onrender.com/api`. Leave unset in dev (the
  Vite proxy handles it); required in production since the frontend and
  backend are on different domains.
