"""Port of views/admin_submissions.py (post/edit/delete assignments, grade
submissions -> triggers certificate issuance on approval) and the
student-facing views/assignments.py (lesson-completion-gated assignment
list + submission)."""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from db import (
    assignments_col,
    courses_col,
    enrollments_col,
    lessons_col,
    modules_col,
    progress_col,
    quiz_attempts_col,
    quizzes_col,
    submissions_col,
    users_col,
)
from schemas import (
    CreateAssignmentRequest,
    GradeSubmissionRequest,
    SubmitAssignmentRequest,
    UpdateAssignmentRequest,
)
from security import get_current_user, require_roles
from serializers import assignment_out, submission_out
from utils.certificates import course_modules_complete, ensure_certificate
from utils.tracks import display_title, normalize_track

router = APIRouter(prefix="/api", tags=["assignments"])


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id.")


def _managed_course_ids(user: dict) -> list[str]:
    query = {} if user["role"] == "admin" else {"instructor_id": user["id"]}
    return [str(c["_id"]) for c in courses_col().find(query)]


def _assert_can_manage_assignment(user: dict, assignment: dict) -> None:
    course = courses_col().find_one({"_id": _oid(assignment["course_id"])})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    if user["role"] == "admin":
        return
    if user["role"] == "instructor" and course.get("instructor_id") == user["id"]:
        return
    raise HTTPException(status_code=403, detail="You don't manage this assignment.")


# --- Admin/instructor: manage assignments -----------------------------------

@router.get("/assignments/manage")
def manage_list(user: dict = Depends(require_roles("admin", "instructor"))):
    course_ids = _managed_course_ids(user)
    return [assignment_out(a) for a in assignments_col().find({"course_id": {"$in": course_ids}})]


@router.post("/assignments")
def create_assignment(body: CreateAssignmentRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    course = courses_col().find_one({"_id": _oid(body.course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    if user["role"] == "instructor" and course.get("instructor_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You don't manage this course.")
    doc = {
        "course_id": body.course_id,
        "title": body.title,
        "description": body.description,
        "due_date": body.due_date,
    }
    result = assignments_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return assignment_out(doc)


@router.patch("/assignments/{assignment_id}")
def update_assignment(assignment_id: str, body: UpdateAssignmentRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    assignment = assignments_col().find_one({"_id": _oid(assignment_id)})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    _assert_can_manage_assignment(user, assignment)
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if update:
        assignments_col().update_one({"_id": assignment["_id"]}, {"$set": update})
    return assignment_out(assignments_col().find_one({"_id": assignment["_id"]}))


@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    assignment = assignments_col().find_one({"_id": _oid(assignment_id)})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    _assert_can_manage_assignment(user, assignment)
    submissions_col().delete_many({"assignment_id": assignment_id})
    assignments_col().delete_one({"_id": assignment["_id"]})
    return {"ok": True}


@router.get("/assignments/{assignment_id}/submissions")
def list_submissions(assignment_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    assignment = assignments_col().find_one({"_id": _oid(assignment_id)})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    _assert_can_manage_assignment(user, assignment)
    out = []
    for s in submissions_col().find({"assignment_id": assignment_id}):
        item = submission_out(s)
        student = users_col().find_one({"_id": _oid(s["user_id"])})
        item["student_name"] = student["name"] if student else "Unknown"
        item["student_email"] = student["email"] if student else "—"
        out.append(item)
    return out


@router.patch("/submissions/{submission_id}")
def grade_submission(submission_id: str, body: GradeSubmissionRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    submission = submissions_col().find_one({"_id": _oid(submission_id)})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    assignment = assignments_col().find_one({"_id": _oid(submission["assignment_id"])})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    _assert_can_manage_assignment(user, assignment)

    if body.status not in ("pending", "approved", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status.")

    submissions_col().update_one(
        {"_id": submission["_id"]},
        {"$set": {"grade": body.grade, "feedback": body.feedback, "status": body.status}},
    )

    cert_issued = False
    if body.status == "approved":
        cert = ensure_certificate(submission["user_id"], assignment["course_id"])
        cert_issued = cert is not None

    return {"ok": True, "certificate_issued": cert_issued}


# --- Student-facing: view + submit -------------------------------------

@router.get("/my/assignments")
def my_assignments(user: dict = Depends(get_current_user)):
    enrolled_course_ids = [e["course_id"] for e in enrollments_col().find({"user_id": user["id"]})]
    if not enrolled_course_ids:
        return []

    out = []
    for a in assignments_col().find({"course_id": {"$in": enrolled_course_ids}}):
        course = courses_col().find_one({"_id": _oid(a["course_id"])})
        course_title = course["title"] if course else "Unknown"
        # Track lives on the course now (global, set at creation/edit) —
        # not per-enrollment.
        course_title = display_title(course_title, normalize_track(course.get("track")) if course else "course")

        modules_done = course_modules_complete(user["id"], a["course_id"])
        item = assignment_out(a)
        item["course_title"] = course_title

        if user["role"] == "student" and not modules_done:
            # Shown right next to "finish every module (lessons + module
            # quiz, passed)" — so it has to report both, not just lessons.
            # Lessons-only used to show e.g. "39/39 lessons completed"
            # while still locked, which reads as a bug (why is this locked
            # if it's 100%?) when really the module quizzes just weren't
            # counted here at all.
            module_ids = [str(m["_id"]) for m in modules_col().find({"course_id": a["course_id"]})]
            lesson_ids = [str(l["_id"]) for l in lessons_col().find({"module_id": {"$in": module_ids}})]
            done_count = progress_col().count_documents(
                {"user_id": user["id"], "lesson_id": {"$in": lesson_ids}, "completed": True}
            )

            quizzes = list(quizzes_col().find({"module_id": {"$in": module_ids}}))
            quizzes_done = sum(
                1
                for quiz in quizzes
                if quiz_attempts_col().find_one(
                    {"quiz_id": str(quiz["_id"]), "user_id": user["id"], "passed": True}
                )
            )

            item["locked"] = True
            item["lessons_completed"] = done_count
            item["lessons_total"] = len(lesson_ids)
            item["quizzes_completed"] = quizzes_done
            item["quizzes_total"] = len(quizzes)
            out.append(item)
            continue

        item["locked"] = False
        existing = submissions_col().find_one({"assignment_id": str(a["_id"]), "user_id": user["id"]})
        item["submission"] = submission_out(existing) if existing else None
        out.append(item)

    return out


@router.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: str, body: SubmitAssignmentRequest, user: dict = Depends(get_current_user)):
    assignment = assignments_col().find_one({"_id": _oid(assignment_id)})
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")

    is_enrolled = enrollments_col().find_one({"user_id": user["id"], "course_id": assignment["course_id"]})
    if not is_enrolled:
        raise HTTPException(status_code=403, detail="You're not enrolled in this course.")

    if user["role"] == "student" and not course_modules_complete(user["id"], assignment["course_id"]):
        raise HTTPException(status_code=403, detail="Finish every module (lessons + quiz) in this course before submitting.")

    if not body.link_or_text.strip():
        raise HTTPException(status_code=400, detail="Add a link or answer before submitting.")

    existing = submissions_col().find_one({"assignment_id": assignment_id, "user_id": user["id"]})
    if existing:
        raise HTTPException(status_code=409, detail="You've already submitted this assignment.")

    doc = {
        "assignment_id": assignment_id,
        "user_id": user["id"],
        "link_or_text": body.link_or_text.strip(),
        "submitted_at": datetime.now(timezone.utc),
        "grade": None,
        "feedback": "",
        "status": "pending",
    }
    result = submissions_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return submission_out(doc)
