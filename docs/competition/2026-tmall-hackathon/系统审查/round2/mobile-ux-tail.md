# 移动端 UX 收尾三件套（round2 / mobile-ux-tail）

> 基线：wt8 @ 6e9abd97（analyzer sweep 108→0 之后）。分域：community / chat / goal UI（与 wt3/wt5/wt6 无文件交集）。
> 配套：网关终态透传 b62b530b（`community-ws-502.md/.patch`）的客户端半场。

## 1. 客户端终态重试停止（社群 WS 挂账闭环）

**问题**：网关 b62b530b 已把上游终态拒绝（引擎 401/403/404）透传为
`{"error":"websocket_upstream_rejected","upstream_status":403,"retryable":false}`
（拨号超时→504、拒连→502 保持瞬态语义），但客户端仍把一切连接失败当瞬态：
`CommunityWebSocketService` onDone→`_scheduleGroupReconnect`，且 `connectToGroup`
每次入口复位 `_groupReconnectAttempts=0`——退避计数永远归零，等价无限重连；
`GroupChatNotifier._handleConnectionError` 对 403/404 同样按 `_maxRetries=5`
指数退避。round1 故障窗口的 ×15 风暴正是两边（服务 ×10 + 通知器 ×5）叠加放大。

### 1.1 红测（先红）

`test/features/community/data/services/community_websocket_service_test.dart`
新增 4 条（`terminal connection failures (M-3 client-side retry stop)` 组）：

- **403 拒帧零重试**（任务要求的核心红测）：本地 `HttpServer` 对每个 WS 升级
  请求返回 403 + 网关同构拒帧 JSON，统计收到的请求数。断言等待 700ms（足够
  旧实现跑完 6 档 ×40ms 退避）后 **requestCount == 1**（零后续重试）、
  终态 `WsConnectionState.failed`、`groupFailureReason` 非空且含 `403`。
  旧代码实测：`onError→onDone→reconnect` 计数无法封顶，连打 N 个请求 → 红。
- personal 通道 401 同构验证（requestCount == 1 + failed + reason 含 `401`）。
- `isTerminalCommunityWsFailure` 分类器：401/403/404 握手错误串、网关 JSON、
  `retryable: false`、4401/4403/4404 close code → true；`Connection refused`、
  502/504 → false（瞬态必须继续重试）。
- `isTerminalCommunityWsFrame` 带内拒帧分类：`retryable:false` / `upstream_status`
  401/403/404 / error 类型帧 → true；`retryable:true` 与普通消息帧 → false。

### 1.2 实现（绿）

`community_websocket_service.dart`：

- 顶层 `bool isTerminalCommunityWsFailure(Object? error)`：识别
  `websocket_upstream_rejected` 标记、`"retryable":false`、
  `HTTP status code: 40x`（dart:io `WebSocketException.toString()` 实测格式：
  `WebSocketException: Connection to '…' was not upgraded to websocket, HTTP status code: 403`）、
  `upstream_status":40x`、close code 4401/4403/4404。瞬态（refused/502/504）不误伤。
- 顶层 `bool isTerminalCommunityWsFrame(Map frame)`：带内（已升级 socket）拒帧判定。
- 终态路径 `_failGroupPermanently/_failPersonalPermanently`：置位终态标记 +
  `groupFailureReason`/`personalFailureReason` 对外暴露 → 取消重连定时器 →
  清 `_currentGroupId`/channel/subscription → 状态钉死 `failed`。
  `_handleGroupDone/_handlePersonalDone`、`_schedule*Reconnect`、100ms connected
  门控全部带终态守卫；重新连接的唯一入口是显式 `connectToGroup/connectToPersonal`
  （入口复位终态标记）。
- 新增测试注入 `wsBaseUrlOverride`（默认仍 `ApiConstants.wsBaseUrl`）。
- `channel.ready.catchError` 消费握手失败（错误本体仍走 stream onError 分类），
  堵住未处理异步异常泄漏（与 `core/services/websocket_service.dart` 同款模式）。

