# Builder stage with uv for faster dependency resolution
# P2: Modernized dependency management with uv (50%+ faster builds)
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml .
COPY requirements.txt .
COPY uv.lock* .

# Install dependencies using uv with locked version (if available) or requirements.txt
# For faster, more reproducible builds, ensure uv.lock is generated locally with: uv lock
RUN if [ -f uv.lock ]; then \
      uv pip install --system --no-cache --requirements uv.lock; \
    else \
      uv pip install --system --no-cache -r requirements.txt || \
      pip install --no-cache-dir -r requirements.txt; \
    fi

# Final stage
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root application user for security
RUN groupadd -r sparkle && useradd -r -g sparkle sparkle

# Install runtime dependencies (libpq5 for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# Set ownership to sparkle user
RUN chown -R sparkle:sparkle /app

# Switch to non-root user
USER sparkle

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
