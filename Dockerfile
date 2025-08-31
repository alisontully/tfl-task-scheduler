# syntax=docker/dockerfile:1
FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy metadata and source first (for proper wheel build + caching)
COPY pyproject.toml README.md ./
# If you commit poetry.lock and want reproducible locks, uncomment:
# COPY poetry.lock ./
COPY src ./src

# Install runtime deps from your project (PEP 517/518 build via poetry-core)
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir .

# If you have other non-src assets to include at runtime, copy them now
# COPY . .

EXPOSE 5555

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',5555))" || exit 1

# src/ layout requires the package import path here:
CMD ["uvicorn", "tfl_task_scheduler.main:app", "--host", "0.0.0.0", "--port", "5555"]
