"""Timezone utilities — direct port of utils/timezones.py. Logic unchanged."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones

from bson import ObjectId

from db import users_col

DEFAULT_TIMEZONE = "Asia/Kolkata"

CURATED_TIMEZONES = [
    "Asia/Kolkata", "Asia/Dubai", "Asia/Singapore", "Asia/Hong_Kong", "Asia/Tokyo",
    "Asia/Shanghai", "Asia/Karachi", "Asia/Dhaka", "Asia/Bangkok", "Asia/Jakarta",
    "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Madrid", "Europe/Rome",
    "Europe/Amsterdam", "Europe/Moscow", "Africa/Johannesburg", "Africa/Cairo",
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Toronto", "America/Sao_Paulo", "America/Mexico_City",
    "Australia/Sydney", "Australia/Perth", "Pacific/Auckland", "UTC",
]


def all_timezones() -> list[str]:
    zones = [z for z in available_timezones() if "/" in z and not z.startswith(("Etc/", "SystemV/"))]
    return sorted(zones)


def timezone_options() -> list[str]:
    rest = [z for z in all_timezones() if z not in CURATED_TIMEZONES]
    return CURATED_TIMEZONES + rest


def tz_display_label(tz_name: str, at: datetime | None = None) -> str:
    at = at or datetime.now(timezone.utc)
    local = at.astimezone(ZoneInfo(tz_name))
    offset = local.strftime("%z") or "+0000"
    offset_fmt = f"{offset[:3]}:{offset[3:]}"
    abbr = local.tzname()
    return f"{tz_name} — UTC{offset_fmt} ({abbr})"


def local_input_to_utc(local_date, local_time, tz_name: str) -> datetime:
    naive = datetime.combine(local_date, local_time)
    local_aware = naive.replace(tzinfo=ZoneInfo(tz_name))
    return local_aware.astimezone(timezone.utc)


def utc_to_tz(dt_utc: datetime, tz_name: str) -> datetime:
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(ZoneInfo(tz_name))


def format_in_tz(dt_utc: datetime, tz_name: str) -> str:
    local = utc_to_tz(dt_utc, tz_name)
    return f"{local.strftime('%b %d, %Y at %I:%M %p')} {local.tzname()}"


def get_user_timezone(user_id: str) -> str:
    user = users_col().find_one({"_id": ObjectId(user_id)})
    if user and user.get("timezone"):
        return user["timezone"]
    return DEFAULT_TIMEZONE


def set_user_timezone(user_id: str, tz_name: str) -> None:
    users_col().update_one({"_id": ObjectId(user_id)}, {"$set": {"timezone": tz_name}})
