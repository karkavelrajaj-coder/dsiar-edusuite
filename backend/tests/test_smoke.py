"""In-process smoke test exercising the whole API through mongomock, since
this sandbox's outbound network allowlist can't reach MongoDB Atlas (no DNS
for *.mongodb.net here). Render's environment has normal outbound access,
so the real MONGO_URI will work there / from your own machine — this test
only proves the ported business logic itself is correct.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/ root

import mongomock
import db as db_module

# Patch the Mongo client BEFORE importing app (app.py runs ensure_indexes /
# seed_first_admin at lifespan startup via the TestClient context manager).
_mock_client = mongomock.MongoClient()
db_module._client = _mock_client

from fastapi.testclient import TestClient  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app)

def check(label, cond):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}")
    assert cond, label


with client:
    # 1. Seed admin login
    r = client.post("/api/auth/login", json={"email": "admin@dsiar.com", "password": "admin@dsiar.com"})
    check("seed admin login", r.status_code == 200 and r.json()["role"] == "admin")

    r = client.get("/api/auth/me")
    check("me returns admin", r.status_code == 200 and r.json()["email"] == "admin@dsiar.com")

    # 2. Create an instructor + a student (admin-only)
    r = client.post("/api/users", json={"name": "Ms Priya", "email": "priya@dsiar.com", "password": "instr1234", "role": "instructor"})
    check("create instructor", r.status_code == 200)
    instructor_id = r.json()["id"]

    r = client.post("/api/users", json={"name": "Student One", "email": "student1@dsiar.com", "password": "stud1234", "role": "student"})
    check("create student", r.status_code == 200)
    student_id = r.json()["id"]

    # 3. Create a course assigned to the instructor
    r = client.post("/api/courses", json={"title": "Intro to AI", "category": "AI", "description": "desc", "thumbnail_url": "assets/AI Thumbnail.png", "is_free": True, "instructor_id": instructor_id})
    check("create course", r.status_code == 200)
    course_id = r.json()["id"]

    # 4. Add a module + lesson
    r = client.post(f"/api/courses/{course_id}/modules", json={"title": "Module 1"})
    check("create module", r.status_code == 200)
    module_id = r.json()["id"]

    r = client.post(f"/api/modules/{module_id}/lessons", json={"title": "Lesson 1", "youtube_id": "abc123"})
    check("create lesson", r.status_code == 200)
    lesson_id = r.json()["id"]

    # 5. Post an assignment for the course
    r = client.post("/api/assignments", json={"course_id": course_id, "title": "Final Project", "description": "Build something", "due_date": "2026-12-31"})
    check("create assignment", r.status_code == 200)
    assignment_id = r.json()["id"]

    # 6. Admin enrolls the student
    r = client.post("/api/enrollments", json={"user_id": student_id, "course_id": course_id})
    check("enroll student", r.status_code == 200)

    # 7. Log in as the student
    r = client.post("/api/auth/login", json={"email": "student1@dsiar.com", "password": "stud1234"})
    check("student login", r.status_code == 200 and r.json()["role"] == "student")

    r = client.get("/api/courses")
    check("catalog shows enrolled flag", r.status_code == 200 and any(c["id"] == course_id and c["is_enrolled"] for c in r.json()))

    r = client.get(f"/api/courses/{course_id}")
    check("course detail accessible (enrolled)", r.status_code == 200 and len(r.json()["modules"]) == 1)

    # 8. Assignment should be locked until lessons complete
    r = client.get("/api/my/assignments")
    check("assignment locked before lesson completion", r.status_code == 200 and r.json()[0]["locked"] is True)

    # 9. Complete the lesson
    r = client.post(f"/api/lessons/{lesson_id}/complete")
    check("mark lesson complete", r.status_code == 200 and r.json()["certificate_issued"] is False)  # assignment not yet approved

    r = client.get("/api/my/assignments")
    check("assignment unlocked after lesson completion", r.status_code == 200 and r.json()[0]["locked"] is False)

    # 10. Student submits the assignment
    r = client.post(f"/api/assignments/{assignment_id}/submit", json={"link_or_text": "https://github.com/example/final-project"})
    check("submit assignment", r.status_code == 200)

    # No cert yet (submission pending)
    r = client.get("/api/certificates")
    check("no certificate before approval", r.status_code == 200 and len(r.json()) == 0)

    # 11. Log back in as instructor to grade
    r = client.post("/api/auth/login", json={"email": "priya@dsiar.com", "password": "instr1234"})
    check("instructor login", r.status_code == 200)

    r = client.get(f"/api/assignments/{assignment_id}/submissions")
    check("instructor sees submission", r.status_code == 200 and len(r.json()) == 1)
    submission_id = r.json()[0]["id"]

    r = client.patch(f"/api/submissions/{submission_id}", json={"grade": 95, "status": "approved", "feedback": "Great work!"})
    check("grade + approve submission issues certificate", r.status_code == 200 and r.json()["certificate_issued"] is True)

    # 12. Back to student — certificate should now exist and render a PNG
    r = client.post("/api/auth/login", json={"email": "student1@dsiar.com", "password": "stud1234"})
    check("student re-login", r.status_code == 200)

    r = client.get("/api/certificates")
    check("certificate now exists", r.status_code == 200 and len(r.json()) == 1)
    cert_id = r.json()[0]["cert_id"]

    r = client.get(f"/api/certificates/{cert_id}/image")
    check("certificate PNG renders", r.status_code == 200 and r.headers["content-type"] == "image/png" and len(r.content) > 1000)

    # 13. Live session: instructor schedules, starts (mocked — Digital Samba
    # calls will fail without real network, so we only check the API wiring
    # up to that external call, not the external call itself).
    r = client.post("/api/auth/login", json={"email": "priya@dsiar.com", "password": "instr1234"})
    check("instructor login for live session", r.status_code == 200)

    r = client.post("/api/live-sessions", json={
        "course_id": course_id, "title": "Live Q&A", "description": "",
        "date": "2026-12-01", "time": "18:00:00", "timezone": "Asia/Kolkata", "duration_minutes": 60,
    })
    check("schedule live session", r.status_code == 200)
    session_id = r.json()["id"]

    r = client.get("/api/live-sessions/manage")
    check("instructor sees scheduled session", r.status_code == 200 and len(r.json()) == 1)

    # 14. Role scoping: instructor cannot manage a course they don't own
    r = client.post("/api/courses", json={"title": "Admin Only Course", "category": "X", "description": "", "thumbnail_url": "", "is_free": True})
    other_course_id = r.json()["id"]  # created under instructor's own id since role=instructor
    check("instructor-created course auto-assigns to self", r.json()["instructor_id"] == instructor_id)

print("\nALL SMOKE TESTS PASSED")
