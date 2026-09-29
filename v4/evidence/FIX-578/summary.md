# FIX-578 summary — celery env URL DNS 悬空收口（P2）

**结论**：V3-FIX-578 缺陷成立并已修。FIX-563 容器名分化后，`sparkle_redis:6379`/`sparkle_tempo:4317` 系旧容器名当 DNS 用（服务键实为 `redis`/`tempo`），别名集实证不含旧名 → celery 全路径（make celery-up、compose celery、e2e smoke、acceptance）redis/OTEL 连接必败；`sparkle_db:5432` 系真服务键一直可解析（F563 豁免对它碰巧成立，对其余两名的豁免系错误前设）。

**修法**：统一指向最稳面——compose 服务键。可执行消费（两 compose + Makefile + 两脚本 + 五 env 模板）`sparkle_redis→redis`、`sparkle_tempo→tempo`；`sparkle_db` 零触碰；settings.py/gateway config.go 本地桥 lockstep（映射集增 `redis`，存量兼容）；活文档三件同扫（QUICK_START_CELERY/CELERY_DEPLOYMENT_GUIDE/11_Docker）；F577R1-C2 三处弃用指引补 caveat（替代路径已可用）。

**验证**：compose config 六场景 exit 0；`make -n celery-up` exit 0；bash -n/py_compile/gofmt 零输出；backend 单测 24 passed 2 skipped；o05 14 passed；supervisor 6 passed + 1 failed（daemon 环境态 base 同败——main 复测同败归因 + diff 零触碰）；gateway `go test ./internal/config/` ok。可执行消费面旧名 grep 残留 0。

**移交**：遗留四项登记（prod db 服务键分叉、k8s 陈置嫌疑、start_celery 体内史录、standalone OTEL）；真实起栈连通性验证建议随下一次授权窗口补。台账 V3-FIX-578 OPEN→FIXED@<分支头 sha>。

证据五件套：run_manifest / verification（含 URL↔alias 对照表）/ grep_exemptions / limitations / summary。
