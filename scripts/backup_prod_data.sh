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
_BACKUP_START_EPOCH="$(date +%s)"

echo "[backup] target=${TARGET_DIR}"

echo "[backup] dumping postgres..."
# --clean --if-exists：转储自带 DROP/重建语句，restore 重放到既有库时先删后建，
# 得到与备份点完全一致的快照（备份后新增行被清掉、备份后硬删行被找回、
# 备份点已墓碑的 memory 不会以任何形态复活）。无此标志时 restore 进非空库
# 会 CREATE 冲突 + COPY 主键冲突，产出假成功的混合态（O-05 演练 RED 实录：
# 2156 条 SQL 错误、退出码仍 0）。--if-exists 保证空库/首装路径同样可重放。
docker exec -t "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" --clean --if-exists "${POSTGRES_DB}" \
  | gzip > "${TARGET_DIR}/postgres.sql.gz"

echo "[backup] snapshotting redis..."
redis_cli --rdb /tmp/sparkle-backup.rdb >/dev/null
docker cp "${REDIS_CONTAINER}:/tmp/sparkle-backup.rdb" "${TARGET_DIR}/redis.rdb"
docker exec "${REDIS_CONTAINER}" rm -f /tmp/sparkle-backup.rdb

echo "[backup] archiving minio..."
# MinIO 官方镜像（RELEASE.2025-09-07T16-13-09Z 已实测）不带 tar——原
# `docker exec minio tar -C /data ...` 在生产容器内 exit 127，且 set -e 令
# sha256sums/manifest 从未产出，cron 每晚实际拿不到完整备份包（O-05 演练实录）。
# 改为容器无关通路：docker cp 拷出数据面目录 → 宿主机 tar 打包（产物文件名
# minio-data.tar.gz 不变，restore 侧兼容）。注意这是对运行中服务的尽力一致
# 快照（demo 量级 MB 级 + 低峰 cron 03:15）；强一致窗口需停写或卷快照，见 notes。
if docker exec "${MINIO_CONTAINER}" sh -lc "test -d ${MINIO_DATA_PATH}" 2>/dev/null; then
  rm -rf "${TARGET_DIR}/minio-data"
  mkdir -p "${TARGET_DIR}/minio-data"
  docker cp "${MINIO_CONTAINER}:${MINIO_DATA_PATH}/." "${TARGET_DIR}/minio-data/"
  tar -C "${TARGET_DIR}/minio-data" -czf "${TARGET_DIR}/minio-data.tar.gz" .
  rm -rf "${TARGET_DIR}/minio-data"
else
  echo "[backup] WARNING: minio data path ${MINIO_DATA_PATH} missing in ${MINIO_CONTAINER}; skipping minio archive" >&2
fi

echo "[backup] writing checksums..."
(
  cd "${TARGET_DIR}"
  checksum_file postgres.sql.gz redis.rdb minio-data.tar.gz > sha256sums.txt
)

# ---- config 覆盖面：环境配置是恢复 staging 的前提（DEPLOYMENT.md：config 不进
# App；栈凭据/模型 key 只在部署 checkout 的 .env，不在 git 内）。没有 .env 的
# 备份包还原得出 schema 却起不了栈。权限 600——包内含密钥，不得放宽。
CONFIG_FILES=""
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_repo_env="${_script_dir}/../.env"
if [[ -f "${_repo_env}" ]]; then
  mkdir -p "${TARGET_DIR}/config"
  cp "${_repo_env}" "${TARGET_DIR}/config/env"
  chmod 600 "${TARGET_DIR}/config/env"
  CONFIG_FILES='["config/env"]'
  echo "[backup] config: .env captured (chmod 600)"
else
  CONFIG_FILES='[]'
  echo "[backup] WARNING: repo-root .env not found; backup bundle has no config plane" >&2
fi

# ---- manifest 增强：alembic 版本戳 + PG 服务端版本 + 转储标志 + 耗时（RPO/RTO
# 实测锚点）。restore 侧可据此核对 schema 代差，避免新代码库吃旧 schema 包。
_pg_server_version="$(docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -A -c "SHOW server_version_num;" 2>/dev/null || echo "unknown")"
_alembic_head="$(docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -A -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "unknown")"
_backup_end="$(date +%s)"
_backup_duration="$((_backup_end - _BACKUP_START_EPOCH))"

cat > "${TARGET_DIR}/manifest.json" <<EOF
{
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "postgres_container": "${POSTGRES_CONTAINER}",
  "postgres_db": "${POSTGRES_DB}",
  "postgres_server_version_num": "${_pg_server_version}",
  "postgres_dump_flags": "--clean --if-exists",
  "alembic_head": "${_alembic_head}",
  "redis_container": "${REDIS_CONTAINER}",
  "minio_container": "${MINIO_CONTAINER}",
  "minio_data_path": "${MINIO_DATA_PATH}",
  "config_files": ${CONFIG_FILES},
  "backup_duration_seconds": ${_backup_duration},
  "checksum_file": "sha256sums.txt"
}
EOF

echo "[backup] pruning backups older than ${KEEP_DAYS} days..."
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +"${KEEP_DAYS}" -exec rm -rf {} +

echo "[backup] done in ${_backup_duration}s"