`community_provider.dart`（`GroupChatNotifier`）：

- `_handleConnectionError` 入口短路：终态已发生 → 任何自动重连入口直接 return。
- 403/404/`retryable:false`（`isTerminalCommunityWsFailure` 命中）→ 立即
  `_retryCount=_maxRetries`、`hasTerminalConnectionFailure=true`、
  `connectionFailureReason=error.toString()`，并重发消息列表通知 UI（与 `setQuote`
  相同的 notify 模式）。**401 语义仍走既有"刷新一次令牌→失败即 logout"的有界
  路径**（凭证轮换一次不属风暴，行为保持不变）；`manualReconnect()` 清终态标记，
  用户显式重试始终可用。

`group_chat_screen.dart`（surfaced 明确错误）：

- 消息列表下方新增与 `agentState.error` 同款的轻量横幅：终态失败时显示
  `communityChatConnectionLost`（"实时连接已被服务器拒绝，自动重连已停止"）+
  `communityChatReconnect`（"重新连接"）按钮（调 `manualReconnect`）。全部
  design 令牌（`DS.error/DS.fontSizeSm/DS.spacing*`），不触碰 UI-TOKENS 棘轮。
- l10n：`app_zh.arb`/`app_en.arb` 各 +2 key，`flutter gen-l10n` 重新生成
  `app_localizations*.dart`。

### 1.3 红绿证据

红（实现前）：编译失败（`wsBaseUrlOverride`/分类器不存在）+ 旧代码 403 场景
`[WS] Scheduling group reconnect … (attempt 1)` 连打请求，`requestCount` 断言失败。
绿：`flutter test test/features/community --concurrency=4` 全绿，日志可见
`[WS] Group terminal failure (no retry): … HTTP status code: 403`，requestCount=1。

## 2. N-7 继续键 UX 旁路（goal 向导 Entry Wire）

**问题**：`GoalCreationWizardScreen` 第 0 步（意图输入）底部继续键恒禁用
（`_primaryActionEnabled` 对 `_intentAnalysis == null` 一律 `return false`），
用户必须点输入卡内的「让我先看看你的情况」——单路径，违反双手拇指习惯
（键盘弹出时卡内按钮可能被遮挡，底部按钮看得见却点不得）。

### 2.1 红测（先红）

`test/features/goal/presentation/goal_creation_wizard_screen_test.dart`
新增 4 条（`N-7 底部继续键 UX 旁路` 组）。红状态下 2 条失败（正是旁路本体）：

- 「文本非空时点亮继续键，点击走与输入卡提交同一分析路径」：输入
  『通过高数考试』后断言底部 `FilledButton('继续').onPressed != null`（旧码 null→红）；
  点底部继续键后断言 `_RecordingDisabledIntentService.analyzeCalls == 1` 且回退
  选择器（『学术』）可见——证明旁路复用同一 Entry Wire 分析路径而非跳步。
- 「分析进行中继续键禁用，确认卡出现后不抢确认卡的路径」：actionable 桩返回
  `exam_rescue`，底部键提交后确认卡（『高数急救计划』）出现、底部键回到禁用
  （旧码分析都触发不了→红）。
- 空文本 / 纯空白文本两条：`onPressed == null` 恒成立（守护性断言，红绿同过）。

### 2.2 实现（绿）

`goal_creation_wizard_screen.dart`：

- `initState` 注册 `_intentController.addListener` → `setState`（底部键随输入
  实时点亮/熄灭）；`dispose` 先 `removeListener`（cascade 消 analyzer info）。
- `_primaryActionEnabled`：`_step == 0 && _intentAnalysis == null` 时改为
  `_intentController.text.trim().isNotEmpty`；`_analyzingIntent` 由函数头部的
  既有守卫覆盖（分析中禁用）；actionable 确认卡仍禁用（卡内 chips/action rows
  主导，不抢道）。
