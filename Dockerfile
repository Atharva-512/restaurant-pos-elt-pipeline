# ==================================================
# Restaurant POS ELT Pipeline
# Dockerfile
# ==================================================

FROM python:3.14-slim

# --------------------------------------------------
# OCI Labels
# --------------------------------------------------
LABEL org.opencontainers.image.title="Restaurant POS ELT Pipeline"
LABEL org.opencontainers.image.description="End-to-End ELT Pipeline using Medallion Architecture"
LABEL org.opencontainers.image.authors="Atharva Rahul Korwar"
LABEL org.opencontainers.image.version="1.0.0"

# --------------------------------------------------
# Python Environment
# --------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --------------------------------------------------
# Working Directory
# --------------------------------------------------
WORKDIR /app

# --------------------------------------------------
# Copy Runtime Requirements
# --------------------------------------------------
COPY requirements/requirements-runtime.txt .

# --------------------------------------------------
# Install Runtime Dependencies
# --------------------------------------------------
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-runtime.txt

# --------------------------------------------------
# Create Non-Root User
# --------------------------------------------------
RUN addgroup --system pipeline && \
    adduser --system --ingroup pipeline pipeline

USER pipeline

# --------------------------------------------------
# Health Check
# --------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
CMD python --version || exit 1

# --------------------------------------------------
# Default Entry Point
# --------------------------------------------------
ENTRYPOINT ["python", "main.py"]