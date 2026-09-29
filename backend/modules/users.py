"""Port of views/admin_users.py (account creation, role changes) plus the
per-user timezone preference from utils/timezones.py."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import count_active_users, users_col
from schemas import CreateUserRequest, SetTimezoneRequest, UpdateRoleRequest, UpdateStatusRequest
from security import ROLES, get_current_user, hash_password, require_roles
from serializers import user_out
from utils.tenants import current_tenant
from utils.timezones import set_user_timezone, timezone_options

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users")
def list_users(user: dict = Depends(require_roles("admin"))):
    return [user_out(u) for u in users_col().find().sort("created_at", 1)]


@router.get("/users/instructors")
def list_instructors(user: dict = Depends(require_roles("admin"))):
    """For the 'assign to instructor' dropdown when creating/editing a course.
    Deactivated instructors are excluded — they shouldn't be assignable to
    new courses, though a course they already teach keeps their name."""
    return [user_out(u) for u in users_col().find({"role": "instructor", "disabled": {"$ne": True}})]


@router.post("/users")
def create_user(body: CreateUserRequest, user: dict = Depends(require_roles("admin"))):
    email = body.email.strip().lower()
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")
    if users_col().find_one({"email": email}):
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    # Checkpoint 2: hard seat limit, matching how TalentLMS and most
    # multi-tenant LMS SaaS platforms enforce plans — creation is blocked
    # outright once the tenant's plan limit is reached, not just warned.
    tenant = current_tenant()
    if tenant and tenant.get("max_users"):
        active_count = count_active_users()
        if active_count >= tenant["max_users"]:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Your plan allows up to {tenant['max_users']} active users, and you're "
                    f"already at that limit. Upgrade your plan to add more."
                ),
            )

    doc = {
        "name": body.name.strip(),
        "email": email,
        "password_hash": hash_password(body.password),
        "role": body.role,
        "created_at": datetime.now(timezone.utc),
        "timezone": "Asia/Kolkata",
    }
    result = users_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return user_out(doc)


@router.patch("/users/{user_id}/role")
def update_role(user_id: str, body: UpdateRoleRequest, user: dict = Depends(require_roles("admin"))):
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")
    if user_id == user["id"] and body.role != "admin":
        raise HTTPException(status_code=400, detail="You can't demote your own account.")
    result = users_col().update_one({"_id": ObjectId(user_id)}, {"$set": {"role": body.role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"ok": True}


@router.patch("/users/{user_id}/status")
def update_status(user_id: str, body: UpdateStatusRequest, user: dict = Depends(require_roles("admin"))):
    """Deactivate/reactivate an account (soft delete). A deactivated account
    can't log in and drops out of enroll/assign pickers, but nothing about
    it — enrollments, progress, quiz attempts, submissions, certificates,
    or (for an instructor) the courses they teach — is touched or deleted.
    Reactivating just flips the flag back."""
    if user_id == user["id"] and body.disabled:
        raise HTTPException(status_code=400, detail="You can't deactivate your own account.")

    target = users_col().find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if body.disabled and target["role"] == "admin":
        other_active_admins = users_col().count_documents(
            {"role": "admin", "disabled": {"$ne": True}, "_id": {"$ne": target["_id"]}}
        )
        if other_active_admins == 0:
            raise HTTPException(status_code=400, detail="Can't deactivate the last active admin account.")

    # Reactivating also occupies a seat — same hard limit as creating a
    # brand new user, so a plan can't be worked around by disabling and
    # re-enabling accounts.
    if not body.disabled and target.get("disabled"):
        tenant = current_tenant()
        if tenant and tenant.get("max_users"):
            active_count = count_active_users()
            if active_count >= tenant["max_users"]:
                raise HTTPException(
                    status_code=402,
                    detail=(
                        f"Your plan allows up to {tenant['max_users']} active users, and you're "
                        f"already at that limit. Upgrade your plan to reactivate this account."
                    ),
                )

    users_col().update_one({"_id": target["_id"]}, {"$set": {"disabled": body.disabled}})
    return {"ok": True}


@router.get("/timezones")
def get_timezone_options(user: dict = Depends(get_current_user)):
    return {"options": timezone_options()}


@router.patch("/users/me/timezone")
def update_my_timezone(body: SetTimezoneRequest, user: dict = Depends(get_current_user)):
    set_user_timezone(user["id"], body.timezone)
    return {"ok": True, "timezone": body.timezone}
