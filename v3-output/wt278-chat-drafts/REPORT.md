# wt278-chat-drafts · N46 单机草稿持久化（A-SPEC8A 会话连续性改造 #1）

> 2026-09-22 ｜ worktree **wt278-chat-drafts**（分支同名，本地 commit 不 push）｜ M 级
> 依据：`v3-output/A-SPEC8A-SESSION-CONT/REPORT.md` 改造 #1 / N46 条目——三个聊天输入面草稿零持久化（chat_screen.dart:188/:1072、private_chat_screen.dart:41/:61、community_chat_input.dart 组件内态），对标 Telegram「离开会话必须保留未发送草稿」官方客户端义务（单机版，跨设备同步按 N46 边界明确不做）。

## 一、持久层选型与三入口接入点

**选型：shared_preferences（仓库既有依赖 ^2.2.2，零新增依赖）**，形制对齐同层既有范式 `AgentSessionStore`（features/chat/data/services/agent_session_store.dart：构造注入 SharedPreferences + 逐键读写 + `SharedPreferences.setMockInitialValues` 可测）。未用 Hive/Isar（Hive 每会话一 box 的 ChatCacheService 形制对 100 条 LRU 过重；Isar 需要模型生成链路）。Provider 挂既有 `sharedPreferencesProvider`（main.dart override 注入），无新初始化时序。

**键口径**：`chat_draft:<scope>:<conversationId>:<userId>`，scope ∈ {chat, privateChat, groupChat}；conversationId 未生成（首条未发出）落 `_new` 兜底键；userId=登录 id→guestId→'anon' 三级回退（对齐 agent_session 的 userId 口径）。

| 入口 | 文件 | controller 形制（改造前） | 会话键 | 接入点 |
|---|---|---|---|---|
| 主 AI 聊天 | mobile/lib/features/chat/presentation/screens/chat_screen.dart | `_draftController` 屏级纯内存（:188 声明/:1072 区 dispose） | chatProvider.conversationId（未定落 `_new`） | initState 加 listener+首次归属同步；listenManual conversationId 变化做「归还旧会话草稿→载入新会话草稿」；dispose flush |
| 私聊 | mobile/lib/features/chat/presentation/screens/private_chat_screen.dart | `_composerController` 屏级纯内存（:41/:61） | widget.friendId | initState 加 listener+恢复（composer 非空不覆盖）；dispose flush |
| 群聊（第三入口） | mobile/lib/features/chat/presentation/screens/group_chat_screen.dart | CommunityChatInput 组件内态（改造后屏级 controller 下传） | widget.groupId | 新建 `_composerController` 下传输入组件；initState listener+恢复；dispose flush |

**发送成功清除**：两输入组件（ChatInput / CommunityChatInput）发送后 `_controller.clear()` → 屏侧 listener 收到空文本 → `scheduleSave('')` 即删草稿（ChatInput 的 web 回灌守护路径同覆盖）。主聊天离线队列先落盘后上网，发送即清草稿不丢消息。
**会话删除清除**：friends_screen `_handleDeleteFriend` 成功后清 `friendInfo.friend.id`（好友用户 id，非 friendshipId——草稿按 privateChatProvider(friendId) 同键）私聊草稿；group_detail_screen `leaveGroup()` 成功后清该群草稿；两者 try/catch 不阻塞删除主流程。

## 二、容量上界（防无限膨胀）

- **单草稿 ≤4096 UTF-8 字节**：超界截断保头部，回退扫描码点边界（不截出非法 UTF-8）。
- **总量 ≤100 条 LRU**：索引存 `chat_draft:@lru_index` StringList；save 与 load 均刷新位次；溢出淘汰最久未用；读-改-写经实例内 Future 链串行防交错。

## 三、边界（防过度施工，按 N46）

- 仅单机；跨设备草稿同步不做（N51 观察行维持）。
- 语音实时转写中间态（community_chat_input `_voiceDraftText`）**不持久化**：录音中途离开语义即放弃（麦克风已断，无可「续写」的对象）；已 commit 进 composer 的语音文本随 composer 草稿同等待遇。如需覆盖留待后续卡（需输入组件新增会话键透传）。
- 主聊天屏内会话切换采用「归属切换」语义（旧文本归还旧会话、载入新会话草稿），startNewSession 后 composer 清空属预期（旧草稿仍归旧会话，切回可恢复）。

## 四、改动清单

| 文件 | 改动 |
|---|---|
| mobile/lib/features/chat/data/services/chat_draft_store.dart | **新增** ChatDraftStore：save/load/clear/scheduleSave(500ms 防抖)/flush/cancelScheduled + 字节截断 + LRU |
| mobile/lib/features/chat/presentation/providers/chat_draft_store_provider.dart | **新增** chatDraftStoreProvider + resolveChatDraftUserId（登录→guest→anon） |
| mobile/lib/features/chat/presentation/screens/chat_screen.dart | N46 草稿归属字段 + `_handleDraftTextChanged` + `_initChatDraftSync` + `_syncDraftWithConversation`（conversationId listenManual）+ dispose flush + 2 imports |
| mobile/lib/features/chat/presentation/screens/private_chat_screen.dart | listener + `_restoreComposerDraft` + dispose flush + 2 imports |
| mobile/lib/features/chat/presentation/screens/group_chat_screen.dart | 新建屏级 controller 下传 CommunityChatInput + listener + 恢复 + dispose flush + 2 imports |
| mobile/lib/features/community/presentation/screens/friends_screen.dart | 删好友成功后清私聊草稿 + 2 imports |
| mobile/lib/features/community/presentation/screens/group_detail_screen.dart | 退群成功后清群聊草稿 + 2 imports |
| mobile/test/unit/chat_draft_store_test.dart | **新增** 四路径 9 用例（形制对齐 agent_session_store_test） |

## 五、测试与验证

- `test/unit/chat_draft_store_test.dart`：**11 用例全 PASS**（保存/防抖合并、跨实例恢复、`_new` 键与 userId 隔离、clear/空文本 scheduleSave/flush 空清除、4KB CJK 码点边界截断、ASCII 截断、100 条 LRU 溢出、load 触碰免淘汰）。
- analyze：定向 `flutter analyze` 5 个改动屏与 HEAD 基线克隆（git clone 到 /tmp 对比）**逐条 diff 零新增**；3 个新文件 0 issue（过程中 7 条新增 lint 已修毕）。
- l10n：pub get 触发的 gen-l10n 重排已 `git checkout -- mobile/lib/l10n/` 还原，未入库。

## 六、收工核查

- [x] 主仓与其它 worktree 只读未动；无 push/stash/reset/clean（l10n 纯格式还原除外）
- [x] 分支本地 commit（不 push）；v3-output/wt278-chat-drafts/（本 REPORT.md + changes.patch）
- [x] /tmp 基线克隆与分析中间文件已清理；worktree 内无 build 产物
- [x] 测试错峰：swap 门禁核验后单文件单进程执行
