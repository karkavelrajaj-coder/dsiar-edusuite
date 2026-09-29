from fastapi import APIRouter, Depends, HTTPException, Response, status

from db import set_tenant_db
from security import (
    authenticate,
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    set_auth_cookie,
)
from schemas import LoginRequest, UserOut
from utils.tenants import current_tenant, resolve_tenant

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, response: Response):
    """Returns the JWT in the response body (as access_token) AND still sets
    it as an httpOnly cookie. The frontend uses the body token, sent as an
    Authorization: Bearer header on every request — this is what actually
    works when the frontend and backend are deployed on different
    *.onrender.com subdomains, since browsers (Incognito/private mode
    especially) block third-party cookies between them even though both
    are technically "onrender.com". The cookie is kept as a bonus for local
    dev, where the Vite proxy makes everything same-origin and the cookie
    alone is enough.

    Checkpoint 2 (multi-tenant): the company code picks which client's
    database to authenticate against BEFORE we even look the email up —
    the same email can exist in more than one client's database, and
    without this we wouldn't know which one to check. Resolving the
    tenant and setting it here (rather than relying on the request
    middleware, which only knows a tenant from an existing token) is what
    makes login itself work; every request AFTER login carries the
    resolved database inside its own JWT, and TenantContextMiddleware
    (app.py) picks it up from there."""
    try:
        tenant = resolve_tenant(body.company_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    set_tenant_db(tenant["db_name"])
    try:
        user = authenticate(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    token = create_access_token(user, tenant_db=tenant["db_name"], company_code=tenant["company_code"])
    set_auth_cookie(response, token)
    return {
        **user,
        "access_token": token,
        "company_code": tenant["company_code"],
        "company_name": tenant.get("name"),
        "features": tenant.get("features", {}),
    }


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    tenant = current_tenant()
    return {
        **user,
        "company_code": tenant.get("company_code") if tenant else None,
        "company_name": tenant.get("name") if tenant else None,
        "features": tenant.get("features", {}) if tenant else {},
    }
