"""Port of the enrollment half of views/admin_users.py + the
admin/instructor self-enroll-preview button in views/catalog.py.

No public sign-up, no self-enroll for students — matches the paid-
enrollment business model: only an admin enrolls a student in a course.
"""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import certificates_col, courses_col, enrollments_col, users_col
from schemas import CreateEnrollmentRequest
from security import get_current_user, require_roles
from serializers import enrollment_out
from utils.tracks import display_title, normalize_track

router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])


@router.get("")
def list_enrollments(user: dict = Depends(get_current_user)):
    if user["role"] == "admin":
        docs = list(enrollments_col().find())
    else:
        docs = list(enrollments_col().find({"user_id": user["id"]}))
    out = []
    for e in docs:
        item = enrollment_out(e)
        student = users_col().find_one({"_id": ObjectId(e["user_id"])})
        course = courses_col().find_one({"_id": ObjectId(e["course_id"])})
        item["student_name"] = student["name"] if student else "Unknown"
        item["student_email"] = student["email"] if student else "—"
        track = normalize_track(course.get("track")) if course else "course"
        item["course_title"] = display_title(course["title"], track) if course else "Unknown"
        item["track"] = track
        out.append(item)
    return out


@router.post("")
def create_enrollment(body: CreateEnrollmentRequest, user: dict = Depends(require_roles("admin"))):
    # No track here — the course itself already carries one (set at
    # creation, editable via PATCH /courses/{id}), the same for every
    # student. See modules/courses.py.
    existing = enrollments_col().find_one({"user_id": body.user_id, "course_id": body.course_id})
    if existing:
        raise HTTPException(status_code=409, detail="This student is already enrolled in that course.")
    doc = {
        "user_id": body.user_id,
        "course_id": body.course_id,
        "enrolled_at": datetime.now(timezone.utc),
    }
    result = enrollments_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return enrollment_out(doc)


@router.post("/preview/{course_id}")
def self_enroll_preview(course_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    """Admins can self-enroll to preview ANY course's content, same as the
    'Enroll (preview)' button in the old catalog.py. Instructors are NOT
    admins, though: they may only preview courses assigned to them (which
    they already have automatic access to via course_detail's
    _has_course_access — this endpoint mainly exists for admin's benefit
    now, but stays open to instructors for their own courses too)."""
    if user["role"] == "instructor":
        course = courses_col().find_one({"_id": ObjectId(course_id)})
        if not course:
            raise HTTPException(status_code=404, detail="Course not found.")
        if course.get("instructor_id") != user["id"]:
            raise HTTPException(status_code=403, detail="You can only access courses assigned to you.")

    existing = enrollments_col().find_one({"user_id": user["id"], "course_id": course_id})
    if existing:
        return enrollment_out(existing)
    doc = {
        "user_id": user["id"],
        "course_id": course_id,
        "enrolled_at": datetime.now(timezone.utc),
    }
    result = enrollments_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return enrollment_out(doc)


@router.delete("/{enrollment_id}")
def delete_enrollment(enrollment_id: str, user: dict = Depends(require_roles("admin"))):
    # Look the enrollment up first (rather than delete_one blind) so we know
    # which user/course to also revoke the certificate for — the confirm
    # dialog on the frontend promises the student loses "certificate
    # eligibility" too, so leaving an already-issued certificate downloadable
    # after access is pulled would contradict that.
    enrollment = enrollments_col().find_one({"_id": ObjectId(enrollment_id)})
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found.")
    enrollments_col().delete_one({"_id": enrollment["_id"]})
    certificates_col().delete_one({"user_id": enrollment["user_id"], "course_id": enrollment["course_id"]})
    return {"ok": True}
