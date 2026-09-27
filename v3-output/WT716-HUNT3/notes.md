# WT716-HUNT3 — 网关（Go）×跨层契约面专项猎缺（第一轮双轮审查·轮1）

- Agent: wt716 ｜ 分支: `agent/node-b/wt716/hunt3`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt716-hunt3`，基线 main@4756ab18）
- 日期: 2026-09-25 ｜ 主线仓库只读，未修任何代码 ｜ 台账登记 V3-FIX-426/427/428（预占 429 未动用）
- 方法: 五猎场静态走查（grep 定位+逐文件读上下文）+ `go vet ./...`（exit 0）+ 台账/既有登记避重扫描（FIX-334 三态重放、push proxy 组、BA-ROUTES、registerREST、CQRS 面均未触碰）。`go test -race` 未跑（本机未配 Go 集成环境依赖，走查口径已在逐条 notes 注明——vet 静态+单测口径复验步骤已写入各台账行 Reproduction 列）。

## 登记（3 条，全 OPEN 带证据）

### V3-FIX-426 (P2) 鉴权审计/会话/知情同意 IP 归因——跨层 XFF 口径分裂
- 链: 网关 Director 对客户端可注入的 XFF **追加**真实 IP（`backend/gateway/cmd/server/setup.go:973-979`）→ 限流侧已按 EI-09 右起解析（`backend/app/core/rate_limiting.py:50-62`，免疫）→ 但三处消费方仍取**首段**（=客户端可任意伪造段）：
  - `backend/app/core/auth_audit_service.py:21-23` `_client_ip` → `auth_audit_log.ip_address`
  - `backend/app/services/auth_session_service.py:33-39` `extract_client_metadata` → 设备会话记录 ip_address
  - `backend/app/api/v1/research_consent.py:44-48` → 知情同意 IP 存证
- 复验: `curl -X POST :8080/api/v1/auth/guest -H 'X-Forwarded-For: 8.8.8.8' -d '{}'` 后查 auth_audit_log 最新行 ip_address=8.8.8.8；`grep 'split(",")\[0\]' backend/app` 恰得全部三处。
- 影响: 爆破取证、新设备风控基线、合规存证三类 IP 消费面可被未登录方投毒。修向: 三处统一改用 `get_real_ip` 同款右起第 N 段（与 EI-09 单一出口收拢）。

### V3-FIX-427 (P2) ChatHistoryPersister 优雅关停批量丢消息
- 链: `backend/gateway/cmd/server/main.go:89` bgCtx（注释明示关停 cancel）→ `:142` bgCancel() 先于 HTTP drain → `:103` Run(bgCtx) → `backend/gateway/internal/service/chat_history_persister.go:167-174` ctx.Done 分支以已取消 ctx 调 flushWithRetry：
  - 路径①: `:278-279` batch 已换出为局部变量；首试 `pool.Acquire(取消ctx)` 必败；attempt≥1 backoff select 命中 ctx.Done → `:290 return ctx.Err()`——批 ≤100 条**未写库未 requeue 直接丢弃**（与 `:178-179/:312-315` 注释「failures are logged and the batch is re-queued」矛盾）。
  - 路径②: 重试耗尽走 `:315` requeueMessages(同一取消 ctx) → `:416` `p.rdb.LPush(ctx,...)` 错误被丢弃。
  - `main.go:142` 必先于 `:105` defer Stop()，stopCh 分支无幸免。
- 影响: 每次部署/重启丢 5s flush 窗口内在途批；该队列系 RB-06 引擎漏写兜底（损失=引擎同样未落库的轮次），故 P2 非 P1（已在台账行诚实标注）。
- 复验: 单测口径（修前应双红）: 预填批 → cancel ctx → Run 返回 → 断言 `queue:persist:history` 长度不变且 DB 无行。修向: 最终 flush+requeue 挂 `context.WithoutCancel`+短超时（chatflow.go detachedPersistCtx 先例），LPush 逐条查错。

### V3-FIX-428 (P3) 反向代理 X-Forwarded-Host 恒为内网主机
- 链: `setup.go:970` `req.Host = targetURL.Host` 先覆写 → `:984-985` XFH 空则读 req.Host → XFH 恒写 `sparkle_api:8000`（`:972` 注释「sees real client info」对该头不成立）；客户端自带 XFH 原样透传（反向可伪造）。消费方 `backend/app/api/v1/vocabulary.py:35-54` `_external_base_url` fallback 链在 DICTIONARY_PACKAGE_BASE_URL/GATEWAY_INTERNAL_URL 未设时以 XFH 拼 `:258` 下载绝对 URL → `http://sparkle_api:8000/...` 坏链+内网拓扑外泄（与已修 301↔307 内网泄漏同类、另一入口）。
- 复验: unset 两 env 后过网关取词典下载链接观察 host；Director 顺序可 go 单测钉。

