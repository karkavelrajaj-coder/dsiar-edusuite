"""Port of views/admin_live_sessions.py (schedule/edit/delete, host
start/end) and views/live_sessions.py (student-facing join), backed by
Digital Samba exactly as before — the same UUID-vs-friendly_url handling,
the same 'always generate a fresh room_name' rule, the same ended_at-wins
status logic."""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from db import courses_col, enrollments_col, live_sessions_col
from schemas import CreateLiveSessionRequest, UpdateLiveSessionRequest
from security import get_current_user, require_roles
from serializers import live_session_out
from utils.digital_samba import create_room, end_room_now, generate_join_link
from utils.live_sessions import (
    can_student_join,
    generate_room_name,
    room_expiry_for,
    session_status,
)
from utils.timezones import local_input_to_utc

router = APIRouter(prefix="/api", tags=["live-sessions"])


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id.")


def _managed_course_ids(user: dict) -> list[str]:
    query = {} if user["role"] == "admin" else {"instructor_id": user["id"]}
    return [str(c["_id"]) for c in courses_col().find(query)]


def _assert_can_manage_session(user: dict, session: dict) -> None:
    course = courses_col().find_one({"_id": _oid(session["course_id"])})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    if user["role"] == "admin":
        return
    if user["role"] == "instructor" and course.get("instructor_id") == user["id"]:
        return
    raise HTTPException(status_code=403, detail="You don't manage this session.")


def _with_status(doc: dict) -> dict:
    item = live_session_out(doc)
    item["status"] = session_status(doc["scheduled_at"], doc["duration_minutes"], doc.get("ended_at"))
    return item


# --- Admin/instructor: manage sessions ---------------------------------

@router.get("/live-sessions/manage")
def manage_list(user: dict = Depends(require_roles("admin", "instructor"))):
    course_ids = _managed_course_ids(user)
    docs = live_sessions_col().find({"course_id": {"$in": course_ids}}).sort("scheduled_at", -1)
    return [_with_status(s) for s in docs]


@router.post("/live-sessions")
def schedule_session(body: CreateLiveSessionRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    course = courses_col().find_one({"_id": _oid(body.course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    if user["role"] == "instructor" and course.get("instructor_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You don't manage this course.")

    scheduled_at = local_input_to_utc(body.date, body.time, body.timezone)
    doc = {
        "course_id": body.course_id,
        "title": body.title,
        "description": body.description,
        "scheduled_at": scheduled_at,
        "scheduled_tz": body.timezone,
        "duration_minutes": int(body.duration_minutes),
        "room_name": generate_room_name(),
        "host_id": user["id"],
        "host_name": user["name"],
        "created_at": datetime.now(timezone.utc),
    }
    result = live_sessions_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return _with_status(doc)


@router.patch("/live-sessions/{session_id}")
def update_session(session_id: str, body: UpdateLiveSessionRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    session = live_sessions_col().find_one({"_id": _oid(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _assert_can_manage_session(user, session)

    update = {}
    if body.title is not None:
        update["title"] = body.title
    if body.description is not None:
        update["description"] = body.description
    if body.duration_minutes is not None:
        update["duration_minutes"] = int(body.duration_minutes)

    # Date/time/timezone are entangled — recompute scheduled_at if any changed.
    if body.date is not None or body.time is not None or body.timezone is not None:
        tz = body.timezone or session.get("scheduled_tz", "Asia/Kolkata")
        from utils.timezones import utc_to_tz
        current_local = utc_to_tz(session["scheduled_at"], tz)
        new_date = body.date or current_local.date()
        new_time = body.time or current_local.time()
        update["scheduled_at"] = local_input_to_utc(new_date, new_time, tz)
        update["scheduled_tz"] = tz

    if update:
        live_sessions_col().update_one({"_id": session["_id"]}, {"$set": update})
    return _with_status(live_sessions_col().find_one({"_id": session["_id"]}))


@router.delete("/live-sessions/{session_id}")
def delete_session(session_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    session = live_sessions_col().find_one({"_id": _oid(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _assert_can_manage_session(user, session)
    live_sessions_col().delete_one({"_id": session["_id"]})
    return {"ok": True}


@router.post("/live-sessions/{session_id}/start")
def start_session(session_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    """Host clicks Start/rejoin. Mirrors admin_live_sessions.py exactly:
    a brand-new room is created only if the session has never been started,
    was ended, or is somehow missing a room_id — otherwise the host rejoins
    the existing room. ALWAYS generates a fresh room_name for a new room,
    never reusing the old one (friendly_url must be globally unique)."""
    session = live_sessions_col().find_one({"_id": _oid(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _assert_can_manage_session(user, session)

    needs_new_room = bool(session.get("ended_at")) or not session.get("started_at") or not session.get("room_id")
    if needs_new_room:
        room_name = generate_room_name()
        expiry = room_expiry_for(session["scheduled_at"], session["duration_minutes"])
        try:
            room = create_room(room_name, expiry)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Couldn't create the video room: {e}")
        live_sessions_col().update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "room_name": room_name,
                    "room_id": room["id"],
                    "started_at": datetime.now(timezone.utc),
                },
                "$unset": {"ended_at": ""},
            },
        )
        session = live_sessions_col().find_one({"_id": session["_id"]})

    try:
        join_link = generate_join_link(session["room_id"], user["name"], role="teacher")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Couldn't generate your join link: {e}")

    return {"join_link": join_link, "session": _with_status(session)}


@router.post("/live-sessions/{session_id}/end")
def end_session(session_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    session = live_sessions_col().find_one({"_id": _oid(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _assert_can_manage_session(user, session)

    if session.get("room_id"):
        try:
            end_room_now(session["room_id"])
        except Exception:
            pass  # room may already be closed — mark it finished anyway
    live_sessions_col().update_one({"_id": session["_id"]}, {"$set": {"ended_at": datetime.now(timezone.utc)}})
    return {"ok": True}


# --- Student-facing: view + join -----------------------------------------

@router.get("/my/live-sessions")
def my_live_sessions(user: dict = Depends(get_current_user)):
    enrolled_course_ids = [e["course_id"] for e in enrollments_col().find({"user_id": user["id"]})]
    if not enrolled_course_ids:
        return []
    docs = live_sessions_col().find({"course_id": {"$in": enrolled_course_ids}}).sort("scheduled_at", -1)
    out = []
    for s in docs:
        item = _with_status(s)
        can_join, reason = can_student_join(s)
        item["can_join"] = can_join
        item["join_blocked_reason"] = reason
        course = courses_col().find_one({"_id": _oid(s["course_id"])})
        item["course_title"] = course["title"] if course else "Unknown"
        out.append(item)
    return out


@router.post("/live-sessions/{session_id}/join")
def join_session(session_id: str, user: dict = Depends(get_current_user)):
    session = live_sessions_col().find_one({"_id": _oid(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    is_enrolled = enrollments_col().find_one({"user_id": user["id"], "course_id": session["course_id"]})
    if not is_enrolled:
        raise HTTPException(status_code=403, detail="You're not enrolled in this course.")

    can_join, reason = can_student_join(session)
    if not can_join:
        raise HTTPException(status_code=403, detail=reason)

    try:
        join_link = generate_join_link(session["room_id"], user["name"], role="student")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Couldn't join right now: {e}")

    return {"join_link": join_link}
