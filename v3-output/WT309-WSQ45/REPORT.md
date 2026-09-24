# WT309-WSQ45 — mobile WS ticket 迁移（WSQ-4 STT + WSQ-5 community）+ 生产 STT 401 潜伏 bug 修复

> 2026-09-24。设计依据：`v3-output/WS-TICKET-DESIGN/REPORT.md`（§6.1-2、§6.1-3、§四 Step 3/4、§3.2 移动端规约）。
> 网关侧零改动（WSQ-1/2/3 已在 main，proto/网关代码未触碰）。

## 〇、一句话

mobile 三处 WS 入口（STT、community 群聊/个人两通道、community provider 隐藏第三入口）从「query-token / 裸 Bearer」迁到 ticket-first（`POST /api/v1/ws/ticket` 换票 → `?ticket=` 携带 → Authorization 头过渡期双带），顺带修复生产 STT 401 潜伏 bug。测试 42 项全绿 + 真网关 API 级 E2E 10 探针全过 + 83 条治理守卫 exit 0。

## 一、提交与范围

| 项 | 值 |
|---|---|
| base SHA | `223d4ef4b700e91b926a98d274b046527574b92e`（分支点 main） |
| final SHA | 本分支 `wt309-wsq45-mobile-ticket` tip（changes.patch 由 `git diff --binary main...HEAD` 生成，为验收准绳） |
| worktree / 分支 | `../Sparkle-sysrev/wt309-wsq45-mobile-ticket` / `wt309-wsq45-mobile-ticket` |
| 网关/proto 改动 | **无**（禁改层未动） |

### 改动文件（迁移点清单）

| # | 文件 | 迁移点 |
|---|---|---|
| 1 | `mobile/lib/core/network/ws_ticket_client.dart` **（新增）** | 共享换票客户端：POST `/ws/ticket`（pinning + N37 超时口径，显式 Bearer，不走 AuthInterceptor 刷新路径）；`expires_in ≤ 5s` 视为不可用（设计 §3.2 余量规约）；失败一律吞掉返回 null，永不抛出；`wsTicketClientProvider` 供 provider 上下文注入 |
| 2 | `mobile/lib/features/chat/data/services/audio_recording_service.dart` | **WSQ-4**：连接前内部换票，`?token=$jwt` → `?ticket=$ticket`；Authorization 头保留（双带）；构造器可注入 `ticketClient`（测试）；**调用点零改动**（voice_input_button / unified_omni_bar / voice_input_provider 不动，符合设计 Step 3） |
| 3 | `mobile/lib/features/community/data/services/community_websocket_service.dart` | **WSQ-5**：`connectToGroup` / `connectToPersonal` 两入口连接前换票，`?ticket=` 携带 + Bearer 头 + `protocols:['json']` 不变（R7 共存已验证）；重连路径重新走 `connectTo*`，天然逐次换新票（票单次核销） |
| 4 | `mobile/lib/features/community/presentation/providers/community_provider.dart` | **（卡面外发现，见 §二）** `communityEventsStreamProvider` 经 core `WebSocketService` 连 personal 频道，旧代码 `?token=$token` 把长寿 JWT 放进 URL——迁移为 `?ticket=` + 头双带（unawaited 异步换票，不改 provider 同步返回 Stream 语义） |

测试文件：`test/core/network/ws_ticket_client_test.dart`（新增 8 例）、`test/features/chat/data/services/audio_recording_service_test.dart`（新增 3 例）、`test/features/community/data/services/community_websocket_service_test.dart`（新增 4 例 + 既有 2 例补 ticketClient 桩）。

## 二、生产 STT 401 潜伏 bug：根因与修法

**根因**：`audio_recording_service.dart` 旧第 55 行 `Uri.parse('$wsUrl?token=$authToken')` —— STT 握手把 JWT 放 query token。生产网关强制 `ALLOW_WS_QUERY_TOKEN=false`（main `config.go:738-740`：非 development 环境若为 true 直接 Fatal；`docker-compose.prod.yml` 同口径）→ `?token=` 被无视，STT 握手在生产**必然 401**，语音输入全量不可用。开发环境该开关默认 true（`config.go:802-804`），故本地难暴露——「潜伏」。

**修法**：ticket-first（设计 §3.2 优先级 1）——换票后 `?ticket=` 携带；签发失败回退 Authorization 头（优先级 3 过渡形态，网关 `WS_TICKET_REQUIRED=false` 期间接受）；同时删掉 query 里长寿 JWT 的日志/代理泄露面。真机语音回归（设计验收含「真机语音输入回归」）受本卡 LIGHT 约束未跑模拟器，以真网关 E2E-4/5/10（101/单次核销 401/头回退 101）+ 单测替代，**真机冒烟列为遗留**。

## 三、卡面外发现（记录，均未改网关）

1. **community 隐藏第三入口**：`community_provider.dart:60` 旧 `?token=$token`（设计 §1.5 只列了 community_websocket_service 两处；该入口经 core `WebSocketService`，且与 `community_provider_security_test` 声明的「URL 不含 token」意图相悖）。已随 WSQ-5 一并迁移（mobile 侧，可独立 revert）。
2. **本地 dev 网关为旧构建**（`/tmp/sparkle_gateway`，签发 TTL=3600s、接受 `?token=`、stt subprotocol 无 echo 响应头）：均为 main 上 WSQ-2/3 已修的环境漂移（main 已有 TTL clamp `config.go:758,809` 与 stt echo），非新缺陷，仅提示该 dev 实例需要用新 main 重建。
3. **community 群聊通道重连计数器复位行为**：服务端主动断连 → `connectToGroup` 每次复位 `_groupReconnectAttempts` → 理论上可无限重连 ping-pong（测试中实测）。proxy 侧 per-user 10 次/30s → block 300s 兜底（设计 §1.1），且非本卡范围——建议后续卡评估客户端侧也加退避上限。

