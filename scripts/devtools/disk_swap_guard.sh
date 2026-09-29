#!/bin/bash
# disk_swap_guard.sh — 资源双红线守卫（2026-09-30 用户铁令，AGENTS.md 资源双红线节）
# 每 15 分钟由 ZCode 定时自动化执行；分级主动处置，绝不等到崩溃。
# 日志：v3/06_agent_fleet/RESOURCE_GUARD.log（只追加）
set -u
LOG="/Users/brsama/code/GitHub/Sparkle-project/v3/06_agent_fleet/RESOURCE_GUARD.log"
OFFLOAD="/Volumes/移动E/sparkle-offload"
TS() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(TS)] $*" >> "$LOG"; }

# --- 读数 ---
DISK_FREE_GB=$(df -g / | tail -1 | awk '{print $4}')
SWAP_USED_MB=$(sysctl -n vm.swapusage | sed -n 's/.*used = \([0-9]\+\)\..*/\1/p')
SWAP_USED_MB=${SWAP_USED_MB:-0}
log "check disk_free=${DISK_FREE_GB}G swap_used=${SWAP_USED_MB}MB"

clean_worktree_builds() { # $1 = mode (t1: 1h 未动 / t2: 全部)
  local mode=$1
  for w in /Users/brsama/code/GitHub/wt*/mobile/build /Users/brsama/code/GitHub/Sparkle-project/mobile/build; do
    [ -d "$w" ] || continue
    if [ "$mode" = t1 ]; then
      find "$w" -maxdepth 1 -mindepth 1 -mmin +60 -exec rm -rf {} + 2>/dev/null
    else
      rm -rf "$w"/* 2>/dev/null
    fi
  done
}
clean_caches() {
  rm -rf ~/Library/Caches/go-build 2>/dev/null
  rm -rf ~/Library/Caches/Homebrew/downloads/* 2>/dev/null
  rm -rf ~/.gradle/caches 2>/dev/null
  find ~/.zcode/cli/exec -name '*.log' -mtime +2 -delete 2>/dev/null
}
offload_backups() {
  [ -d "$OFFLOAD" ] || mkdir -p "$OFFLOAD/backups"
  [ -d ~/backups ] && mv ~/backups/* "$OFFLOAD/backups/" 2>/dev/null && rmdir ~/backups 2>/dev/null
}

# --- 分级（磁盘阈值以 GB 计；swap 以 MB 计） ---
if [ "$DISK_FREE_GB" -lt 8 ] || [ "$SWAP_USED_MB" -gt 16000 ]; then
  log "T3-RED free=${DISK_FREE_GB}G swap=${SWAP_USED_MB}MB — 全清理+杀瞬态编译进程"
  clean_worktree_builds t2; clean_caches; offload_backups
  pkill -f flutter_tester 2>/dev/null && log "T3 killed flutter_tester"
  find /private/var/folders -name 'flutter_tools.*' -mtime +1 -delete 2>/dev/null
  log "T3 done → $(df -g / | tail -1 | awk '{print $4}')G"
elif [ "$DISK_FREE_GB" -lt 12 ] || [ "$SWAP_USED_MB" -gt 14000 ]; then
  log "T2 free=${DISK_FREE_GB}G swap=${SWAP_USED_MB}MB — 全 build 目录+缓存清理+备份外置"
  clean_worktree_builds t2; clean_caches; offload_backups
  log "T2 done → $(df -g / | tail -1 | awk '{print $4}')G"
elif [ "$DISK_FREE_GB" -lt 20 ] || [ "$SWAP_USED_MB" -gt 10000 ]; then
  log "T1 free=${DISK_FREE_GB}G swap=${SWAP_USED_MB}MB — 清 1h 未动 build+缓存"
  clean_worktree_builds t1; clean_caches
  log "T1 done → $(df -g / | tail -1 | awk '{print $4}')G"
fi
echo "guard-ok free=${DISK_FREE_GB}G swap=${SWAP_USED_MB}MB"

# --- PG env↔卷 hash 漂移探针（FIX-586 R-2，只读指纹化；失败不阻塞守卫主流程） ---
PG_PROBE="$(dirname "$0")/pg_env_drift_probe.sh"
if [ -f "$PG_PROBE" ]; then
  PG_PROBE_OUT="$(bash "$PG_PROBE" --quiet 2>&1)"
  PG_PROBE_RC=$?
  log "$PG_PROBE_OUT (exit=$PG_PROBE_RC)"
else
  log "pg_env_drift_probe 缺席：$PG_PROBE"
fi
