#!/usr/bin/env bash
# Copy Let's Encrypt SSL certificates to Sparkle project ssl/ directory
# Usage: ./scripts/ssl/setup_certs.sh <domain> [cert_dir]
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain> [cert_dir]}"
CERT_DIR="${2:-./ssl}"
SRC="/etc/letsencrypt/live/$DOMAIN"

if [ ! -f "$SRC/fullchain.pem" ]; then
    echo "ERROR: Certificate not found at $SRC/fullchain.pem"
    echo "Run 'sudo certbot certonly --standalone -d $DOMAIN' first"
    exit 1
fi

mkdir -p "$CERT_DIR"
cp "$SRC/fullchain.pem" "$CERT_DIR/fullchain.pem"
cp "$SRC/privkey.pem"   "$CERT_DIR/privkey.pem"
chmod 644 "$CERT_DIR/fullchain.pem"
chmod 600 "$CERT_DIR/privkey.pem"

echo "OK SSL certificates copied to $CERT_DIR"
echo "  fullchain.pem ($(wc -c < "$CERT_DIR/fullchain.pem") bytes)"
echo "  privkey.pem   ($(wc -c < "$CERT_DIR/privkey.pem") bytes)"
