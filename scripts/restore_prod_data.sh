#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# restore_prod_data.sh — 备份包恢复（staging 演练 / 灾难恢复通路）
#
# O-05 演练（V3-FIX-504）修前 RED 实录：对"备份后继续演化"的库重放旧式转储，
# 2156 条 already-exists/duplicate-key 错误被 psql 静默吞掉、脚本退出码 0——
# 产出混合态：备份后新增行残留（ghost）、备份后硬删行未找回、run 状态被
# 备份后推进污染、outbox/processed_events 漂移全数存活。
#
# 本版三条硬保证：
#   1. PG 快照语义：配 --clean --if-exists 转储 + ON_ERROR_STOP=1 + 恢复前排空
#      目标库连接（防 DROP 被长事务锁挂死），恢复结果 = 备份点精确快照；
#   2. MinIO 无 tar 通路：官方镜像不带 tar（生产镜像实测 exit 127），改宿主机
#      解包 + 容器内 rm 清空后 docker cp 整树精确交换（多余对象随 .minio.sys
#      一并清除，与 PG --clean 同一快照语义），重启重扫元数据；
#   3. 假成功不可能：任何 SQL 错误即中断非零退出；schema 代差（manifest
#      alembic_head != 库内 alembic_version）按 STRICT_SCHEMA=1 可升级为硬失败。
#
# 用法: bash scripts/restore_prod_data.sh <backup-dir>
# 环境变量：容器名/库名同 backup_prod_data.sh；STRICT_SCHEMA=1 时 schema 代差硬失败。
# =============================================================================

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/restore_prod_data.sh <backup-dir>"
  exit 1
fi

