"""Pydantic request/response models for every endpoint."""

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---------------------------------------------------------------

class LoginRequest(BaseModel):
    # Checkpoint 2 (multi-tenant): which client company's database to log
    # into. Required in the multi-tenant deployment; the registry lookup in
    # modules/auth.py is what actually enforces that.
    company_code: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    timezone: Optional[str] = None
    # Checkpoint 2 (multi-tenant): which company this session belongs to,
    # and what's switched on for them (e.g. features.live_sessions) — the
    # frontend uses this to decide what to show in navigation. Absent /
    # empty for a Super Admin session, which has no single tenant.
    company_code: Optional[str] = None
    company_name: Optional[str] = None
    features: dict = {}


# --- Platform (Super Admin) -------------------------------------------------

class PlatformLoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreateTenantRequest(BaseModel):
    company_code: str
    company_name: str
    plan: str = "starter"
    max_users: Optional[int] = 100
    features: dict = {}
    admin_name: str
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)


class UpdateTenantRequest(BaseModel):
    plan: Optional[str] = None
    max_users: Optional[int] = None
    features: Optional[dict] = None
    active: Optional[bool] = None


# --- Users (admin) --------------------------------------------------------

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "student"


class UpdateRoleRequest(BaseModel):
    role: str


class UpdateStatusRequest(BaseModel):
    disabled: bool


class SetTimezoneRequest(BaseModel):
    timezone: str


# --- Admin settings (Digital Samba credentials, session length) -----------

class SettingsOut(BaseModel):
    digitalsamba_developer_key: Optional[str] = None
    digitalsamba_developer_key_set: bool = False
    digitalsamba_developer_key_source: str = "env"
    digitalsamba_team_id: Optional[str] = None
    digitalsamba_team_id_set: bool = False
    digitalsamba_team_id_source: str = "env"
    jwt_expire_minutes: int
    jwt_expire_minutes_source: str = "env"
    quiz_pass_percent: int
    quiz_pass_percent_source: str = "default"
    quiz_max_attempts: int
    quiz_max_attempts_source: str = "default"
    quiz_shuffle_questions: bool
    quiz_shuffle_questions_source: str = "default"
    quiz_shuffle_options: bool
    quiz_shuffle_options_source: str = "default"


class SettingsUpdate(BaseModel):
    # Any field left out of the request body is left untouched. Sending
    # null clears that override and falls back to the default again (see
    # runtime_settings.py).
    digitalsamba_developer_key: Optional[str] = None
    digitalsamba_team_id: Optional[str] = None
    jwt_expire_minutes: Optional[int] = Field(default=None, ge=5, le=43200)
    quiz_pass_percent: Optional[int] = Field(default=None, ge=0, le=100)
    quiz_max_attempts: Optional[int] = Field(default=None, ge=0, le=50)
    quiz_shuffle_questions: Optional[bool] = None
    quiz_shuffle_options: Optional[bool] = None


# --- Courses --------------------------------------------------------------

class CreateCourseRequest(BaseModel):
    title: str
    category: str = ""
    description: str = ""
    thumbnail_url: str = ""
    is_free: bool = True
    instructor_id: Optional[str] = None
    # Checkpoint 2: track is set once, on the course itself, by whoever
    # creates it — not per student/enrollment. Every student enrolled in
    # this course sees the same track labeling.
    track: str = "course"  # course | internship | diploma | nano_degree


class UpdateCourseRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_free: Optional[bool] = None
    instructor_id: Optional[str] = None
    track: Optional[str] = None


# --- Modules / Lessons -----------------------------------------------------

class CreateModuleRequest(BaseModel):
    title: str


class UpdateModuleRequest(BaseModel):
    title: str


class CreateLessonRequest(BaseModel):
    title: str
    youtube_id: str = ""
    ppt_link: str = ""
    colab_link: str = ""
    dataset_link: str = ""


class UpdateLessonRequest(BaseModel):
    title: Optional[str] = None
    youtube_id: Optional[str] = None
    ppt_link: Optional[str] = None
    colab_link: Optional[str] = None
    dataset_link: Optional[str] = None


# --- Enrollments ------------------------------------------------------------

class CreateEnrollmentRequest(BaseModel):
    user_id: str
    course_id: str
    # No track here in Checkpoint 2 — track lives on the course itself now
    # (see CreateCourseRequest.track), the same for every student.


# --- Assignments / Submissions ---------------------------------------------

class CreateAssignmentRequest(BaseModel):
    course_id: str
    title: str
    description: str = ""
    due_date: Optional[str] = None


class UpdateAssignmentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None


class SubmitAssignmentRequest(BaseModel):
    link_or_text: str


class GradeSubmissionRequest(BaseModel):
    grade: int = Field(ge=0, le=100)
    status: str  # pending | approved | rejected
    feedback: str = ""


# --- Module quizzes (5 auto-graded questions per module) -------------------

class QuizOptionIn(BaseModel):
    id: Optional[str] = None  # server assigns one if omitted
    text: str


class QuizQuestionIn(BaseModel):
    id: Optional[str] = None  # server assigns one if omitted
    type: str  # "single" | "multi" | "true_false"
    text: str
    options: list[QuizOptionIn]
    correct_option_ids: list[str]


class SaveQuizRequest(BaseModel):
    # Was pinned to exactly 5 — the one-by-one quiz builder now lets an
    # admin/instructor add or remove individual questions, so this just
    # keeps a sane floor/ceiling instead of a fixed count. The bulk-import
    # template (modules/bulk.py) still expects exactly 5 rows per module —
    # that's a separate, unrelated constraint on the spreadsheet format.
    questions: list[QuizQuestionIn] = Field(min_length=1, max_length=50)


class SubmitQuizAnswer(BaseModel):
    question_id: str
    selected_option_ids: list[str] = []


class SubmitQuizRequest(BaseModel):
    answers: list[SubmitQuizAnswer]


# --- Live sessions ----------------------------------------------------------

class CreateLiveSessionRequest(BaseModel):
    course_id: str
    title: str
    description: str = ""
    date: date
    time: time
    timezone: str
    duration_minutes: int = Field(default=60, ge=15, le=300)


class UpdateLiveSessionRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    timezone: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=300)