## 未成立/存疑清单（不占台账号）

1. **client-telemetry 公开路由**（无 auth POST /events、/events/batch）: 非裸奔——api 组级 apiRateLimit(15/30)+MaxBodySize+引擎侧 `get_optional_current_user`（JWT 源）三重覆盖；X-User-ID 伪造不成立（Python 零消费，见 7）。
2. **NoRoute 代理缺 TimeoutMiddleware**: 已反驳——`setup.go:860` 全局 `r.Use(NetworkResilienceMiddleware)`（gin NoRoute 跑全局链）给 NoRoute 代理面 30s 总闸；transport 虽无 ResponseHeaderTimeout 但有该兜底。
3. **Python StreamChat 硬取消路径**（grpc.aio GeneratorExit 在 yield 点注入 → `agent_grpc_service.py:534 await db_session.commit()` 被跳过；仅 `:507 context.cancelled()` 轮询到的温和取消才 commit）: 疑似网关 GW-P1-2 取消流后引擎不落部分结果 → GetRequestResult 无记录 → 重试全额重算。**证据不足以裁决**（需先证 orchestrator 幂等账本的写入时机在 commit 内还是流中），列存疑待专项，不登记。
4. **AB assign 同步在链调用**（`proxy_routes.go:1335` 每显式代理请求同步 POST 引擎 /experiments/{id}/assign，3s 预算；chat POST 热路径双往返）: 引擎侧自动补建实验（`experiments.py:524-540`），功能自洽，属设计权衡非缺陷；仅记观察。
5. **Persister 计数器竞态**（totalPersisted/totalFailed/lastFlushTime 在 GetStats 无锁读）: 生产无 GetStats 调用方（仅 error_book/dlq 同名函数），不成立为缺陷；卫生级注记。
6. **Persister Stop() 双 close panic**: 唯一调用方 `main.go:105` defer 单次，不成立。
7. **X-User-ID 死面**: 网关两处注入（proxy_routes.go:1359、galaxy_handler.go:983）+代理不剥客户端自带头，但 Python 全仓零消费（identity 走 Bearer JWT）——现为无害死面+未来漂移陷阱（若后续端点误信即成仿冒洞）；并入 428 的代理头卫生修向，不单列。
8. **WS 生命周期面**（chat_orchestrator GW-P1-2 读泵取消、ws_registry 原子双删、signal_hub R2-GW-5 快照写、ws_proxy GW-P3-4/5+wt275 加固、ticket GETDEL 原子核销 ws_auth.go:20,128）: 多轮加固后未发现新增泄漏/重复投递窗口。
9. **契约快照漂移源**: 三快照生成链之外的手写面=①BA-ROUTES 守卫「method-agnostic ledger matching」（守卫头注自述限制: 已 ledger 路径新增 METHOD 不再触发）②TimeoutMiddleware SSE 豁免清单纯手工审计（isLongRunningRoute）——今日实测引擎 4 处 SSE 面（chat/galaxy/simulation×2/background-tasks）全部在列无漂移；两处均为已知文档化限制，结构性风险记此备查。
10. `go vet ./...` 零告警（backend/gateway 全模块）。

## 产出
- 台账: `v3/06_agent_fleet/DYNAMIC_ISSUES.md` +V3-FIX-426/427/428（verify 零 FAIL: 301 行 V3-FIX、8 裸管形态、无重号）
- 本 notes: `v3-output/WT716-HUNT3/notes.md`