- `_next()`：`_step == 0 && _intentAnalysis == null` 时 `await _runIntentAnalysis()`
  ——与卡内提交完全同一路径（含 kill-switch 回退播种 title/motivation、
  `_seedLegacyFromAnalysis` 预填），而不是跳到 step 1。

绿：goal 套件 5/5（含原有端到端向导用例——旧「点卡内按钮」路径无回归）。

## 3. chat_bubble.dart 巨石拆分预研（L1 P2-12，3,692 行——只出方案，V3 收录）

> 现状：`mobile/lib/features/chat/presentation/widgets/chat_bubble.dart`
> 3,692 行（chat/presentation/widgets 目录 39,658 行的第一巨石，第二大是
> action_card.dart 3,858 行，本方案的方法论可直接复用）。7 个消费方：
> chat_screen / group_chat_screen / private_chat_screen / simulation_screen /
> focus_agent_sheet / task_chat_panel / thread_sheet。

### 3.1 结构地图（按行号段）

| 行段 | 内容 | 归属 |
|---|---|---|
| 1–52 | 50 条 import，横跨 chat/community/plan/report/simulation/task/theater/user 8 个 feature | 耦合面证据 |
| 54–72 | `_defaultTransparencyPreferences`、`ChatBubbleDeliveryStatus` enum | 常量/枚举 |
| 73–115 | `ChatBubble` ConsumerStatefulWidget；**`message` 字段是 `Object` 动态三型**（ChatMessageModel / PrivateMessageInfo / MessageInfo） | 公共 API |
| 116–336 | `_ChatBubbleState`：类型试探 getter 群（`_isUser/_isAgent/_isRevoked/_content/_createdAt/_widgets…`，全是 `is X as X` 强转链） | 模型适配层缺失 |
| 173–220 | 入场动画 AnimationController（200/220ms、CurvedAnimation×2） | 动画 |
| 339–390 | 单击/双击（爱心）→ 消息详情页 push | 交互 |
| 392–552 | `_showContextMenu` 长按菜单 sheet（复制/举报/反馈/撤回…） | 交互 |
| 553–841 | `_showPureModeAccessorySheet` 纯模式附件 sheet（theater/simulation/report 预览+深链，~290 行） | 交互 |
| 842–1310 | `build()` ~470 行：watch 纯模式+透明度 providers、解包 `agentCollaboration` 六种 preview、组装气泡主体 | 组合根 |
| 1312–1890 | 附件簇：`_buildAccessoryDisclosure`、`_buildAccessoryCluster`（~280 行）、`_getActionLabel` + **20+ case 的 action 类型大 switch（1455–1580）**——与后端 `card_protocol/` 的契约面（已知债务台账提示动它先看台账） | 附件/协议 |
| 1891–2168 | inline prompt 流（`_continueInlinePrompt`、prompt 预览） | 附件 |
| 2169–2408 | theater/simulation/report 预览卡 + `_buildTimingBadge` | 预览卡 |
| 2409–2519 | 回应反馈行/chips + **static `_responseFeedbackSelections`（≤200 条的进程级记忆）** | 反馈 |
| 2520–2674 | 引用区、撤回占位、消息状态、离线投递状态 | 底栏 |
| 2675–2928 | 头像、爱心动画、`_confirmGeneratedTasks`（task provider 依赖） | 底栏/副作用 |
| 2912–3145 | 分享判定/adopt/资源提取/分享卡点按（community share 仓库依赖） | 分享域 |
| 3153–3692 | 5 个私有叶子 widget：`_DeliveryBadge`、`_InsightLinkCard`、`_InlinePromptAction`、`_AccessoryPreviewPage/Shell`、`_CollaborationSignatureCard` | 可直接平移 |

### 3.2 目标分层与状态提升

目录形态（strangler，公共 API 不动）：`chat/presentation/chat_bubble/` 一族 +
`chat_bubble.dart` 原路径保留为 barrel（7 个消费方 import 零改动）。

