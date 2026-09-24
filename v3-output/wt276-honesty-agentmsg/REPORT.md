# wt276-honesty-agentmsg 卡报告（A 线·诚实性红线修复，S 级）

日期：2026-09-23 ｜ 分支：wt276-honesty-agentmsg（本地 1 commit `3433b263`，未 push）｜ 基点：d89c5af5

## ① 确证的失败路径（file:line，基点复核无误）

**主靶（私信侧，卡面 665-680）**：`mobile/lib/features/community/presentation/providers/community_agent_provider.dart`
- `PrivateAgentChatNotifier.sendAgentMessage` → `_persistPrivateAgentMessage`：`repository.sendPrivateMessage` 抛错被 `catch (_)` 吞掉，返回伪造的 `PrivateMessageInfo(id: 假 Uuid, isRead: true)` → UI 渲染为带"已读 done_all"的已送达消息，服务端无此记录，重启拉历史后凭空消失。**诚实性红线违规实锤。**
- 补充发现：该私有方法当前无 UI 调用方（私信屏走 composeDraft→输入框→普通发送，已是诚实通道），属 provider 公开 API 上的活体红线；`GroupAgentChatNotifier.sendAgentMessage`（`group_chat_screen.dart:804` 实时调用）内 `_persistGroupAgentMessage` 存在**同型** `catch (_)` 伪造 `MessageInfo`，且是用户实时可达路径——一并修复。

**修复前先摸清的既有诚实通道**（全部平移形制、未发明新视觉）：
- `PrivateChatNotifier.sendMessage`（community_provider.dart:2025-2108）：本地 pending 消息（`local_$nonce`、`isSending:true`）→ 成功替换服务器消息 / 失败 `hasError:true` + offline pending 队列。
- `ChatBubble._buildMessageStatus`：`PrivateMessageInfo.isSending`→转圈、`hasError`→红色 error 图标；群聊 AI 侧 `_DeliveryBadge`（failed 徽标 + 重试 action，chatDeliveryFailed/chatDeliveryRetry 文案）。
- 删除入口已存在：私信屏 agent 消息 `onRevoke → removeLocalDraft`。

## ② 改动清单（5 文件，+690/-98）

1. `community_agent_provider.dart`：
   - 私信 `sendAgentMessage`：先落本地 pending（`local_<uuid>`、`isRead:false`、`isSending:true`），成功→服务器消息替换；失败→`_markLocalMessageFailed`（`hasError:true` + `state.error`），**绝不伪造成功**。
   - 新增 `retryAgentMessage(messageId)`：失败消息原内容重新持久化（成功替换/再失败保持 failed）。
   - 删除 `catch (_)` 伪造返回：`_persistPrivateAgentMessage`、`_persistGroupAgentMessage` 两处全部移除。
   - 群聊 `sendAgentMessage`：持久化失败直接进既有 `agentState.error` 横幅（group_chat_screen.dart:667-677 已有渲染），不再追加幽灵消息。
2. `chat_bubble.dart`：状态行渲染条件 `isUser` → `isUser || _isAgent`（agent 气泡原本不渲染投递状态，失败会被静默）；`hasError` 且有重试回调时复用群聊侧 `_DeliveryBadge`（failed+retry 同形制），无回调保持原 error 图标。
3. `private_chat_screen.dart`：仅为 failed 的 agent 消息接 `onRetryDelivery → retryAgentMessage`（普通消息失败补偿仍走 offline pending 队列，避免双重发送）。
4. `test/unit/community_agent_provider_test.dart`：+7 个失败注入 notifier 测试。
5. `test/widget/agent_message_failed_state_test.dart`：新建，+3 个失败态可见性 widget 测试。

交付物：`v3-output/wt276-honesty-agentmsg/REPORT.md` + `changes.patch`（`git format-patch -1 --stdout`，924 行）。

## ③ 测试 / analyze 结果（原样）

定向单测（`flutter test test/unit/community_agent_provider_test.dart --concurrency=1`）：

```
00:00 +8: GroupAgentChatNotifier.sendAgentMessage honesty (wt276) persist failure surfaces error state with no phantom message
00:00 +9: GroupAgentChatNotifier.sendAgentMessage honesty (wt276) persist success appends the real server message
00:01 +10: All tests passed!
```

widget 测试（`flutter test test/widget/agent_message_failed_state_test.dart --concurrency=1`）：

```
00:00 +2: settled agent message never shows fake read receipt when unread
00:00 +3: All tests passed!
```

回归（ChatBubble 消费方 `j1_frontend_closure_test.dart`）：

```
00:01 +6: All tests passed!
```

analyze（本卡 5 文件定向；authored 文件零 issue，其余 2 个 lib 文件仅存量 info、`git diff -U0` 确认全部位于未改动行）：

```
Analyzing 3 items...
No issues found! (ran in 5.6s)
```

## ④ 资源峰值

- 无模拟器/Gradle/浏览器；仅单文件 flutter test ×3 次与分析器。测试全程执行错峰门：swap 空闲曾 778M/525M 低于 1.2G 即等待重试（含 wt277 在跑 flutter_tester 时避让），实际放行时 swap 空闲 1202M/1320M/1376M，load 峰值 4.99（<8），单文件单进程（--concurrency=1）。
- `buf generate` 仅补齐 Dart 产物（protoc-gen-dart 走 ~/.pub-cache/bin），未动 Go/Python。

## ⑤ 交接建议

1. **l10n 重排已按卡规还原**：`flutter pub get` 曾触发 `lib/l10n/app_localizations*.dart` 重排，已 `git checkout -- mobile/lib/l10n/`（卡规允许项）；后续会话若再跑 pub get 需同样处理，commit 前务必核对 `git status`。
2. **群聊侧 failed 气泡未做**：MessageInfo 无 isSending/hasError 瞬态字段（PrivateMessageInfo 才有），群聊 agent 发送失败现为"错误横幅 + 无幽灵消息"（诚实但不留痕）。若要 failed 气泡+重试，需给 MessageInfo 加非 HiveField 瞬态字段（不动 .g.dart adapter）+ GroupChatBubble 状态渲染，建议单开卡。
3. **`saveSelfVisibleDraft` 遗留观察项**：`PrivateAgentChatNotifier.saveSelfVisibleDraft`（同文件 543-578）本地自留草稿 `isRead:true` 且仅存内存——用户主动选择的"仅自己可见"语义，非发送伪造，本次未动；但重启即失且渲染已读回执，建议 A 线后续评估本地持久化或去 isRead 语义。
4. 私信屏普通消息失败路径（offline pending 队列）未接入徽标重试，属既有设计，勿混入本卡语义。
