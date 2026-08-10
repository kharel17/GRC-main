FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies for asyncpg and OCR (tesseract-ocr)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer & CrossEncoder models into image for air-gapped deployments
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
    SentenceTransformer('all-MiniLM-L6-v2'); \
    CrossEncoder('cross-encoder/ms-marco-MiniLM-L6-v2')"

COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 8000

# Run migrations before starting the app (non-fatal: server starts even if migrations fail)
CMD sh -c "alembic upgrade head || echo 'WARNING: Migration failed, starting server anyway'; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
