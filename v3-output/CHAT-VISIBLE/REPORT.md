# CHAT-VISIBLE — 主聊天「发了但看不见」Blocker 修复报告（B-01，北极星第一会话断裂）

> Worker：C 纵队修复 Worker（北极星主链线）｜ worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt206`（基线 `7e17a068`）｜ 日期：2026-09-23
> 交付物：本报告 + `changes.patch`（6 M + 1 新测试，+205/−51）。未 commit / 未 push。零凭据。

---

## ① 断点定位（file:line + 证据）

**一句话根因：WS/gRPC 主链上没有任何组件写 `chat_sessions` 头行——引擎只写消息体，网关 persister（唯一的头写入者）默认关闭，于是 onboarding→chat 的第一个 session 永远「有消息无会话」。**

V13 复现链路逐环节走查（均为 worktree 内路径）：

| 环节 | 位置 | 事实 |
|---|---|---|
| 网关生成 session UUID | `backend/gateway/internal/handler/chat_orchestrator_chatflow.go:640-643` | 客户端未带 session_id 时网关 `uuid.New()`，经 gRPC `ChatRequest.SessionId` 下发——session id 本身没问题（V13 DB 里 `eec22e1e-…` 是合法 UUID） |
| 引擎持久化 USER 行 | `backend/app/orchestration/context_builder.py:2002`（`_persist_user_message`） | 只 add `ChatMessage`（flush 不 commit，提交权在 `agent_grpc_service.py:437` 流末统一提交）——**不建 session 头** |
| 引擎持久化 ASSISTANT 行 | `backend/app/orchestration/persistence_layer.py:52`（`_persist_assistant_message`） | 独立 session 自持提交，同样**只写 ChatMessage**——不建 session 头 |
| WS 路径唯一的头写入者（未运行） | `backend/gateway/internal/service/chat_history_persister.go:48-55,380-383` | `chatSessionUpsertSQL` 会 upsert `chat_sessions`，但它消费 `queue:persist:history`，而 `CHAT_PERSISTER_ENABLED` 默认 **false**（`backend/gateway/internal/config/config.go:562`；`cmd/server/setup.go:208-210` 关生产者，`cmd/server/main.go:98-104` 连消费者都不启动）——P2-D 立的规矩：engine 是 single authoritative chat writer |
| 断裂暴露面（网关 sessions 列表） | `backend/gateway/internal/service/chat_history.go:846`（`getRecentSessionsFromDB`，路由 `cmd/server/setup.go:579`） | `GET /api/v1/chat/sessions` **只读 `chat_sessions` 表** → 新用户 0 行 → 空列表 |
| 移动端重启不可见的直接原因 | `mobile/lib/features/chat/data/repositories/chat_repository.dart:293` | `getRecentConversations()` 打网关 `/chat/sessions` 拿不到 session → 没有 conversationId → `loadConversationHistory` 无从触发。历史本体读取（`getMessagesFromDB`，`chat_history.go:628-648`）按 `(session_id,user_id)` 查 `chat_messages`，其实能查到——**卡在入口拿不到 id** |

对照系（为什么只有新用户断）：REST 面 `POST /api/v1/chat`（`backend/app/api/v1/chat.py:1085-1097` `save_chat_message`）自带 `ChatSessionModel` get-or-create；guest 种子（`guest_seed_service.py:3691`）与 checkpoint nudge（`checkpoint_nudge_service.py:790-797`）也各建各的头。**唯独 WS 主链的首会话无人建头**——与 V13 取证（`chat_messages` 4 行 / `chat_sessions` 0 行，全表 253 行均属其他用户）完全吻合。

**复现方式选择**：纯代码走查 + **真实 sqlite 引擎单测复现**（未起最小栈）。理由：本断点是纯持久化数据形状问题（头行缺失），不涉 LLM/网络时序；引擎栈需 Postgres+Redis+LLM mock 全套，成本与信噪比不划算。红证测试 `backend/tests/core/test_b01_ws_turn_creates_chat_session_header.py` 在基线代码上 3 failed（头缺失断言）/ 1 passed（legacy label 跳过语义），修复后 4/4 绿——红→绿闭环。

## ② 修法

### 主修（后端：WS 路径幂等补建 session 头）

新增共享助手（`backend/app/orchestration/persistence_layer.py:29-43`）：

```python
async def ensure_chat_session_header(db, *, user_id, session_id) -> None:
    # get-or-create，与 REST save_chat_message 同构；零 UUID（legacy label 降级）跳过
