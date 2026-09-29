# ENV-OUTAGE：Docker Desktop 崩溃（数据平面中断窗口）
- 崩溃时间：~14:05 +0800（2026-09-29）；协调方通报：swap 95% 高压致 Docker Desktop 崩溃，非本卡栈配置/代码问题
- 本卡实测错误面（q01_r1_part1_console.log + logs/gateway.log + logs/backend_api.log）：
  - gateway: `dial tcp 127.0.0.1:6379: connect: connection refused`（rate limiter Redis 失败回退 local）；
    POST /api/v1/auth/guest → 500（11:43:41 - 11:44:18 多次）——访客进入 UI 点击无法落-dashboard 的直接原因
  - backend: `Error 61 connecting to 127.0.0.1:6379. Connection refused.`（summarization_worker 批处理）
  - 恢复期 docker API 500（containers/json 不可用）；df 实测磁盘 7.1Gi→2.1Gi（本卡构建产物 ~1.5G 已清理 + 并行因素），
    清理 go-build/Google caches 后回 5.1Gi
- 恢复动作：Docker Desktop 重启（server 29.8.0）→ cosmos 仓 compose `up -d sparkle_db redis minio`
  （FIX-557 属主路径；sparkle_db Exited(255) 重新 Started）→ 三容器 healthy、5432/6379/9000 可达、pg_isready OK
- 判定影响：恢复前失败轮次（r1 part1 多次 identity_entry/wizard_open FAIL）标 ENV-OUTAGE，不计产品失败；
  验收三连跑以恢复后轮次为准