```
chat_bubble.dart                      # facade：ChatBubble + build 组合（目标 ≤400 行）
chat_bubble_message_view.dart         # BubbleMessageView 值类型：三型强转收敛为唯一 casts 区
chat_bubble_entry_animation.dart      # 入场动画（State 的 mixin 或独立 controller holder）
chat_bubble_interactions.dart         # 单击/双击/长按 + context menu sheet + pure-mode sheet
chat_bubble_accessories.dart          # 附件簇 + action 类型 switch → Map<String, Builder> 注册表
chat_bubble_preview_cards.dart        # theater/simulation/report 预览卡 + AccessoryPreviewShell/Page
chat_bubble_feedback.dart             # 回应反馈行/chips + 选择记忆 → Riverpod 化
chat_bubble_status_footer.dart        # 引用/撤回占位/投递状态/DeliveryBadge/TimingBadge/头像/爱心
chat_bubble_share.dart                # 分享判定/adopt/资源提取
chat_bubble_collaboration.dart        # InsightLinkCard/CollaborationSignatureCard/inline prompt
```

状态提升决策：

1. **`BubbleMessageView`（核心）**：把 336 行前的动态三型 getter 群收敛为一个
   不可变视图值（`isUser/isAgent/isRevoked/content/createdAt/widgets/responseId…`），
   widget 树只消费视图值。这是唯一的"模型适配层"，也让 community 侧的
   agent 判定谓词（`isCommunityAgentMessage` 等）只在一处被引用。
2. **`_responseFeedbackSelections` static Map** → `responseFeedbackSelectionProvider`
   （**keepAlive/autoDispose: false**——现有语义是进程级存活，用 autoDispose 会
   丢记忆，属于行为变更禁区）。
3. **`_showHeart/_isPressed`** 留在 State（纯瞬态动画状态，提升反而增加重建面）。
4. **`_messageHeightState`** 属于列表层关注点：迁移时改为由消费方（chat_screen 的
   滚动控制器域）注入，气泡本身无状态持有。
5. build() 内解包的 `agentCollaboration` 六 preview → `BubbleAgentCollaborationView`
   值类型，在 `chat_bubble_message_view.dart` 一次解包。

### 3.3 文件切分图（迁移前后）

```
迁移前（3692 行单文件）                迁移后
┌──────────────────────────┐          chat_bubble.dart (facade ≤400)
│ ChatBubble + State 3040行 │   ──►    ├─ message_view      (~150)
│ build 470 / sheets 490   │          ├─ entry_animation   (~80)
│ switch 20+case 125行     │          ├─ interactions      (~600: 2 sheets 为主)
│ 5 私有叶子 540行          │          ├─ accessories       (~700: 注册表化)
└──────────────────────────┘          ├─ preview_cards      (~350)
                                      ├─ feedback           (~250)
                                      ├─ status_footer      (~450)
                                      ├─ share              (~350)
                                      ├─ collaboration      (~550)
                                      └─ 9 文件 + barrel，单文件全部 <800 行
```

### 3.4 迁移步骤（每步独立可验证、可回滚）

0. **金样基线先行**：现测试仅 5 个文件引用 ChatBubble 且多为间接；拆分前先给
   关键变体补 golden/结构测试——user/assistant、streaming、revoked、带引用、
   带附件 action、aurora 多消息、分享卡、纯模式。无金样不动刀。
1. 平移 5 个私有叶子 widget（3153–3692）→ collaboration/preview_cards/status_footer。
   零行为风险，验证 `flutter test` + analyze 即可。
2. 抽 `BubbleMessageView`，getter 群逐个替换（每 PR 一个 cluster），消费点从
   `_isUser` 改读 `view.isUser`。
3. 抽 sheets（context menu / pure-mode）为顶层函数，显式传参
   （`BubbleMessageView` + 回调表），注意 sheet 内 `context.read` 的 context 归属。
4. `build()` 拆三段：`BubbleChrome`（行布局/头像/气泡壳）、`BubbleBody`
   （markdown+citations+附件）、`BubbleFooter`（引用/状态/时间戳）。
