"""Module-level quizzes: exactly 5 auto-graded questions per module
(single-answer MCQ, multi-select, or true/false), gating "module complete"
alongside lesson completion — see utils/certificates.py for how that feeds
into the certificate flow.

Ownership/RBAC is identical to courses/modules/lessons/assignments:
admin manages every quiz, an instructor only manages quizzes on modules
belonging to courses assigned to them (_assert_can_manage_module below
mirrors _assert_can_manage_course in courses.py exactly).
"""

import random
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from db import (
    courses_col,
    enrollments_col,
    lessons_col,
    modules_col,
    progress_col,
    quiz_attempts_col,
    quizzes_col,
    users_col,
)
from runtime_settings import get_setting
from schemas import SaveQuizRequest, SubmitQuizRequest
from security import get_current_user, require_roles
from serializers import quiz_attempt_out, quiz_manage_out, quiz_out
from utils.certificates import ensure_certificate

router = APIRouter(prefix="/api", tags=["quizzes"])

VALID_TYPES = {"single", "multi", "true_false"}


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id.")


def _get_module_or_404(module_id: str) -> dict:
    module = modules_col().find_one({"_id": _oid(module_id)})
    if not module:
        raise HTTPException(status_code=404, detail="Module not found.")
    return module


def _get_course_for_module(module: dict) -> dict:
    course = courses_col().find_one({"_id": _oid(module["course_id"])})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    return course


def _assert_can_manage_module(user: dict, module: dict) -> dict:
    """Same ownership rule as _assert_can_manage_course in courses.py.
    Returns the course so callers don't have to look it up twice."""
    course = _get_course_for_module(module)
    if user["role"] == "admin":
        return course
    if user["role"] == "instructor" and course.get("instructor_id") == user["id"]:
        return course
    raise HTTPException(status_code=403, detail="You don't manage this course.")


def _lessons_complete_for_module(user_id: str, module_id: str) -> bool:
    lesson_ids = [str(l["_id"]) for l in lessons_col().find({"module_id": module_id})]
    if not lesson_ids:
        return True
    done = progress_col().count_documents(
        {"user_id": user_id, "lesson_id": {"$in": lesson_ids}, "completed": True}
    )
    return done >= len(lesson_ids)


def _validate_and_normalize_questions(questions) -> list[dict]:
    """Enforces: exactly 5 questions (already checked by the pydantic
    schema's min/max_length), each a valid type, at least 2 options, no
    duplicate option ids, and a correct-answer set that matches the
    question type (exactly one for single/true_false, at least one for
    multi)."""
    normalized = []
    for idx, q in enumerate(questions):
        if q.type not in VALID_TYPES:
            raise HTTPException(status_code=400, detail=f"Question {idx + 1}: invalid type '{q.type}'.")
        if not q.text.strip():
            raise HTTPException(status_code=400, detail=f"Question {idx + 1}: text can't be empty.")
        if len(q.options) < 2:
            raise HTTPException(status_code=400, detail=f"Question {idx + 1}: needs at least 2 options.")

        option_ids = []
        options_out = []
        for opt_idx, opt in enumerate(q.options):
            if not opt.text.strip():
                raise HTTPException(status_code=400, detail=f"Question {idx + 1}: an option's text can't be empty.")
            oid = (opt.id or f"o{opt_idx + 1}").strip()
            option_ids.append(oid)
            options_out.append({"id": oid, "text": opt.text.strip()})
        if len(set(option_ids)) != len(option_ids):
            raise HTTPException(status_code=400, detail=f"Question {idx + 1}: duplicate option ids.")

        correct = [c for c in q.correct_option_ids if c in option_ids]
        if not correct:
            raise HTTPException(status_code=400, detail=f"Question {idx + 1}: mark at least one correct option.")
        if q.type in ("single", "true_false") and len(correct) != 1:
            raise HTTPException(
                status_code=400,
                detail=f"Question {idx + 1}: single-answer/true-false questions need exactly one correct option.",
            )

        normalized.append(
            {
                "id": (q.id or f"q{idx + 1}").strip(),
                "type": q.type,
                "text": q.text.strip(),
                "options": options_out,
                "correct_option_ids": correct,
            }
        )

    question_ids = [q["id"] for q in normalized]
    if len(set(question_ids)) != len(question_ids):
        raise HTTPException(status_code=400, detail="Duplicate question ids.")
    return normalized


# --- Admin/instructor: manage a module's quiz -------------------------------

