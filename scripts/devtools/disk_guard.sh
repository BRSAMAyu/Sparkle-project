#!/usr/bin/env bash
# disk_guard.sh — Sparkle 开发机磁盘守卫（2026-09-18 多次 ENOSPC 事故后设立）
#
# 职责：每 60s 检查根盘空闲；低于软阈值清"已知安全缓存"，低于硬阈值追加清理
#       工作树构建产物；全部动作记 /tmp/disk_guard.log。永不删除：用户文档、
#       数据库卷、源码、截图档案。
#
# 用法：nohup bash scripts/devtools/disk_guard.sh >/dev/null 2>&1 &
#       （协调者会话负责拉起；重启后需重新拉起）

set -u
SOFT_MB=8000   # 8Gi 触发常规清理
HARD_MB=4000   # 4Gi 触发激进清理（含活跃工作树构建产物）
LOG=/tmp/disk_guard.log
WT_ROOT=/Users/brsama/code/GitHub/Sparkle-sysrev
MAIN_REPO=/Users/brsama/code/GitHub/Sparkle-project

free_mb() { df -m / | awk 'NR==2 {print $4}'; }
log() { echo "$(date '+%m-%d %H:%M:%S') $*" >> "$LOG"; }

safe_clean() {
  # 已完成/非活跃工作树的构建产物与分析缓存
  for wt in "$WT_ROOT"/wt*; do
    [ -d "$wt" ] || continue
    # 活跃判定：30 分钟内有 .dart_tool 写入的工作树跳过（其构建可能进行中）
    if [ -n "$(find "$wt/mobile/.dart_tool" -newermt '-30 minutes' -print -quit 2>/dev/null)" ]; then
      continue
    fi
    rm -rf "$wt/mobile/build" "$wt/mobile/.dart_tool" 2>/dev/null
  done
  find "$WT_ROOT" "$MAIN_REPO" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null
  find "$MAIN_REPO/backend" -name ".pytest_cache" -type d -prune -exec rm -rf {} + 2>/dev/null
  find /tmp -maxdepth 1 -name "*.log.*" -mtime +1 -delete 2>/dev/null
  docker builder prune -f >/dev/null 2>&1
}

aggressive_clean() {
  safe_clean
  # 全部工作树构建产物（含活跃）
  for wt in "$WT_ROOT"/wt*; do
    [ -d "$wt" ] || continue
    rm -rf "$wt/mobile/build" 2>/dev/null
  done
  rm -rf "$MAIN_REPO/mobile/build/web" 2>/dev/null
  xcrun simctl delete unavailable >/dev/null 2>&1
}

log "disk_guard started (soft=${SOFT_MB}MB hard=${HARD_MB}MB)"
while true; do
  mb=$(free_mb)
  if [ "$mb" -lt "$HARD_MB" ]; then
    log "HARD ${mb}MB — aggressive clean"
    aggressive_clean
  elif [ "$mb" -lt "$SOFT_MB" ]; then
    log "SOFT ${mb}MB — safe clean"
    safe_clean
  fi
  sleep 60
done
