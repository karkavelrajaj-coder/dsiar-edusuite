"""Turns raw Mongo documents into JSON-safe dicts (ObjectId -> str,
datetime -> isoformat), matching the same field names the Streamlit views
used so the frontend logic maps 1:1 onto the old app's behavior."""

from datetime import datetime


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def user_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "role": doc.get("role"),
        "timezone": doc.get("timezone"),
        "disabled": bool(doc.get("disabled")),
        "created_at": _iso(doc.get("created_at")),
    }


def course_out(doc: dict) -> dict:
    from utils.tracks import normalize_track  # local import to avoid a top-level circularity

    return {
        "id": str(doc["_id"]),
        "title": doc.get("title"),
        "category": doc.get("category", ""),
        "description": doc.get("description", ""),
        "thumbnail_url": doc.get("thumbnail_url", ""),
        "is_free": doc.get("is_free", True),
        "instructor_id": doc.get("instructor_id"),
        "order": doc.get("order", 0),
        "track": normalize_track(doc.get("track")),
    }


def module_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "course_id": doc.get("course_id"),
        "title": doc.get("title"),
        "order": doc.get("order", 0),
    }


def lesson_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "module_id": doc.get("module_id"),
        "title": doc.get("title"),
        "youtube_id": doc.get("youtube_id", ""),
        "ppt_link": doc.get("ppt_link", ""),
        "colab_link": doc.get("colab_link", ""),
        "dataset_link": doc.get("dataset_link", ""),
        "order": doc.get("order", 0),
    }


def enrollment_out(doc: dict) -> dict:
    # No track here in Checkpoint 2 — see course_out(); track is a course
    # attribute now, not an enrollment one.
    return {
        "id": str(doc["_id"]),
        "user_id": doc.get("user_id"),
        "course_id": doc.get("course_id"),
        "enrolled_at": _iso(doc.get("enrolled_at")),
    }


def assignment_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "course_id": doc.get("course_id"),
        "title": doc.get("title"),
        "description": doc.get("description", ""),
        "due_date": doc.get("due_date"),
    }


def submission_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "assignment_id": doc.get("assignment_id"),
        "user_id": doc.get("user_id"),
        "link_or_text": doc.get("link_or_text"),
        "submitted_at": _iso(doc.get("submitted_at")),
        "grade": doc.get("grade"),
        "feedback": doc.get("feedback", ""),
        "status": doc.get("status", "pending"),
    }


def certificate_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "user_id": doc.get("user_id"),
        "course_id": doc.get("course_id"),
        "cert_id": doc.get("cert_id"),
        "issued_at": _iso(doc.get("issued_at")),
    }


def quiz_out(doc: dict) -> dict:
    """Student-facing view of a module quiz: never includes
    correct_option_ids — those only ever go to admin/instructor
    (quiz_manage_out) or come back in a submit response's per-question
    review, after grading."""
    return {
        "id": str(doc["_id"]),
        "module_id": doc.get("module_id"),
        "questions": [
            {"id": q["id"], "type": q["type"], "text": q["text"], "options": q["options"]}
            for q in doc.get("questions", [])
        ],
    }


def quiz_manage_out(doc: dict) -> dict:
    """Admin/instructor view — includes correct_option_ids so the quiz
    builder can show/edit the answer key."""
    return {
        "id": str(doc["_id"]),
        "module_id": doc.get("module_id"),
        "questions": doc.get("questions", []),
        "updated_at": _iso(doc.get("updated_at")),
    }


def quiz_attempt_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "quiz_id": doc.get("quiz_id"),
        "module_id": doc.get("module_id"),
        "user_id": doc.get("user_id"),
        "attempt_number": doc.get("attempt_number"),
        "score_percent": doc.get("score_percent"),
        "passed": doc.get("passed"),
        "submitted_at": _iso(doc.get("submitted_at")),
    }


def live_session_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "course_id": doc.get("course_id"),
        "title": doc.get("title"),
        "description": doc.get("description", ""),
        "scheduled_at": _iso(doc.get("scheduled_at")),
        "scheduled_tz": doc.get("scheduled_tz"),
        "duration_minutes": doc.get("duration_minutes"),
        "room_name": doc.get("room_name"),
        "room_id": doc.get("room_id"),
        "host_id": doc.get("host_id"),
        "host_name": doc.get("host_name"),
        "started_at": _iso(doc.get("started_at")),
        "ended_at": _iso(doc.get("ended_at")),
        "created_at": _iso(doc.get("created_at")),
    }
