"""Admin-only Settings API.

Lets an admin change a small, deliberately narrow set of operational
values from the app itself — Digital Samba credentials and the login
session length — without touching Render's dashboard or triggering a
redeploy. See runtime_settings.py for exactly which keys this covers and
why everything else (database URI, JWT signing secret, cookie flags, seed
admin credentials, CORS, the frontend's own build-time API URL) is
deliberately left out and stays in Render env vars only.

Secrets are masked in GET responses by default (last 4 characters shown)
and only returned in full when the caller explicitly asks with
?reveal=true — still admin-only, still over HTTPS.
"""

from fastapi import APIRouter, Depends

import runtime_settings as rs
from schemas import SettingsOut, SettingsUpdate
from security import require_roles

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask(value) -> str | None:
    if not value:
        return value
    value = str(value)
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * (len(value) - 4) + value[-4:]


def _build_response(reveal: bool) -> dict:
    effective = rs.get_effective_settings()
    dev_key = effective["digitalsamba_developer_key"]
    team_id = effective["digitalsamba_team_id"]
    expire = effective["jwt_expire_minutes"]
    pass_pct = effective["quiz_pass_percent"]
    max_attempts = effective["quiz_max_attempts"]
    shuffle_q = effective["quiz_shuffle_questions"]
    shuffle_o = effective["quiz_shuffle_options"]
    return {
        "digitalsamba_developer_key": dev_key["value"] if reveal else _mask(dev_key["value"]),
        "digitalsamba_developer_key_set": bool(dev_key["value"]),
        "digitalsamba_developer_key_source": dev_key["source"],
        "digitalsamba_team_id": team_id["value"] if reveal else _mask(team_id["value"]),
        "digitalsamba_team_id_set": bool(team_id["value"]),
        "digitalsamba_team_id_source": team_id["source"],
        "jwt_expire_minutes": expire["value"],
        "jwt_expire_minutes_source": expire["source"],
        "quiz_pass_percent": pass_pct["value"],
        "quiz_pass_percent_source": pass_pct["source"],
        "quiz_max_attempts": max_attempts["value"],
        "quiz_max_attempts_source": max_attempts["source"],
        "quiz_shuffle_questions": shuffle_q["value"],
        "quiz_shuffle_questions_source": shuffle_q["source"],
        "quiz_shuffle_options": shuffle_o["value"],
        "quiz_shuffle_options_source": shuffle_o["source"],
    }


@router.get("", response_model=SettingsOut)
def get_settings(reveal: bool = False, user: dict = Depends(require_roles("admin"))):
    return _build_response(reveal)


@router.patch("", response_model=SettingsOut)
def update_settings(body: SettingsUpdate, user: dict = Depends(require_roles("admin"))):
    updates = body.model_dump(exclude_unset=True)
    rs.save_settings(updates)
    return _build_response(reveal=False)
