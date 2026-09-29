"""Live session scheduling helpers — port of utils/live_sessions.py, minus
the two Streamlit-iframe render_room()/render_host_room() functions (the
React frontend embeds the Digital Samba SDK directly; the backend's job is
only to hand it a signed join link).
"""

import uuid
from datetime import datetime, timedelta, timezone

JOIN_OPENS_MINUTES_BEFORE = 10
JOIN_STAYS_OPEN_MINUTES_AFTER_END = 30
ROOM_LIFETIME_BUFFER_HOURS = 6


def generate_room_name() -> str:
    return f"dsiar-{uuid.uuid4().hex[:16]}"


def session_status(scheduled_at: datetime, duration_minutes: int, ended_at: datetime | None = None) -> str:
    if ended_at:
        return "ended"
    now = datetime.now(timezone.utc)
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    end = scheduled_at + timedelta(minutes=duration_minutes)
    if now < scheduled_at:
        return "upcoming"
    if now <= end:
        return "live"
    return "ended"


def join_window_open(scheduled_at: datetime, duration_minutes: int) -> bool:
    now = datetime.now(timezone.utc)
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    opens_at = scheduled_at - timedelta(minutes=JOIN_OPENS_MINUTES_BEFORE)
    closes_at = scheduled_at + timedelta(minutes=duration_minutes + JOIN_STAYS_OPEN_MINUTES_AFTER_END)
    return opens_at <= now <= closes_at


def can_student_join(session: dict) -> tuple[bool, str]:
    if session.get("ended_at"):
        return False, "This session has been marked finished by the host."
    if not join_window_open(session["scheduled_at"], session["duration_minutes"]):
        return False, "Join opens 10 minutes before the scheduled start time."
    if not session.get("started_at"):
        return False, "Waiting for the host to start this session — check back shortly."
    if not session.get("room_id"):
        return False, "Session isn't ready yet — try again in a moment."
    return True, ""


def room_expiry_for(scheduled_at: datetime, duration_minutes: int) -> datetime:
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    return scheduled_at + timedelta(minutes=duration_minutes, hours=ROOM_LIFETIME_BUFFER_HOURS)
