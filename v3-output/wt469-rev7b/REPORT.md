# wt469 独立审查报告 — 审查轮 7B

- 审查人：wt469（未参与 wt444..wt466 任一实现会话）
- 审查对象：`b5a59b1b..310d6b22` 集成窗（wt444/wt446/wt448/wt450/wt452/wt454/wt456b/wt458/wt460/wt462/wt464/wt466）中 **Go 网关 + Flutter mobile** 改动，base `310d6b22`
- 范围 diff：15 文件，+608/−19（`git diff --stat b5a59b1b..310d6b22 -- backend/gateway mobile`）
- 方法：逐对象读 diff+现实现 → 动手证伪（Go build/vet/fmt/test、flutter test 66 例、gen-l10n、arb 键计数、3 个临时 Go 探针），探针红/实锤才算 finding。探针文件未提交，证据已摘录本文。

## 总 verdict

**ACCEPT（本窗改动可保留），附 2 个新登记缺陷（V3-FIX-168/169，均经探针实锤）+ V3-FIX-160 证据增补。**

本窗两个主修（FIX-155 网关/mobile 面、FIX-145 双层 404）在各自声明范围内成立；测试为净增强，无弱化。但 FIX-155 的网关缓存退出存在**结构盲区**（探针 A：引擎侧检测的截断轮，部分文本仍被写入语义缓存），且更深的既有缺陷是**网关语义缓存查询面整体死亡**（探针 B/C：任何轮次都不会命中缓存）——它使 FIX-155 的缓存退出守卫当前为空转，也使该守卫的既有验证不足以支撑"截断文本不得被缓存重投递"这一不变量。

---

## 逐对象 verdict

### 1. `backend/gateway/internal/handler/chat_orchestrator_chatflow.go`（FIX-155 网关面，+36）

**verdict：有条件成立——声明的"EOF 无 finish_reason"面实现正确；但存在盲区（→ V3-FIX-168）。**

已验证的正确面：
- `possiblyTruncated := !sawUpstreamFinishReason`（:988）：健康轮（含 Aurora runtime 轮，`orchestrator.py:1355-1397` 终帧带 `finish_reason=STOP`）不会误标截断，无误报回归。
- 截断轮 `saveExtra["truncated"]=true`（:1018-1020）与 R2-GW-1 recv-error 路径（:755-758）键对齐一致。
- 缓存写入跳过（:1024-1033）仅包住 `SetExact` goroutine，持久化路径不受影响；synthetic STOP done（:961-978）保留，客户端不会挂起——与台账"契约锁"声明一致。
- 逐分支排除其他绕过：recv-error 路径提前 return 不写缓存；quota 中断路径提前 return；clientGone 路径 fullText 已完整，写缓存无害。**唯一缓存写入点就是正常收尾路径，绕过即 V3-FIX-168 所述引擎侧检测形态。**

**盲区（探针实锤）**：wt466 引擎哨兵落地后，上游截断的主导形态已从"EOF 无 finish_reason"变为"引擎检测后下发 error 帧（finish_reason=ERROR）+ 终帧（full_text=部分文本、finish_reason=STOP、metadata.generation_stream_truncated=true）"（`standard_workflow.py:2084-2095`、`response_builder.py:994-999`）。网关 :794 只看 `FinishReason != NULL` → ERROR/STOP 都置 `sawUpstreamFinishReason=true` → `possiblyTruncated=false` → **部分文本照常进缓存、历史行不带任何截断标注**。网关对 `generation_stream_truncated` metadata 零消费（`grep -rn generation_stream_truncated backend/gateway` = 0 命中）。详见 Findings。

### 2. `backend/gateway/internal/handler/proxy_routes.go` + `proxy_routes_copy_to_library_test.go`（FIX-145 网关面）

**verdict：成立。**
- 引擎侧路由在案：`backend/app/api/v1/community.py:2572` POST `/groups/{group_id}/files/{file_id}/copy-to-library`（authed）；网关补挂 `proxy_routes.go:664` 同 authed 组、同 proxy 链，路径形状一致。
- 测试双钉：真 upstream 形制（404→200+路径不变）+ 方法面注册锁（POST 存在、GET/PUT/PATCH/DELETE 缺席）。`go test ./...` 含此二测全绿。

### 3. `mobile/lib/features/chat/presentation/providers/chat_provider.dart`（FIX-155 mobile 面）

