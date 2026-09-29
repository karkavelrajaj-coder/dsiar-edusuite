"""Super Admin (platform-level) API — Checkpoint 2 only.

This is D'siar Tech's own console for running the LMS as a service: log in
as the platform operator (not a member of any client's tenant), onboard a
new client company (register them + create their first Admin login, in one
call — no script, no direct DB edit), see every client's usage, and adjust
a client's plan/seat-limit/feature-flags or suspend them.

A Super Admin session is a completely separate account type from every
tenant's users — see db.super_admins_col() and
security.get_current_super_admin(). It never appears in, and can never log
into, any client's own /api/auth/login.
"""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Response, status

from db import count_active_users, set_tenant_db, tenants_col, users_col
from schemas import CreateTenantRequest, PlatformLoginRequest, UpdateTenantRequest
from security import (
    authenticate_super_admin,
    clear_auth_cookie,
    create_platform_token,
    get_current_super_admin,
    hash_password,
    set_auth_cookie,
)
from utils.tenants import create_tenant, normalize_company_code

router = APIRouter(prefix="/api/platform", tags=["platform"])


# --- Auth --------------------------------------------------------------

@router.post("/auth/login")
def platform_login(body: PlatformLoginRequest, response: Response):
    try:
        admin = authenticate_super_admin(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    token = create_platform_token(admin)
    set_auth_cookie(response, token)
    return {**admin, "role": "super_admin", "access_token": token}


@router.post("/auth/logout")
def platform_logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/auth/me")
def platform_me(admin: dict = Depends(get_current_super_admin)):
    return {**admin, "role": "super_admin"}


# --- Tenants -------------------------------------------------------------

def _tenant_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "company_code": doc["company_code"],
        "company_name": doc.get("name"),
        "db_name": doc.get("db_name"),
        "plan": doc.get("plan", "starter"),
        "max_users": doc.get("max_users"),
        "features": doc.get("features", {}),
        "active": doc.get("active", True),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "active_users": count_active_users(doc.get("db_name")),
    }


@router.get("/tenants")
def list_tenants(admin: dict = Depends(get_current_super_admin)):
    return [_tenant_out(t) for t in tenants_col().find().sort("created_at", 1)]


@router.post("/tenants")
def create_tenant_endpoint(body: CreateTenantRequest, admin: dict = Depends(get_current_super_admin)):
    """The Super Admin console's "Add client" action — the only supported
    way to onboard a new client company in Checkpoint 2. Registers the
    tenant, creates its first Admin login, and indexes its (new, empty)
    database, all in one call."""
    code = normalize_company_code(body.company_code)
    if tenants_col().find_one({"company_code": code}):
        raise HTTPException(status_code=409, detail=f"Company code '{code}' is already registered.")
    db_name = f"lms_{code}"
    if tenants_col().find_one({"db_name": db_name}):
        raise HTTPException(status_code=409, detail="That database name is already in use — pick a different company code.")

    tenant = create_tenant(
        company_code=code,
        db_name=db_name,
        name=body.company_name.strip(),
        plan=body.plan,
        max_users=body.max_users,
        features=body.features,
    )

    from db import ensure_indexes_for  # local import to avoid a top-level circularity

    set_tenant_db(db_name)
    ensure_indexes_for(db_name)
    email = body.admin_email.strip().lower()
    users_col().insert_one(
        {
            "name": body.admin_name.strip(),
            "email": email,
            "password_hash": hash_password(body.admin_password),
            "role": "admin",
            "created_at": datetime.now(timezone.utc),
            "timezone": "Asia/Kolkata",
        }
    )
    set_tenant_db(None)

    # insert_one() (inside create_tenant()) mutated `tenant` in place with
    # its new _id, same pymongo behavior every other module in this app
    # already relies on.
    return _tenant_out(tenant)


@router.patch("/tenants/{company_code}")
def update_tenant(company_code: str, body: UpdateTenantRequest, admin: dict = Depends(get_current_super_admin)):
    """Change a client's plan/seat-limit/feature-flags, or suspend/reinstate
    them (active=false blocks every login for that company without
    touching or deleting any of their data)."""
    code = normalize_company_code(company_code)
    tenant = tenants_col().find_one({"company_code": code})
    if not tenant:
        raise HTTPException(status_code=404, detail="No such company code.")
    update = {}
    if body.plan is not None:
        update["plan"] = body.plan
    if body.max_users is not None:
        update["max_users"] = body.max_users
    if body.features is not None:
        update["features"] = {**tenant.get("features", {}), **body.features}
    if body.active is not None:
        update["active"] = body.active
    if update:
        tenants_col().update_one({"_id": tenant["_id"]}, {"$set": update})
    return _tenant_out(tenants_col().find_one({"_id": tenant["_id"]}))
