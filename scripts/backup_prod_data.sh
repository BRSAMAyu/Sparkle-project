#!/usr/bin/env bash
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-./backups}"
STAMP="${STAMP:-$(date +%Y%m%d_%H%M%S)}"
TARGET_DIR="${BACKUP_ROOT}/${STAMP}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-sparkle_db}"
POSTGRES_DB="${POSTGRES_DB:-sparkle}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-sparkle_redis}"
MINIO_CONTAINER="${MINIO_CONTAINER:-sparkle_minio}"
MINIO_DATA_PATH="${MINIO_DATA_PATH:-/data}"
KEEP_DAYS="${KEEP_DAYS:-7}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

checksum_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$@"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$@"
  else
    echo "[backup] checksum tool not found; install sha256sum or shasum" >&2
    return 1
  fi
}

redis_cli() {
  if [[ -n "${REDIS_PASSWORD}" ]]; then
    docker exec -e REDISCLI_AUTH="${REDIS_PASSWORD}" "${REDIS_CONTAINER}" redis-cli "$@"
  else
    docker exec "${REDIS_CONTAINER}" redis-cli "$@"
  fi
}

mkdir -p "${TARGET_DIR}"

echo "[backup] target=${TARGET_DIR}"

echo "[backup] dumping postgres..."
docker exec -t "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
  | gzip > "${TARGET_DIR}/postgres.sql.gz"

echo "[backup] snapshotting redis..."
redis_cli --rdb /tmp/sparkle-backup.rdb >/dev/null
docker cp "${REDIS_CONTAINER}:/tmp/sparkle-backup.rdb" "${TARGET_DIR}/redis.rdb"
docker exec "${REDIS_CONTAINER}" rm -f /tmp/sparkle-backup.rdb

echo "[backup] archiving minio..."
docker exec "${MINIO_CONTAINER}" tar -C "${MINIO_DATA_PATH}" -czf /tmp/minio-data.tar.gz .
docker cp "${MINIO_CONTAINER}:/tmp/minio-data.tar.gz" "${TARGET_DIR}/minio-data.tar.gz"
docker exec "${MINIO_CONTAINER}" rm -f /tmp/minio-data.tar.gz

echo "[backup] writing checksums..."
(
  cd "${TARGET_DIR}"
  checksum_file postgres.sql.gz redis.rdb minio-data.tar.gz > sha256sums.txt
)

cat > "${TARGET_DIR}/manifest.json" <<EOF
{
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "postgres_container": "${POSTGRES_CONTAINER}",
  "postgres_db": "${POSTGRES_DB}",
  "redis_container": "${REDIS_CONTAINER}",
  "minio_container": "${MINIO_CONTAINER}",
  "minio_data_path": "${MINIO_DATA_PATH}",
  "checksum_file": "sha256sums.txt"
}
EOF

echo "[backup] pruning backups older than ${KEEP_DAYS} days..."
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +"${KEEP_DAYS}" -exec rm -rf {} +

echo "[backup] done"
