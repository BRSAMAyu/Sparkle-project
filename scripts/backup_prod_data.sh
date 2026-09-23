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

# prod Redis 三账号 ACL 形制下 default 账号也带密码（docker-compose.prod.yml users.acl）。
# cron 调度环境没有 shell profile，未显式传 REDIS_PASSWORD 时从仓库根 .env 提取一次——
# 只取值、不 source（避免执行 .env 内容）；去引号语义与 scripts/deploy/bootstrap.sh env_get 一致。
if [[ -z "${REDIS_PASSWORD}" ]]; then
  _backup_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  _env_file="${_backup_script_dir}/../.env"
  if [[ -f "${_env_file}" ]]; then
    _val="$(grep -E '^REDIS_PASSWORD=' "${_env_file}" | tail -n 1 | cut -d= -f2- | tr -d '\r')"
    if [[ ${#_val} -ge 2 ]]; then
      if [[ "${_val:0:1}" == '"' && "${_val: -1}" == '"' ]]; then _val="${_val:1:${#_val}-2}"; fi
      if [[ "${_val:0:1}" == "'" && "${_val: -1}" == "'" ]]; then _val="${_val:1:${#_val}-2}"; fi
    fi
    if [[ -n "${_val}" ]]; then
      REDIS_PASSWORD="${_val}"
      export REDIS_PASSWORD
    fi
  fi
  unset _backup_script_dir _env_file _val
fi

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
