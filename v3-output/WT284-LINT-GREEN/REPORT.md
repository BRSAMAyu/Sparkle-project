# WT284-lint-green 修复报告 — D 线 CI golangci-lint 门清绿

日期：2026-09-24 ｜ 卡号：wt284-lint-green ｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt284-lint-green`（分支同名，本地 commit 未 push）

## 一、结论

- **34/34 项存量 lint 发现全部修复，0 豁免**（CI 日志 36 行 error = 34 项发现 + SA5011 related-information 行 + "issues found" 汇总行）
- 本地 `golangci-lint run ./...`（v1.64.8，与 CI 同配置 `.golangci.yml`）**零输出、exit=0**
- 治理守卫 `scripts/run_all_rule_guards.sh` **exit=0，96 PASS / 0 FAIL**

## 二、36 行 CI 错误 → 修复映射表

### gofmt（4）
| # | CI 位置 | 修复 |
|---|---|---|
| 1 | internal/config/config.go:80 | gofmt -w（DF-2 注释块插入导致结构体对齐组分裂，52 行纯空白重排；`git diff -w` 为空可证） |
| 2 | internal/handler/proxy_routes_leaderboard_self_anchor_test.go:13 | gofmt -w |
| 3 | internal/handler/ws_e2e_roundtrip_test.go:76 | gofmt -w（含 if-return 重排后重新格式化） |
| 4 | internal/service/chat_history_persister_sql_test.go:19 | gofmt -w |

### revive package-comments（8）
| # | CI 位置 | 修复 |
|---|---|---|
| 5 | internal/cqrs/event/types.go:7 | 删除注释块与 `package` 语句间空行 |
| 6 | internal/cqrs/outbox/publisher.go:7 | 同上 |
| 7 | internal/cqrs/outbox/repository.go:7 | 同上 |
| 8 | internal/cqrs/projection/handlers.go:16 | 同上 |
| 9 | internal/cqrs/projection/manager.go:7 | 同上 |
| 10 | internal/cqrs/saga.go:8 | 同上 |
| 11 | internal/cqrs/worker/base.go:7 | 同上 |
| 12 | internal/cqrs/worker/dlq.go:7 | 同上 |

### bodyclose（9 处发现，实改 12 处）
| # | CI 位置 | 修复 |
|---|---|---|
| 13 | internal/handler/chat_orchestrator_disconnect_test.go:109 | `_, ` → 捕获 `wsResp` + `defer wsResp.Body.Close()` |
| 14 | internal/handler/file_events_test.go:40 | 同上 |
| 15 | internal/handler/stt_handler_test.go:149 | 同上；**同文件 63/107 两处同型裸调用一并补齐**（同型预防，非 CI 报点） |
| 16 | internal/handler/websocket_proxy_dedup_test.go:61 | 同上 |
| 17 | internal/handler/websocket_proxy_test.go:162 | 已捕获 resp 未关 → `require.NotNil` 后补 `defer resp.Body.Close()` |
| 18 | internal/handler/websocket_proxy_test.go:190 | 同上 |
| 19 | internal/handler/websocket_proxy_test.go:226 | 同上 |
| 20 | internal/handler/ws_shutdown_drain_test.go:49 | helper 内 `t.Cleanup(func(){ _ = wsResp.Body.Close() })` |
| 21 | internal/service/file_event_hub_test.go:212 | 循环 Dial 捕获 `wsResp` + `defer` 关闭 |

### noctx（5）
| # | CI 位置 | 修复 |
|---|---|---|
| 22 | internal/handler/galaxy_handler_graph_shape_test.go:280 | `http.Get` → `http.NewRequestWithContext(context.Background(),…)` + `DefaultClient.Do` |
| 23 | internal/handler/galaxy_handler_shape_batch2_test.go:399 | 同上 |
| 24 | internal/handler/galaxy_handler_user_status_test.go:250 | 同上 |
| 25 | internal/handler/proxy_routes_test.go:466 | 同上（补 `"context"` import） |
| 26 | internal/handler/galaxy_handler_test.go:296 | `http.NewRequest` → `http.NewRequestWithContext(context.Background(),…)` |

### context-as-argument（2，含调用点同步）
| # | CI 位置 | 修复 |
|---|---|---|
| 27 | internal/cqrs/worker/base.go:35 | `LogRunnerStopped(log, ctx, name, err)` → `(ctx, log, name, err)`；**11 个调用点同步**：cmd/server/setup.go ×7、worker/base_test.go ×4 |
| 28 | internal/handler/galaxy_handler_test.go:116 | `(s *capturingGalaxyServer).record(method, ctx)` → `(ctx, method)`；文件内全部调用点同步 |

### errcheck（2）
| # | CI 位置 | 修复 |
|---|---|---|
| 29 | cmd/server/main.go:100 | `go chatPersister.Run(bgCtx)` → goroutine 内 `cqrsWorker.LogRunnerStopped(bgCtx, logger.Log, "Chat history persister", …)`。理由：Run 优雅停机时返回 `ctx.Err()`（context.Canceled），直接打 ERROR 会制造停机噪声；复用既有 PROD-LOG #8 分级工具（停机→INFO，活进程失败→ERROR），与 setup.go 其余 runner 同构 |
| 30 | internal/service/chat_history_persister.go:374 | `sp.Rollback(ctx)` → `if rerr := sp.Rollback(ctx); rerr != nil { log… }`（失败路径上记录回滚错误） |

### errorlint（2）
| # | CI 位置 | 修复 |
|---|---|---|
| 31 | internal/service/chat_history.go:878 | `err != redis.Nil` → `!errors.Is(err, redis.Nil)` |
| 32 | internal/service/chat_history_persister.go:201 | `err == redis.Nil` → `errors.Is(err, redis.Nil)`（补 `"errors"` import） |

### revive if-return（1）+ staticcheck SA5011（1）+ CI 日志非发现行（2）
| # | CI 位置 | 修复 |
|---|---|---|
| 33 | internal/handler/ws_e2e_roundtrip_test.go:75 | 末段 `if err := send(…); err != nil { return err }` + `return nil` 合并为 `return send(…)` |
| 34 | internal/handler/ws_e2e_roundtrip_test.go:251 | `require.NotNil` + 尾部 `if resp != nil`（SA5011 触发源）改为前置 nil-guard `if resp == nil { t.Fatal(…) }`，后续解引用与 `_ = resp.Body.Close()` 不变 |
| — | :252（related information） | 同一 SA5011 发现的伴随行，非独立问题，随 #34 消除 |
| — | "issues found" 汇总行 | CI 日志汇总行，非发现 |

## 三、未修豁免

**无**。34 项发现全部以代码修复清零，未使用任何 `//nolint` 或配置豁免。

