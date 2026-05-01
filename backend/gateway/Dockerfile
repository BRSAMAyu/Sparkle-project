FROM golang:1.24.0-alpine AS builder

WORKDIR /app

# Install git for go mod download if needed
RUN apk add --no-cache git

# Configure Go module proxy for better connectivity in China
ENV GOPROXY=https://goproxy.cn,direct
ENV GO111MODULE=on

COPY go.mod go.sum ./
RUN go mod download

COPY . .
# Build the binary
# -ldflags="-w -s" strips debug information to reduce size
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o gateway ./cmd/server

# Use debian slim for runtime to avoid Alpine TLS/apk issues
FROM debian:bookworm-slim

# Install CA certificates, timezone data, and curl (for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a stable non-root application user for security.
ARG SPARKLE_UID=10001
ARG SPARKLE_GID=10001
RUN groupadd --gid "${SPARKLE_GID}" sparkle \
    && useradd --uid "${SPARKLE_UID}" --gid sparkle --home-dir /app --shell /usr/sbin/nologin sparkle

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/gateway .

# Set ownership to sparkle user
RUN chown -R sparkle:sparkle /app

# Switch to non-root user
USER sparkle

# Expose port
EXPOSE 8080

# Run the binary
CMD ["./gateway"]
