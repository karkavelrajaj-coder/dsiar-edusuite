"""Enrollment "tracks" — Course / Internship / Diploma / Nano Degree.

A track is set once on the enrollment, at enrollment time, by an admin (it
can also be edited later by an admin — see modules/enrollments.py). It does
NOT change what content a student sees or what's required to finish a
course: lessons, quizzes, and the assignment are identical across all four
tracks. It only changes how that same course is *labeled* for that student
— everywhere from "My Learning" to the certificate itself — and which
color/wording the certificate uses.

Single source of truth for both the backend (course-title suffixing,
certificate wording/color) and anything that needs the human-readable
track list (e.g. validating the admin's enroll-form choice).
"""

TRACK_COURSE = "course"
TRACK_INTERNSHIP = "internship"
TRACK_DIPLOMA = "diploma"
TRACK_NANO_DEGREE = "nano_degree"

VALID_TRACKS = {TRACK_COURSE, TRACK_INTERNSHIP, TRACK_DIPLOMA, TRACK_NANO_DEGREE}

TRACKS = {
    TRACK_COURSE: {
        "label": "Course",
        "suffix": "",  # "Artificial Intelligence" stays as-is
        "accent": "#4f46e5",  # LMS brand purple (--color-brand-600)
        "cert_heading": "CERTIFICATE OF COMPLETION",
        "cert_body": "has successfully completed the course",
    },
    TRACK_INTERNSHIP: {
        "label": "Internship",
        "suffix": " Internship",  # "Artificial Intelligence Internship"
        "accent": "#0d9488",  # teal
        "cert_heading": "CERTIFICATE OF INTERNSHIP",
        "cert_body": "has successfully completed the internship program in",
    },
    TRACK_DIPLOMA: {
        "label": "Diploma",
        "suffix": " Diploma",  # "Artificial Intelligence Diploma"
        "accent": "#b45309",  # amber/gold
        "cert_heading": "DIPLOMA CERTIFICATE",
        "cert_body": "has been awarded the Diploma in",
    },
    TRACK_NANO_DEGREE: {
        "label": "Nano Degree",
        "suffix": " Nano Degree",  # "Artificial Intelligence Nano Degree"
        "accent": "#1e40af",  # indigo/blue
        "cert_heading": "CERTIFICATE OF NANO DEGREE",
        "cert_body": "has successfully completed the Nano Degree program in",
    },
}


def normalize_track(track: str | None) -> str:
    """Any missing/unrecognized value (old enrollment docs from before this
    feature existed, or a bad value that somehow slipped through) falls
    back to the plain "course" track rather than erroring — nothing about
    a pre-existing enrollment should break."""
    return track if track in VALID_TRACKS else TRACK_COURSE


def track_meta(track: str | None) -> dict:
    return TRACKS[normalize_track(track)]


def display_title(course_title: str, track: str | None) -> str:
    """The suffixed title shown on student-facing pages (My Learning,
    Course Player, Assignments, the Certificates list card) — NOT on the
    certificate image itself, which uses the plain course_title because its
    heading/sentence already states the track (see certificate_image.py)."""
    return f"{course_title}{track_meta(track)['suffix']}"
