"""MongoDB connection layer — direct port of the Streamlit app's utils/db.py,
minus the st.cache_resource (replaced with a plain module-level singleton,
since FastAPI has no equivalent decorator; the client is created once at
import time and reused for the life of the process, same effect).

CHECKPOINT 2 (multi-tenant): this process serves every client company from
ONE deployment, but each company's data lives in its OWN database inside the
same MongoDB Atlas cluster (settings.MONGO_URI). Which database a request
should use is decided at login (company code -> db name, via the tenant
registry below) and carried for the rest of that session inside the JWT.
Every request then has its "current tenant database" stashed in a
contextvar by the ASGI middleware in app.py, BEFORE any route code runs.

Nothing below this point (users_col(), courses_col(), ... every existing
module in the app) needed to change for multi-tenancy: they all already go
through get_db(), which is the one place that now resolves per-request
instead of always returning the same fixed database.
"""

import contextvars

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.server_api import ServerApi

from config import settings

_client: MongoClient | None = None

# The fixed, well-known database that holds the tenant registry itself —
# NOT tenant data. It has to live somewhere that doesn't depend on already
# knowing which tenant we're talking to (chicken-and-egg), so it's always
# this one literal name, in the same free cluster as everything else.
REGISTRY_DB_NAME = "platform_registry"

# Request-scoped "which tenant database should get_db() use right now".
# Set by TenantContextMiddleware (app.py) from the JWT's "db" claim before
# any dependency or route handler runs, and explicitly by the login
# endpoint itself (modules/auth.py) once it has resolved a company code.
# Falls back to settings.DB_NAME when nothing set it — this is what keeps
# ad-hoc scripts (seed_quizzes.py, tests, a REPL) and Checkpoint 1's old
# single-tenant behavior working unchanged.
_tenant_db_name: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_db_name", default=None
)


def set_tenant_db(db_name: str | None) -> None:
    _tenant_db_name.set(db_name)


def get_tenant_db_name() -> str | None:
    return _tenant_db_name.get()


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI, server_api=ServerApi("1"))
    return _client


def get_db() -> Database:
    return get_client()[_tenant_db_name.get() or settings.DB_NAME]


def tenants_col():
    """The platform-level registry: one document per client company —
    {company_code, db_name, name, plan, max_users, features, active,
    created_at}. Lives in REGISTRY_DB_NAME, never in a tenant's own
    database."""
    return get_client()[REGISTRY_DB_NAME]["tenants"]


def super_admins_col():
    """D'siar Tech's own platform-operator accounts — separate from every
    tenant's users_col(), same REGISTRY_DB_NAME as tenants_col(). A super
    admin doesn't belong to any client's database and never appears in any
    tenant's user list."""
    return get_client()[REGISTRY_DB_NAME]["super_admins"]


def count_active_users(db_name: str | None = None) -> int:
    """Active (non-disabled) user count for a tenant database — used to
    enforce plan seat limits. Defaults to whatever tenant is already
    current; pass db_name explicitly to check a different tenant (e.g. the
    Super Admin usage dashboard, which has no tenant of "its own")."""
    target = db_name or _tenant_db_name.get()
    if not target:
        return 0
    col = get_client()[target]["users"]
    return col.count_documents({"disabled": {"$ne": True}})


# --- Convenience collection accessors (same names as the Streamlit app) -----

def users_col():
    return get_db()["users"]


def courses_col():
    return get_db()["courses"]


def modules_col():
    return get_db()["modules"]


def lessons_col():
    return get_db()["lessons"]


def assignments_col():
    return get_db()["assignments"]


def submissions_col():
    return get_db()["submissions"]


def progress_col():
    return get_db()["progress"]


def enrollments_col():
    return get_db()["enrollments"]


def certificates_col():
    return get_db()["certificates"]


def live_sessions_col():
    return get_db()["live_sessions"]


def settings_col():
    """Single-document collection holding admin-editable operational
    settings (Digital Samba credentials, JWT session length) — see
    runtime_settings.py. Everything else stays exclusively in Render env
    vars."""
    return get_db()["settings"]


def quizzes_col():
    """One document per module (5 auto-graded questions each) — see
    modules/quizzes.py."""
    return get_db()["quizzes"]


def quiz_attempts_col():
    return get_db()["quiz_attempts"]


def ensure_indexes():
    """Same resilience pattern as the Streamlit app: wrapped in try/except so
    a leftover duplicate can't crash startup.

    Multi-tenant note: this only indexes whatever database get_db() resolves
    to at call time (the default/fallback db when called with no tenant
    context set, e.g. at process startup). Each tenant's OWN database gets
    its indexes created once, when that tenant is onboarded — see
    ensure_indexes_for(db_name) and scripts/create_tenant.py — not on every
    app boot, since the app never knows the full tenant list without asking
    the registry."""
    index_specs = [
        (users_col, "email", {"unique": True}),
        (modules_col, "course_id", {}),
        (lessons_col, "module_id", {}),
        (enrollments_col, [("user_id", 1), ("course_id", 1)], {"unique": True}),
        (progress_col, [("user_id", 1), ("lesson_id", 1)], {"unique": True}),
        (submissions_col, [("assignment_id", 1), ("user_id", 1)], {}),
        (certificates_col, [("user_id", 1), ("course_id", 1)], {"unique": True}),
        (certificates_col, "cert_id", {"unique": True}),
        (live_sessions_col, "course_id", {}),
        (live_sessions_col, "room_name", {"unique": True}),
        (quizzes_col, "module_id", {"unique": True}),
        (quiz_attempts_col, [("quiz_id", 1), ("user_id", 1)], {}),
    ]
    for col_fn, keys, kwargs in index_specs:
        try:
            col_fn().create_index(keys, **kwargs)
        except (DuplicateKeyError, OperationFailure):
            pass
    try:
        tenants_col().create_index("company_code", unique=True)
    except (DuplicateKeyError, OperationFailure):
        pass


def ensure_indexes_for(db_name: str) -> None:
    """Same as ensure_indexes(), but targeted at one specific tenant
    database regardless of what's currently in the contextvar. Used when
    onboarding a new client company."""
    token = _tenant_db_name.set(db_name)
    try:
        ensure_indexes()
    finally:
        _tenant_db_name.reset(token)
