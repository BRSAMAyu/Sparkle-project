#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
IMAGE_TAG="${IMAGE_TAG:?IMAGE_TAG is required}"
GATEWAY_IMAGE="${GATEWAY_IMAGE:-}"
BACKEND_IMAGE="${BACKEND_IMAGE:-}"
DRAIN_SECONDS="${DRAIN_SECONDS:-90}"
OBSERVE_SECONDS="${OBSERVE_SECONDS:-180}"
SMOKE_URLS="${SMOKE_URLS:-/api/v1/health}"
APP_NETWORK="${APP_NETWORK:-sparkle_app}"
UPSTREAM_FILE="${UPSTREAM_FILE:-nginx/upstream.conf}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Missing compose file: $COMPOSE_FILE"
  exit 1
fi

mkdir -p "$(dirname "$UPSTREAM_FILE")"

if [[ ! -f "$UPSTREAM_FILE" ]]; then
  cat > "$UPSTREAM_FILE" <<EOF
upstream gateway_upstream {
  least_conn;
  server gateway_blue:8080;
  keepalive 64;
}
EOF
fi

current_color="$(grep -Eo 'gateway_(blue|green)' "$UPSTREAM_FILE" | head -1 | cut -d_ -f2 || true)"
if [[ "$current_color" != "blue" && "$current_color" != "green" ]]; then
  current_color="blue"
fi

if [[ "$current_color" == "blue" ]]; then
  target_color="green"
else
  target_color="blue"
fi

export IMAGE_TAG GATEWAY_IMAGE BACKEND_IMAGE

echo "Current: $current_color, Target: $target_color"

docker compose -f "$COMPOSE_FILE" pull "gateway_${target_color}" backend
docker compose -f "$COMPOSE_FILE" rm -f toxiproxy_init >/dev/null 2>&1 || true
docker compose -f "$COMPOSE_FILE" up -d backend "gateway_${target_color}" toxiproxy toxiproxy_init nginx

health_url="http://gateway_${target_color}:8080/api/v1/health"
echo "Health check: $health_url"
healthy="false"
for _ in $(seq 1 30); do
  if docker run --rm --network "$APP_NETWORK" curlimages/curl:8.7.1 -fsS "$health_url" >/dev/null 2>&1; then
    healthy="true"
    break
  fi
  sleep 2
done

if [[ "$healthy" != "true" ]]; then
  echo "Health check failed for gateway_${target_color}"
  exit 1
fi

cat > "$UPSTREAM_FILE" <<EOF
upstream gateway_upstream {
  least_conn;
  server gateway_${target_color}:8080;
  keepalive 64;
}
EOF

docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload

echo "Running smoke checks..."
smoke_failed="false"
for path in $SMOKE_URLS; do
  url="http://gateway_${target_color}:8080${path}"
  if ! docker run --rm --network "$APP_NETWORK" curlimages/curl:8.7.1 -fsS "$url" >/dev/null 2>&1; then
    echo "Smoke failed: $url"
    smoke_failed="true"
    break
  fi
done

if [[ "$smoke_failed" == "true" ]]; then
  echo "Smoke checks failed, rolling back to ${current_color}"
  cat > "$UPSTREAM_FILE" <<EOF
upstream gateway_upstream {
  least_conn;
  server gateway_${current_color}:8080;
  keepalive 64;
}
EOF
  docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload
  exit 1
fi

echo "Observing for ${OBSERVE_SECONDS}s..."
observe_failed="false"
end=$((SECONDS + OBSERVE_SECONDS))
while [[ $SECONDS -lt $end ]]; do
  if ! docker run --rm --network "$APP_NETWORK" curlimages/curl:8.7.1 -fsS "$health_url" >/dev/null 2>&1; then
    observe_failed="true"
    break
  fi
  sleep 5
done

if [[ "$observe_failed" == "true" ]]; then
  echo "Observation failed, rolling back to ${current_color}"
  cat > "$UPSTREAM_FILE" <<EOF
upstream gateway_upstream {
  least_conn;
  server gateway_${current_color}:8080;
  keepalive 64;
}
EOF
  docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload
  exit 1
fi

echo "Draining old gateway for ${DRAIN_SECONDS}s..."
sleep "$DRAIN_SECONDS"

docker compose -f "$COMPOSE_FILE" stop "gateway_${current_color}"

echo "Deployment complete. Active: $target_color"
