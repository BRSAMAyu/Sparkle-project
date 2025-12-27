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
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o gateway cmd/server/main.go

FROM alpine:latest

# Install CA certificates and Timezone data
RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/gateway .

# Expose port
EXPOSE 8080

# Run the binary
CMD ["./gateway"]