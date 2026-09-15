# Builder stage with uv for faster dependency resolution
# P2: Modernized dependency management with uv (50%+ faster builds)
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv for fast dependency resolution without external image dependency
RUN pip install --no-cache-dir uv

# Install build dependencies
RUN apt-get -o Acquire::Retries=5 update && apt-get install -y --fix-missing --no-install-recommends -o Acquire::Retries=5 \
    build-essential \
    gcc \
    libc6-dev \
    libpq-dev \
    liblzo2-dev \
    && rm -rf /var/lib/apt/lists/*

# python-lzo can fail under uv's isolated wheel build on aarch64; prebuild it with pip first.
RUN pip install --no-cache-dir python-lzo==1.15

# Copy dependency files
COPY pyproject.toml .
COPY requirements.txt .
COPY uv.lock* .

# Install dependencies using uv with locked version (if available) or requirements.txt
# For faster, more reproducible builds, ensure uv.lock is generated locally with: uv lock
RUN if [ -f uv.lock ]; then \
      uv export --frozen --no-dev --no-emit-project --no-header --format requirements-txt -o /tmp/requirements.lock.txt; \
      uv pip install --system --no-cache -r /tmp/requirements.lock.txt; \
    else \
      uv pip install --system --no-cache -r requirements.txt || \
      pip install --no-cache-dir -r requirements.txt; \
    fi

# 一次性补齐所有大概率缺失的 AI 核心包
# 补齐所有 AI 和文档处理包
RUN uv pip install --system --no-cache \
    celery \
    grpcio-reflection \
    pdfplumber pypdf python-docx python-pptx \
    langgraph langchain-openai langchain-anthropic \
    langchain-community langchain-core langchain-text-splitters \
    langchain-huggingface dashscope \
    cryptography pydantic-settings tiktoken \
    openpyxl python-multipart \
    # HTML parsing utils (keep lightweight optional parsers)
    beautifulsoup4 lxml \
    y-py>=0.6.0
# Final stage
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a stable non-root application user for security. The fixed UID/GID
# lets compose pin runtime users and keeps named volume ownership predictable.
ARG SPARKLE_UID=10001
ARG SPARKLE_GID=10001
RUN groupadd --gid "${SPARKLE_GID}" sparkle \
    && useradd --uid "${SPARKLE_UID}" --gid sparkle --home-dir /app --shell /usr/sbin/nologin sparkle

# Install runtime dependencies (libpq5 for PostgreSQL, curl for healthchecks)
RUN apt-get -o Acquire::Retries=5 update && apt-get install -y --fix-missing --no-install-recommends -o Acquire::Retries=5 \
    libpq5 \
    liblzo2-2 \
    libglib2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    shared-mime-info \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*


# Copy installed python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# Make entrypoint executable and ensure runtime write paths exist before the
# image switches away from root.
RUN mkdir -p /app/logs /app/uploads /app/data /app/.cache \
    && chmod +x /app/docker-entrypoint.sh

# Set ownership to sparkle user
RUN chown -R sparkle:sparkle /app

# Switch to non-root user
USER sparkle

# Expose port
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
