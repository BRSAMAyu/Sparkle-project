#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/restore_prod_data.sh <backup-dir>"
  exit 1
fi

BACKUP_DIR="$1"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-sparkle_db}"
POSTGRES_DB="${POSTGRES_DB:-sparkle}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-sparkle_redis}"
MINIO_CONTAINER="${MINIO_CONTAINER:-sparkle_minio}"
MINIO_DATA_PATH="${MINIO_DATA_PATH:-/data}"

if [[ ! -d "${BACKUP_DIR}" ]]; then
  echo "Backup directory not found: ${BACKUP_DIR}"
  exit 1
fi

echo "[restore] source=${BACKUP_DIR}"

if [[ -f "${BACKUP_DIR}/postgres.sql.gz" ]]; then
  echo "[restore] restoring postgres..."
  gunzip -c "${BACKUP_DIR}/postgres.sql.gz" \
    | docker exec -i "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"
fi

if [[ -f "${BACKUP_DIR}/redis.rdb" ]]; then
  echo "[restore] restoring redis snapshot..."
  docker cp "${BACKUP_DIR}/redis.rdb" "${REDIS_CONTAINER}:/data/dump.rdb"
  docker restart "${REDIS_CONTAINER}" >/dev/null
fi

if [[ -f "${BACKUP_DIR}/minio-data.tar.gz" ]]; then
  echo "[restore] restoring minio objects..."
  docker cp "${BACKUP_DIR}/minio-data.tar.gz" "${MINIO_CONTAINER}:/tmp/minio-data.tar.gz"
  docker exec "${MINIO_CONTAINER}" sh -lc "rm -rf ${MINIO_DATA_PATH:?}/* && tar -C ${MINIO_DATA_PATH} -xzf /tmp/minio-data.tar.gz"
  docker exec "${MINIO_CONTAINER}" rm -f /tmp/minio-data.tar.gz
fi

echo "[restore] done"
