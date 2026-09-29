"""Runs the real FastAPI app over real HTTP (uvicorn) but with the Mongo
client swapped for mongomock, so we can verify the full HTTP/cookie/CORS
stack works end-to-end without needing outbound network access to Atlas
(unavailable in this sandbox). This is ONLY for local verification here;
the real deployment uses the real MONGO_URI.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mongomock
import db as db_module

db_module._client = mongomock.MongoClient()

import uvicorn
from app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
