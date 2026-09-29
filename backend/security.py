"""Authentication + Role-Based Access Control (RBAC) — FastAPI port of the
Streamlit app's utils/auth.py.

Same three roles, same rules:
- "admin"      : full control.
- "instructor" : scoped to courses where instructor_id == their own id.
- "student"    : enrollment-gated learner.

Session is now a JWT in an httpOnly cookie instead of st.session_state.
There is still no public sign-up endpoint — only an admin (or the seed
admin created on first boot) can create accounts, matching the paid-
enrollment business model.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Cookie, Depends, Header, HTTPException, Response, status

from config import settings
from db import super_admins_col, users_col
from runtime_settings import get_setting

ROLES = ["admin", "instructor", "student"]


# --- Password helpers (identical to the Streamlit app) -----------------------

def hash_password(raw_password: str) -> bytes:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())


def verify_password(raw_password: str, hashed) -> bool:
    try:
        if isinstance(hashed, str):
            hashed = hashed.encode("utf-8")
        return bcrypt.checkpw(raw_password.encode("utf-8"), hashed)
    except (ValueError, TypeError):
        return False


# --- Seed admin on first boot (same logic as _seed_first_admin) -------------

def seed_first_admin():
    col = users_col()
    if col.find_one({"role": "admin"}):
        return
    email = settings.SEED_ADMIN_EMAIL
    password = settings.SEED_ADMIN_PASSWORD
    name = settings.SEED_ADMIN_NAME
    if not email or not password:
        return
    if col.find_one({"email": email}):
        col.update_one({"email": email}, {"$set": {"role": "admin"}})
        return
    col.insert_one(
        {
            "name": name,
            "email": email,
            "password_hash": hash_password(password),
            "role": "admin",
            "created_at": datetime.now(timezone.utc),
            "timezone": "Asia/Kolkata",
        }
    )


# --- JWT ----------------------------------------------------------------

def create_access_token(user: dict, tenant_db: str | None = None, company_code: str | None = None) -> str:
    # JWT_EXPIRE_MINUTES can be overridden by an admin from the Settings
    # page (stored in MongoDB) — falls back to the Render env var default
    # when no override has been saved. See runtime_settings.py.
    expire_minutes = get_setting("jwt_expire_minutes")
    payload = {
        "sub": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    # Multi-tenant (Checkpoint 2): which client company's database this
    # session belongs to. Absent in single-tenant deployments (Checkpoint
    # 1), where get_db() just falls back to settings.DB_NAME as always.
    if tenant_db:
        payload["db"] = tenant_db
    if company_code:
        payload["company_code"] = company_code
    payload["scope"] = "tenant"
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_platform_token(admin: dict) -> str:
    """A Super Admin session token. Deliberately has NO "db" claim — a
    super admin isn't tied to any one tenant's database, they operate
    against the platform registry (db.tenants_col(), db.super_admins_col())
    directly. The "scope": "platform" marker is what tells
    get_current_user and get_current_super_admin apart, so a token minted
    for one can never be used as the other, even by accident."""
    payload = {
        "sub": admin["id"],
        "name": admin["name"],
        "email": admin["email"],
        "role": "super_admin",
        "scope": "platform",
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def set_auth_cookie(response: Response, token: str) -> None:
    expire_minutes = get_setting("jwt_expire_minutes")
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=expire_minutes * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.COOKIE_NAME, path="/")


# --- Login / lookup -----------------------------------------------------

def authenticate(email: str, password: str) -> dict:
    email = email.strip().lower()
    user = users_col().find_one({"email": email})
    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password.")
    if user.get("disabled"):
        raise ValueError("This account has been deactivated. Contact an admin.")
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }


# --- FastAPI dependencies (replace require_login / require_role) -----------

def get_current_user(
    dsiar_session: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> dict:
    # Prefer the Authorization header (what the deployed frontend sends —
    # works across different onrender.com subdomains where third-party
    # cookies get blocked). Fall back to the cookie for local dev, where
    # the Vite proxy makes frontend and backend same-origin.
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif dsiar_session:
        token = dsiar_session

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid.")

    # A Super Admin (platform) token is a different account type entirely —
    # it doesn't belong to any tenant's users_col(), so it must never be
    # accepted here even by accident (there's no "db" claim on it for
    # TenantContextMiddleware to have set anyway, but this is the explicit,
    # readable check).
    if payload.get("scope") == "platform":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a tenant session.")

    # Re-check the user still exists / role hasn't changed since token issue.
    try:
        user = users_col().find_one({"_id": ObjectId(payload["sub"])})
    except InvalidId:
        user = None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account no longer exists.")
    if user.get("disabled"):
        # Kills any session already in progress the moment an admin
        # deactivates the account, not just new logins.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This account has been deactivated.")

    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }


def require_roles(*allowed_roles: str):
    """Usage: Depends(require_roles("admin", "instructor"))"""

    def _dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to do that.",
            )
        return user

    return _dependency


# --- Super Admin (platform-level, D'siar Tech's own operator account) ------

def authenticate_super_admin(email: str, password: str) -> dict:
    email = email.strip().lower()
    admin = super_admins_col().find_one({"email": email})
    if not admin or not verify_password(password, admin["password_hash"]):
        raise ValueError("Invalid email or password.")
    if admin.get("disabled"):
        raise ValueError("This account has been deactivated.")
    return {"id": str(admin["_id"]), "name": admin["name"], "email": admin["email"]}


def seed_platform_super_admin():
    """Same bootstrap pattern as Checkpoint 1's seed_first_admin(), but for
    the platform's own Super Admin account (db.super_admins_col(), never a
    tenant's users_col()). Runs once on boot; a no-op once a super admin
    already exists."""
    col = super_admins_col()
    if col.find_one({}):
        return
    email = settings.PLATFORM_SUPER_ADMIN_EMAIL
    password = settings.PLATFORM_SUPER_ADMIN_PASSWORD
    if not email or not password:
        return
    col.insert_one(
        {
            "name": settings.PLATFORM_SUPER_ADMIN_NAME,
            "email": email.strip().lower(),
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc),
        }
    )


def get_current_super_admin(
    authorization: str | None = Header(default=None),
) -> dict:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid.")
    if payload.get("scope") != "platform":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a platform session.")
    try:
        admin = super_admins_col().find_one({"_id": ObjectId(payload["sub"])})
    except InvalidId:
        admin = None
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account no longer exists.")
    if admin.get("disabled"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This account has been deactivated.")
    return {"id": str(admin["_id"]), "name": admin["name"], "email": admin["email"]}
