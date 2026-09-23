#!/usr/bin/env bash
# =============================================================================
# scripts/install_backup_cron.sh — 备份 cron 调度面安装器（D-DEPLOY-FIX G2）
# =============================================================================
# 对应 D-DEPLOY 报告 §2 G2 最小解①：「bootstrap 加一步安装 cron 条目 + 校验首次备份」。
# 背景：备份脚本（scripts/backup_prod_data.sh，PG dump + Redis RDB + MinIO tar，
#       sha256sums + 7 天滚动清理）早已在库，但 cron 只是摘要里的一行建议——
#       没有落地机制等于没有备份。本脚本把「建议」变成「装机即有」。
#
# 载体选择：宿主 crontab（每台 Linux VPS 自带，零新容器、零 systemd 单元放置权限）。
#           否决 prod compose 内 cron 服务形态：需要把 docker.sock 挂进调度容器，
#           攻击面与镜像依赖都不划算（D-DEPLOY-FIX 报告 §G2 有记录）。
# 幂等：只管理本脚本 marker 注释块内的条目，重装先摘旧块再写新块，
#       不碰用户 crontab 里的其它条目。
# 异地化：登记待办、未实现（单机磁盘损坏 = 备份同损）——后续把 ./backups 最新包
#         mc mirror 到对象存储（约 ¥5-10/月；可先用 MinIO 的 sparkle-backups 桶过渡）。
#
# 用法：
#   bash scripts/install_backup_cron.sh [--print] [--run-now] [--remove]
#
#   --print    干跑：只打印将写入的 crontab 条目，不做任何变更
#   --run-now  安装后立即跑一次备份，校验 PG+Redis+MinIO 三件套链路
#              （演示期数据量级为 MB 级；失败以退出码 2 区分，不掩蔽安装成败）
#   --remove   摘除本管理块（其余 crontab 条目原样保留）
#
# 退出码：0 = 安装成功且（若 --run-now）首次备份通过；2 = 安装成功但首次备份失败；
#         1 = 安装本身失败。
# 环境变量：SPARKLE_BACKUP_REPO_DIR（默认脚本上级目录）、SPARKLE_BACKUP_SCHEDULE（默认 15 3 * * *）。
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${SPARKLE_BACKUP_REPO_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
SCHEDULE="${SPARKLE_BACKUP_SCHEDULE:-15 3 * * *}"
LOG_FILE="${REPO_DIR}/backups/backup.log"

BEGIN_MARK="# === sparkle-backup cron (managed by scripts/install_backup_cron.sh; do not edit inline) ==="
END_MARK="# === sparkle-backup cron end ==="

log()  { printf '[backup-cron] %s\n' "$*"; }
warn() { printf '[backup-cron] ⚠️  %s\n' "$*" >&2; }
die()  { printf '[backup-cron] ❌ %s\n' "$*" >&2; exit 1; }

# 管理块全文（crontab 条目用绝对仓库路径；cron 默认 PATH 可找到 bash/docker）
managed_block() {
  printf '%s\n' "${BEGIN_MARK}"
  printf '%s cd %s && bash scripts/backup_prod_data.sh >> %s 2>&1\n' "${SCHEDULE}" "${REPO_DIR}" "${LOG_FILE}"
  printf '%s\n' "${END_MARK}"
}

current_crontab() {
  crontab -l 2>/dev/null || true
}

# stdin -> stdout：摘除管理块，其余条目原样透传（awk 字符串匹配，免正则转义坑）
strip_managed_block() {
  awk -v b="${BEGIN_MARK}" -v e="${END_MARK}" \
    'index($0, b) == 1 { skip = 1; next } index($0, e) == 1 { skip = 0; next } !skip { print }'
}

do_print() {
  log "将写入 crontab（用户: $(id -un)）的管理块："
  managed_block | sed 's/^/    /'
}

do_install() {
  command -v crontab >/dev/null 2>&1 ||
    die "宿主机没有 crontab 命令（cron 未安装？）。手动安装一行即可: $(managed_block | sed -n 2p)"
  # 备份日志的重定向先于备份脚本执行，目录必须先存在
  mkdir -p "${REPO_DIR}/backups"
  local rest merged
  rest="$(current_crontab | strip_managed_block)"
  if [[ -n "${rest}" ]]; then
    merged="$(printf '%s\n%s\n' "${rest}" "$(managed_block)")"
  else
    merged="$(managed_block)"
  fi
  printf '%s\n' "${merged}" | crontab -
  log "crontab 条目已安装（用户: $(id -un)，调度: ${SCHEDULE}）:"
  managed_block | sed -n 2p | sed 's/^/    /'
  log "日志: ${LOG_FILE}；备份保留 KEEP_DAYS=7 天滚动"
}

do_remove() {
  local rest
  rest="$(current_crontab | strip_managed_block)"
  if [[ -z "${rest}" ]]; then
    crontab -r 2>/dev/null || true
    log "管理块已摘除；crontab 无其它条目，已整体移除"
  else
    printf '%s\n' "${rest}" | crontab -
    log "管理块已摘除（其余条目原样保留）"
  fi
}

do_run_now() {
  log "首次备份校验（PG dump + Redis RDB + MinIO tar + sha256sums）…"
  if (cd "${REPO_DIR}" && bash scripts/backup_prod_data.sh); then
    log "首次备份通过（包位于 ${REPO_DIR}/backups/，还原演练: bash scripts/restore_prod_data.sh <包>）"
    return 0
  fi
  warn "首次备份失败（不阻塞上线）。排查: cd ${REPO_DIR} && bash scripts/backup_prod_data.sh"
  warn "常见原因: docker 权限（cron 用户需能 docker exec sparkle_db）/ .env 缺 REDIS_PASSWORD"
  return 2
}

MODE="install"
RUN_NOW=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --print)  MODE="print" ;;
    --remove) MODE="remove" ;;
    --run-now) RUN_NOW=true ;;
    -h | --help)
      grep -E '^#   ' "$BASH_SOURCE" | head -12 | sed 's/^#   //'
      exit 0
      ;;
    *) die "未知参数: $1（--help 看用法）" ;;
  esac
  shift
done

case "${MODE}" in
  print)  do_print ;;
  remove) do_remove ;;
  install)
    do_install
    if [[ "${RUN_NOW}" == "true" ]]; then
      do_run_now || exit 2   # 安装成功、首次备份失败 → 退出码 2
    fi
    ;;
esac