5. action 大 switch → `Map<String, WidgetBuilder(WidgetPayload)>` 注册表
   （1455–1580 的 20+ case 变 O(1) 查表；此步触碰 card_protocol 契约面，
   按台账要求先复核 `KNOWN_CODE_DEBT_LEDGER.md`）。
6. 反馈选择记忆 Riverpod 化（keepAlive 语义保持）。
7. 收尾：facade 只剩组合与公共 API；跑 `bash scripts/run_all_rule_guards.sh`。

### 3.5 风险清单

| 风险 | 说明 | 缓解 |
|---|---|---|
| 三型 union 无公共接口 | ChatMessageModel/PrivateMessageInfo/MessageInfo 靠强转试探；agent 判定谓词跨 community feature | BubbleMessageView 单一 casts 区先行，步骤 2 逐 getter 灰度 |
| 进程级反馈记忆 | static Map 生命周期=App；Provider 化错用 autoDispose 即行为变更 | 显式 keepAlive + 步骤 6 单独 PR + 专项测试 |
| 入场动画重放 | AnimationController 在 initState 订阅 message 变化，搬动时机不当会重播/不播 | 步骤 1 前先录 golden；controller 留在 State，仅抽 mixin |
| sheet 的 context 归属 | `_showPureModeAccessorySheet` 内深链 push 依赖根 navigator context | 顶层函数化时显式传 `NavigatorState` |
| card_protocol 契约 | 20+ case switch 是后端卡片协议的客户端映射，台账已标注已知债务 | 注册表化不改任何 case 语义；前后 diff 逐 case 对照 |
| 棘轮/守卫 | 移动代码会改变每文件 lint/token 计数 | 每步跑 UI-TOKENS 棘轮 + analyze gate；只许降不许升 |
| 体量邻近巨石 | action_card.dart（3,858 行）同构问题 | 本方案步骤 1/4/5 的手法直接复用，V3 单列 |

工作量估计：步骤 0–1 约 1 人日，2–4 各 0.5–1 人日，5–6 各 0.5 人日；
全程不阻塞功能开发（strangler，facade 冻结）。

## 4. 验证与纪律

- 测试：`flutter test test/features/community test/features/goal --concurrency=4`
  → **38/38 绿**（含 8 条新增：WS 服务 4 + 向导 4）。
- dart analyze：改动 6 文件 **error=0, warning=0**；全仓 non-vendored
  error+warning = 0（与 6e9abd97 sweep 基线一致）；INFO 按码对比 6e9abd97
  **零新增**（dart fix 顺手净降 OMIT_LOCAL_VARIABLE_TYPES −2、
  PREFER_CONST_DECLARATIONS −1、PREFER_FINAL_LOCALS −2、
  PREFER_FUNCTION_DECLARATIONS_OVER_VARIABLES −2、REQUIRE_TRAILING_COMMAS −1）。
- UI-TOKENS 棘轮：`PASS — ratchet holds at color=275/275, fontSize=727/727`。
- 磁盘：结束时清 `build/`、`.dart_tool/`、`lib/gen/`（本次 cp -RL 的工作副本）。
- 禁 commit/push：全部产出在补丁 `mobile-ux-tail.patch`。

## 5. V3 挂账（不在本轮做）

1. `action_card.dart`（3,858 行）按 §3 方法论单列拆分。
2. `CommunityWebSocketService` 的 `connectToGroup` 入口复位
   `_groupReconnectAttempts` 的"无限退避"缺陷已随终态守卫止血，但瞬态失败的
   退避计数仍会在显式重连时归零——改为"按连接存活时长门控刷新"（core
   WebSocketService 的 M6-R2-02 模式）更彻底。
3. 终态失败目前仅 group chat 挂横幅；friends/私聊侧共用
   `communityEventsStreamProvider` 的断线 surfaced 可复用同一横幅组件（V3 统一）。
