# 05 · Go 网关 R2 修复台账（Wave1 · G5）

- 修复员：G5（Go 网关切片）｜对应复审报告：[05-r2-gateway.md](05-r2-gateway.md)
- 基线：main@ca86bda8 工作树 `/Users/brsama/code/GitHub/Sparkle-sysrev/wt5`（未 commit）
- 环境复核：macOS arm64，Go 1.25.7，`CGO_ENABLED=0`；`CGO_ENABLED=0 go vet ./...` 零输出
- 验证协议：一次一个 go test、按包粒度；`SECRET_KEY=x JWT_SECRET=test-secret-0123456789abcdef`

---

## 1. 已修复项

### R2-GW-1（P1）终局持久化挂在可取消 streamCtx → 客户端收完终帧即断则丢整轮回答 — **已修**

红：DeepAudit 留下的 E2E 复现探针（基线 8 跑 7 复现 `history=[user]` + `Failed to save chat message: context canceled`；本机基线复跑同样复现）。

修（`chat_orchestrator_chatflow.go`）：
1. 新增 `detachedPersistCtx(parent)`：`context.WithTimeout(context.WithoutCancel(parent), 5*time.Second)`，与 :938 语义缓存更新同款写法；
2. **终局 assistant 落史**（原 :930）与**流中断截断保存**（原 :712）改挂 detached ctx；
3. **终局 RecordUsage 计费对账**（原 :809/:818 两分支）改挂 detached ctx；流中分段计量（RecordUsageSegment）按报告保持随流取消（活配额闸口）；
4. **报告未点名的同窗口第二丢转形态一并修复**：meta/合成 done 终帧写失败原先 `return true` 直接跳过持久化——客户端恰在 meta 与 done 之间断开时同样永久丢转。改为记 `clientGone` 标志、照常持久化、仍以 `return clientGone` 关闭连接（关闭语义不变）。

绿：E2E 探针转**硬断言**（`require.Eventually` 断言断连竞速后 history 必含 assistant，`-count=3` 稳定）。

### R2-GW-8（P1）生产拒空 Origin → 原生移动端四条 WS 链路生产全 403 — **已修**

修（按报告方案"鉴权成功后放行空 Origin，保留非空白名单校验"）：
- `websocket_factory.go` `checkOrigin`：空 Origin 直接放行（CheckOrigin 在 WsAuth 之后、升级时才执行，能到这里即已持有效 JWT/ticket；非空 Origin 仍走 `IsOriginAllowed` 白名单防浏览器跨站劫持）；
- `websocket_proxy.go` community 双链 CheckOrigin：同策略。**并删除一处死代码**：旧 localhost-Host 特判读 `r.Header.Get("Host")`，而 Go 的 Host 不在 Header map 中、恒为空——即旧实现对空 Origin 无条件拒绝，与报告"仅放行 localhost:8080"的描述不符（实际更糟）。

测试面变化（全部为 R2-GW-8 证据链）：
- **新发现基线红 #2**：`TestWebSocketProxyRejectsPerConnectionRateLimit`（拨号无 Origin → 恒 403 → `require.NoError` 失败，基线复跑证实）→ 修复后绿；
- **新发现基线红 #3**：`TestSTTHandlerAllowsMissingOriginForSameOriginClients`（断言生产放行空 Origin，与旧实现矛盾）→ 修复后绿；
- `stt_origin_test.go` GW-P2-2 回归测试按新策略改写（production_allows_empty_origin_after_wsauth / 非空白名单仍拒绝）；
- `websocket_factory_test.go` 新增 `TestCheckOrigin_EmptyOriginAllowedInProduction`。

### F5 移交（P1 收尾）saveMessage nil 守卫 + QuotaIntegration 根因修 — **已修**

- `chat_orchestrator_feedback.go`：`saveMessage` 增加 `h.chatHistory == nil` 守卫（test-only wiring 直接跳过，不再 panic）；
- `quota_integration_test.go` 按报告修法重写：删除 `os.Setenv("ENVIRONMENT","prod")` 跨用例污染源；工厂改**精确 Origin**（ts 启动后取 `ts.Listener.Addr()`）；拨号显式带 Origin 头；拨号失败 `assert→require` 中止（杜绝 nil conn panic）。基线红（nil conn panic 栈，本机复跑证实）→ 绿。

### R2-GW-4（P2）STT 双泵无 read deadline/ping → 半开连接泄漏 — **已修**

`stt_handler.go`：两侧连接 `SetReadDeadline(pongWait)` + PongHandler 刷新（pongWait 取 `WSPongWaitSeconds`，默认 90s）；新增 ping ticker（间隔 pongWait/2）：上行经 `writePython`（互斥+写死线）、下行经 `clientWriter.WriteControl`（wsSafeWriter 内部锁）；ping 失败推入 errChan + closeDone，handler 首错后即 closeDone。新增回归测试 `TestSTTHandlerReapsSilentClientViaReadDeadline`（静默客户端在 pongWait=1s 内被服务端回收）。

### R2-GW-5（P2）SignalHub 全局 sendMu 跨用户队头阻塞 — **已修（红绿双证）**