**verdict：成立。**
- 无终态流关闭 → `finalizeRun(phase: failed, errorCode: STREAM_INTERRUPTED, isRetryable: true)`（:2245-2254）；`finalizeRun` 的既有 failed 语义（:1259-1266）只保留结构化内容，裸部分文本不落消息，且 `streamingContent: ''`（:1341）清掉在流气泡——用户见错误态而非半截答案，与声明一致。
- 误触发面排除：用户主动停止走 `cancelActiveRun`（:332-351）→ `_streamGeneration++` 使 `isCurrentRequest()` 为假，静默关闭的旧流不会进 STREAM_INTERRUPTED 分支；用户停止的部分内容走既有 `isInterrupted` 保留（:352-370），语义分层正确。
- DoneEvent/ErrorEvent/NackEvent 均先置 `sawTerminalEvent`，不会与 STREAM_INTERRUPTED 双落。
- 分层注记（非缺陷）：网关 EOF-无-finish_reason 轮会下发 synthetic STOP done，mobile 因此永远不会对该类截断显示 STREAM_INTERRUPTED——该码只覆盖 socket 层静默断开。这与网关"契约锁"是同一枚硬币的两面，归入三轨矛盾段。

### 4. `mobile/test/widget/core_provider_keep_alive_test.dart`（wt464）+ `mobile/test/shared/no_network_http_overrides.dart` + auth 双测隔离

**verdict：成立，mock 未掩盖真缺陷。**
- FIX-159 处置：`SharedPreferences.setMockInitialValues` + `sharedPreferencesProvider.overrideWithValue` 只移除环境性 `UnimplementedError`（异步链 `warmUpConnection→authProvider→checkAuthStatus` 需要 prefs）；**被钉的产品语义（sessionBoundProviders 真清单失效 → disposeCount=1 + chat 态清空）保持真值未被钉空**——若真清单有回归，本测依然会红。
- `no_network_http_overrides.dart`：transport 层 HttpOverrides 全局禁网，失败形态取 `SocketException` 与"网关不在场"基线同形（provider 既有吞异常路径消化），`addTearDown` 恢复，无 pending timer。实测运行中日志出现 `Error: null http://10.0.2.2:8080/api/v1/user/settings`——即守卫成功拦下屏内未覆盖 provider 的真发尝试，6 文件 66 测全绿，证明守卫必要且有效。

### 5. `mobile/lib/core/services/evidence_resolve_service.dart`（FIX-157）+ `data_consistency_checker.dart` + `community_repository.dart` + `file_repository.dart`（FIX-145 mobile 面）

**verdict：成立。**
- 5 处去 `/api/v1` 字面前缀与 dio `baseUrl+path` 拼接语义一致；`community_repository.dart:1503` 附近与事实相反的 TODO 勘误属实（引擎自 initial commit 即服务该路由）。
- 我方独立同族扫描：`grep "api/v1" mobile/lib`（排除 gen/注释/ApiEndpoints）仅剩注释与 `_wsBaseUrl` 主机级拼接（WS base 不含路径前缀，合法）——**无漏网同病**。
- `dio_base_url_double_prefix_regression_test.dart`：真 dio + recording adapter，钉 4 族解析后完整 URL，非 mock 自说自话；`evidence_cards_test.dart` 两处 verify 改现值是产品侧已修（wt452）后的测试对齐，非弱化。

### 6. `mobile/lib/l10n/app_en.arb` / `app_zh.arb`（union 合并键完整性）

**verdict：成立。**
- `flutter gen-l10n` 零错误零警告；en/zh 各 **11589** 键，差集双向为空；arb 键与生成文件成员比对缺失 0。（重跑产生的生成文件 diff 为纯 dart_style 新版格式化，无键差，已还原不入库。）
- `chatInterrupted`（STREAM_INTERRUPTED 文案）en `app_en.arb:12701` / zh `app_zh.arb:9820` 双语在案，生成物同步。

### 7. 网关 Go 三道门

`go build ./...` + `go vet ./...` + `gofmt -l internal`（空）+ `go test ./...` **全绿**（handler 28.4s，含本窗新增测试）。gen/ 不入库，按惯例自主仓 `cp -RL` 后验证。

---

## Findings（新登记）

### V3-FIX-168（P2）引擎侧检测的截断轮绕过网关 FIX-155 缓存退出——截断部分文本进语义缓存 + 历史行无标注