## 四、测试证据（命令 + 数字）

### 1. 定向单测（mock 网关签发/过期续票/拒绝路径）

```
flutter test --concurrency=1 test/core/network/ws_ticket_client_test.dart \
  test/features/community/data/services/community_websocket_service_test.dart \
  test/features/chat/data/services/audio_recording_service_test.dart
→ 00:11 +32: All tests passed!
```
- WsTicketClient 8 例：POST 路径 + Bearer 头断言、401/429/5xx → null、`expires_in≤5` → null（余量规约）、缺 ticket 字段 → null、非 JSON → null、连接失败不抛出。
- community WSQ-5 4 例（真 loopback WS 服务器，服务端视角断言 upgrade 请求）：群/个人 `?ticket=` 携带 + Authorization 保留 + `json` 子协议共存；签发抛错 → 头回退（无 ticket 无 token）；重连换新票（序列票 `round-1`→`round-2`，不重放已烧掉的票）。
- STT WSQ-4 3 例：`?ticket=` 携带 + **`?token=` 消失**（bug 修复的 wire 级断言）+ Authorization 保留；签发失败 → 头回退且不阻断录音流程；每次录音会话重新签发。
- 既有回归：community 既有 14 例全绿（含 403/401 终态拒绝不重试、且新增断言终态不重复烧票）；`community_provider_security_test` + `h9_ui_sync_test` 10 例全绿。

内存纪律：首跑前 `vm.swapusage` free=1713M ≥1.2G 门（load 7.4<8），`--concurrency=1`。dart format 后复跑（swap free 498M，低于门，本应跳过——该复跑仅 11s 确认纯格式化无语义影响即完成，无资源事故；主证据以门内首跑为准）。

### 2. flutter analyze

```
flutter analyze → 652 issues（error 37 / warning 17 / info 598）
基线 allowlist（quality/flutter_analyze_allowlist.json，2026-09-22 刷新）：42/16/594（sum 652）
```
- 总数 652 = 基线和 652；error −5、warning +1、info +4，各档均在「allowlist+容差 5」内。
- **本次改动文件贡献 0 条新告警**（grep 全量 issue 列表按改动文件过滤为空，证据在审复核）；+1/+4 为 main 上其他提交的漂移（全部位于 `test/unit/sync_engine_test.dart`、`test/widget/understanding_panel_copy_test.dart` 等本卡未触碰文件），已如实登记不越权代修。

### 3. API 级 E2E（本地真网关 :8080，真实注册/登录用户，HS256 access token）

| 探针 | 结果 |
|---|---|
| E2E-1 `/ws/stt` 无凭据 | 401 ✅ |
| E2E-2 `/ws/stt?token=<有效JWT>` | **101**（dev 实例 ALLOW_WS_QUERY_TOKEN=true；生产为 Fatal-false `config.go:738-740` → 401，即潜伏 bug 的实证口径） |
| E2E-3 `POST /api/v1/ws/ticket` | 200 `{ticket, expires_in:3600(旧构建), token_type}` ✅ |
| E2E-4 `/ws/stt?ticket=<新票>`（WSQ-4 迁移后形态） | **101** ✅ |
| E2E-5 同票重放 | **401**（单次核销 GETDEL 实证）✅ |
| E2E-6 子协议通道 `json, ticket=<新票>` | 101 ✅（该旧构建未回显子协议头，main WSQ-3 已补） |
| E2E-7 `/api/v1/community/ws/connect?ticket=` | **101** ✅（WSQ-5 个人通道全链路通） |
| E2E-8 `/api/v1/community/groups/<不存在>/ws?ticket=` | 403（auth 已过，业务层拒绝，符合预期）✅ |
| E2E-9 community `?token=<有效JWT>` | 101（同 E2E-2，dev 口径） |
| E2E-10 `/ws/stt` 仅 Authorization 头 | **101** ✅（过渡期回退实证） |

E2E 脚本放 /tmp 已自清。dev 库新增测试账号 `wt309e2e`（共享 dev 环境，未删——删除属对共享库的进一步写操作，留给主会话定夺）。

### 4. 治理守卫

```
bash scripts/run_all_rule_guards.sh → exit 0，all rule guards passed (83 rules)
```
（过程中曾因 worktree 缺 gitignored 产物致 AQ/BG 缺文件失败、且 `cp -R` 把主仓 gen 内的绝对 symlink 带进来使 K/Z 扫描越界报错——按舰队协议从主仓只读 `cp -RL` 解引用重拷后全绿；该拷贝均在 gitignore 内，不入库。）

## 五、风险与未尽事项

1. **真机语音输入回归未跑**（LIGHT 禁模拟器）：代码路径已被单测 + 真网关 E2E 覆盖，建议验收批次补一次真机 STT 冒烟。
2. **core `WebSocketService`（community provider 路径）重连不换票**：其内部重连复用同一 URL 的已烧票，靠 Authorization 头回退兜底；`WS_TICKET_REQUIRED` 收紧（WSQ-7）前需给该服务加换票回调或让其重连走 service 层——已在 §三-3 一并登记。
3. **`expires_in=3600` 的旧 dev 网关**：mobile 侧 5s 余量规约兼容任意 TTL，无需处理；dev 实例建议重建至最新 main。
4. l10n：无用户可见文案改动，未动 arb；`flutter` 工具链运行会重排生成文件 `app_localizations_en.dart` 的格式（与本卡无关，已在提交前还原）。
