"""DB-backed overrides for a small, deliberately narrow set of operational
settings that an admin can change from the UI at any time, with no redeploy.

Everything here falls back to the existing Render/.env value
(config.settings) until an admin saves an override in MongoDB — so nothing
breaks on first boot before this collection has any document in it.

Two kinds of keys live here:
  - Keys with a Render env var counterpart (digitalsamba_developer_key,
    digitalsamba_team_id, jwt_expire_minutes) — fall back to that env var
    until an admin saves an override.
  - Keys with NO env var at all (the quiz_* settings below) — these are
    purely app-level dials that only ever lived in the database, with a
    hardcoded default used until an admin saves a value.

Everything else (MONGO_URI, DB_NAME, CORS_ORIGINS, JWT_SECRET,
COOKIE_SECURE, COOKIE_SAMESITE, SEED_ADMIN_*, and the frontend's
VITE_API_BASE_URL) stays exclusively in Render env vars on purpose:
those are either bootstrap values needed before any database connection
exists, security-critical secrets that shouldn't be movable/visible in an
app UI, one-time-use values, or (for VITE_API_BASE_URL) baked into the
frontend at build time and structurally impossible to change at runtime
from anywhere, database included.
"""

import time
from threading import Lock

from config import settings as env_settings
from db import settings_col

SETTINGS_DOC_ID = "app_settings"


def _to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


# key -> schema. "env_attr" is the attribute on config.settings used as the
# fallback default until an admin saves an override for that key; "default"
# is used instead for keys with no env var counterpart at all.
ADMIN_SETTINGS_SCHEMA = {
    "digitalsamba_developer_key": {"env_attr": "DIGITALSAMBA_DEVELOPER_KEY", "secret": True, "cast": str},
    "digitalsamba_team_id": {"env_attr": "DIGITALSAMBA_TEAM_ID", "secret": True, "cast": str},
    "jwt_expire_minutes": {"env_attr": "JWT_EXPIRE_MINUTES", "secret": False, "cast": int},
    # Module quizzes: pass mark, retake cap (0 = unlimited), and whether
    # each attempt reshuffles questions/options — see modules/quizzes.py.
    "quiz_pass_percent": {"env_attr": None, "default": 60, "secret": False, "cast": int},
    "quiz_max_attempts": {"env_attr": None, "default": 0, "secret": False, "cast": int},
    "quiz_shuffle_questions": {"env_attr": None, "default": True, "secret": False, "cast": _to_bool},
    "quiz_shuffle_options": {"env_attr": None, "default": True, "secret": False, "cast": _to_bool},
}


def _default_for(key: str):
    schema = ADMIN_SETTINGS_SCHEMA[key]
    if schema.get("env_attr"):
        return getattr(env_settings, schema["env_attr"])
    return schema["default"]

_lock = Lock()
_cache = {"doc": None, "ts": 0.0}
_CACHE_TTL_SECONDS = 15  # short-lived cache so digital_samba.py / security.py
# don't hit MongoDB on every single request, while still picking up an
# admin's save within seconds without needing a process restart.


def _load_doc() -> dict:
    now = time.monotonic()
    with _lock:
        if _cache["doc"] is not None and (now - _cache["ts"]) < _CACHE_TTL_SECONDS:
            return _cache["doc"]
    doc = settings_col().find_one({"_id": SETTINGS_DOC_ID}) or {}
    with _lock:
        _cache["doc"] = doc
        _cache["ts"] = now
    return doc


def invalidate_cache() -> None:
    with _lock:
        _cache["doc"] = None
        _cache["ts"] = 0.0


def get_setting(key: str):
    """The effective value for one admin-configurable setting: the admin's
    saved override if there is one, else its default (Render/.env for the
    keys that have one, else the hardcoded default above)."""
    doc = _load_doc()
    value = doc.get(key)
    if value not in (None, ""):
        return value
    return _default_for(key)


def get_effective_settings() -> dict:
    """All admin-configurable settings, each tagged with whether its
    current value is coming from the database, a Render env var, or a
    hardcoded default."""
    doc = _load_doc()
    result = {}
    for key, schema in ADMIN_SETTINGS_SCHEMA.items():
        db_value = doc.get(key)
        has_override = db_value not in (None, "")
        result[key] = {
            "value": db_value if has_override else _default_for(key),
            "source": "database" if has_override else ("env" if schema.get("env_attr") else "default"),
        }
    return result


# --- Certificate branding (logo / signature) ---------------------------
#
# Lives in this same per-tenant settings document, but deliberately outside
# ADMIN_SETTINGS_SCHEMA above: those are small scalar values with a generic
# get/set/mask UI, while a logo/signature is an uploaded image (stored as a
# base64 data: URL — see modules/settings.py's upload endpoint, same
# reasoning as course thumbnails in modules/courses.py: Render's free-tier
# disk doesn't survive a redeploy, a database field does). Falls back, in
# utils/certificate_image.py, to the older file-based
# backend/assets/{company_code}_logo.png convention if neither this nor an
# upload exists yet — so a client onboarded before this feature existed
# (D'siar Tech itself) keeps working unchanged.
BRANDING_KEYS = {"logo": "branding_logo", "signature": "branding_signature"}


def get_branding() -> dict:
    doc = _load_doc()
    return {name: doc.get(key) for name, key in BRANDING_KEYS.items()}


def save_branding(name: str, data_url: str | None) -> None:
    """name: "logo" or "signature". data_url=None clears it (falls back to
    the file-based asset, then plain text, same as if it were never set)."""
    key = BRANDING_KEYS[name]
    if data_url:
        settings_col().update_one({"_id": SETTINGS_DOC_ID}, {"$set": {key: data_url}}, upsert=True)
    else:
        settings_col().update_one({"_id": SETTINGS_DOC_ID}, {"$unset": {key: ""}}, upsert=True)
    invalidate_cache()


def save_settings(updates: dict) -> None:
    """updates: dict of key -> new value. Passing None or "" for a key
    clears the override so that key falls back to the env var again. Unknown
    keys are silently ignored (defense in depth — the API layer already
    validates via a pydantic schema with only these three fields)."""
    to_set = {}
    to_unset = {}
    for key, value in updates.items():
        if key not in ADMIN_SETTINGS_SCHEMA:
            continue
        if value in (None, ""):
            to_unset[key] = ""
        else:
            cast = ADMIN_SETTINGS_SCHEMA[key]["cast"]
            to_set[key] = cast(value)

    update_doc = {}
    if to_set:
        update_doc["$set"] = to_set
    if to_unset:
        update_doc["$unset"] = to_unset
    if update_doc:
        settings_col().update_one({"_id": SETTINGS_DOC_ID}, update_doc, upsert=True)
    invalidate_cache()
