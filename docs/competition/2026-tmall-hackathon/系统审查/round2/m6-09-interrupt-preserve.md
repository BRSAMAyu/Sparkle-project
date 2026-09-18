# M6-09「流式取消=中断保留」实现记录（round2 / 产品决策落地）

> 裁决来源：`../漏洞台账.md` 末节「2026-09-18 产品决策落定」——**打断时已生成内容保留在 UI 与历史（服务端截断保存已有，G5），气泡标「已中断」**。理由：内容消失=信任破坏；对齐主流 AI 伙伴（ChatGPT/Claude）语义。
> 基线：wt5（最新 main）+ 前任留存的 4 文件半成品（模型层字段/枚举/红测试）。

## 1. 前任进度审查与问题定位

前任留有 4 个已改文件（本轮全部验证后采纳）：

| 文件 | 内容 | 验证结论 |
|---|---|---|
| `mobile/lib/features/chat/data/models/chat_message_model.dart` + `.g.dart` | 新增 `isInterrupted` 字段（`is_interrupted`，`includeIfNull: false`）+ copyWith/序列化 | 正确，直接采纳 |
| `mobile/lib/features/chat/presentation/providers/chat_state.dart` | 新增 `ChatRunPhase.interrupted`（区别于 completed/cancelled/failed）并纳入 `isTerminal` | 正确，直接采纳 |
| `mobile/test/unit/chat_notifier_stream_test.dart` | 4 条红测试（新消息中断/手动停止/空气泡/JSON 往返） | 跑通确认红（2 失败 2 过） |

**「部分回复被移除」的确切点**（`chat_provider.dart`）：

1. `cancelActiveRun()` → `_invalidateActiveStreamState()` 直接把 `streamingContent` 清空；
2. 已生成全文 `accumulatedContent` 是 `sendMessage()` 闭包局部变量，取消路径无人读取；
3. 旧流随后在 `await for` 顶部因 `_streamGeneration` 失效 break，`finalizeRun()` 首行 `!isCurrentRequest()` 早退——**已收 chunk 就此全部丢弃**；
4. 附带缺陷：流式 UI 走 50ms `_Debouncer`，`cancelActiveRun` 原先直接 `_streamDebouncer.cancel()`，即使要取 state 也只能取到防抖窗口前的旧值。

## 2. 实现要点

### 2.1 取消路径保留（`chat_provider.dart`）

- `cancelActiveRun()` 新顺序：`_streamDebouncer.flushPending()`（先冲刷防抖增量，state 拿到完整已生成内容）→ `_preservePartialReplyAsInterrupted()`（非空则追加 `isInterrupted: true` 的助手消息，id 前缀 `ai_interrupted_`）→ `_invalidateActiveStreamState(phase: ChatRunPhase.interrupted)`。
- 冲刷安全性：`flushPending` 执行的是旧 run 调度的 `applyPending` 闭包，其内部 `isCurrentRequest()` 守卫在取消时刻仍为真（generation 自增发生在其后），故能同步落地；迟到事件因 generation 失效被拒，不会改写已保留内容、不会产生重复气泡。
- 空内容（尚无任何 chunk）不产生空气泡。
- 覆盖两条用户中断路径：`sendMessage` 内 `cancelActiveRun(reason: 'new_message')`（发新消息开新轮）与 ChatInput `onStop` 的 `cancelActiveRun(reason: 'user_stop')`；导航类调用（`new_session`/`switch_plan`/`history_switch`）随後整体替换 messages，保留动作无副作用且瞬间即被服务端历史覆盖。

### 2.2 防抖器（`chat_provider_wiring.dart`）

`_Debouncer` 记录 `_pendingAction` 并新增 `flushPending()`（执行并清空已调度动作）；`run`/`flush`/`cancel` 同步维护该引用。

### 2.3 「已中断」UI 标记（`chat_bubble.dart`）

气泡内 Column 尾部新增轻量标记：`Icons.stop_circle_outlined`（`DS.iconSizeXs`）+ `context.l10n.chatInterrupted`（`DS.captionStyle`/`DS.textTertiary`），仅 `chatMessage?.isInterrupted == true` 时渲染。全部走 design 令牌，不触碰 UI-TOKENS 棘轮基线。

### 2.4 l10n

`chatInterrupted`：zh=「已中断」/ en="Interrupted"。同步登记 `app_zh.arb`、`app_en.arb` 与三份已入库生成文件（`app_localizations*.dart`），与 `chatCompleted` 相邻。

### 2.5 历史持久化语义

- **会话内**：中断消息进入 `state.messages`，新消息开新轮后仍按 [用户旧消息 → 中断的部分回复 → 新用户消息 → 新回复] 顺序保留（红测试断言）。
- **跨会话持久**：依赖服务端截断保存（G5 已有，网关侧断开时截断入库）。客户端 `is_interrupted` 序列化字段保证本地 JSON 往返不丢标记。

## 3. 测试（红→绿）

`flutter test --concurrency=4 test/unit/chat_notifier_stream_test.dart`：

- 红（实现前）：2 失败——mid-stream 新消息与 user_stop 两条语义测试（内容被丢弃，`hasLength(0)`）；既有 4 条通过。
- 绿（实现后）：**8/8 通过**（4 既有 + 4 M6-09：内容保留+标记存在+新消息后旧内容仍在+空气泡防护+JSON 往返）。

回归：`chat_notifier_actions_test` / `chat_provider_test` ×2 / `chat_notifier_attachments_test`（65 过）、`chat_scroll_test` / `chat_history_sheet_regression_test` / `reasoning_visualization_test`（5 过）全绿。

静态检查：`dart analyze` 定向（provider/wiring/bubble/state/model/l10n）= 8 条 info，与 HEAD 基线逐条持平（stash 对照验证），**零 error、零 warning、零新增**。

## 4. 与 M6-R2-03（消息补拉）的交互——只记录不扩修

- 服务端重载历史（`loadConversationHistory`/分页补拉）返回的消息**不带** `is_interrupted` 标记（服务端 schema 无此列），中断气泡在重拉后将显示为普通助手消息——内容仍由 G5 截断保存保证，仅客户端标记丢失。
- 处置建议：M6-R2-03 补拉专项落地时，可由服务端消息表补 `is_interrupted` 列或按 `finish_reason` 推导；本轮不改网关/proto（超出移动端决策范围）。
- 另一已知边界：导航切换（switch_plan/history_switch）场景下保留的消息会被服务端历史整体替换，属预期（会话切换而非用户中断语义）。

## 5. 恢复说明（接手必读）

1. **本改动未 commit**（任务禁令）。全部改动已快照为 patch：
   ```bash
   # 在 wt5 仓库根目录应用（如工作树被还原后需要重放）：
   git apply docs/competition/2026-tmall-hackathon/系统审查/round2/m6-09-interrupt-preserve.patch
   ```
   patch 由 `git add -A && git diff --cached > <patch> && git reset` 生成，含全部 14 项（12 代码/测试文件 + 本文档 + 目录 README 登记）；patch 不含其自身。
2. **跑测试前需恢复 proto 生成产物**（`mobile/lib/gen/` 被 gitignore，worktree 缺失；本轮验证后已按磁盘纪律清除）：
   ```bash
   cp -R <主仓库>/mobile/lib/gen mobile/lib/gen   # 或在仓库根 make proto-gen
   cd mobile && flutter test --concurrency=4 test/unit/chat_notifier_stream_test.dart
   ```
3. 验证静态检查基线：`dart analyze` 定向 8 条 info 为存量（HEAD 同数），不应出现 error。
4. 后续接续点见 §4：M6-R2-03 补拉时补服务端标记链路。
