"""Tenant registry lookups — Checkpoint 2 (multi-tenant) only.

The registry is a small collection (db.tenants_col(), living in the fixed
REGISTRY_DB_NAME database, never in a tenant's own database) with one
document per client company:

    {
        "company_code": "dsiar",       # what the client types at login
        "db_name": "dsiar_lms_v2",     # which database holds their data
        "name": "D'siar Tech",         # display name
        "active": True,
        "created_at": datetime(...),
    }

Company codes are matched case-insensitively and stored lowercase.
"""

from datetime import datetime, timezone

from db import get_tenant_db_name, tenants_col


def normalize_company_code(raw: str) -> str:
    return (raw or "").strip().lower()


def resolve_tenant(company_code: str) -> dict:
    """Returns the tenant registry doc for this company code, or raises
    ValueError with a message safe to show at login (doesn't reveal whether
    the company code exists vs. is just inactive, to avoid leaking which
    codes are real)."""
    code = normalize_company_code(company_code)
    if not code:
        raise ValueError("Enter your company code.")
    tenant = tenants_col().find_one({"company_code": code})
    if not tenant or not tenant.get("active", True):
        raise ValueError("Unrecognized company code.")
    return tenant


DEFAULT_FEATURES = {"live_sessions": False}


def create_tenant(
    company_code: str,
    db_name: str,
    name: str,
    plan: str = "starter",
    max_users: int | None = 100,
    features: dict | None = None,
) -> dict:
    """Registers a new client company. Does NOT create their admin user —
    see modules/platform.py's create_tenant endpoint, which does both in
    one step (the Super Admin console's "Add client" action)."""
    code = normalize_company_code(company_code)
    if not code:
        raise ValueError("company_code is required.")
    if tenants_col().find_one({"company_code": code}):
        raise ValueError(f"Company code '{code}' is already registered.")
    doc = {
        "company_code": code,
        "db_name": db_name,
        "name": name,
        "plan": plan,
        "max_users": max_users,
        "features": {**DEFAULT_FEATURES, **(features or {})},
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    tenants_col().insert_one(doc)
    return doc


def current_tenant() -> dict | None:
    """The tenant registry doc for whichever database the current request
    is already scoped to (set by TenantContextMiddleware / login). None
    inside a Super Admin (platform) request, which has no tenant of its
    own."""
    db_name = get_tenant_db_name()
    if not db_name:
        return None
    return tenants_col().find_one({"db_name": db_name})