- **位置**：`backend/gateway/internal/handler/chat_orchestrator_chatflow.go:794-796`（sawUpstreamFinishReason 判据）、`:988`（possiblyTruncated）、`:1018-1033`（标注+缓存退出）；对照 `backend/app/agents/standard_workflow.py:2078-2095`、`backend/app/orchestration/response_builder.py:994-999`。
- **机理**：wt466 引擎哨兵使 LLM-EOF 截断在引擎内转形为「error 帧（finish_reason=ERROR）+ 终帧（full_text=部分文本，STOP，metadata.generation_stream_truncated=true）」。网关判据 `FinishReason != NULL` 对 ERROR/STOP 均为真 → possiblyTruncated 恒假 → 部分文本照常 `SetExact` 入缓存（TTL 1h，`semantic_cache.go:15`），assistant 历史行无 truncated 键。网关全仓 0 处读取 `generation_stream_truncated`。
- **探针证据**（临时 Go 探针，miniredis + in-process gRPC mock + 真 WS 栈，已删未提交）：
  - 探针 A：mock 依上述形态收流后，miniredis 出现 `cache:text:user_probe-user_mode_standard_ctx_…:hello` = `"partial truncated answer"`；`chat:history:sess-probe-a` 的 assistant 行 JSON **无任何截断字段**。客户端帧序列：delta → error 帧 → full_text(STOP, generation_stream_truncated=true) → meta → synthetic done(STOP)。
- **危害**：当前因 V3-FIX-169（查询面死亡）暂无用户可见危害；一旦查询门被修复，同 user+scope+query 的后续轮将命中缓存，把截断部分文本当完整答案重投递——恰是 FIX-155 登记的危害本体，而 wt466 的"缓存退出"验证（单测面）未覆盖此形态。
- **建议**：chatflow 收流循环补 `if strings.EqualFold(resp.GetMetadata()["generation_stream_truncated"], "true") { sawEngineTruncation = true }`，并入 `possiblyTruncated` 判据（缓存退出 + saveExtra 截断标注）；与 V3-FIX-160 的持久化面统一裁决同批处理。

### V3-FIX-169（P2）网关语义缓存查询面死亡——两道无条件门使命中路径不可达，FIX-155 缓存退出空转

- **位置**：`backend/gateway/internal/handler/chat_orchestrator_chatflow.go:527`（shouldSkipCache）；门 ①`:480-487`（ensureChatExtraContext 无条件向 `input.ExtraContext` 写入 use_document_context/document_filter/conversation_settings ≥3 键后，`len(input.ExtraContext) > 0` 恒真）；门 ②`:374` 用户消息先存 → `:494-505` 历史加载已见该消息 → `sessionHasHistory` 对一切带 session_id 的轮恒真（与 :523-526 注释声明的"首轮可缓存"意图相反）。
- **探针证据**（同一 harness）：
  - 探针 B：预种同 scope+query 的缓存条目（`SetExact` 成功）后发首轮（带 session_id）→ 引擎照常被调用（hit 信道触发），客户端收到引擎新答案，`is_cache_hit:false`。
  - 探针 C：轮 1（带 session）写入缓存后，轮 2 以**空 session_id**（查询门理应开启的唯一形态）发同一问题 → 引擎再次被调用（第二次调用返回标记文本 "SECOND CALL DISTINCT ANSWER"，排除了缓存命中歧义）→ 缓存条目未被消费。
- **危害**：语义缓存读面为零收益（每轮必打引擎，成本/延迟优化失效，`is_cache_hit` 恒 false）；会话轮写入的死条目占 Redis 至 TTL（1h）；**使 V3-FIX-155 的缓存退出守卫当前空转**——其"截断文本不被重投递"效果纯靠查询面死亡这一巧合成立，结构上不成立（修复 169 即触发 168 的危害面）。此为窗前既有缺陷，非本窗引入；但 wt466 对缓存退出的验证声明应据此重新定界。
- **建议**：①把 :481-483 的无条件填充移出 `input.ExtraContext`（入局部 map 或在 scope 计算后再回写），还 `len(ExtraContext)>0` 以"调用方真实编排载荷"本义；②用户消息落库移到历史加载/缓存查询之后，或 `sessionHasHistory` 只统计 assistant 轮；③修复后为缓存命中面补端到端红测，并同步重验 V3-FIX-168 的缓存退出。

---

## V3-FIX-160 证据增补（不占新号，写实）

