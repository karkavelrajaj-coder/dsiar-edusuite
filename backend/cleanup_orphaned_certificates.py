"""One-time cleanup: finds certificates whose student is no longer
enrolled in that course (e.g. issued before the "removing an enrollment
also revokes its certificate" fix existed) and deletes them.

HOW TO RUN (from your own computer, same as seed_quizzes.py):

    pip install pymongo
    export MONGO_URI="mongodb+srv://karkavelrajaj_db_user:YOUR_PASSWORD@cluster0.ua3bzky.mongodb.net/?retryWrites=true&w=majority"
    python cleanup_orphaned_certificates.py            # dry run - just lists what it would delete
    python cleanup_orphaned_certificates.py --apply     # actually deletes them

SAFE TO RE-RUN: with no --apply flag it only reads and prints, never
writes. Only certificates with zero matching enrollment are touched;
anything for a student who is still enrolled in that course is left
alone.
"""

import os
import sys

from pymongo import MongoClient
from pymongo.server_api import ServerApi

MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME", "dsiar_lms_v2")
APPLY = "--apply" in sys.argv

if not MONGO_URI:
    print("ERROR: set the MONGO_URI environment variable first.")
    sys.exit(1)

client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
db = client[DB_NAME]

users = db["users"]
courses = db["courses"]
enrollments = db["enrollments"]
certificates = db["certificates"]

orphaned = []
for cert in certificates.find():
    has_enrollment = enrollments.find_one({"user_id": cert["user_id"], "course_id": cert["course_id"]})
    if has_enrollment:
        continue
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        student = users.find_one({"_id": ObjectId(cert["user_id"])})
    except InvalidId:
        student = None
    try:
        course = courses.find_one({"_id": ObjectId(cert["course_id"])})
    except InvalidId:
        course = None
    orphaned.append(
        {
            "cert_id": cert["cert_id"],
            "student": student["email"] if student else f"(deleted user {cert['user_id']})",
            "course": course["title"] if course else f"(deleted course {cert['course_id']})",
            "_id": cert["_id"],
        }
    )

if not orphaned:
    print("No orphaned certificates found. Nothing to do.")
    sys.exit(0)

print(f"Found {len(orphaned)} orphaned certificate(s) (issued, but student no longer enrolled):\n")
for o in orphaned:
    print(f"  - {o['cert_id']}  |  {o['student']}  |  {o['course']}")

if not APPLY:
    print("\nDry run only - nothing deleted. Re-run with --apply to delete these.")
    sys.exit(0)

result = certificates.delete_many({"_id": {"$in": [o["_id"] for o in orphaned]}})
print(f"\nDeleted {result.deleted_count} orphaned certificate(s).")