超出 CI 报点的最小增量（均同型预防、零行为变更）：stt_handler_test.go 63/107 两处 bodyclose 同型补齐；config.go 纯 gofmt 空白重排 52 行。

## 四、本地复验证据

| 检查 | 命令 | 结果 |
|---|---|---|
| Lint | `CGO_ENABLED=0 golangci-lint run ./...`（v1.64.8，CI 同配置） | 零输出，**exit=0** |
| Build | `CGO_ENABLED=0 go build ./...` | 通过 |
| Vet | `CGO_ENABLED=0 go vet ./...` | 通过 |
| Test | `go test ./cmd/server ./internal/config ./internal/cqrs/... ./internal/handler ./internal/service` | 全部 ok（handler 31.1s / service 12.6s / worker 5.9s / cmd 2.9s）。`internal/config` 裸跑失败为**环境缺 JWT_SECRET**（非本卡改动；gofmt 前后 `diff -w` 为空），带 `JWT_SECRET` 复跑 ok |
| 守卫 | `bash scripts/run_all_rule_guards.sh; echo exit=$?` | **exit=0**（96 PASS / 0 FAIL，含 AX 路由守卫 PASS-DIFF） |

注：CI 步骤从 run 35950036101 的 `Go Lint (golangci-lint)` 取全量清单；本地首跑复现 36 行与 CI 完全一致（仅 config.go 报点行号 80/82 差一，同一发现），修复后清零。

### 环境性备注（不影响 CI 判定）
worktree 缺 gitignored 生成产物：已 `buf generate`（Go）+ 脚本生成 Python stubs；Dart/Python 侧产物与主仓 proto 逐字节一致（`diff -rq proto` 仅 .DS_Store 差异），故从主仓只读复制齐平。复制带入的 3 个指向主仓绝对路径的符号链接已物化为真实副本（曾致 K/Z 守卫扫描越界，物化后 exit=0）。产物均 gitignored、随 worktree 生命周期回收。

## 五、CI 复跑判据（主会话）

- 本卡分支 commit 已就绪、lint 本地清零 → 主会话按合入管线（备份→apply→定向测试→commit→push）合入后，ghcr 镜像发布门（Code Quality & Linting → Go Lint）应转绿。
- 若 CI 复跑仍红：核对 CI golangci-lint 版本是否仍为解析此 `.golangci.yml` 的 v1 系列（本地 v1.64.8 已对齐）；本卡改动只涉 `backend/gateway/**`，不触 proto/移动端。
- 判定标准：`Go Lint (golangci-lint)` 步骤 exit 0，错误行数 0。

## 六、资源与纪律

- 资源峰值：本卡为 LIGHT（无模拟器/Gradle/浏览器）；收工时 swap free 690M / load 4.56（远低于熔断线）；磁盘 `/` 剩 9.6G（>6G 阈值）。
- Go 全程 `CGO_ENABLED=1` 未使用——所有 go 命令均 `CGO_ENABLED=0`。
- 未 push、未动 main、未 stash/reset/clean；主仓只读（仅读取 gen 产物与 `gh run view`）。
- /tmp 产物已清：`/tmp/wt284-guards.log`、`/tmp/wt284-guards2.log`。
- 交付物：本 worktree 改动（29 文件 +144/-118）+ `v3-output/WT284-LINT-GREEN/REPORT.md`（本文件）+ `v3-output/WT284-LINT-GREEN/changes.patch`，均已本地 commit（未 push）。
