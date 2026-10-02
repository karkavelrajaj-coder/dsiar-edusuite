"""Port of views/catalog.py, views/admin_courses.py, views/my_learning.py,
views/course_player.py — course catalog, course/module/lesson CRUD (scoped
by role exactly like the Streamlit admin_courses.py: admin sees/edits every
course, instructor only their own via instructor_id), and lesson-completion
progress tracking (which triggers certificate issuance, same as the
Streamlit course_player.py "Mark as complete" button).
"""

import base64
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from db import (
    courses_col,
    enrollments_col,
    lessons_col,
    modules_col,
    progress_col,
    quiz_attempts_col,
    quizzes_col,
)
from utils.tracks import VALID_TRACKS, display_title, normalize_track
from schemas import (
    CreateCourseRequest,
    CreateLessonRequest,
    CreateModuleRequest,
    UpdateCourseRequest,
    UpdateLessonRequest,
    UpdateModuleRequest,
)
from security import get_current_user, require_roles
from serializers import course_out, lesson_out, module_out
from utils.certificates import course_lessons_complete, ensure_certificate

router = APIRouter(prefix="/api", tags=["courses"])


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id.")


def _get_course_or_404(course_id: str) -> dict:
    course = courses_col().find_one({"_id": _oid(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    return course


def _assert_can_manage_course(user: dict, course: dict) -> None:
    """Same ownership rule as admin_courses.py: admin manages everything,
    instructor only courses assigned to them."""
    if user["role"] == "admin":
        return
    if user["role"] == "instructor" and course.get("instructor_id") == user["id"]:
        return
    raise HTTPException(status_code=403, detail="You don't manage this course.")


def _has_course_access(user: dict, course: dict, is_enrolled: bool) -> bool:
    """Who may open a course's actual content (as opposed to just seeing it
    listed in the catalog): admins always; an instructor for courses they're
    assigned to (automatically, no separate enrollment needed); anyone else
    only if actually enrolled. An instructor is NOT granted access to a
    colleague's course just by being an instructor — that would let them
    browse content the way only admins should be able to."""
    if user["role"] == "admin":
        return True
    if user["role"] == "instructor" and course.get("instructor_id") == user["id"]:
        return True
    return is_enrolled


# --- Catalog (any logged-in role) -------------------------------------------

@router.get("/courses")
def catalog(user: dict = Depends(get_current_user)):
    courses = list(courses_col().find().sort("order", 1))
    my_enrollments = {e["course_id"] for e in enrollments_col().find({"user_id": user["id"]})}
    out = []
    for c in courses:
        item = course_out(c)
        actually_enrolled = str(c["_id"]) in my_enrollments
        # An instructor sees their own assigned course as accessible right
        # away — no separate "enroll" step, same as an admin. Anyone else
        # (students, and instructors on courses that aren't theirs) only
        # sees it as accessible once an actual enrollment exists.
        item["is_enrolled"] = _has_course_access(user, c, actually_enrolled)
        out.append(item)
    return out


# --- Course management (admin / instructor, scoped) -------------------------

@router.get("/courses/manage")
def manage_list(user: dict = Depends(require_roles("admin", "instructor"))):
    query = {} if user["role"] == "admin" else {"instructor_id": user["id"]}
    return [course_out(c) for c in courses_col().find(query).sort("order", 1)]


@router.post("/courses")
def create_course(body: CreateCourseRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    if body.track not in VALID_TRACKS:
        raise HTTPException(status_code=400, detail="Invalid track.")
    instructor_id = body.instructor_id if user["role"] == "admin" else user["id"]
    doc = {
        "title": body.title,
        "category": body.category,
        "description": body.description,
        "thumbnail_url": body.thumbnail_url,
        "is_free": body.is_free,
        "instructor_id": instructor_id,
        "order": courses_col().count_documents({}) + 1,
        "track": body.track,
    }
    result = courses_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return course_out(doc)


@router.get("/courses/{course_id}")
def course_detail(course_id: str, user: dict = Depends(get_current_user)):
    """Full course content (modules + lessons + per-lesson completion),
    gated exactly like course_player.py: students must be enrolled."""
    course = _get_course_or_404(course_id)
    enrollment = enrollments_col().find_one({"user_id": user["id"], "course_id": course_id})
    actually_enrolled = bool(enrollment)
    has_access = _has_course_access(user, course, actually_enrolled)
    if not has_access:
        raise HTTPException(status_code=403, detail="You don't have access to this course.")
    track = normalize_track(course.get("track"))

    modules = list(modules_col().find({"course_id": course_id}).sort("order", 1))
    completed_lesson_ids = {
        p["lesson_id"]
        for p in progress_col().find({"user_id": user["id"], "completed": True})
    }
    modules_out = []
    for m in modules:
        lessons = list(lessons_col().find({"module_id": str(m["_id"])}).sort("order", 1))
        lessons_payload = []
        for l in lessons:
            lp = lesson_out(l)
            lp["completed"] = lp["id"] in completed_lesson_ids
            lessons_payload.append(lp)
        mp = module_out(m)
        mp["lessons"] = lessons_payload
        modules_out.append(mp)

    payload = course_out(course)
    payload["title"] = display_title(course["title"], track)
    payload["track"] = track
    payload["is_enrolled"] = has_access
    payload["modules"] = modules_out
    return payload


@router.patch("/courses/{course_id}")
def update_course(course_id: str, body: UpdateCourseRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    course = _get_course_or_404(course_id)
    _assert_can_manage_course(user, course)
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "instructor_id" in update and user["role"] != "admin":
        update.pop("instructor_id")  # only admin may reassign
    if "track" in update and update["track"] not in VALID_TRACKS:
        raise HTTPException(status_code=400, detail="Invalid track.")
    if update:
        courses_col().update_one({"_id": course["_id"]}, {"$set": update})
    return course_out(courses_col().find_one({"_id": course["_id"]}))


_THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024  # 2MB — plenty for a course card image, small enough to live happily as a Mongo field
_THUMBNAIL_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/webp": "webp",
}


@router.post("/courses/{course_id}/thumbnail")
async def upload_course_thumbnail(
    course_id: str, file: UploadFile, user: dict = Depends(require_roles("admin", "instructor"))
):
    """Lets an admin/instructor set a course's thumbnail by uploading an
    image directly, instead of needing a `thumbnail_url` (which, before
    this, meant either hosting it somewhere yourself or asking us to drop a
    file into backend/assets/ via GitHub — a real friction point for every
    client). Stored as a base64 data: URL right on the course document
    rather than written to disk: Render's free-tier filesystem is
    ephemeral (wiped on every redeploy/restart), so anything saved to disk
    at runtime would vanish the next time the service restarts. A data URL
    has no such problem — it's just a string field, backed by the same
    Atlas database everything else already relies on — at the cost of a
    few hundred KB per course in that tenant's database, which is trivial
    against even the free M0 tier."""
    course = _get_course_or_404(course_id)
    _assert_can_manage_course(user, course)

    ext = _THUMBNAIL_CONTENT_TYPES.get(file.content_type)
    if not ext:
        raise HTTPException(status_code=400, detail="Only PNG, JPEG, or WEBP images are supported.")
    raw = await file.read()
    if len(raw) > _THUMBNAIL_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large — please use one under 2MB.")

    data_url = f"data:{file.content_type};base64,{base64.b64encode(raw).decode('ascii')}"
    courses_col().update_one({"_id": course["_id"]}, {"$set": {"thumbnail_url": data_url}})
    return course_out(courses_col().find_one({"_id": course["_id"]}))


@router.delete("/courses/{course_id}")
def delete_course(course_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    course = _get_course_or_404(course_id)
    _assert_can_manage_course(user, course)
    module_ids = [str(m["_id"]) for m in modules_col().find({"course_id": course_id})]
    lessons_col().delete_many({"module_id": {"$in": module_ids}})
    modules_col().delete_many({"course_id": course_id})
    courses_col().delete_one({"_id": course["_id"]})
    return {"ok": True}


# --- Modules -----------------------------------------------------------

@router.post("/courses/{course_id}/modules")
def create_module(course_id: str, body: CreateModuleRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    course = _get_course_or_404(course_id)
    _assert_can_manage_course(user, course)
    doc = {
        "course_id": course_id,
        "title": body.title,
        "order": modules_col().count_documents({"course_id": course_id}) + 1,
    }
    result = modules_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return module_out(doc)


@router.patch("/modules/{module_id}")
def update_module(module_id: str, body: UpdateModuleRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    module = modules_col().find_one({"_id": _oid(module_id)})
    if not module:
        raise HTTPException(status_code=404, detail="Module not found.")
    course = _get_course_or_404(module["course_id"])
    _assert_can_manage_course(user, course)
    modules_col().update_one({"_id": module["_id"]}, {"$set": {"title": body.title}})
    return module_out(modules_col().find_one({"_id": module["_id"]}))


@router.delete("/modules/{module_id}")
def delete_module(module_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    module = modules_col().find_one({"_id": _oid(module_id)})
    if not module:
        raise HTTPException(status_code=404, detail="Module not found.")
    course = _get_course_or_404(module["course_id"])
    _assert_can_manage_course(user, course)
    lessons_col().delete_many({"module_id": module_id})
    modules_col().delete_one({"_id": module["_id"]})
    return {"ok": True}


# --- Lessons -------------------------------------------------------------

@router.post("/modules/{module_id}/lessons")
def create_lesson(module_id: str, body: CreateLessonRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    module = modules_col().find_one({"_id": _oid(module_id)})
    if not module:
        raise HTTPException(status_code=404, detail="Module not found.")
    course = _get_course_or_404(module["course_id"])
    _assert_can_manage_course(user, course)
    doc = {
        "module_id": module_id,
        "title": body.title,
        "youtube_id": body.youtube_id.strip(),
        "ppt_link": body.ppt_link.strip(),
        "colab_link": body.colab_link.strip(),
        "dataset_link": body.dataset_link.strip(),
        "order": lessons_col().count_documents({"module_id": module_id}) + 1,
    }
    result = lessons_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return lesson_out(doc)


@router.patch("/lessons/{lesson_id}")
def update_lesson(lesson_id: str, body: UpdateLessonRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    lesson = lessons_col().find_one({"_id": _oid(lesson_id)})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    module = modules_col().find_one({"_id": _oid(lesson["module_id"])})
    course = _get_course_or_404(module["course_id"])
    _assert_can_manage_course(user, course)
    update = {k: v.strip() if isinstance(v, str) else v for k, v in body.model_dump(exclude_unset=True).items()}
    if update:
        lessons_col().update_one({"_id": lesson["_id"]}, {"$set": update})
    return lesson_out(lessons_col().find_one({"_id": lesson["_id"]}))


@router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    lesson = lessons_col().find_one({"_id": _oid(lesson_id)})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    module = modules_col().find_one({"_id": _oid(lesson["module_id"])})
    course = _get_course_or_404(module["course_id"])
    _assert_can_manage_course(user, course)
    lessons_col().delete_one({"_id": lesson["_id"]})
    return {"ok": True}


# --- Progress (learner marks a lesson complete) ------------------------------

@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: str, user: dict = Depends(get_current_user)):
    lesson = lessons_col().find_one({"_id": _oid(lesson_id)})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    module = modules_col().find_one({"_id": _oid(lesson["module_id"])})
    if not module:
        raise HTTPException(status_code=404, detail="Module not found.")
    course_id = module["course_id"]

    progress_col().update_one(
        {"user_id": user["id"], "lesson_id": lesson_id},
        {
            "$set": {
                "user_id": user["id"],
                "lesson_id": lesson_id,
                "completed": True,
                "completed_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    cert = ensure_certificate(user["id"], course_id)
    return {"ok": True, "certificate_issued": cert is not None}


# --- My learning (enrollments + progress summary) ----------------------------

@router.get("/my/learning")
def my_learning(user: dict = Depends(get_current_user)):
    """Progress here must count the same "steps" as the course player does
    (lessons + each module's quiz, if it has one) — see buildFlatItems() in
    CoursePlayer.jsx. Counting lessons only would show a different, lower
    percentage here than the course player shows once its quiz statuses
    finish loading, which is exactly the inconsistency this was fixed to
    avoid."""
    enrollments = list(enrollments_col().find({"user_id": user["id"]}))
    out = []
    for e in enrollments:
        course = courses_col().find_one({"_id": _oid(e["course_id"])})
        if not course:
            continue
        module_ids = [str(m["_id"]) for m in modules_col().find({"course_id": e["course_id"]})]
        lesson_ids = [str(l["_id"]) for l in lessons_col().find({"module_id": {"$in": module_ids}})]
        total = len(lesson_ids)
        done = progress_col().count_documents(
            {"user_id": user["id"], "lesson_id": {"$in": lesson_ids}, "completed": True}
        )

        quizzes = list(quizzes_col().find({"module_id": {"$in": module_ids}}))
        total += len(quizzes)
        for quiz in quizzes:
            has_pass = quiz_attempts_col().find_one(
                {"quiz_id": str(quiz["_id"]), "user_id": user["id"], "passed": True}
            )
            if has_pass:
                done += 1

        track = normalize_track(course.get("track"))
        item = course_out(course)
        item["title"] = display_title(course["title"], track)
        item["track"] = track
        item["lessons_total"] = total
        item["lessons_completed"] = done
        item["progress_pct"] = (done / total) if total else 0
        out.append(item)
    return out
