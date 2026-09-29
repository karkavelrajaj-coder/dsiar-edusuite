# D'siar Tech LMS — backend container (FastAPI).
#
# The frontend is deployed separately as a Render *Static Site* (just a
# `npm run build` + serving the static `dist/` folder — no server, no
# Docker needed, and it's free with no sleep). This Dockerfile only builds
# the API, which is the piece that actually needs a long-running process.
#
# Build/run locally:
#   docker build -t dsiar-lms-backend .
#   docker run -p 8000:8000 --env-file backend/.env dsiar-lms-backend

FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow (certificate image generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
