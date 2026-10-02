"""Bulk create/update via Excel upload — alongside the existing one-by-one
admin screens, never instead of them. Each endpoint accepts an .xlsx built
from its matching /template download, applies every row it can, and
reports exactly what happened to each row (created / updated / skipped /
error) so an admin can fix just the rows that failed and re-upload.

Same ownership rules as the one-by-one endpoints throughout: an instructor
can only create/touch their own courses; an admin can touch anything.
"""

import io
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook

from db import (
    assignments_col,
    courses_col,
    enrollments_col,
    lessons_col,
    modules_col,
    quizzes_col,
    users_col,
)
from modules.quizzes import _validate_and_normalize_questions
from schemas import QuizOptionIn, QuizQuestionIn
from security import hash_password, require_roles
from utils.tracks import VALID_TRACKS

router = APIRouter(prefix="/api/bulk", tags=["bulk"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _template_response(headers: list[str], example_rows: list[list], filename: str) -> StreamingResponse:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in example_rows:
        ws.append(row)
    for col_idx, header in enumerate(headers, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = max(14, len(header) + 2)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _read_rows(file: UploadFile) -> list[dict]:
    """Returns one dict per non-blank row, keyed by the header row's cell
    text (stripped, so trailing spaces in a template's header don't
    matter). Every value is stringified and stripped; blanks become ""."""
    raw = await file.read()
    try:
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="That doesn't look like a valid .xlsx file.")
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows)
    except StopIteration:
        return []
    headers = [str(h).strip() if h is not None else "" for h in header_row]
    out = []
    for raw_row in rows:
        if raw_row is None or all(c is None or str(c).strip() == "" for c in raw_row):
            continue
        item = {}
        for i, h in enumerate(headers):
            if not h:
                continue
            v = raw_row[i] if i < len(raw_row) else None
            item[h] = "" if v is None else str(v).strip()
        out.append(item)
    return out


def _oid(id_str: str) -> ObjectId | None:
    try:
        return ObjectId(id_str)
    except Exception:
        return None


def _find_manageable_course(title: str, user: dict) -> dict | None:
    query = {"title": {"$regex": f"^{title.strip()}$", "$options": "i"}}
    if user["role"] == "instructor":
        query["instructor_id"] = user["id"]
    return courses_col().find_one(query)


# --- Courses (+ nested modules/lessons) -------------------------------------

_COURSE_HEADERS = [
    "Course Title", "Category", "Description", "Is Free (yes/no)", "Track",
    "Module Title", "Lesson Title", "YouTube ID", "PPT Link", "Practice Link", "Resource Link",
]


@router.get("/courses/template")
def courses_template(user: dict = Depends(require_roles("admin", "instructor"))):
    """One row per lesson — repeat the course/module columns on every row
    for that course/module (like a normal flat spreadsheet export). A row
    can also leave Module Title and Lesson Title blank to just
    create/update the course itself with no content yet."""
    return _template_response(
        _COURSE_HEADERS,
        [
            ["Artificial Intelligence", "AI", "Intro to AI", "yes", "course",
             "Getting Started", "What is AI?", "dQw4w9WgXcQ", "", "", ""],
            ["Artificial Intelligence", "AI", "Intro to AI", "yes", "course",
             "Getting Started", "History of AI", "dQw4w9WgXcQ", "", "", ""],
        ],
        "courses_template.xlsx",
    )


@router.post("/courses")
async def bulk_courses(file: UploadFile, user: dict = Depends(require_roles("admin", "instructor"))):
    rows = await _read_rows(file)
    results = []
    course_cache: dict[str, dict] = {}
    module_cache: dict[tuple, dict] = {}

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        title = row.get("Course Title", "")
        if not title:
            results.append({"row": i, "status": "error", "message": "Course Title is required."})
            continue
        track = (row.get("Track") or "course").lower().strip()
        if track not in VALID_TRACKS:
            results.append({"row": i, "status": "error", "message": f"Invalid track '{track}'."})
            continue

        cache_key = title.lower()
        course = course_cache.get(cache_key)
        created_course = False
        if course is None:
            course = _find_manageable_course(title, user)
            if course is None:
                course = {
                    "title": title,
                    "category": row.get("Category", ""),
                    "description": row.get("Description", ""),
                    "thumbnail_url": "",
                    "is_free": (row.get("Is Free (yes/no)", "yes").lower() != "no"),
                    "instructor_id": user["id"] if user["role"] == "instructor" else None,
                    "order": courses_col().count_documents({}) + 1,
                    "track": track,
                }
                result = courses_col().insert_one(course)
                course["_id"] = result.inserted_id
                created_course = True
            course_cache[cache_key] = course

        module_title = row.get("Module Title", "")
        lesson_title = row.get("Lesson Title", "")
        module = None
        if module_title:
            mod_key = (cache_key, module_title.lower())
            module = module_cache.get(mod_key)
            if module is None:
                module = modules_col().find_one({"course_id": str(course["_id"]), "title": module_title})
                if module is None:
                    module = {
                        "course_id": str(course["_id"]),
                        "title": module_title,
                        "order": modules_col().count_documents({"course_id": str(course["_id"])}) + 1,
                    }
                    result = modules_col().insert_one(module)
                    module["_id"] = result.inserted_id
                module_cache[mod_key] = module

        created_lesson = False
        if lesson_title:
            if not module:
                results.append({"row": i, "status": "error", "message": "Lesson Title needs a Module Title too."})
                continue
            lesson = {
                "module_id": str(module["_id"]),
                "title": lesson_title,
                "youtube_id": row.get("YouTube ID", ""),
                "ppt_link": row.get("PPT Link", ""),
                # "Practice Link"/"Resource Link" are the current template
                # headers (generic wording — not every course is AI/data, so
                # "Colab"/"Dataset" was misleading). Still accepts the old
                # header names too, so a template someone already downloaded
                # before this rename keeps working.
                "colab_link": row.get("Practice Link") or row.get("Colab Link", ""),
                "dataset_link": row.get("Resource Link") or row.get("Dataset Link", ""),
                "order": lessons_col().count_documents({"module_id": str(module["_id"])}) + 1,
            }
            lessons_col().insert_one(lesson)
            created_lesson = True

        results.append({
            "row": i,
            "status": "ok",
            "message": f"{'Created' if created_course else 'Used existing'} course"
                       + (f", module '{module_title}'" if module_title else "")
                       + (f", added lesson '{lesson_title}'" if created_lesson else ""),
        })

    return _summary(results)


# --- Assignments -------------------------------------------------------

_ASSIGNMENT_HEADERS = ["Course Title", "Assignment Title", "Description", "Due Date (YYYY-MM-DD)"]


@router.get("/assignments/template")
def assignments_template(user: dict = Depends(require_roles("admin", "instructor"))):
    return _template_response(
        _ASSIGNMENT_HEADERS,
        [["Artificial Intelligence", "Capstone Project", "Build a small AI demo.", "2026-12-31"]],
        "assignments_template.xlsx",
    )


@router.post("/assignments")
async def bulk_assignments(file: UploadFile, user: dict = Depends(require_roles("admin", "instructor"))):
    rows = await _read_rows(file)
    results = []
    for i, row in enumerate(rows, start=2):
        title = row.get("Assignment Title", "")
        course_title = row.get("Course Title", "")
        if not title or not course_title:
            results.append({"row": i, "status": "error", "message": "Course Title and Assignment Title are required."})
            continue
        course = _find_manageable_course(course_title, user)
        if not course:
            results.append({"row": i, "status": "error", "message": f"No course you manage matches '{course_title}'."})
            continue
        assignments_col().insert_one({
            "course_id": str(course["_id"]),
            "title": title,
            "description": row.get("Description", ""),
            "due_date": row.get("Due Date (YYYY-MM-DD)") or None,
        })
        results.append({"row": i, "status": "ok", "message": f"Created '{title}' on '{course['title']}'."})
    return _summary(results)


# --- Quizzes (5 rows = 5 questions per module) ------------------------------

_QUIZ_HEADERS = [
    "Course Title", "Module Title", "Question",
    "Option A", "Option B", "Option C", "Option D", "Correct Option (A/B/C/D)",
]


@router.get("/quizzes/template")
def quizzes_template(user: dict = Depends(require_roles("admin", "instructor"))):
    rows = [
        ["Artificial Intelligence", "Getting Started", f"Sample question {n}?", "Option A", "Option B", "Option C", "Option D", "A"]
        for n in range(1, 6)
    ]
    return _template_response(_QUIZ_HEADERS, rows, "quizzes_template.xlsx")


@router.post("/quizzes")
async def bulk_quizzes(file: UploadFile, user: dict = Depends(require_roles("admin", "instructor"))):
    rows = await _read_rows(file)
    groups: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for i, row in enumerate(rows, start=2):
        key = (row.get("Course Title", "").lower(), row.get("Module Title", "").lower())
        row["_row_num"] = i
        groups.setdefault(key, [])
        if key not in order:
            order.append(key)
        groups[key].append(row)

    results = []
    for key in order:
        group = groups[key]
        course_title, module_title = group[0].get("Course Title", ""), group[0].get("Module Title", "")
        row_nums = [r["_row_num"] for r in group]
        if len(group) != 5:
            results.append({
                "row": row_nums[0],
                "status": "error",
                "message": f"'{course_title}' / '{module_title}' has {len(group)} question row(s) — a module quiz needs exactly 5.",
            })
            continue
        course = _find_manageable_course(course_title, user)
        if not course:
            results.append({"row": row_nums[0], "status": "error", "message": f"No course you manage matches '{course_title}'."})
            continue
        module = modules_col().find_one({"course_id": str(course["_id"]), "title": module_title})
        if not module:
            results.append({"row": row_nums[0], "status": "error", "message": f"No module '{module_title}' on '{course_title}'."})
            continue

        try:
            questions = []
            for q_idx, row in enumerate(group):
                options = [
                    QuizOptionIn(id=f"o{letter_idx + 1}", text=row.get(f"Option {letter}", ""))
                    for letter_idx, letter in enumerate("ABCD")
                ]
                correct_letter = row.get("Correct Option (A/B/C/D)", "").strip().upper()
                correct_idx = "ABCD".find(correct_letter)
                if correct_idx == -1:
                    raise ValueError(f"row {row['_row_num']}: Correct Option must be A, B, C or D.")
                questions.append(QuizQuestionIn(
                    id=f"q{q_idx + 1}",
                    type="single",
                    text=row.get("Question", ""),
                    options=options,
                    correct_option_ids=[f"o{correct_idx + 1}"],
                ))
            normalized = _validate_and_normalize_questions(questions)
        except (ValueError, HTTPException) as e:
            results.append({"row": row_nums[0], "status": "error", "message": str(getattr(e, "detail", e))})
            continue

        now = datetime.now(timezone.utc)
        existing = quizzes_col().find_one({"module_id": str(module["_id"])})
        if existing:
            quizzes_col().update_one({"_id": existing["_id"]}, {"$set": {"questions": normalized, "updated_at": now}})
        else:
            quizzes_col().insert_one({"module_id": str(module["_id"]), "questions": normalized, "created_at": now, "updated_at": now})
        results.append({"row": row_nums[0], "status": "ok", "message": f"Saved quiz for '{course_title}' / '{module_title}'."})

    return _summary(results)


# --- Enrollments (bulk-enroll students, creating accounts if needed) -------

_ENROLLMENT_HEADERS = ["Student Email", "Student Name", "Password", "Course Title"]


@router.get("/enrollments/template")
def enrollments_template(user: dict = Depends(require_roles("admin"))):
    return _template_response(
        _ENROLLMENT_HEADERS,
        [["jane@example.com", "Jane Doe", "9876543210", "Artificial Intelligence"]],
        "enrollments_template.xlsx",
    )


@router.post("/enrollments")
async def bulk_enrollments(file: UploadFile, user: dict = Depends(require_roles("admin"))):
    """Admin-only, matching the one-by-one /api/enrollments (no public
    sign-up, no instructor self-enroll bulk path). Creates the student
    account if the email doesn't exist yet — the generated password (if
    any) is reported back in that row's result so it can be shared with
    the student; it's never stored anywhere else."""
    from db import count_active_users
    from utils.tenants import current_tenant
    import secrets

    rows = await _read_rows(file)
    tenant = current_tenant()
    results = []
    for i, row in enumerate(rows, start=2):
        email = row.get("Student Email", "").lower()
        course_title = row.get("Course Title", "")
        if not email or not course_title:
            results.append({"row": i, "status": "error", "message": "Student Email and Course Title are required."})
            continue
        course = courses_col().find_one({"title": {"$regex": f"^{course_title.strip()}$", "$options": "i"}})
        if not course:
            results.append({"row": i, "status": "error", "message": f"No course matches '{course_title}'."})
            continue

        student = users_col().find_one({"email": email})
        generated_password = None
        if not student:
            if tenant and tenant.get("max_users") and count_active_users() >= tenant["max_users"]:
                results.append({"row": i, "status": "error", "message": f"Plan seat limit ({tenant['max_users']}) reached — upgrade to add more."})
                continue
            # "Password" is the current header; still reads the old
            # "Password (leave blank to auto-generate)" header too, so an
            # already-downloaded template keeps working. Leaving the column
            # blank still auto-generates one (reported back below) — the
            # header rename is just to stop it reading as optional, since
            # most clients want to set a real, memorable one (e.g. the
            # student's own phone number) rather than a random string.
            generated_password = (
                row.get("Password") or row.get("Password (leave blank to auto-generate)") or secrets.token_urlsafe(9)
            )
            student_doc = {
                "name": row.get("Student Name") or email.split("@")[0],
                "email": email,
                "password_hash": hash_password(generated_password),
                "role": "student",
                "created_at": datetime.now(timezone.utc),
                "timezone": "Asia/Kolkata",
            }
            result = users_col().insert_one(student_doc)
            student_doc["_id"] = result.inserted_id
            student = student_doc

        existing = enrollments_col().find_one({"user_id": str(student["_id"]), "course_id": str(course["_id"])})
        if existing:
            results.append({"row": i, "status": "skipped", "message": f"{email} is already enrolled in '{course_title}'."})
            continue

        enrollments_col().insert_one({
            "user_id": str(student["_id"]),
            "course_id": str(course["_id"]),
            "enrolled_at": datetime.now(timezone.utc),
        })
        msg = f"Enrolled {email} in '{course_title}'."
        if generated_password:
            msg += f" New account created — temporary password: {generated_password}"
        results.append({"row": i, "status": "ok", "message": msg})

    return _summary(results)


def _summary(results: list[dict]) -> dict:
    return {
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "rows": results,
    }
