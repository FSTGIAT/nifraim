# Stage 1: Build frontend
# Official Docker images via AWS's public mirror: Docker Hub rate-limits Railway's
# shared builders (2026-10-10: two deploys failed with "429 Too Many Requests").
FROM public.ecr.aws/docker/library/node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend
FROM public.ecr.aws/docker/library/python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    tesseract-ocr tesseract-ocr-heb poppler-utils && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Playwright chromium binary + system libs (libnss3, libgbm, fonts, …) for portal automation
RUN python -m playwright install --with-deps chromium

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

EXPOSE 8080

CMD sh -c "echo '=== Starting deployment ===' && python -m alembic upgrade heads && echo '=== Migrations OK ===' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
