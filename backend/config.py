"""Central settings, loaded from environment variables (.env locally, Render
dashboard env vars in production). Nothing here is hardcoded so the same
image runs in dev and prod.

IMPORTANT: this points at a BRAND NEW database name (DB_NAME below) inside
the same free MongoDB Atlas cluster the Streamlit app already uses. The
Streamlit app's own database is never opened by this codebase — different
DB_NAME means a completely separate set of collections, so nothing here can
touch the working production data or tables.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str | None = None, required: bool = False) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


class Settings:
    # --- Mongo ---------------------------------------------------------------
    MONGO_URI: str = _get("MONGO_URI", required=True)
    # A NEW database name — separate from the Streamlit app's "dsiar_lms" DB.
    DB_NAME: str = _get("DB_NAME", "dsiar_lms_v2")

    # --- Auth / JWT ------------------------------------------------------------
    JWT_SECRET: str = _get("JWT_SECRET", required=True)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(_get("JWT_EXPIRE_MINUTES", "10080"))  # 7 days
    COOKIE_NAME: str = "dsiar_session"
    # "none" is required for a cross-site cookie (frontend and backend on
    # different Render domains); set COOKIE_SECURE=true in production (HTTPS).
    COOKIE_SECURE: bool = _get("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = _get("COOKIE_SAMESITE", "lax")  # "none" in prod cross-site

    # --- Seed admin (created once, on first boot, if no admin exists yet) -----
    # Checkpoint 2 has no equivalent for a TENANT admin (each client's first
    # admin is created through the Super Admin console when they're
    # onboarded, not an env var) — these are unused here, kept only so
    # nothing breaks if this same config.py is ever diffed against
    # Checkpoint 1's.
    SEED_ADMIN_EMAIL: str | None = _get("SEED_ADMIN_EMAIL")
    SEED_ADMIN_PASSWORD: str | None = _get("SEED_ADMIN_PASSWORD")
    SEED_ADMIN_NAME: str = _get("SEED_ADMIN_NAME", "Admin")

    # --- Platform super admin (D'siar Tech's own account — created once, on
    # first boot, if no super admin exists yet). This is infrastructure
    # bootstrapping, the same pattern Checkpoint 1 uses for its one admin —
    # not a course/business-data seed script. Every client company's own
    # first admin is created afterward through the Super Admin console
    # (POST /api/platform/tenants), never through an env var or a script.
    PLATFORM_SUPER_ADMIN_EMAIL: str | None = _get("PLATFORM_SUPER_ADMIN_EMAIL")
    PLATFORM_SUPER_ADMIN_PASSWORD: str | None = _get("PLATFORM_SUPER_ADMIN_PASSWORD")
    PLATFORM_SUPER_ADMIN_NAME: str = _get("PLATFORM_SUPER_ADMIN_NAME", "D'siar Tech")

    # --- Digital Samba (live sessions) -----------------------------------------
    DIGITALSAMBA_TEAM_ID: str | None = _get("DIGITALSAMBA_TEAM_ID")
    DIGITALSAMBA_DEVELOPER_KEY: str | None = _get("DIGITALSAMBA_DEVELOPER_KEY")

    # --- CORS --------------------------------------------------------------
    # Comma-separated list of allowed frontend origins, e.g.
    # "https://dsiar-lms.onrender.com,http://localhost:5173"
    CORS_ORIGINS: list[str] = [
        o.strip() for o in _get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
    ]


settings = Settings()
