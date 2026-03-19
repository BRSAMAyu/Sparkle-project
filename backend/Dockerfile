# Builder stage with uv for faster dependency resolution
# P2: Modernized dependency management with uv (50%+ faster builds)
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv for fast dependency resolution without external image dependency
RUN pip install --no-cache-dir uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libc6-dev \
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

# 一次性补齐所有大概率缺失的 AI 核心包
# 补齐所有 AI 和文档处理包
RUN uv pip install --system --no-cache \
    pdfplumber pypdf python-docx python-pptx \
    langgraph langchain-openai langchain-anthropic \
    langchain-community langchain-core langchain-text-splitters \
    langchain-huggingface dashscope \
    cryptography pydantic-settings tiktoken \
    openpyxl python-multipart \
    # HTML parsing utils (keep lightweight optional parsers)
    beautifulsoup4 lxml
# Final stage
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root application user for security
RUN groupadd -r sparkle && useradd -r -g sparkle sparkle

# Install runtime dependencies (libpq5 for PostgreSQL, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
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

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Set ownership to sparkle user
RUN chown -R sparkle:sparkle /app

# Switch to non-root user
USER sparkle

# Expose port
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