BACKUP_DIR="$1"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-sparkle_proj_db}"
POSTGRES_DB="${POSTGRES_DB:-sparkle}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-sparkle_proj_redis}"
MINIO_CONTAINER="${MINIO_CONTAINER:-sparkle_proj_minio}"
MINIO_DATA_PATH="${MINIO_DATA_PATH:-/data}"
STRICT_SCHEMA="${STRICT_SCHEMA:-0}"
# V3-FIX-532①：REDIS_PASSWORD 必须有缺省——set -u 下未导出时 `${REDIS_PASSWORD}`
# 本身即 unbound 崩溃（与下方空数组展开同属无密码路径断链）。
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# 从仓库根 .env 提取单键值（只取值、不 source；与 backup_prod_data.sh 同法）。
# 当前用于未来需要凭据的恢复路径；保持与 backup 侧同一解析语义。
env_get() {
  local key="$1" val=""
  local script_dir env_file
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  env_file="${script_dir}/../.env"
  if [[ -f "${env_file}" ]]; then
    val="$(grep -E "^${key}=" "${env_file}" | tail -n 1 | cut -d= -f2- | tr -d '\r')"
    if [[ ${#val} -ge 2 ]]; then
      if [[ "${val:0:1}" == '"' && "${val: -1}" == '"' ]]; then val="${val:1:${#val}-2}"; fi
      if [[ "${val:0:1}" == "'" && "${val: -1}" == "'" ]]; then val="${val:1:${#val}-2}"; fi
    fi
  fi
  printf '%s' "${val}"
}
# shellcheck disable=SC2317  # env_get 预留给需要凭据的恢复路径

# redis-cli 容器执行器（与 backup_prod_data.sh 的 redis_cli 同形）。
# V3-FIX-532①：旧实现 `_redis_cli_args=()` 空数组后 `"${_redis_cli_args[@]}"`
# 展开，在 bash<4.4 且 set -u 下空数组即 unbound 崩溃（本机 bash 3.2.57 实测：
# PG 恢复完成后中止——最脆弱时点断链）。按密码有无显式分支，不使用数组展开。
redis_cli_exec() {
  if [[ -n "${REDIS_PASSWORD}" ]]; then
    docker exec -e "REDISCLI_AUTH=${REDIS_PASSWORD}" "${REDIS_CONTAINER}" redis-cli "$@"
  else
    docker exec "${REDIS_CONTAINER}" redis-cli "$@"
  fi
}

verify_checksums() {
  if [[ ! -f "${BACKUP_DIR}/sha256sums.txt" ]]; then
    echo "[restore] WARNING: checksum file missing; bundle is unverified (legacy or partial backup)" >&2
    return 0
  fi

  echo "[restore] verifying checksums..."
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "${BACKUP_DIR}" && sha256sum -c sha256sums.txt)
  elif command -v shasum >/dev/null 2>&1; then
    (cd "${BACKUP_DIR}" && shasum -a 256 -c sha256sums.txt)
  else
    echo "[restore] checksum tool not found; install sha256sum or shasum" >&2
    return 1
  fi
}

if [[ ! -d "${BACKUP_DIR}" ]]; then
  echo "Backup directory not found: ${BACKUP_DIR}"
  exit 1
fi

_RESTORE_START_EPOCH="$(date +%s)"

echo "[restore] source=${BACKUP_DIR}"
verify_checksums

# ---- schema 代差核对：备份包与目标库的 alembic head 不一致 = 新代码吃旧包
# （或反向），恢复后引擎行为未定义。默认告警，STRICT_SCHEMA=1 时硬失败。
_manifest_alembic="$(python3 -c "import json;print(json.load(open('${BACKUP_DIR}/manifest.json')).get('alembic_head',''))" 2>/dev/null || true)"
if [[ -n "${_manifest_alembic}" && "${_manifest_alembic}" != "unknown" ]]; then
  _db_alembic="$(docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -t -A -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "")"
  if [[ -n "${_db_alembic}" && "${_db_alembic}" != "${_manifest_alembic}" ]]; then
    if [[ "${STRICT_SCHEMA}" == "1" ]]; then
      echo "[restore] FATAL: schema drift — bundle alembic_head=${_manifest_alembic} != db ${_db_alembic}" >&2
      exit 1
    fi
    echo "[restore] WARNING: schema drift — bundle alembic_head=${_manifest_alembic} != db ${_db_alembic}（恢复后需跑 alembic 迁移对齐）" >&2
  fi
fi

if [[ -f "${BACKUP_DIR}/postgres.sql.gz" ]]; then
  echo "[restore] restoring postgres (clean+if-exists replay, ON_ERROR_STOP=1)..."
  # 排空目标库其它连接：--clean 的 DROP TABLE 会被残留长事务锁挂死，
  # 表现为 restore 无限等待（演练实录外的常见翻车点）。
  docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();" \
    >/dev/null 2>&1 || true
  gunzip -c "${BACKUP_DIR}/postgres.sql.gz" \
    | docker exec -i "${POSTGRES_CONTAINER}" psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" "${POSTGRES_DB}"
fi

if [[ -f "${BACKUP_DIR}/redis.rdb" ]]; then
  echo "[restore] restoring redis snapshot..."
  # redis-stack-server 的持久化 dir 是 /var/lib/redis-stack 而非 /data
  # （演练容器实测：写 /data/dump.rdb 后重启零加载——静默无效恢复，V3-FIX-505）。
  # 恢复目标路径必须取自目标服务器自身 CONFIG GET dir。
  _redis_dir="$(redis_cli_exec --no-auth-warning CONFIG GET dir 2>/dev/null | tail -n 1 | tr -d '\r')"
  _redis_dir="${_redis_dir:-/data}"
  echo "[restore] redis persistence dir=${_redis_dir}"
  docker cp "${BACKUP_DIR}/redis.rdb" "${REDIS_CONTAINER}:${_redis_dir}/dump.rdb"
  docker restart "${REDIS_CONTAINER}" >/dev/null
fi

if [[ -f "${BACKUP_DIR}/minio-data.tar.gz" ]]; then
  echo "[restore] restoring minio objects (exact swap)..."
  # 精确交换路径（无 tar/mc 依赖，官方镜像实测只带 rm/ls/mv 等 coreutils）：
  #   1) 清空数据面（含 .minio.sys——备份后新增对象/桶随旧元数据一并清除，
  #      与 PG --clean 同一快照语义；恢复即停机窗口，清空竞态可接受）；
  #   2) 宿主机解包 + docker cp 整树拷入（容器内无 tar，不能在容器内解包）；
  #   3) 重启让 MinIO 重扫元数据。
  _tmp_snap="$(mktemp -d)"
  tar -xzf "${BACKUP_DIR}/minio-data.tar.gz" -C "${_tmp_snap}"
  docker exec "${MINIO_CONTAINER}" sh -lc "rm -rf ${MINIO_DATA_PATH:?}/* ${MINIO_DATA_PATH:?}/.[!.]*"
  docker cp "${_tmp_snap}/." "${MINIO_CONTAINER}:${MINIO_DATA_PATH}/"
  rm -rf "${_tmp_snap}"
  docker restart "${MINIO_CONTAINER}" >/dev/null
else
  echo "[restore] WARNING: no minio-data.tar.gz in bundle; minio data plane NOT restored" >&2
fi

_restore_end="$(date +%s)"
echo "[restore] done in $((_restore_end - _RESTORE_START_EPOCH))s"
