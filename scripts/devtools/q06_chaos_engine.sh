#!/bin/bash
# wt406 chaos 引擎重启（:50062，上游三 base_url → mock :9099，redis db2）
# 用法: bash scripts/devtools/q06_chaos_engine.sh start|stop|restore
set -e
WT=/Users/brsama/code/GitHub/Sparkle-sysrev/wt406-q06-perf
PY=/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python
ENVF=$WT/backend/.env
CHAOS_MARK="# wt406 chaos overrides"

case "${1:-}" in
  start)
    # 追加 chaos 覆盖（幂等：先删旧 chaos 段）
    perl -ni -e "print unless /\\Q$CHAOS_MARK\\E/../EOF_CHAOS/" "$ENVF" || true
    cat >> "$ENVF" <<EOF
$CHAOS_MARK
GRPC_PORT=50062
REDIS_URL=redis://:sparkle_dev_redis_2026@127.0.0.1:6379/2
DASHSCOPE_BASE_URL_COMPATIBLE=http://127.0.0.1:9099/compatible-mode/v1
DEEPSEEK_BASE_URL=http://127.0.0.1:9099/compatible-mode/v1
ZHIPU_BASE_URL=http://127.0.0.1:9099/api/paas/v4
# EOF_CHAOS
EOF
    cd "$WT/backend" && nohup "$PY" grpc_server.py > logs/wt406_chaos_grpc_stdout.log 2>&1 &
    echo "chaos engine PID:$!"
    sleep 16
    lsof -iTCP:50062 -sTCP:LISTEN | tail -1
    ;;
  stop)
    # 只杀 worktree 自己的引擎（:50061/:50062），绝不 pkill 全局 grpc_server.py
    # （常驻 :50051 是全舰队共享实例）
    for port in 50061 50062; do
      pids=$(lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null || true)
      [ -n "$pids" ] && kill $pids 2>/dev/null || true
    done
    # 连带杀掉 redis db1 的 billing worker（命令行含 billing_worker 且 cwd=worktree）
    pids=$(pgrep -f "app.services.billing_worker" 2>/dev/null || true)
    for p in $pids; do
      cwd=$(lsof -p $p 2>/dev/null | awk '$4=="cwd"{print $NF}')
      case "$cwd" in
        "$WT"*) kill $p 2>/dev/null || true ;;
      esac
    done
    sleep 3
    echo "worktree engines stopped (resident :50051 untouched)"
    ;;
  restore)
    perl -ni -e "print unless /\\Q$CHAOS_MARK\\E/../EOF_CHAOS/" "$ENVF" || true
    grep -q "GRPC_PORT=50061" "$ENVF" || printf '\n# wt406 Q-06 bench overrides (local only, never commit)\nGRPC_PORT=50061\nREDIS_URL=redis://:sparkle_dev_redis_2026@127.0.0.1:6379/1\n' >> "$ENVF"
    echo "env restored to bench (:50061, real providers, redis db1)"
    ;;
  *)
    echo "usage: $0 start|stop|restore"
    ;;
esac