`internal/service/signal_hub.go`：删除 hub 级 `sendMu`，对齐 FileEventHub 快照模式（RLock 内快照、锁外逐 conn 写；per-conn 串行由生产注册的 wsSafeWriter 自身保证）。新增回归测试 `TestSignalHubSendDoesNotHeadOfLineBlockOtherUsers`（阻塞态慢连接不得妨碍他用户推送）。**红验**：临时还原 sendMu 后该测试 2s 超时 FAIL（2.5s 实测），恢复修复后绿。

### R2-GW-2（P2）decr_quota.lua EXPIRE 守卫恒真 — **已修（保守方案）**

`internal/db/scripts/decr_quota.lua`：守卫由恒真的 `result == current - 1` 改为 `redis.call("TTL", KEYS[1]) == -1`（仅无 TTL 的键盖一次戳），消除"活跃用户每日配额键永不过期→配额永不重置"的埋雷。`quota_test.go` 新增 TTL 语义子测试（首次扣减盖戳；人工把 TTL 钉在 1h 后再扣减，断言未被滑动回 24h 默认值）。注：该 reserve/refund/decr 族当前零生产调用者，维持保留不删（超出本轮授权，台账见报告 §4.1 选项 1 的建议）。

---

## 2. 新发现并顺手修复（复审报告未列）

| 项 | 说明 | 处置 |
|---|---|---|
| 基线红 `TestWebSocketProxyHTTPGuards`（第 4 个基线红，自初始提交即坏） | 429 断言用 `strings.Repeat("a", 4)` 作 session_id，先被 `isValidUUID` 拦成 400，重连限流分支从未被走到 | 测试改用合法 UUID（`11111111-…`）真实打通限流分支，符合测试本意；基线代理实现下复跑证实为既有红、非本次引入 |

**复审报告测试记录勘误**：报告 §5 称 handler 包"唯一红 = QuotaIntegration"；基线实况为 **4 红**（QuotaIntegration、TestWebSocketProxyRejectsPerConnectionRateLimit、TestSTTHandlerAllowsMissingOriginForSameOriginClients、TestWebSocketProxyHTTPGuards），前三者均为 R2-GW-8 的测试形态证据，第 4 个为独立测试缺陷。

## 3. 范围内已识别、未在本轮处理的（移交清单）

- **R2-GW-3（P2）** file 订阅者 recover 后无重启/无指标——未列入本波任务清单，未动；
- **R2-GW-6/7/9（P3）** 双 drain deadline、fire-and-forget 扇出无上限、密钥失败不进限流计数——P3 未列入任务清单；
- **R2-GW-1 邻接注记**：流中写帧失败（对端中途消失）路径仍不保存部分文本（return false 早退），属"流未完成"语义，报告未列为缺陷；dedup 幂等键使重连重发安全。用户消息落史（:362）仍在 streamCtx 上，窗口为流开始前的毫秒级，超出报告修法范围未动；
- **配额 Lua 族死代码**：报告建议整族删除（选项 1），本轮仅按授权执行语义修复（选项 2），删除需另行决策。

## 4. 测试记录

```
$ CGO_ENABLED=0 go vet ./...                                          → 零输出
$ export SECRET_KEY=x JWT_SECRET=test-secret-0123456789abcdef CGO_ENABLED=0
逐包 -count=1（一次一个 go test 进程）：
  ok  internal/logsafe  0.480s      ok  internal/config  0.494s
  ok  internal/db       0.561s      ok  internal/cqrs/event  0.505s
  ok  internal/agent    0.960s      ok  cmd/server  0.654s
  ok  internal/middleware  5.608s    ok  internal/service  8.392s
  ok  internal/cqrs     2.731s      ok  internal/handler  18.115s
handler 包内关键新绿：
  TestChatOrchestrator_WSFullChainE2E（含 R2-GW-1 硬断言，单跑 -count=3 稳定）
  TestChatOrchestrator_QuotaIntegration（F5 修复后绿）
  TestWebSocketProxyRejectsPerConnectionRateLimit / TestWebSocketProxyHTTPGuards（基线红转绿）
  TestSTTHandlerReapsSilentClientViaReadDeadline（R2-GW-4 新增）
  TestSignalHubSendDoesNotHeadOfLineBlockOtherUsers（service 包；红验 FAIL→修复后 PASS）
  TestQuotaService_DcrQuota/ttl_stamped_once…（db 脚本经 service 包 Lua 执行，红验未做——旧脚本恒 EXPIRE 24h，与断言 ttl<2h 矛盾，红态显然）
```

-race 仍因 CGO_ENABLED=0 铁律不可用；并发结论为静态论证 + 行为性并发测试。工作树未 commit（受冻结约束）；完整差异见 [05-r2-fixes.patch](05-r2-fixes.patch)（gen/ 无改动）。

---

*修复手法均对齐复审报告给出方案；R2-GW-1 额外覆盖终帧写失败跳过持久化的同窗口第二形态，R2-GW-8 一并修正报告未察觉的 Host 特判死代码。*