```

两个落库点各插一处调用（幂等、非致命）：
1. `context_builder.py:2004-2019`（`_persist_user_message` 内、消息 add 之前）：与用户消息同事务，由 `agent_grpc_service` 流末统一提交。**这是 V13 场景（首条消息、用户中途杀 app 只落了 user 行）的关键保底**。
2. `persistence_layer.py:72-81`（`_persist_assistant_message` 独立 session 内）：与 assistant 行同事务提交——即使共享流事务回滚（该路径既有语义），头与消息也不出现孤儿态（自愈）。

设计要点：
- **幂等**：`db.get` 未命中才 add；已存在则推进 `last_message_at` + `is_active=True`（与 REST 先例逐字段同构）。同 session 第二轮不产生多头（测试锁定）。
- **零 UUID 守卫**：`context_builder._coerce_session_uuid` 对 legacy label（如 `df-d2-s1`）降级为 `UUID(int=0)`，该值跨用户共用主键且 sessions 查询本就排除之——跳过建头，保持既有语义（网关侧对 label 有自己的 uuid5 派生，见 `chat_history_persister.go:73-82`，不在本卡面内）。
- **失败降级**：头建失败（如并发同 session 首消息的极端竞态触发唯一键冲突）只吞掉告警，消息持久化不受影响；最坏退化 = 竞态败者的本轮头行由另一落库点/下一轮自愈补齐。
- **契约零破坏**：rb06「共享会话禁中途 commit」契约保持——两处调用都在既有 flush/commit 语义内（flush 由既有语句完成，头行随之落库）。
- **重启可见性自然恢复**：头行落库后，网关 `GetRecentSessions`（读 `chat_sessions`）→ 移动端会话列表/「上次聊到这里」恢复卡拿到 conversationId → `GET /chat/history/:id` → `getMessagesFromDB` 按 `(session_id,user_id)` 命中引擎已落库的消息行（`userOwnsSessionInDB` 双通道任一命中）。aurora-core 恢复面（`runtime_v1/service.py:2172` 读 ChatSession）随之可见。

### 次生面（mobile：无反馈窗口的防重复 + 防冲刷）

1. **in-flight 禁发**（`mobile/lib/features/chat/presentation/providers/chat_provider.dart:964-971`）：`sendMessage` 在 `state.isSending` 时由「cancelActiveRun 隐式顶替」改为**静默丢弃并早退**（早退点在 auth/guest 读取之前）。V13 实测的重复发送（同 prompt 2 条 USER + 2 条 LLM 回复重复计费）由此封死。注意这是**有意的行为契约变更**：原「新消息顶替在途流」语义（M6-09）改为只能经显式取消（输入条 onStop → `cancelActiveRun`）触发；3 个编码旧契约的测试已同卡更新（见③）。
2. **在途禁止历史回拉冲刷**（`mobile/.../providers/chat_notifier_history.dart:49-60`）：`loadConversationHistory` 开头对 `state.isSending` 早退。该方法原本会把 `isSending`、`streamingContent` 与乐观上屏的用户气泡整体替换成（通常尚未落库的）空服务端历史——正是「发送后 UI 零渲染」的移动端共因形状。计划切换不受影响：`switchPlanSession` 先 `cancelActiveRun` 置 `isSending=false` 再回拉。发送无反馈窗口本身由既有乐观上屏（`_beginRun` 即插用户气泡）+ 流式 UI 承担，不再被回拉冲掉，无需新增 loading 组件。
3. **UI 层既有防线确认**：输入条在 `hasActiveRun` 时已禁用（`chat_screen.dart:3017` `enabled: !chatState.hasActiveRun` + `chat_input.dart:503` `canSend`），叠加 1/2 后在途窗口不再意外解锁。

## ③ 冲突面声明

- **本卡触碰文件**：`backend/app/orchestration/{context_builder.py, persistence_layer.py}`（引擎）；`mobile/lib/features/chat/presentation/providers/{chat_provider.dart, chat_notifier_history.dart}` + 2 个测试文件（mobile）。
- **wt204（exam/sprint/prism + SPEC.md）**：零交集。未触碰 exam/sprint/prism 面，未动 SPEC.md，未动 `mobile/lib/core/design/`。
- **wt205（backend context/prompts/chat legacy，红旗 3）**：**未触碰 `chat.py`**——本卡对 `chat.py` 的 diff 为空，与 wt205 红旗 3（chat.py 面）无 hunk 关系。需要主会话留意的唯一潜在叠面：`context_builder.py`。本卡在该文件的 hunk **仅限 `_persist_user_message` 函数体内一处插入**（当前行 2004-2019），不触碰 `_build_full_context` 的上下文组装/提示词相关区域；若 wt205 也改 `context_builder.py`，只要其 hunk 不落在 `_persist_user_message` 内即可无冲突 apply（`git apply --3way` 下不同 hunk 自动合并）。
- **测试契约变更（有意）**：`chat_notifier_stream_test.dart` 3 例随 in-flight 禁发改写（见②.1）；`chat_provider_test.dart` +2 例新契约。引擎侧 `test_rb06_followup_no_midstream_commit.py::test_persist_assistant_message_uses_flush_not_commit` 存量失败（基线即败，与 NBP-1 独立 session 改造相关的旧断言残留），本卡未改其断言。

## ④ 诚实申报（验收等级）

- **UI 端到端未验**（V13 模拟器槽已收工，本卡为 LIGHT 卡不占 HEAVY）：「新号 onboarding→跳过→发消息→气泡/流式可见→杀 app 重启→消息可见」的真机旅程需主会话在下一轮 HEAVY 窗口复测。
- **API 级替代验证（已完成）**：
  1. 引擎持久化层（真实 sqlite 引擎，非 mock）：轮次落库后 `chat_sessions` 头存在 + `chat_messages` 行同 UUID + 幂等 + 零 UUID 守卫——4/4 绿（红→绿闭环）。
  2. 网关读路径为**既有未改代码**：`getRecentSessionsFromDB`/`getMessagesFromDB`/`userOwnsSessionInDB` 走查确认只依赖上述两表两键；`go test ./internal/service/ -run TestChatHistory` 与 `./internal/handler/ -run "TestChatOrchestrator|TestChatHistory|TestGetConversation"` 全绿（对比法：网关零改动）。
  3. 移动端 190 过 / 2 败，2 败为存量设计语言测试（基线复跑同败：硬编码色扫描命中存量文件 + dark golden 像素 diff，V13-FIX 报告⑤已在案）。
- **残留（不在本卡面）**：① legacy label session（非 UUID）依旧无头行——存量语义，网关 uuid5 派生面是独立课题；② `sendMessage` 早退为静默丢弃（无 toast）——与「单点最小面」取舍，若验收要求可闻反馈需另开小卡；③ 极端并发同 session 双首消息的竞态最坏丢一轮头行（另一落库点自愈），未做跨进程互斥；④ 29s onboarding（M-01）、访谈停摆（B-02）等 V13 其余缺陷不在本卡。

## ⑤ 收工核查

- [x] patch 可在 HEAD 干净克隆 apply（`git apply --check` 于 `/tmp/wt206-baseline` 克隆验证通过，已删）。
- [x] 未 commit / 未 push；worktree 改动 = 6 M + 1 新测试 + `v3-output/CHAT-VISIBLE/`（本报告 + patch）。
- [x] pytest 全程 `--timeout` + `SECRET_KEY=test` + `DATABASE_URL=sqlite`；定向文件级运行，未宽扫；生成物（`backend/app/gen`、`gateway/gen`、`mobile/lib/gen`）为构建必需的 gitignored 重生成，不入库不入 patch。
- [x] Go 验证用 `CGO_ENABLED=0`；flutter test `--concurrency=1`；无模拟器、无 docker、无独立端口进程残留。
- [x] 主仓只读未触碰；/tmp 自产文件已清理；swap 全程 >1.2G 未触熔断。
