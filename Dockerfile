# S.P.A.R.K. — Dockerfile for Google Cloud Run
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (ffmpeg, tesseract-ocr for image tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy only cloud-safe requirements first to leverage Docker layer caching
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

# Copy all application source code
COPY . .

# Cloud Run sets the PORT environment variable dynamically (defaults to 8080)
EXPOSE 8080

# Run uvicorn server binding to port assigned by Cloud Run
CMD exec uvicorn api.server:app --host 0.0.0.0 --port ${PORT:-8080}
