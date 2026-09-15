#!/usr/bin/env bash
# Generate self-signed SSL certificates for development.
# For production, use Let's Encrypt or your own CA-signed certs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${1:-$SCRIPT_DIR/../../ssl}"

mkdir -p "$SSL_DIR"

if [ -f "$SSL_DIR/fullchain.pem" ] && [ -f "$SSL_DIR/privkey.pem" ]; then
  echo "[SSL] Certificates already exist in $SSL_DIR — skipping."
  echo "      Delete them and re-run to regenerate."
  exit 0
fi

echo "[SSL] Generating self-signed certificates in $SSL_DIR ..."

openssl req -x509 -nodes \
  -days 365 \
  -newkey rsa:2048 \
  -keyout "$SSL_DIR/privkey.pem" \
  -out "$SSL_DIR/fullchain.pem" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

echo "[SSL] Done. Mount $SSL_DIR as SSL_CERT_DIR in docker-compose."
