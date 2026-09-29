"""Port of views/certificates.py — lists the current user's certificates
and streams the generated PNG for each."""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Response

from db import certificates_col, courses_col
from security import get_current_user
from serializers import certificate_out
from utils.certificate_image import build_certificate
from utils.tenants import current_tenant
from utils.tracks import display_title, normalize_track

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id.")


def _track_for(course: dict | None) -> str:
    """Track lives on the course, not the enrollment or the certificate —
    look it up live so an admin's later edit to the course (PATCH
    /courses/{id}) is reflected immediately, without needing to touch any
    certificate row. Falls back to "course" if the course is somehow gone."""
    return normalize_track(course.get("track")) if course else "course"


@router.get("")
def my_certificates(user: dict = Depends(get_current_user)):
    out = []
    for cert in certificates_col().find({"user_id": user["id"]}):
        course = courses_col().find_one({"_id": _oid(cert["course_id"])})
        course_title = course["title"] if course else "Unknown course"
        track = _track_for(course)
        item = certificate_out(cert)
        # Suffixed for the page card (e.g. "Artificial Intelligence
        # Internship") — the certificate IMAGE itself uses the plain title
        # instead, since its heading/sentence already state the track.
        item["course_title"] = display_title(course_title, track)
        item["track"] = track
        out.append(item)
    return out


@router.get("/{cert_id}/image")
def certificate_image(cert_id: str, user: dict = Depends(get_current_user)):
    cert = certificates_col().find_one({"cert_id": cert_id})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")
    # Only the owner (or an admin/instructor previewing) can fetch the image.
    if cert["user_id"] != user["id"] and user["role"] not in ("admin", "instructor"):
        raise HTTPException(status_code=403, detail="Not your certificate.")

    course = courses_col().find_one({"_id": _oid(cert["course_id"])})
    course_title = course["title"] if course else "Unknown course"
    track = _track_for(course)

    from db import users_col  # local import to avoid a top-level circularity

    student = users_col().find_one({"_id": _oid(cert["user_id"])})
    student_name = student["name"] if student else "Unknown"

    tenant = current_tenant()

    image_bytes = build_certificate(
        student_name=student_name,
        course_title=course_title,  # plain title — heading/sentence already state the track
        cert_id=cert["cert_id"],
        issued_at=cert["issued_at"],
        track=track,
        # Checkpoint 2: logo/signature come from this client's own
        # {company_code}_logo.png / {company_code}_signature.png if present,
        # falling back to their plain company name in text otherwise — see
        # utils/certificate_image.py.
        company_code=tenant.get("company_code") if tenant else None,
        company_name=tenant.get("name") if tenant else None,
    )
    return Response(content=image_bytes, media_type="image/png")
