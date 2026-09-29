"""One-time migration: copies EVERY document, exactly as-is, from the old
Streamlit app's database into this new app's database — same cluster,
different database name, so the Streamlit app is never modified.

READ-ONLY on the source database. This script only ever calls .find() on
SOURCE_DB_NAME. Every write goes to TARGET_DB_NAME.

_id values are preserved exactly, so all the string references the app
uses internally (course_id, module_id, user_id, assignment_id, etc., all
stored as str(ObjectId)) keep working identically after the copy — a
course's modules, a student's enrollments and progress, everything stays
linked exactly as it was.

Usage:
    cd backend
    python scripts/migrate_from_streamlit.py

Run this from your own machine (wherever you already have network access
to MongoDB Atlas and pymongo installed — the same environment you ran
seed_ml_course.py from). It reads MONGO_URI from backend/.env if present,
or you can export it as an environment variable first.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/ root

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from pymongo import MongoClient
from pymongo.errors import BulkWriteError
from pymongo.server_api import ServerApi

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    print("MONGO_URI not set. Either put it in backend/.env or:")
    print('  $env:MONGO_URI = "mongodb+srv://...`"   (PowerShell)')
    sys.exit(1)

SOURCE_DB_NAME = "dsiar_lms"       # the Streamlit app's database — READ ONLY
TARGET_DB_NAME = os.environ.get("DB_NAME", "dsiar_lms_v2")  # this app's database

COLLECTIONS = [
    "users",
    "courses",
    "modules",
    "lessons",
    "assignments",
    "submissions",
    "progress",
    "enrollments",
    "certificates",
    "live_sessions",
]

client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
source_db = client[SOURCE_DB_NAME]
target_db = client[TARGET_DB_NAME]

print(f"Source (read-only): {SOURCE_DB_NAME}")
print(f"Target:              {TARGET_DB_NAME}")
print()

confirm = input(
    f"This will DELETE everything currently in '{TARGET_DB_NAME}' and replace it with an\n"
    f"exact copy of '{SOURCE_DB_NAME}'. '{SOURCE_DB_NAME}' itself is never modified.\n"
    f"Continue? [y/N] "
)
if confirm.strip().lower() != "y":
    print("Cancelled — nothing was changed.")
    sys.exit(0)

print()
total = 0
for name in COLLECTIONS:
    source_col = source_db[name]
    target_col = target_db[name]

    docs = list(source_col.find())  # read-only against the source

    target_col.delete_many({})  # only ever touches the TARGET db
    if docs:
        try:
            target_col.insert_many(docs, ordered=True)
        except BulkWriteError as e:
            print(f"  ! {name}: bulk write error — {e.details.get('writeErrors', e.details)}")
            continue

    print(f"  {name}: {len(docs)} document(s) copied")
    total += len(docs)

print()
print(f"Done. {total} documents copied into '{TARGET_DB_NAME}'.")
print(f"'{SOURCE_DB_NAME}' (your Streamlit app's database) was not modified.")
print()
print("Note: your new app's seed admin account has been REPLACED by the exact")
print("admin account(s) from the old database — log in with your Streamlit")
print("app's admin credentials now, not the SEED_ADMIN_* values from Render.")
