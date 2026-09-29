"""D'siar Tech LMS API — CHECKPOINT 2 (multi-tenant / white-label build).

One deployment serves every client company. Each company's data lives in
its own MongoDB database inside the same Atlas cluster; a request is tied
to the right database via TenantContextMiddleware below, which reads the
"db" claim out of the caller's JWT (set at login — see modules/auth.py)
into a per-request contextvar (db.py) before any route code runs. Every
existing module (courses, enrollments, certificates, ...) is completely
unaware of any of this — they all just call e.g. courses_col(), which
already went through db.get_db(), which now resolves per-tenant instead of
to one fixed database.

There is no automatic seed-admin on boot here (unlike Checkpoint 1): a new
client company doesn't exist until it's explicitly onboarded — see
scripts/create_tenant.py, which registers the company AND creates its
first admin user in one step.
"""

from contextlib import asynccontextmanager
from http.cookies import SimpleCookie

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from db import ensure_indexes, set_tenant_db
from security import decode_access_token, get_current_user, seed_platform_super_admin
from utils.tenants import current_tenant

from modules import (
    assignments,
    auth,
    bulk,
    certificates,
    courses,
    enrollments,
    live_sessions,
    platform,
    quizzes,
    settings as settings_module,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Indexes the fallback/default database only (settings.DB_NAME) — not
    # any tenant's database, since the app has no fixed list of tenants at
    # import time. Each tenant gets its indexes created once, at onboarding
    # (POST /api/platform/tenants -> db.ensure_indexes_for(db_name)).
    ensure_indexes()
    # D'siar Tech's own Super Admin account — see config.PLATFORM_SUPER_ADMIN_*.
    seed_platform_super_admin()
    yield


app = FastAPI(title="D'siar Tech LMS API", version="1.0.0", lifespan=lifespan)


class TenantContextMiddleware:
    """Pure ASGI middleware (deliberately NOT FastAPI's
    @app.middleware("http") / BaseHTTPMiddleware, which historically runs
    the rest of the request in a separate task and can silently drop
    contextvar writes). This class stays in the exact same coroutine/task
    as the rest of the request, so a contextvar set here is reliably seen
    by every dependency and route handler downstream, even the ones that
    run in their own worker thread — they each inherit a *copy* of this
    already-mutated context, which is all read access needs.

    Reads the bearer token (or session cookie) straight off the raw ASGI
    headers, decodes it, and — if it carries a "db" claim — sets that as
    this request's tenant database before the request is handled at all.
    A missing or invalid token just leaves no tenant set; unauthenticated
    routes (like /api/health) don't need one, and authenticated routes
    still get a clean 401 from get_current_user as before."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            token = self._extract_token(scope)
            if token:
                try:
                    payload = decode_access_token(token)
                except Exception:
                    payload = None
                if payload and payload.get("db"):
                    set_tenant_db(payload["db"])
        await self.app(scope, receive, send)

    @staticmethod
    def _extract_token(scope) -> str | None:
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        auth_header = headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()
        cookie_header = headers.get("cookie")
        if cookie_header:
            jar = SimpleCookie()
            try:
                jar.load(cookie_header)
            except Exception:
                return None
            morsel = jar.get(settings.COOKIE_NAME)
            if morsel:
                return morsel.value
        return None


# Order matters: CORS should wrap everything (added last = outermost), so
# it still runs its preflight/header logic in the usual place. The tenant
# middleware just needs to run before routing, which it does either way.
app.add_middleware(TenantContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # required so the httpOnly auth cookie is sent/received
    allow_methods=["*"],
    allow_headers=["*"],
)

def _require_live_sessions(user: dict = Depends(get_current_user)) -> dict:
    """Live Sessions is an add-on, off by default for every client
    (tenants_col() doc's features.live_sessions) — it was originally built
    only for D'siar Tech. This blocks the whole live-sessions API for any
    tenant that hasn't had it switched on, without touching
    modules/live_sessions.py at all; the Super Admin console flips it on
    per client via PATCH /api/platform/tenants/{code}."""
    tenant = current_tenant()
    if not tenant or not tenant.get("features", {}).get("live_sessions"):
        raise HTTPException(status_code=403, detail="Live sessions aren't enabled for your organization.")
    return user


app.include_router(auth.router)
app.include_router(platform.router)
app.include_router(bulk.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(enrollments.router)
app.include_router(assignments.router)
app.include_router(certificates.router)
app.include_router(live_sessions.router, dependencies=[Depends(_require_live_sessions)])
app.include_router(quizzes.router)
app.include_router(settings_module.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serves course thumbnails, the logo, and certificate fonts straight off
# this backend's own filesystem (same "read from disk, not an external
# URL" pattern the Streamlit app switched to after its GitHub repo went
# private) — reachable at /api/static/<filename>, e.g.
# /api/static/AI Thumbnail.png
import os  # noqa: E402

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
app.mount("/api/static", StaticFiles(directory=_ASSETS_DIR), name="static")
