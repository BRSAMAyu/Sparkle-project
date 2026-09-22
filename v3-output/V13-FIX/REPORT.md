# V13 修复报告：聊天历史回放中引用/来源摘要展开无内容

> Worker：V13 ｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt84`（分支 `wt84-v3`，基于 main@de613e34）｜ 日期：2026-09-22
> 交付物：`v3-output/V13-FIX/changes.patch`（4 文件，+532/−19）+ 本报告。未 commit / 未 push。

---

## ① 根因（一句话 + 证据）

**网关在持久化已完成轮次的 assistant 消息时，把引擎流式推送的 citations 事件整个丢弃了**——live 流里 citations 只被转发给客户端（这是 live 能展开的原因），但 `saveMessage` 的 extra 载荷里只有延迟统计 meta，没有任何 citation 数据；历史回放（`GET /chat/history/:id`，无论 Redis 快路径还是 DB fallback）拿到的消息体因此不含引用，mobile 的引用条与「来源摘要」托盘展开后无卡片。

证据链（file:line，均为 worktree 内绝对路径的相对表示）：

| 环节 | 位置 | 事实 |
|---|---|---|
| live 转发（正常） | `backend/gateway/internal/handler/chat_orchestrator_protocol.go`（`convertResponseToJSON` 的 `ChatResponse_Citations` 分支） | citations 事件被转成 `{type:"citations", citations:[...], metadata.ux_sources}` 推给客户端——仅此一次，转瞬即逝 |
| **断链点（根因）** | `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:986`（修复前） | 完成落库时 extra 仅含 `meta`（latency 统计）、`workflow_id`、`prompt_version`、`trace_id`、`response_id`；流循环中收到的 `resp.GetCitations()` 从未被留存 |
| Redis 快路径无引用 | `backend/gateway/internal/service/chat_history.go`（`SaveMessage` / `getMessagesFromRedis`） | 原样存取 JSON 载荷，载荷里没有就不会出现在回放里 |
| DB fallback 无富数据（既有架构性现状） | `backend/gateway/internal/service/chat_history.go:639-645` | gfix03 迁移已删除 `chat_messages.metadata`，手写 SQL 只 select 6 个基本列；注释明言「富元数据由引擎侧持久化管道负责」 |
| 引擎侧也不持久化引用 | `backend/app/orchestration/persistence_layer.py:43-49`（`_persist_assistant_message`） | 流式聊天落库只写 `user_id/session_id/role/content/model_name`；`chat_messages.actions` JSON 列存在但未被此路径使用 |
| mobile 解析面（本身无恙） | `mobile/lib/features/chat/data/models/chat_message_model.dart:396-431`（`ChatCitation.listFromMessage`） | 只从 `meta.citations`（rawMetadata）与 `widgets[source_summary].data.citations` 两个键取数——回放载荷里两个键都不存在，故为空 |

结论：**不是 mobile 解析分叉、不是 schema 缺列、不是 proto 形状分叉**，而是网关流循环→持久化之间的一处数据丢失。mobile 两个解析键在 live 路径早已验证可用（`chat_provider.dart` 的 `upsertSourceSummaryCitations` / `captureCitationMetadata`），因此修复只需让历史载荷携带与 live 相同形状的数据。

## ② 修复面（最小侵入：仅网关 handler 层，2 改 2 增）

| 文件 | 变更 | 行数 |
|---|---|---|
| `backend/gateway/internal/handler/chat_orchestrator_chatflow.go` | 流循环中捕获本轮 citations（`resp.GetCitations()`，最新非空为准）；两处 `saveMessage`（完成轮次 + 流中断部分保存）改经 `attachTurnCitationsToSave` 增强后再落库 | +21/−15 |
| `backend/gateway/internal/handler/chat_orchestrator_protocol.go` | 抽出 `citationsToMapList` 共享转换（live 转发与持久化同一形状）；新增 `attachTurnCitationsToSave`：把 `meta.citations` 与 `widgets=[{type:"source_summary",data:buildSourceSummary(...)}]` 注入保存载荷；meta 先拷贝再注入，**live meta 帧零改动** | +47/−14 |
| `backend/gateway/internal/handler/chat_citations_history_test.go` | 新增：红→绿回归测试 + HTTP DTO 契约测试（350 行） | +350 |
| `mobile/test/features/chat/data/models/chat_message_model_citation_replay_test.dart` | 新增：回放载荷解析契约测试（119 行） | +119 |

- 不改 proto（零再生成义务）、不改 DB schema（零 Alembic 迁移）、不改引擎、不改 mobile lib 代码、不引入新组件——纯数据链路修复，符合冲突面约束（U-01/Step 系列零接触）。
- 持久化形状 = live 轮次在 mobile 端已产出的同构数据（`meta.citations` + `source_summary` widget），两个消费面（`AssistantCitationStrip` 引用条、`AssistantMessageMetadataTray` 来源摘要托盘）无需任何改动即可在回放中渲染卡片。
- 无 citations 的轮次（绝大多数普通对话）：`attachTurnCitationsToSave` 是 no-op，载荷与修复前逐字节一致。

## ③ 测试：红→绿证明与统计

**红证（修复前）**：
- `TestChatOrchestrator_CitationsPersistedForHistoryReplay`（真 WS 拨号 → 真 chatflow → mock 引擎发 delta+citations+finish → 查历史存储）：FAIL，`assistant turn must be persisted with widgets`——精确复现 B-04「回放无引用」。同测试的 live 段（citations 帧转发）在红证运行中已通过，证明断链只在持久化侧。

**绿证（修复后）**：
- `TestChatOrchestrator_CitationsPersistedForHistoryReplay` PASS（0.03s）：断言 ① live citations 帧仍达客户端（红线）；② 持久化消息含 `meta.citations`（id/file_id 正确）；③ `widgets[source_summary].data` 含 `citations_available=true`、citations 列表非空、title/content 保全。
- `TestGetConversationHistory_ServesCitationsToMobile` PASS：含引用的历史载荷经 handler DTO 后 `meta.citations` 与 `widgets` 完整存活（HTTP 契约锁）。
- mobile `chat_message_model_citation_replay_test.dart` 4/4 PASS（`flutter test --concurrency=1`）：旧形状（仅延迟 meta）→ citations 为空（记录病症）；新形状 meta.citations → 引用条字段全恢复；source_summary widget → 托盘可展开；双源去重（meta 与 widget 同引用只渲染一枚 chip）。
- 既有契约回归：`chat_history_contract_test.go` 两个测试 PASS（mobile 契约字段与 null 形状不受影响）。

**全量回归**：
- 网关：`go test ./internal/handler/`（27.9s 全绿，含 live 全链路 `TestChatOrchestrator_WSFullChainE2E`、R2-GW-1 断连竞速、FIX-51~54 相关契约）；`./internal/service/`、`./internal/agent/`、`./internal/cqrs/...` 全绿；`go vet` 干净；改动文件 gofmt 干净。
- mobile：`flutter test test/features/chat/ --concurrency=1` → **153 过 / 2 败**。2 个失败均为**存量问题、与本次无关**（详见⑤）。

**测试环境备注**：worktree 为新检出，gitignored 的生成物缺失，已在本树内重新生成（未入库、不入 patch）：`buf generate --template buf.gen.yaml`（gateway `gen/`）与 `buf.gen.dart.yaml`（mobile `lib/gen/`，需 `$HOME/.pub-cache/bin` 在 PATH）。否则 gateway 测试无法编译、mobile 23 个测试文件因缺 `lib/gen/*.pb.dart` 编译失败——两者均为环境现象，非代码回归。

## ④ 红线面对照结果

| 红线 | 结果 | 证据 |
|---|---|---|
| live 引用展开行为保持 | ✅ | 回归测试显式断言 live citations 帧到达客户端；live meta 帧内容零变化（meta 拷贝后才注入 citations，注入只发生在保存载荷）；live 全链路 e2e 全绿 |
| 历史回放既有消息渲染不受影响 | ✅ | 无 citations 轮次的保存载荷与修复前逐字节一致（helper no-op）；既有历史契约测试（字段齐全性 + null 形状）双绿；mobile 端 lib 零改动 |
| gRPC/SSE 双通道核对 | ✅（网关侧单通道收敛） | 网关聊天只有 WS 一条流式通道，三种 responder（legacy JSON / envelope / protobuf）共用同一 `handleChatMessage` 流循环——citations 捕获点在 responder 分派之前，通道无关；`POST /chat`、`POST /chat/stream` REST 为直连引擎代理（proxyWithHeaders），其历史由引擎 `save_chat_message` 写 `actions` 列，不经本路径，维持现状（见⑤边界） |
| 引擎/网关分层边界 | ✅ | 只动网关 handler；无 AI 推理、无业务逻辑越界；schema/proto/SQLC 零触碰 |

## ⑤ 诚实申报与遗留

1. **跨 TTL / DB fallback 的历史仍无引用（未修，需另立项）**：Redis 快路径 TTL 30 分钟、只留最近 20 条；更早消息走 DB fallback，而 gfix03 起该路径就不返回任何富数据（无 widgets、无推理步骤，引用只是其中之一）。补齐需引擎把 citations 写入既有 `chat_messages.actions` JSON 列 + 网关 DB 读映射回 widgets——跨引擎/网关两个服务的写入路径改造，超出本卡「最小侵入面」，且 B-04 实测场景（会话内重进）完全落在本次已修复的快路径上。建议作为后续卡。
2. **citations 采集策略**：一轮多次 citations 事件时取「最新非空」而非合并。引擎当前实现（`standard_workflow.py` retrieval 节点单次发射）每轮至多一次，语义等价；若未来出现渐进式引用流，需改为累积+去重（mobile 端本就按 feedbackKey 去重，风险可控）。
3. **静态无法覆盖的边界（留给主会话的验证方案）**：实景「发送→杀 App→重进会话→点开来源摘要/引用 chip→出现卡片+摘要+打开文档按钮」需要模拟器实景回放。建议主会话验收时执行一次；API 级等价物（本测试的 WS 全链路 + DTO 契约 + mobile 解析契约）已三段全覆盖，风险点仅在 UI 装配层，而该层代码零改动。
4. **存量失败（非本次引入，已在树上存在）**：`chat_design_language_widgets_test.dart` 两例——①硬编码色扫描命中存量文件 `message_detail_view.dart`、`node_detail_sheet.dart`（该测试只扫 `lib/`，本次对 mobile lib 零改动，`git status` 可证）；②dark 模式 golden 像素 diff（环境字体渲染敏感）。另 `ws_e2e_roundtrip_test.go` 在 HEAD 上即有一处 gofmt 格式漂移（未触碰，按「不重构无关代码」约束不顺手修）。
5. **假设**：buildSourceSummary 的 i18n `evidence_summary` 在保存时按网关当前 locale 渲染并随载荷固化（live 的 ux_sources 亦如此，行为一致）；citations `score` float32→JSON number，mobile `doubleFor` 已兼容。

## ⑥ 收工核查声明

- [x] patch 可在 HEAD 干净克隆上 `git apply --check` 通过（`/tmp/v13-baseline` 验证后已删）
- [x] 未 commit / 未 push；worktree 改动 = 2 M + 2 新测试 + `v3-output/V13-FIX/`（patch+报告）
- [x] 零模拟器、零 docker、零 App 构建；验证全部为 pytest 级等价的 go test / flutter test（flutter test 串行 `--concurrency=1`）
- [x] 主仓只读未触碰；未复制 .env；测试无 env 依赖（miniredis/进程内 mock）
- [x] 生成物（`gateway/gen/`、`mobile/lib/gen/`、`.dart_tool`、build）均为 gitignored，不入库不入 patch
- [x] /tmp 自产文件已清理（v13-baseline）；无遗留独立端口进程