@router.get("/modules/{module_id}/quiz/manage")
def get_quiz_manage(module_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    module = _get_module_or_404(module_id)
    _assert_can_manage_module(user, module)
    quiz = quizzes_col().find_one({"module_id": module_id})
    return quiz_manage_out(quiz) if quiz else None


@router.put("/modules/{module_id}/quiz")
def save_quiz(module_id: str, body: SaveQuizRequest, user: dict = Depends(require_roles("admin", "instructor"))):
    module = _get_module_or_404(module_id)
    _assert_can_manage_module(user, module)
    questions = _validate_and_normalize_questions(body.questions)
    now = datetime.now(timezone.utc)

    existing = quizzes_col().find_one({"module_id": module_id})
    if existing:
        quizzes_col().update_one({"_id": existing["_id"]}, {"$set": {"questions": questions, "updated_at": now}})
        quiz = quizzes_col().find_one({"_id": existing["_id"]})
    else:
        doc = {"module_id": module_id, "questions": questions, "created_at": now, "updated_at": now}
        result = quizzes_col().insert_one(doc)
        doc["_id"] = result.inserted_id
        quiz = doc
    return quiz_manage_out(quiz)


@router.delete("/modules/{module_id}/quiz")
def delete_quiz(module_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    module = _get_module_or_404(module_id)
    _assert_can_manage_module(user, module)
    quiz = quizzes_col().find_one({"module_id": module_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="This module has no quiz.")
    quiz_attempts_col().delete_many({"quiz_id": str(quiz["_id"])})
    quizzes_col().delete_one({"_id": quiz["_id"]})
    return {"ok": True}


@router.get("/modules/{module_id}/quiz/attempts")
def list_attempts(module_id: str, user: dict = Depends(require_roles("admin", "instructor"))):
    module = _get_module_or_404(module_id)
    _assert_can_manage_module(user, module)
    quiz = quizzes_col().find_one({"module_id": module_id})
    if not quiz:
        return []
    out = []
    for a in quiz_attempts_col().find({"quiz_id": str(quiz["_id"])}).sort("submitted_at", -1):
        item = quiz_attempt_out(a)
        student = users_col().find_one({"_id": _oid(a["user_id"])})
        item["student_name"] = student["name"] if student else "Unknown"
        item["student_email"] = student["email"] if student else "—"
        out.append(item)
    return out


# --- Student: take the quiz -------------------------------------------------

@router.get("/modules/{module_id}/quiz")
def get_quiz_for_student(module_id: str, user: dict = Depends(get_current_user)):
    module = _get_module_or_404(module_id)
    course = _get_course_for_module(module)
    course_id = str(course["_id"])
    is_enrolled = bool(enrollments_col().find_one({"user_id": user["id"], "course_id": course_id}))
    has_access = (
        user["role"] == "admin"
        or (user["role"] == "instructor" and course.get("instructor_id") == user["id"])
        or is_enrolled
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="You don't have access to this course.")

    quiz = quizzes_col().find_one({"module_id": module_id})
    if not quiz:
        return None

    attempts = list(
        quiz_attempts_col().find({"quiz_id": str(quiz["_id"]), "user_id": user["id"]}).sort("attempt_number", 1)
    )
    max_attempts = get_setting("quiz_max_attempts")
    passed = any(a["passed"] for a in attempts)
    best_score = max((a["score_percent"] for a in attempts), default=None)
    lessons_complete = _lessons_complete_for_module(user["id"], module_id)

    payload = quiz_out(quiz)
    if get_setting("quiz_shuffle_questions"):
        random.shuffle(payload["questions"])
    if get_setting("quiz_shuffle_options"):
        for q in payload["questions"]:
            random.shuffle(q["options"])

    payload["lessons_complete"] = lessons_complete
    payload["attempts_used"] = len(attempts)
    payload["max_attempts"] = max_attempts
    payload["passed"] = passed
    payload["best_score"] = best_score
    payload["pass_percent"] = get_setting("quiz_pass_percent")
    payload["can_attempt"] = (
        lessons_complete and not passed and (max_attempts == 0 or len(attempts) < max_attempts)
    )
    payload["attempts"] = [quiz_attempt_out(a) for a in attempts]
    return payload


@router.post("/modules/{module_id}/quiz/submit")
def submit_quiz(module_id: str, body: SubmitQuizRequest, user: dict = Depends(get_current_user)):
    module = _get_module_or_404(module_id)
    course = _get_course_for_module(module)
    course_id = str(course["_id"])

    if user["role"] == "student":
        is_enrolled = bool(enrollments_col().find_one({"user_id": user["id"], "course_id": course_id}))
        if not is_enrolled:
            raise HTTPException(status_code=403, detail="You're not enrolled in this course.")

    quiz = quizzes_col().find_one({"module_id": module_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="This module has no quiz.")

    if not _lessons_complete_for_module(user["id"], module_id):
        raise HTTPException(status_code=403, detail="Finish every lesson in this module before taking the quiz.")

    prior_attempts = list(quiz_attempts_col().find({"quiz_id": str(quiz["_id"]), "user_id": user["id"]}))
    if any(a["passed"] for a in prior_attempts):
        raise HTTPException(status_code=409, detail="You've already passed this module's quiz.")
    max_attempts = get_setting("quiz_max_attempts")
    if max_attempts and len(prior_attempts) >= max_attempts:
        raise HTTPException(status_code=409, detail="You've used all your attempts for this quiz.")

    answers_by_qid = {a.question_id: set(a.selected_option_ids) for a in body.answers}
    questions = quiz["questions"]
    correct_count = 0
    review = []
    for q in questions:
        selected = answers_by_qid.get(q["id"], set())
        is_correct = set(q["correct_option_ids"]) == selected
        if is_correct:
            correct_count += 1
        review.append(
            {
                "question_id": q["id"],
                "selected_option_ids": sorted(selected),
                "correct_option_ids": q["correct_option_ids"],
                "correct": is_correct,
            }
        )

    score_percent = round((correct_count / len(questions)) * 100) if questions else 0
    pass_percent = get_setting("quiz_pass_percent")
    passed = score_percent >= pass_percent

    doc = {
        "quiz_id": str(quiz["_id"]),
        "module_id": module_id,
        "user_id": user["id"],
        "attempt_number": len(prior_attempts) + 1,
        "answers": [
            {"question_id": r["question_id"], "selected_option_ids": r["selected_option_ids"]} for r in review
        ],
        "score_percent": score_percent,
        "passed": passed,
        "submitted_at": datetime.now(timezone.utc),
    }
    result = quiz_attempts_col().insert_one(doc)
    doc["_id"] = result.inserted_id

    cert = ensure_certificate(user["id"], course_id) if passed else None

    return {
        "ok": True,
        "attempt_number": doc["attempt_number"],
        "score_percent": score_percent,
        "pass_percent": pass_percent,
        "passed": passed,
        "review": review,
        "certificate_issued": cert is not None,
    }
