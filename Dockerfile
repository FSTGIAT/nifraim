# Stage 1: Build frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + serve frontend
FROM python:3.11-slim
WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Run from project root so relative paths work
WORKDIR /app

EXPOSE 8000

CMD cd backend && \
    echo "=== Starting deployment ===" && \
    echo "DATABASE_URL is set: $([ -n \"$DATABASE_URL\" ] && echo 'yes' || echo 'NO!')" && \
    echo "PORT: ${PORT:-8000}" && \
    (python -m alembic upgrade head 2>&1 && echo "=== Migrations OK ===" || echo "=== Migration failed, continuing... ===") && \
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