FIX-160 已登记"truncated 键无消费方"，本轮把"无消费方"做实到结构层（探针+代码链）：
- 写入的 `truncated` 键在**读取侧即被丢弃**：`service/chat_history.go:131-151` `ChatHistoryMessage` 结构无该字段 → 历史 API DTO（`handler/chat_history.go:20-41`）无该字段 → 网关持久化 SQL（`service/chat_history_persister.go:26-35`）只插 `(id, session_id, user_id, role, content, created_at, updated_at)`，无 metadata 列 → **连 DB 兜底行也不带该标注**。该键唯一存身之处是 Redis `chat:history:{sid}` 裸 JSON（尾 20 条、TTL 内）。
- 仓内已有活着的同义载体：`is_interrupted`（`ChatHistoryMessage` :150 有字段、mobile `chat_message_model.dart:157` / `chat_bubble.dart:1247` 全链消费）——建议 FIX-160 修复时对齐到该载体而非再造第三键。
- 探针 A 佐证 FIX-160 的另一半：gRPC 轨引擎检测截断轮的 assistant 行（网关写的这份）确无任何标注。

---

## 三轨矛盾写实段（FIX-160 背景，不修，只写实）

同一类「上游截断轮」在三条轨道的终态语义互相矛盾（wt466 修后现状）：

| 维度 | REST `/stream`（引擎面） | `/ws/chat` gRPC——引擎检测到截断（LLM-EOF，**主导形态**） | `/ws/chat` gRPC——网关侧 EOF-无-finish_reason（引擎崩溃/生成器早退） |
|---|---|---|---|
| 客户端所见 | done 帧 `completed=false` + `reason=upstream_stream_truncated`，显式中断 | error 帧（retryable）→ mobile failed 态；**但随后仍有 full_text(STOP)+meta+synthetic done(STOP)**，协议层"完整收尾" | 仅 synthetic done(STOP)，**无任何错误指示，客户端视作完整成功** |
| 本轮是否落历史 | 不落库（防部分文本冒充） | 引擎 `_finalize_turn_after_done` 落库无标注（FIX-160）+ 网关 saveMessage 落库无标注（探针 A 实锤）——双写均无标注 | 落库带 `truncated:true`（:1018-1020），但该键读取即被丢弃（见上）|
| 语义缓存 | 不涉及 | **部分文本被写入缓存**（探针 A；当前因 169 无人读取）| 退出缓存写入（FIX-155 本体）|
| 历史回放/重试观感 | 诚实中断 | 部分文本在历史中冒充完整回答；mobile 侧本轮 UI 丢弃部分文本（failed 语义），重载后却会出现这条"完整"助手消息 | 同左（更糟：连实时 UI 都是成功观感）|

矛盾的根：三条轨对"截断"的判定主体不同（REST=引擎哨兵；gRPC 网关=finish_reason 缺席；持久化=无人判定），且网关对引擎已给出的机器可读判据（`generation_stream_truncated` metadata）零消费。建议 FIX-160 裁决时以引擎哨兵为单一判定源，三轨统一消费该信号。

---

## 已验证清单（本人实际执行）

1. `cd backend/gateway && go build ./... && go vet ./... && gofmt -l internal`（空）+ `go test ./...` 全绿（gen 自主仓 cp -RL）。
2. `cd mobile && flutter test`（6 文件 66 例：chat_provider / core_provider_keep_alive / dio_base_url_double_prefix_regression / evidence_cards / login_screen_submit / register_screen_o3_submit）全绿；运行日志确认禁网守卫实际拦截真发请求。
3. `flutter gen-l10n` 零错误；en/zh 键数 11589=11589、双向差集空、arb↔生成物缺失 0。
4. 探针 A/B/C（临时 Go 测试，未提交）：截断部分文本入缓存实锤 / 预种缓存条目首轮仍打引擎 / 空 session 轮仍打引擎（二次调用标记文本排除歧义）。
5. `grep generation_stream_truncated backend/gateway` = 0 命中；`grep "'/api/v1/" mobile/lib` 同族扫描无漏网。
6. 引擎面交叉阅读：`standard_workflow.py` / `response_builder.py` / `orchestrator.py`（Aurora 终帧带 STOP）确认无误报截断回归。
7. 窗内测试全部为净增强；`evidence_cards_test.dart` verify 改值为产品修复后的对齐，非弱化断言。

## 范围与残留

- 本轮未复审 backend/app 纯 Python 面（wt448/454/456b/458/460/462/464 的引擎修复属其他审查线），仅按需交叉阅读与 chatflow 交互的引擎行为。
- V3-FIX-156（pre-pool 瓶颈）、V3-FIX-160（持久化面）保持 OPEN，本轮只做证据增补。
